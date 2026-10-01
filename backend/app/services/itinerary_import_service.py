import json
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import CurrentUser
from app.core.errors import not_found, validation_error
from app.core.observability import EventName, log_event
from app.models import (
    BookModel,
    DestinationModel,
    ItineraryImportJobModel,
    ItineraryImportRecordModel,
    ItineraryModel,
    POIModel,
)
from app.schemas.domain import Itinerary, ItineraryDay, ItineraryStop
from app.schemas.itinerary_import import (
    IMPORT_CONTRACT_VERSION,
    ImportPreviewSummary,
    ImportRecordPreview,
    ImportVerificationRecord,
    ImportVerificationResponse,
    ItineraryImportBatchV1,
    ItineraryImportJobResponse,
    ItineraryImportRecordV1,
)
from app.services import database_repository


MAX_IMPORT_BYTES = 2_000_000


class ItineraryImportService:
    def preview(
        self,
        db: Session,
        batch: ItineraryImportBatchV1,
        *,
        admin: CurrentUser,
    ) -> ItineraryImportJobResponse:
        artifact_json = batch.model_dump(mode="json")
        sensitive_paths = _sensitive_metadata_paths(artifact_json)
        if sensitive_paths:
            raise validation_error(
                "Import artifact metadata contains sensitive-looking key(s): "
                + ", ".join(sensitive_paths)
            )
        artifact_bytes = _canonical_json(artifact_json).encode("utf-8")
        if len(artifact_bytes) > MAX_IMPORT_BYTES:
            raise validation_error(
                f"Import artifact exceeds the {MAX_IMPORT_BYTES}-byte Gate B limit."
            )

        artifact_hash = sha256(artifact_bytes).hexdigest()
        now = _now()
        job = ItineraryImportJobModel(
            id=f"import-{uuid4().hex}",
            batch_identity=batch.batchIdentity,
            contract_version=IMPORT_CONTRACT_VERSION,
            initiated_by_user_id=admin.id,
            dry_run=True,
            status="previewed",
            artifact_hash=artifact_hash,
            artifact_json=artifact_json,
            preview_json={},
            persisted_itinerary_ids=[],
            published_itinerary_ids=[],
            error_json={},
            created_at=now,
            updated_at=now,
        )

        previews = [
            self._preview_record(db, job.id, batch, record, admin=admin)
            for record in batch.records
        ]
        summary = _preview_summary(previews)
        job.preview_json = summary.model_dump(mode="json")
        db.add(job)
        db.commit()
        log_event(
            EventName.ADMIN_ACTION_ATTEMPTED,
            category="ingestion",
            action="itinerary_import_preview",
            allowed=True,
            job_id=job.id,
            batch_identity=job.batch_identity,
            dry_run=True,
            total_records=summary.totalRecords,
            valid_records=summary.validRecords,
            invalid_records=summary.invalidRecords,
            conflict_records=summary.conflicts,
        )
        return _job_response(job)

    def get_job(
        self,
        db: Session,
        job_id: str,
    ) -> ItineraryImportJobResponse:
        return _job_response(_get_job(db, job_id))

    def list_jobs(self, db: Session) -> list[ItineraryImportJobResponse]:
        rows = db.scalars(
            select(ItineraryImportJobModel).order_by(
                ItineraryImportJobModel.created_at,
                ItineraryImportJobModel.id,
            )
        ).all()
        return [_job_response(row) for row in rows]

    def confirm(
        self,
        db: Session,
        job_id: str,
        *,
        admin: CurrentUser,
    ) -> ItineraryImportJobResponse:
        job = _get_job(db, job_id)
        if job.status not in {"previewed", "persistence_failed"}:
            raise validation_error(
                f"Import job '{job.id}' cannot be confirmed from status '{job.status}'."
            )

        batch = ItineraryImportBatchV1.model_validate(job.artifact_json)
        previews = [
            self._preview_record(db, job.id, batch, record, admin=admin)
            for record in batch.records
        ]
        summary = _preview_summary(previews)
        job.preview_json = summary.model_dump(mode="json")
        job.updated_at = _now()

        blocking = [
            item
            for item in previews
            if item.outcome in {"invalid", "conflict"}
        ]
        if blocking:
            job.status = "previewed"
            db.commit()
            raise validation_error(
                "Import confirmation rejected because preview contains invalid records or conflicts."
            )

        job.status = "persisting"
        job.dry_run = False
        db.commit()

        persisted_ids = list(job.persisted_itinerary_ids or [])
        failures: list[dict[str, str]] = []
        for record, preview in zip(batch.records, previews, strict=True):
            if preview.outcome == "already_imported":
                if preview.projectedItineraryId and preview.projectedItineraryId not in persisted_ids:
                    persisted_ids.append(preview.projectedItineraryId)
                continue

            try:
                itinerary = self._build_itinerary(
                    db,
                    job,
                    batch,
                    record,
                    preview,
                    admin=admin,
                )
                audit_record = ItineraryImportRecordModel(
                    id=f"import-record-{uuid4().hex}",
                    job_id=job.id,
                    source_identity=record.sourceIdentity,
                    content_hash=preview.contentHash,
                    contract_version=IMPORT_CONTRACT_VERSION,
                    itinerary_id=itinerary.id,
                    publication_intent=record.publicationIntent,
                    source_attribution=record.sourceAttribution,
                    status="persisted",
                    created_at=_now(),
                )
                db.add(audit_record)
                job.persisted_itinerary_ids = [
                    *persisted_ids,
                    itinerary.id,
                ]
                job.updated_at = _now()
                database_repository.save_itinerary(db, itinerary)
                persisted_ids = list(job.persisted_itinerary_ids)
            except Exception as exc:
                db.rollback()
                failures.append(
                    {
                        "sourceIdentity": record.sourceIdentity,
                        "errorType": exc.__class__.__name__,
                    }
                )
                break

        job = _get_job(db, job.id)
        job.persisted_itinerary_ids = persisted_ids
        job.updated_at = _now()
        if failures:
            job.status = "persistence_failed"
            job.error_json = {"persistenceFailures": failures}
        else:
            job.status = "persisted"
            job.completed_at = job.updated_at
            job.error_json = {}
        db.commit()
        log_event(
            EventName.ADMIN_ACTION_ATTEMPTED,
            category="ingestion",
            action="itinerary_import_confirm",
            allowed=not failures,
            job_id=job.id,
            batch_identity=job.batch_identity,
            persisted_count=len(job.persisted_itinerary_ids or []),
            failure_count=len(failures),
            status=job.status,
        )
        return _job_response(job)

    def verify(
        self,
        db: Session,
        job_id: str,
    ) -> ImportVerificationResponse:
        job = _get_job(db, job_id)
        batch = ItineraryImportBatchV1.model_validate(job.artifact_json)

        verification: list[ImportVerificationRecord] = []
        for source_record in batch.records:
            record = db.scalar(
                select(ItineraryImportRecordModel).where(
                    ItineraryImportRecordModel.source_identity == source_record.sourceIdentity
                )
            )
            expected_itinerary_id = (
                record.itinerary_id
                if record is not None
                else source_record.itinerary.id
                or _deterministic_itinerary_id(source_record.sourceIdentity)
            )
            itinerary = db.get(ItineraryModel, expected_itinerary_id)
            provenance = itinerary.provenance_metadata if itinerary is not None else {}
            publication_state = (
                "published"
                if itinerary is not None and itinerary.is_public and itinerary.visibility == "public"
                else "draft"
            )
            provenance_matches = bool(
                record is not None
                and itinerary is not None
                and provenance.get("stableSourceIdentity") == record.source_identity
                and provenance.get("sourceContentHash") == record.content_hash
                and provenance.get("importJobId") == record.job_id
            )
            verification.append(
                ImportVerificationRecord(
                    sourceIdentity=source_record.sourceIdentity,
                    itineraryId=expected_itinerary_id,
                    exists=itinerary is not None,
                    provenanceMatches=provenance_matches,
                    publicationState=publication_state,
                )
            )

        verified = bool(verification) and all(
            item.exists and item.provenanceMatches for item in verification
        )
        log_event(
            EventName.ADMIN_ACTION_ATTEMPTED,
            category="ingestion",
            action="itinerary_import_verify",
            allowed=True,
            job_id=job.id,
            batch_identity=job.batch_identity,
            record_count=len(verification),
            verified=verified,
        )
        return ImportVerificationResponse(
            jobId=job.id,
            verified=verified,
            records=verification,
        )

    def publish(
        self,
        db: Session,
        job_id: str,
        *,
        admin: CurrentUser,
    ) -> ItineraryImportJobResponse:
        job = _get_job(db, job_id)
        if job.status not in {"persisted", "published", "publication_failed"}:
            raise validation_error(
                f"Import job '{job.id}' cannot publish from status '{job.status}'."
            )

        batch = ItineraryImportBatchV1.model_validate(job.artifact_json)
        source_identities = [
            record.sourceIdentity
            for record in batch.records
            if record.publicationIntent == "publish"
        ]
        if not source_identities:
            raise validation_error(
                f"Import job '{job.id}' has no records eligible for publication."
            )
        records = [
            db.scalar(
                select(ItineraryImportRecordModel).where(
                    ItineraryImportRecordModel.source_identity == source_identity
                )
            )
            for source_identity in source_identities
        ]
        missing_source_identities = [
            source_identity
            for source_identity, record in zip(source_identities, records, strict=True)
            if record is None
        ]
        if missing_source_identities:
            raise validation_error(
                "Cannot publish before persistence for source identity(s): "
                + ", ".join(missing_source_identities)
            )

        published_ids = list(job.published_itinerary_ids or [])
        failures: list[dict[str, str]] = []
        for record in records:
            assert record is not None
            if record.itinerary_id in published_ids:
                continue
            try:
                itinerary = database_repository.get_itinerary(db, record.itinerary_id)
                if itinerary is None:
                    raise ValueError(f"Persisted itinerary not found: {record.itinerary_id}")
                published = itinerary.model_copy(
                    update={
                        "isPublic": True,
                        "visibility": "public",
                        "updatedAt": _now(),
                        "createdByMode": "admin",
                        "createdByUserId": admin.id,
                    },
                    deep=True,
                )
                record.status = "published"
                record.published_at = _now()
                job.published_itinerary_ids = [*published_ids, record.itinerary_id]
                job.updated_at = _now()
                database_repository.save_itinerary(db, published)
                published_ids = list(job.published_itinerary_ids)
            except Exception as exc:
                db.rollback()
                failures.append(
                    {
                        "sourceIdentity": record.source_identity,
                        "errorType": exc.__class__.__name__,
                    }
                )
                break

        job = _get_job(db, job.id)
        job.published_itinerary_ids = published_ids
        job.updated_at = _now()
        if failures:
            job.status = "publication_failed"
            job.error_json = {"publicationFailures": failures}
        else:
            job.status = "published"
            job.completed_at = job.updated_at
            job.error_json = {}
        db.commit()
        log_event(
            EventName.ADMIN_ACTION_ATTEMPTED,
            category="ingestion",
            action="itinerary_import_publish",
            allowed=not failures,
            job_id=job.id,
            batch_identity=job.batch_identity,
            published_count=len(job.published_itinerary_ids or []),
            failure_count=len(failures),
            status=job.status,
        )
        return _job_response(job)

    def _preview_record(
        self,
        db: Session,
        job_id: str,
        batch: ItineraryImportBatchV1,
        record: ItineraryImportRecordV1,
        *,
        admin: CurrentUser,
    ) -> ImportRecordPreview:
        content_hash = _record_hash(record)
        projected_id = record.itinerary.id or _deterministic_itinerary_id(record.sourceIdentity)
        existing_record = db.scalar(
            select(ItineraryImportRecordModel).where(
                ItineraryImportRecordModel.source_identity == record.sourceIdentity
            )
        )
        if existing_record is not None:
            outcome = (
                "already_imported"
                if existing_record.content_hash == content_hash
                else "conflict"
            )
            return ImportRecordPreview(
                sourceIdentity=record.sourceIdentity,
                outcome=outcome,
                contentHash=content_hash,
                projectedItineraryId=existing_record.itinerary_id,
                publicationIntent=record.publicationIntent,
                errors=(
                    []
                    if outcome == "already_imported"
                    else [
                        "Stable source identity already exists with different content."
                    ]
                ),
            )

        errors: list[str] = []
        warnings: list[str] = []
        existing_itinerary = db.get(ItineraryModel, projected_id)
        if existing_itinerary is not None:
            errors.append(
                f"Projected itinerary identity already exists without matching import provenance: {projected_id}"
            )

        try:
            itinerary = self._build_itinerary(
                db,
                _preview_job(job_id, batch, admin),
                batch,
                record,
                ImportRecordPreview(
                    sourceIdentity=record.sourceIdentity,
                    outcome="new",
                    contentHash=content_hash,
                    projectedItineraryId=projected_id,
                    publicationIntent=record.publicationIntent,
                ),
                admin=admin,
            )
            database_repository.validate_itinerary_access_invariants(db, itinerary)
            database_repository.validate_itinerary_persistence_references(db, itinerary)
        except Exception as exc:
            errors.append(str(exc))

        if record.book.semantics == "external_snapshot":
            if not record.book.sourceType:
                warnings.append("External book sourceType defaulted to 'external'.")
            if not record.book.providerId:
                warnings.append("External book has no providerId; stable source identity remains authoritative.")

        return ImportRecordPreview(
            sourceIdentity=record.sourceIdentity,
            outcome="invalid" if errors else "new",
            contentHash=content_hash,
            projectedItineraryId=projected_id,
            publicationIntent=record.publicationIntent,
            warnings=warnings,
            errors=errors,
        )

    def _build_itinerary(
        self,
        db: Session,
        job: ItineraryImportJobModel,
        batch: ItineraryImportBatchV1,
        record: ItineraryImportRecordV1,
        preview: ImportRecordPreview,
        *,
        admin: CurrentUser,
    ) -> Itinerary:
        destination = db.get(DestinationModel, record.destination.id)
        if destination is None:
            raise ValueError(f"Unknown itinerary destination: {record.destination.id}")

        book = db.scalars(
            select(BookModel)
            .where(BookModel.id == record.book.id)
            .options(selectinload(BookModel.destinations))
        ).first()
        if record.book.semantics == "repository":
            if book is None:
                raise ValueError(f"Unknown repository book: {record.book.id}")
            if record.destination.id not in {item.id for item in book.destinations}:
                raise ValueError(
                    f"Repository book '{record.book.id}' is not linked to destination "
                    f"'{record.destination.id}'."
                )
        elif book is not None:
            raise ValueError(
                f"External snapshot identity conflicts with repository book: {record.book.id}"
            )

        if len(record.itinerary.days) != record.itinerary.durationDays:
            raise ValueError("Itinerary day count must equal durationDays.")
        day_numbers = [day.dayNumber for day in record.itinerary.days]
        if sorted(day_numbers) != list(range(1, record.itinerary.durationDays + 1)):
            raise ValueError("Itinerary day numbers must be contiguous starting at 1.")

        itinerary_id = preview.projectedItineraryId or _deterministic_itinerary_id(
            record.sourceIdentity
        )
        days: list[ItineraryDay] = []
        for day in record.itinerary.days:
            orders = [stop.order for stop in day.stops]
            if sorted(orders) != list(range(1, len(day.stops) + 1)):
                raise ValueError(
                    f"Stop order for day {day.dayNumber} must be contiguous starting at 1."
                )
            stops: list[ItineraryStop] = []
            for stop in day.stops:
                poi = db.scalars(
                    select(POIModel)
                    .where(POIModel.id == stop.poiId)
                    .options(selectinload(POIModel.books))
                ).first()
                if poi is None:
                    raise ValueError(f"Unknown itinerary POI: {stop.poiId}")
                if poi.destination_id != record.destination.id:
                    raise ValueError(
                        f"POI '{stop.poiId}' is outside destination '{record.destination.id}'."
                    )
                if book is not None and record.book.id not in {
                    item.id for item in poi.books
                }:
                    raise ValueError(
                        f"POI '{stop.poiId}' is not linked to repository book '{record.book.id}'."
                    )
                stops.append(
                    ItineraryStop(
                        id=f"{itinerary_id}-d{day.dayNumber}-s{stop.order}",
                        poi=database_repository.poi_from_model(poi),
                        order=stop.order,
                        title=stop.title,
                        narrativeNote=stop.narrativeNote,
                        logisticsNote=stop.logisticsNote,
                        estimatedStartTime=stop.estimatedStartTime,
                        estimatedEndTime=stop.estimatedEndTime,
                    )
                )
            days.append(
                ItineraryDay(
                    id=f"{itinerary_id}-day-{day.dayNumber}",
                    dayNumber=day.dayNumber,
                    title=day.title,
                    summary=day.summary,
                    stops=stops,
                    estimatedDistanceKm=day.estimatedDistanceKm,
                    estimatedDurationHours=day.estimatedDurationHours,
                    routeGeometry=[],
                    routingProviderMetadata=None,
                    routingWarnings=[],
                )
            )

        now = _now()
        book_source_type = (
            "repository"
            if record.book.semantics == "repository"
            else (record.book.sourceType or "external")
        )
        provenance = {
            "artifactSource": "import",
            "contractVersion": IMPORT_CONTRACT_VERSION,
            "stableSourceIdentity": record.sourceIdentity,
            "sourceContentHash": preview.contentHash,
            "importBatchIdentity": batch.batchIdentity,
            "importJobId": job.id,
            "sourceAttribution": record.sourceAttribution,
            "batchSource": batch.source.model_dump(mode="json"),
        }
        return Itinerary(
            id=itinerary_id,
            destinationId=record.destination.id,
            bookId=record.book.id,
            title=record.itinerary.title,
            summary=record.itinerary.summary,
            durationDays=record.itinerary.durationDays,
            transportationMode=record.itinerary.transportationMode,
            days=days,
            isPublic=False,
            ownerUserId=None,
            visibility="unlisted",
            generatedFrom="imported",
            sourceType="corpus_import",
            sourceItineraryId=None,
            createdByMode="admin",
            createdByUserId=admin.id,
            subscriberOnly=False,
            adaptationNotes=[],
            createdAt=now,
            updatedAt=now,
            providerName=None,
            providerType="corpus_import",
            providerVersion=IMPORT_CONTRACT_VERSION,
            providerRequestId=job.id,
            generatedByService="itinerary_import_service",
            confidenceScore=None,
            provenanceMetadata=provenance,
            bookTitle=book.title if book is not None else record.book.title,
            bookAuthor=book.author if book is not None else record.book.author,
            bookDescription=book.description if book is not None else record.book.description,
            bookPublicationYear=(
                book.publication_year if book is not None else record.book.publicationYear
            ),
            bookPublicDomain=(
                book.public_domain if book is not None else record.book.publicDomain
            ),
            bookThemes=book.themes if book is not None else record.book.themes,
            bookCoverUrl=book.cover_url if book is not None else record.book.coverUrl,
            bookSourceType=book_source_type,
            bookProviderId=None if book is not None else record.book.providerId,
            bookProvenanceMetadata=(
                {}
                if book is not None
                else {
                    **record.book.provenanceMetadata,
                    "importContractVersion": IMPORT_CONTRACT_VERSION,
                }
            ),
            destinationName=destination.name,
            destinationCountry=destination.country,
            destinationRegion=destination.region,
            destinationDescription=destination.description,
            destinationLatitude=destination.latitude,
            destinationLongitude=destination.longitude,
            destinationImageUrl=destination.image_url,
            destinationSourceType="repository",
            destinationProviderId=None,
            destinationProvenanceMetadata={},
        )


