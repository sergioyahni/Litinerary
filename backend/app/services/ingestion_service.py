from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import not_found, validation_error
from app.models import (
    BookIngestionJobModel,
    BookLocationCandidateModel,
    BookModel,
    BookProcessingArtifactModel,
    BookSourceModel,
    DestinationModel,
    POIModel,
)
from app.services.poi_verification import apply_verification_result, get_poi_verification_adapter
from app.services.schema_converters import candidate_from_model
from app.schemas.ingestion import (
    BookIngestionJob,
    BookIngestionJobCreate,
    BookProcessingArtifact,
    BookSource,
    CandidatePromotionResponse,
)


UNSAFE_METADATA_KEYS = {
    "fullText",
    "full_text",
    "copyrightedFullText",
    "copyrighted_full_text",
    "rawText",
    "raw_text",
}


class BookIngestionService:
    def create_job(self, db: Session, request: BookIngestionJobCreate) -> BookIngestionJob:
        book = db.get(BookModel, request.bookId)
        if book is None:
            raise not_found("book", request.bookId)

        warnings = self.validate_source_metadata(request.source.metadata)
        now = _now()
        source = BookSourceModel(
            id=f"src-{uuid4().hex}",
            book_id=book.id,
            source_type=request.source.sourceType,
            title=request.source.title,
            reference_url=request.source.referenceUrl,
            metadata_json=request.source.metadata,
            source_license=request.source.sourceLicense,
            copyright_status=request.source.copyrightStatus,
            allowed_processing_mode=request.source.allowedProcessingMode,
            source_notes=request.source.sourceNotes,
            created_at=now,
        )
        job = BookIngestionJobModel(
            id=f"ingest-{uuid4().hex}",
            book_id=book.id,
            source=source,
            status="pending",
            extraction_notes=[
                "Created development-only ingestion job from safe source metadata."
            ],
            warnings=warnings,
            created_at=now,
            updated_at=now,
        )
        db.add(job)
        db.commit()
        return self.get_job(db, job.id)

    def validate_source_metadata(self, metadata: dict) -> list[str]:
        unsafe_keys = sorted(key for key in metadata if key in UNSAFE_METADATA_KEYS)
        if unsafe_keys:
            raise validation_error(
                "Unsafe source metadata includes full-text fields. "
                f"Remove: {', '.join(unsafe_keys)}"
            )

        warnings = []
        if not metadata:
            warnings.append("No source metadata supplied; mock extraction will use book metadata.")
        if "summary" in metadata:
            warnings.append("Summary metadata is accepted; do not include copyrighted full text.")
        if "locations" in metadata and not isinstance(metadata["locations"], list):
            raise validation_error("metadata.locations must be a list.")
        return warnings

    def list_jobs(self, db: Session) -> list[BookIngestionJob]:
        rows = db.scalars(
            select(BookIngestionJobModel)
            .options(*_job_load_options())
            .order_by(BookIngestionJobModel.created_at, BookIngestionJobModel.id)
        ).unique().all()
        return [job_from_model(row) for row in rows]

    def get_job(self, db: Session, job_id: str) -> BookIngestionJob:
        job = _get_job_model(db, job_id)
        return job_from_model(job)

    def run_job(self, db: Session, job_id: str) -> BookIngestionJob:
        job = _get_job_model(db, job_id)
        now = _now()
        job.status = "processing"
        job.updated_at = now
        job.extraction_notes = [
            *job.extraction_notes,
            "Started deterministic mock extraction.",
        ]
        db.flush()

        try:
            candidates = self.extract_mock_location_candidates(db, job)
            job.candidates[:] = candidates
            job.artifacts[:] = self.create_mock_processing_artifacts(job, candidates)
            job.status = "completed"
            job.completed_at = _now()
            job.updated_at = job.completed_at
            job.extraction_notes = [
                *job.extraction_notes,
                f"Created {len(candidates)} mock location candidate(s).",
            ]
            if not candidates:
                job.warnings = [*job.warnings, "No mock candidates were extracted."]
            db.commit()
        except Exception:
            db.rollback()
            job = _get_job_model(db, job_id)
            job.status = "failed"
            job.updated_at = _now()
            job.warnings = [*job.warnings, "Mock ingestion failed during processing."]
            db.commit()
            raise

        return self.get_job(db, job.id)

    def extract_mock_location_candidates(
        self,
        db: Session,
        job: BookIngestionJobModel,
    ) -> list[BookLocationCandidateModel]:
        book = db.scalars(
            select(BookModel)
            .where(BookModel.id == job.book_id)
            .options(selectinload(BookModel.destinations))
        ).first()
        if book is None:
            raise not_found("book", job.book_id)

        location_items = _metadata_locations(job.source.metadata_json)
        if not location_items:
            location_items = [
                {
                    "name": f"{destination.name} literary setting",
                    "destinationId": destination.id,
                    "description": f"Metadata-only mock location for {book.title}.",
                }
                for destination in sorted(book.destinations, key=lambda item: item.id)
            ]

        candidates: list[BookLocationCandidateModel] = []
        for index, item in enumerate(location_items, start=1):
            destination = _destination_for_location(db, book, item)
            latitude, longitude = _candidate_coordinates(destination, item, index)
            name = str(item.get("name") or f"{book.title} location {index}")
            candidates.append(
                BookLocationCandidateModel(
                    id=f"cand-{job.id}-{index}",
                    job_id=job.id,
                    book_id=book.id,
                    destination_id=destination.id,
                    name=name,
                    description=str(
                        item.get("description")
                        or f"Mock candidate extracted from safe metadata for {book.title}."
                    ),
                    latitude=latitude,
                    longitude=longitude,
                    literary_relevance=str(
                        item.get("literaryRelevance")
                        or item.get("literary_relevance")
                        or f"Associated with {book.title} during mock ingestion."
                    ),
                    confidence=round(0.9 - min(index - 1, 4) * 0.05, 2),
                    status="candidate",
                    created_at=_now(),
                )
            )
        return candidates

    def create_mock_processing_artifacts(
        self,
        job: BookIngestionJobModel,
        candidates: list[BookLocationCandidateModel],
    ) -> list[BookProcessingArtifactModel]:
        now = _now()
        return [
            BookProcessingArtifactModel(
                id=f"artifact-{job.id}-summary",
                job_id=job.id,
                artifact_type="mock_extraction_summary",
                payload={
                    "sourceType": job.source.source_type,
                    "candidateCount": len(candidates),
                    "copyrightNote": (
                        "Mock processing used only source metadata, summaries, "
                        "or curated location references."
                    ),
                },
                provider_name="mock_local",
                provider_type="book_ingestion",
                provider_version="local-mock",
                provider_request_id=f"mock-ingestion-{job.id}-summary",
                confidence_score=1.0,
                provenance_metadata={
                    "sourceId": job.source_id,
                    "externalCalls": False,
                    "processingMode": job.source.allowed_processing_mode,
                },
                created_at=now,
            ),
            BookProcessingArtifactModel(
                id=f"artifact-{job.id}-candidate-names",
                job_id=job.id,
                artifact_type="mock_candidate_names",
                payload={"names": [candidate.name for candidate in candidates]},
                provider_name="mock_local",
                provider_type="book_ingestion",
                provider_version="local-mock",
                provider_request_id=f"mock-ingestion-{job.id}-candidate-names",
                confidence_score=1.0,
                provenance_metadata={
                    "sourceId": job.source_id,
                    "externalCalls": False,
                    "processingMode": job.source.allowed_processing_mode,
                },
                created_at=now,
            ),
        ]

    def promote_candidate(
        self,
        db: Session,
        candidate_id: str,
    ) -> CandidatePromotionResponse:
        candidate = db.scalars(
            select(BookLocationCandidateModel)
            .where(BookLocationCandidateModel.id == candidate_id)
            .options(selectinload(BookLocationCandidateModel.book))
        ).first()
        if candidate is None:
            raise not_found("candidate", candidate_id)

        result = get_poi_verification_adapter().resolve_candidate(db, candidate)
        poi_id = candidate.promoted_poi_id or f"poi-{candidate.id}"
        poi = db.get(POIModel, poi_id)
        if poi is None:
            poi = POIModel(id=poi_id)
            db.add(poi)

        poi.destination_id = candidate.destination_id
        poi.name = candidate.name
        poi.description = candidate.description
        poi.latitude = candidate.latitude
        poi.longitude = candidate.longitude
        poi.address = None
        poi.estimated_duration_minutes = 45
        poi.ticketing_note = "Created by development-only mock ingestion; verify before use."
        poi.literary_relevance = candidate.literary_relevance
        poi.verification_status = "unverified"
        poi.books = [candidate.book]
        apply_verification_result(poi, result)

        candidate.status = "promoted"
        candidate.promoted_poi_id = poi_id
        db.commit()
        db.refresh(candidate)
        return CandidatePromotionResponse(
            candidate=candidate_from_model(candidate),
            poiId=poi_id,
        )


