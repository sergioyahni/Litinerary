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
from app.schemas.domain import Itinerary, ItineraryDay, ItineraryStop, POI
from app.schemas.itinerary_import import (
    IMPORT_CONTRACT_VERSION,
    ImportDestinationV1,
    ImportPOIV1,
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
        summary = _preview_summary(db, batch, previews)
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
            projected_catalog_mutations=summary.projectedCatalogMutations,
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
        summary = _preview_summary(db, batch, previews)
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
        try:
            _persist_catalog(db, batch)
        except Exception as exc:
            db.rollback()
            job = _get_job(db, job.id)
            job.status = "persistence_failed"
            job.updated_at = _now()
            job.error_json = {
                "persistenceFailures": [
                    {"sourceIdentity": "catalog", "errorType": exc.__class__.__name__}
                ]
            }
            db.commit()
            return _job_response(job)

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
                    allow_projected_catalog=False,
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
        content_hash = _record_hash(batch, record)
        projected_id = record.itinerary.id or _deterministic_itinerary_id(record.sourceIdentity)
        errors = _catalog_errors_for_record(db, batch, record)
        if errors:
            return ImportRecordPreview(
                sourceIdentity=record.sourceIdentity,
                outcome="invalid",
                contentHash=content_hash,
                projectedItineraryId=projected_id,
                publicationIntent=record.publicationIntent,
                errors=errors,
            )

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
                allow_projected_catalog=True,
            )
            database_repository.validate_itinerary_access_invariants(db, itinerary)
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
        allow_projected_catalog: bool,
    ) -> Itinerary:
        destination = db.get(DestinationModel, record.destination.id)
        if destination is None and not allow_projected_catalog:
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
        poi_catalog = {poi.id: poi for poi in batch.pois}
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
                if poi is not None:
                    if poi.destination_id != record.destination.id:
                        raise ValueError(
                            f"POI '{stop.poiId}' is outside destination '{record.destination.id}'."
                        )
                    poi_book_ids = {item.id for item in poi.books}
                    if book is not None and record.book.id not in poi_book_ids:
                        raise ValueError(
                            f"POI '{stop.poiId}' is not linked to repository book '{record.book.id}'."
                        )
                    poi_schema = database_repository.poi_from_model(poi)
                else:
                    imported_poi = poi_catalog.get(stop.poiId)
                    if imported_poi is None or not allow_projected_catalog:
                        raise ValueError(f"Unknown itinerary POI: {stop.poiId}")
                    if imported_poi.destinationId != record.destination.id:
                        raise ValueError(
                            f"POI '{stop.poiId}' is outside destination '{record.destination.id}'."
                        )
                    if book is not None and record.book.id not in imported_poi.repositoryBookIds:
                        raise ValueError(
                            f"POI '{stop.poiId}' is not linked to repository book '{record.book.id}'."
                        )
                    poi_schema = _poi_schema_from_import(imported_poi)
                stops.append(
                    ItineraryStop(
                        id=f"{itinerary_id}-d{day.dayNumber}-s{stop.order}",
                        poi=poi_schema,
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
        destination_name = destination.name if destination is not None else record.destination.name
        destination_country = destination.country if destination is not None else record.destination.country
        destination_region = destination.region if destination is not None else record.destination.region
        destination_description = (
            destination.description if destination is not None else record.destination.description
        )
        destination_latitude = (
            destination.latitude if destination is not None else record.destination.latitude
        )
        destination_longitude = (
            destination.longitude if destination is not None else record.destination.longitude
        )
        destination_image_url = (
            destination.image_url if destination is not None else record.destination.imageUrl
        )
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
            destinationName=destination_name,
            destinationCountry=destination_country,
            destinationRegion=destination_region,
            destinationDescription=destination_description,
            destinationLatitude=destination_latitude,
            destinationLongitude=destination_longitude,
            destinationImageUrl=destination_image_url,
            destinationSourceType="repository",
            destinationProviderId=None,
            destinationProvenanceMetadata={},
        )


def _catalog_errors_for_record(
    db: Session,
    batch: ItineraryImportBatchV1,
    record: ItineraryImportRecordV1,
) -> list[str]:
    errors: list[str] = []
    destination = db.get(DestinationModel, record.destination.id)
    if destination is not None and not _destination_matches_import(destination, record.destination):
        errors.append(
            f"Canonical destination '{record.destination.id}' differs from the import snapshot."
        )

    book = db.scalars(
        select(BookModel)
        .where(BookModel.id == record.book.id)
        .options(selectinload(BookModel.destinations))
    ).first()
    if record.book.semantics == "repository":
        if book is None:
            errors.append(f"Unknown repository book: {record.book.id}")
        elif record.destination.id not in {item.id for item in book.destinations}:
            errors.append(
                f"Repository book '{record.book.id}' is not linked to destination '{record.destination.id}'."
            )
    elif book is not None:
        errors.append(
            f"External snapshot identity conflicts with repository book: {record.book.id}"
        )

    poi_catalog = {poi.id: poi for poi in batch.pois}
    referenced_poi_ids = {
        stop.poiId
        for day in record.itinerary.days
        for stop in day.stops
    }
    for poi_id in sorted(referenced_poi_ids):
        imported_poi = poi_catalog.get(poi_id)
        poi = db.scalars(
            select(POIModel)
            .where(POIModel.id == poi_id)
            .options(selectinload(POIModel.books))
        ).first()
        if poi is not None:
            if poi.destination_id != record.destination.id:
                errors.append(
                    f"POI '{poi_id}' is outside destination '{record.destination.id}'."
                )
            if imported_poi is not None and not _poi_matches_import(poi, imported_poi):
                errors.append(f"Canonical POI '{poi_id}' differs from the import catalog snapshot.")
            existing_book_ids = {item.id for item in poi.books}
            if imported_poi is not None and not set(imported_poi.repositoryBookIds).issubset(existing_book_ids):
                errors.append(
                    f"Canonical POI '{poi_id}' is missing one or more declared repository book links."
                )
            if record.book.semantics == "repository" and record.book.id not in existing_book_ids:
                errors.append(
                    f"POI '{poi_id}' is not linked to repository book '{record.book.id}'."
                )
            continue

        if imported_poi is None:
            errors.append(f"Unknown itinerary POI: {poi_id}")
            continue
        if imported_poi.destinationId != record.destination.id:
            errors.append(
                f"POI '{poi_id}' is outside destination '{record.destination.id}'."
            )
        if record.book.semantics == "repository" and record.book.id not in imported_poi.repositoryBookIds:
            errors.append(
                f"POI '{poi_id}' is not linked to repository book '{record.book.id}'."
            )
        for book_id in imported_poi.repositoryBookIds:
            linked_book = db.scalars(
                select(BookModel)
                .where(BookModel.id == book_id)
                .options(selectinload(BookModel.destinations))
            ).first()
            if linked_book is None:
                errors.append(
                    f"POI '{poi_id}' declares unknown repository book '{book_id}'."
                )
            elif imported_poi.destinationId not in {item.id for item in linked_book.destinations}:
                errors.append(
                    f"POI '{poi_id}' declares repository book '{book_id}' outside destination "
                    f"'{imported_poi.destinationId}'."
                )
    return errors


def _persist_catalog(db: Session, batch: ItineraryImportBatchV1) -> None:
    destinations = {record.destination.id: record.destination for record in batch.records}
    referenced_poi_ids = {
        stop.poiId
        for record in batch.records
        for day in record.itinerary.days
        for stop in day.stops
    }
    poi_catalog = {poi.id: poi for poi in batch.pois if poi.id in referenced_poi_ids}

    for imported_destination in destinations.values():
        if db.get(DestinationModel, imported_destination.id) is not None:
            continue
        db.add(
            DestinationModel(
                id=imported_destination.id,
                name=imported_destination.name,
                country=imported_destination.country,
                region=imported_destination.region,
                description=imported_destination.description,
                latitude=imported_destination.latitude,
                longitude=imported_destination.longitude,
                image_url=imported_destination.imageUrl,
                supported=True,
            )
        )
    db.flush()

    for imported_poi in poi_catalog.values():
        if db.get(POIModel, imported_poi.id) is not None:
            continue
        books = [db.get(BookModel, book_id) for book_id in imported_poi.repositoryBookIds]
        if any(book is None for book in books):
            raise ValueError(f"POI '{imported_poi.id}' declares an unknown repository book.")
        db.add(
            POIModel(
                id=imported_poi.id,
                destination_id=imported_poi.destinationId,
                name=imported_poi.name,
                description=imported_poi.description,
                latitude=imported_poi.latitude,
                longitude=imported_poi.longitude,
                address=imported_poi.address,
                estimated_duration_minutes=imported_poi.estimatedDurationMinutes,
                ticketing_note=imported_poi.ticketingNote,
                literary_relevance=imported_poi.literaryRelevance,
                verification_status=imported_poi.verificationStatus,
                verification_provider=imported_poi.verificationProvider,
                provider_version=imported_poi.providerVersion,
                provider_request_id=imported_poi.providerRequestId,
                verification_confidence=imported_poi.verificationConfidence,
                verified_name=imported_poi.verifiedName,
                verified_address=imported_poi.verifiedAddress,
                verified_latitude=imported_poi.verifiedLatitude,
                verified_longitude=imported_poi.verifiedLongitude,
                opening_hours_note=imported_poi.openingHoursNote,
                ticketing_url=imported_poi.ticketingUrl,
                verification_notes=imported_poi.verificationNotes,
                last_verified_at=imported_poi.lastVerifiedAt,
                manual_review_status=imported_poi.manualReviewStatus,
                reviewed_by_user_id=None,
                provenance_metadata=imported_poi.provenanceMetadata,
                books=[book for book in books if book is not None],
            )
        )
    db.flush()


def _destination_matches_import(row: DestinationModel, imported: ImportDestinationV1) -> bool:
    return (
        row.name == imported.name
        and row.country == imported.country
        and row.region == imported.region
        and row.description == imported.description
        and row.latitude == imported.latitude
        and row.longitude == imported.longitude
        and row.image_url == imported.imageUrl
    )


def _poi_matches_import(row: POIModel, imported: ImportPOIV1) -> bool:
    return (
        row.destination_id == imported.destinationId
        and row.name == imported.name
        and row.description == imported.description
        and row.latitude == imported.latitude
        and row.longitude == imported.longitude
        and row.address == imported.address
        and row.estimated_duration_minutes == imported.estimatedDurationMinutes
        and row.ticketing_note == imported.ticketingNote
        and row.literary_relevance == imported.literaryRelevance
        and row.verification_status == imported.verificationStatus
        and row.verification_provider == imported.verificationProvider
        and row.provider_version == imported.providerVersion
        and row.provider_request_id == imported.providerRequestId
        and row.verification_confidence == imported.verificationConfidence
        and row.verified_name == imported.verifiedName
        and row.verified_address == imported.verifiedAddress
        and row.verified_latitude == imported.verifiedLatitude
        and row.verified_longitude == imported.verifiedLongitude
        and row.opening_hours_note == imported.openingHoursNote
        and row.ticketing_url == imported.ticketingUrl
        and (row.verification_notes or []) == imported.verificationNotes
        and row.last_verified_at == imported.lastVerifiedAt
        and row.manual_review_status == imported.manualReviewStatus
        and (row.provenance_metadata or {}) == imported.provenanceMetadata
    )


def _poi_schema_from_import(imported: ImportPOIV1) -> POI:
    return POI(
        id=imported.id,
        destinationId=imported.destinationId,
        bookIds=imported.repositoryBookIds,
        name=imported.name,
        description=imported.description,
        latitude=imported.latitude,
        longitude=imported.longitude,
        address=imported.address,
        estimatedDurationMinutes=imported.estimatedDurationMinutes,
        ticketingNote=imported.ticketingNote,
        literaryRelevance=imported.literaryRelevance,
        verificationStatus=imported.verificationStatus,
        verificationProvider=imported.verificationProvider,
        providerVersion=imported.providerVersion,
        providerRequestId=imported.providerRequestId,
        verificationConfidence=imported.verificationConfidence,
        verifiedName=imported.verifiedName,
        verifiedAddress=imported.verifiedAddress,
        verifiedLatitude=imported.verifiedLatitude,
        verifiedLongitude=imported.verifiedLongitude,
        openingHoursNote=imported.openingHoursNote,
        ticketingUrl=imported.ticketingUrl,
        verificationNotes=imported.verificationNotes,
        lastVerifiedAt=imported.lastVerifiedAt,
        manualReviewStatus=imported.manualReviewStatus,
        reviewedByUserId=None,
        provenanceMetadata=imported.provenanceMetadata,
    )


def _preview_summary(
    db: Session,
    batch: ItineraryImportBatchV1,
    records: list[ImportRecordPreview],
) -> ImportPreviewSummary:
    new_record_count = sum(item.outcome == "new" for item in records)
    referenced_destination_ids = {
        record.destination.id
        for record, preview in zip(batch.records, records, strict=True)
        if preview.outcome == "new"
    }
    referenced_poi_ids = {
        stop.poiId
        for record, preview in zip(batch.records, records, strict=True)
        if preview.outcome == "new"
        for day in record.itinerary.days
        for stop in day.stops
    }
    destination_creates = sum(
        db.get(DestinationModel, destination_id) is None
        for destination_id in referenced_destination_ids
    )
    poi_creates = sum(db.get(POIModel, poi_id) is None for poi_id in referenced_poi_ids)
    catalog_mutations = destination_creates + poi_creates
    return ImportPreviewSummary(
        totalRecords=len(records),
        validRecords=sum(item.outcome in {"new", "already_imported"} for item in records),
        invalidRecords=sum(item.outcome == "invalid" for item in records),
        newRecords=new_record_count,
        alreadyImportedRecords=sum(item.outcome == "already_imported" for item in records),
        conflicts=sum(item.outcome == "conflict" for item in records),
        warnings=sum(len(item.warnings) for item in records),
        projectedMutations=new_record_count + catalog_mutations,
        projectedCatalogMutations=catalog_mutations,
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


def _record_hash(batch: ItineraryImportBatchV1, record: ItineraryImportRecordV1) -> str:
    referenced_poi_ids = {
        stop.poiId
        for day in record.itinerary.days
        for stop in day.stops
    }
    catalog = [
        poi.model_dump(mode="json")
        for poi in sorted(batch.pois, key=lambda item: item.id)
        if poi.id in referenced_poi_ids
    ]
    record_json = record.model_dump(mode="json")
    payload = record_json if not catalog else {"record": record_json, "pois": catalog}
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


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