def _preview_summary(records: list[ImportRecordPreview]) -> ImportPreviewSummary:
    return ImportPreviewSummary(
        totalRecords=len(records),
        validRecords=sum(item.outcome in {"new", "already_imported"} for item in records),
        invalidRecords=sum(item.outcome == "invalid" for item in records),
        newRecords=sum(item.outcome == "new" for item in records),
        alreadyImportedRecords=sum(item.outcome == "already_imported" for item in records),
        conflicts=sum(item.outcome == "conflict" for item in records),
        warnings=sum(len(item.warnings) for item in records),
        projectedMutations=sum(item.outcome == "new" for item in records),
        publicationIntentCount=sum(
            item.publicationIntent == "publish" for item in records
        ),
        records=records,
    )


def _job_response(job: ItineraryImportJobModel) -> ItineraryImportJobResponse:
    preview = (
        ImportPreviewSummary.model_validate(job.preview_json)
        if job.preview_json
        else None
    )
    return ItineraryImportJobResponse(
        id=job.id,
        batchIdentity=job.batch_identity,
        contractVersion=job.contract_version,
        initiatedByUserId=job.initiated_by_user_id,
        dryRun=job.dry_run,
        status=job.status,
        artifactHash=job.artifact_hash,
        preview=preview,
        persistedItineraryIds=job.persisted_itinerary_ids or [],
        publishedItineraryIds=job.published_itinerary_ids or [],
        errors=job.error_json or {},
        createdAt=job.created_at,
        updatedAt=job.updated_at,
        completedAt=job.completed_at,
    )