def job_from_model(job: BookIngestionJobModel) -> BookIngestionJob:
    return BookIngestionJob(
        id=job.id,
        bookId=job.book_id,
        source=source_from_model(job.source),
        status=job.status,
        extractionNotes=job.extraction_notes or [],
        warnings=job.warnings or [],
        candidates=[candidate_from_model(candidate) for candidate in job.candidates],
        artifacts=[artifact_from_model(artifact) for artifact in job.artifacts],
        createdAt=job.created_at,
        updatedAt=job.updated_at,
        completedAt=job.completed_at,
    )


def source_from_model(source: BookSourceModel) -> BookSource:
    return BookSource(
        id=source.id,
        bookId=source.book_id,
        sourceType=source.source_type,
        title=source.title,
        referenceUrl=source.reference_url,
        metadata=source.metadata_json or {},
        sourceLicense=source.source_license,
        copyrightStatus=source.copyright_status,
        allowedProcessingMode=source.allowed_processing_mode,
        sourceNotes=source.source_notes or [],
        createdAt=source.created_at,
    )


def artifact_from_model(artifact: BookProcessingArtifactModel) -> BookProcessingArtifact:
    return BookProcessingArtifact(
        id=artifact.id,
        jobId=artifact.job_id,
        artifactType=artifact.artifact_type,
        payload=artifact.payload or {},
        providerName=artifact.provider_name,
        providerType=artifact.provider_type,
        providerVersion=artifact.provider_version,
        providerRequestId=artifact.provider_request_id,
        confidenceScore=artifact.confidence_score,
        provenanceMetadata=artifact.provenance_metadata or {},
        createdAt=artifact.created_at,
    )


def _get_job_model(db: Session, job_id: str) -> BookIngestionJobModel:
    job = db.scalars(
        select(BookIngestionJobModel)
        .where(BookIngestionJobModel.id == job_id)
        .options(*_job_load_options())
    ).unique().first()
    if job is None:
        raise not_found("ingestion job", job_id)
    return job


def _job_load_options():
    return (
        selectinload(BookIngestionJobModel.source),
        selectinload(BookIngestionJobModel.candidates),
        selectinload(BookIngestionJobModel.artifacts),
    )


def _metadata_locations(metadata: dict) -> list[dict]:
    locations = metadata.get("locations") or []
    normalized = []
    for item in locations:
        if isinstance(item, str):
            normalized.append({"name": item})
        elif isinstance(item, dict):
            normalized.append(item)
    return normalized


def _destination_for_location(
    db: Session,
    book: BookModel,
    item: dict,
) -> DestinationModel:
    destination_id = item.get("destinationId") or item.get("destination_id")
    if destination_id:
        destination = db.get(DestinationModel, destination_id)
        if destination is None:
            raise not_found("destination", destination_id)
        return destination

    destinations = sorted(book.destinations, key=lambda row: row.id)
    if not destinations:
        raise validation_error(
            f"Book '{book.id}' has no destination metadata for mock ingestion."
        )
    return destinations[0]


def _candidate_coordinates(
    destination: DestinationModel,
    item: dict,
    index: int,
) -> tuple[float, float]:
    latitude = item.get("latitude")
    longitude = item.get("longitude")
    if isinstance(latitude, int | float) and isinstance(longitude, int | float):
        return float(latitude), float(longitude)

    offset = index * 0.003
    return round(destination.latitude + offset, 6), round(destination.longitude - offset, 6)


def _now() -> str:
    return datetime.now(UTC).isoformat()


ingestion_service = BookIngestionService()