def _get_job(db: Session, job_id: str) -> ItineraryImportJobModel:
    job = db.get(ItineraryImportJobModel, job_id)
    if job is None:
        raise not_found("itinerary import job", job_id)
    return job


def _record_hash(record: ItineraryImportRecordV1) -> str:
    return sha256(
        _canonical_json(record.model_dump(mode="json")).encode("utf-8")
    ).hexdigest()


def _canonical_json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _deterministic_itinerary_id(source_identity: str) -> str:
    digest = sha256(source_identity.encode("utf-8")).hexdigest()[:24]
    return f"it-import-{digest}"


def _preview_job(
    job_id: str,
    batch: ItineraryImportBatchV1,
    admin: CurrentUser,
) -> ItineraryImportJobModel:
    now = _now()
    return ItineraryImportJobModel(
        id=job_id,
        batch_identity=batch.batchIdentity,
        contract_version=IMPORT_CONTRACT_VERSION,
        initiated_by_user_id=admin.id,
        dry_run=True,
        status="previewed",
        artifact_hash="preview",
        artifact_json={},
        preview_json={},
        persisted_itinerary_ids=[],
        published_itinerary_ids=[],
        error_json={},
        created_at=now,
        updated_at=now,
    )


_SENSITIVE_KEY_PARTS = {
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
}


def _sensitive_metadata_paths(value: object, path: str = "$") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            child_path = f"{path}.{key_text}"
            if any(part in lowered for part in _SENSITIVE_KEY_PARTS):
                matches.append(child_path)
                continue
            matches.extend(_sensitive_metadata_paths(item, child_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            matches.extend(_sensitive_metadata_paths(item, f"{path}[{index}]"))
    return matches


def _now() -> str:
    return datetime.now(UTC).isoformat()


itinerary_import_service = ItineraryImportService()
