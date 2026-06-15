from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from math import sqrt
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import not_found
from app.core.observability import EventName, log_event, record_provider_selection
from app.core.provider_guards import require_external_call_allowed
from app.models import BookLocationCandidateModel, POIModel
from app.schemas.domain import POI
from app.schemas.poi_verification import CandidateVerificationResponse, POIVerificationResponse
from app.services.database_repository import poi_from_model
from app.services.provider_contracts import ProviderMetadata, ProviderType
from app.services.schema_converters import candidate_from_model, verification_result_response
from app.services.usage_policy import get_usage_guard


POI_VERIFICATION_STATUSES = {
    "unverified",
    "mock_verified",
    "provider_verified",
    "needs_review",
    "rejected",
}


@dataclass(frozen=True)
class PlaceSearchQuery:
    name: str
    city_id: str
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class PlaceSearchResult:
    provider: str
    name: str
    address: str | None
    latitude: float | None
    longitude: float | None
    confidence: float
    source_poi_id: str | None = None
    notes: list[str] = field(default_factory=list)
    metadata: ProviderMetadata | None = None


@dataclass(frozen=True)
class LogisticsMetadata:
    opening_hours_note: str | None = None
    ticketing_url: str | None = None
    metadata: ProviderMetadata | None = None


@dataclass(frozen=True)
class POIVerificationResult:
    status: str
    provider: str
    confidence: float
    verified_name: str | None
    verified_address: str | None
    verified_latitude: float | None
    verified_longitude: float | None
    opening_hours_note: str | None
    ticketing_url: str | None
    notes: list[str]
    metadata: ProviderMetadata | None = None


class POIVerificationAdapter(Protocol):
    def search_places(self, db: Session, query: PlaceSearchQuery) -> list[PlaceSearchResult]:
        """Search places by name and city without exposing provider-specific details."""

    def resolve_candidate(
        self,
        db: Session,
        candidate: BookLocationCandidateModel,
    ) -> POIVerificationResult:
        """Resolve an ingestion location candidate to a real-world POI candidate."""

    def verify_poi(self, db: Session, poi: POIModel) -> POIVerificationResult:
        """Verify an existing POI."""

    def validate_coordinates(self, latitude: float | None, longitude: float | None) -> bool:
        """Return whether coordinates are usable for map display and verification."""

    def fetch_logistics_metadata(self, result: PlaceSearchResult) -> LogisticsMetadata:
        """Fetch basic logistics metadata such as hours notes."""

    def fetch_ticketing_url(self, result: PlaceSearchResult) -> str | None:
        """Fetch a ticketing URL placeholder without contacting a ticketing provider."""


class MockPOIVerificationAdapter:
    provider_name = "mock_local"

    def search_places(self, db: Session, query: PlaceSearchQuery) -> list[PlaceSearchResult]:
        rows = db.scalars(
            select(POIModel)
            .where(POIModel.destination_id == query.city_id)
            .options(selectinload(POIModel.books))
        ).unique().all()
        results = [
            self._result_from_poi(row, query)
            for row in rows
            if row.id and row.name
        ]
        return sorted(results, key=lambda result: (-result.confidence, result.name))

    def resolve_candidate(
        self,
        db: Session,
        candidate: BookLocationCandidateModel,
    ) -> POIVerificationResult:
        query = PlaceSearchQuery(
            name=candidate.name,
            city_id=candidate.destination_id,
            latitude=candidate.latitude,
            longitude=candidate.longitude,
        )
        return self._verification_from_query(db, query)

    def verify_poi(self, db: Session, poi: POIModel) -> POIVerificationResult:
        query = PlaceSearchQuery(
            name=poi.name,
            city_id=poi.destination_id,
            latitude=poi.latitude,
            longitude=poi.longitude,
        )
        return self._verification_from_query(db, query)

    def validate_coordinates(self, latitude: float | None, longitude: float | None) -> bool:
        if latitude is None or longitude is None:
            return False
        if latitude == 0 or longitude == 0:
            return False
        return -90 <= latitude <= 90 and -180 <= longitude <= 180

    def fetch_logistics_metadata(self, result: PlaceSearchResult) -> LogisticsMetadata:
        if result.confidence >= 0.85:
            return LogisticsMetadata(
                opening_hours_note="Mock hours unavailable; verify with a real provider later.",
                ticketing_url=self.fetch_ticketing_url(result),
            )
        return LogisticsMetadata(opening_hours_note="Needs manual review before logistics lookup.")

    def fetch_ticketing_url(self, result: PlaceSearchResult) -> str | None:
        if result.confidence < 0.85:
            return None
        slug = "-".join(result.name.lower().split())
        return f"https://example.test/tickets/{slug}"

    def _verification_from_query(
        self,
        db: Session,
        query: PlaceSearchQuery,
    ) -> POIVerificationResult:
        if not self.validate_coordinates(query.latitude, query.longitude):
            return POIVerificationResult(
                status="needs_review",
                provider=self.provider_name,
                confidence=0.0,
                verified_name=None,
                verified_address=None,
                verified_latitude=None,
                verified_longitude=None,
                opening_hours_note=None,
                ticketing_url=None,
                notes=["Missing or invalid coordinates; manual review required."],
                metadata=self._metadata(0.0, ["Missing or invalid coordinates."]),
            )

        results = self.search_places(db, query)
        best = results[0] if results else None
        if best is None:
            return POIVerificationResult(
                status="needs_review",
                provider=self.provider_name,
                confidence=0.35,
                verified_name=query.name,
                verified_address=None,
                verified_latitude=query.latitude,
                verified_longitude=query.longitude,
                opening_hours_note="No local mock place matched this candidate.",
                ticketing_url=None,
                notes=["No matching seeded POI found; keep for manual review."],
                metadata=self._metadata(0.35, ["No local mock place matched."]),
            )

        logistics = self.fetch_logistics_metadata(best)
        status = "mock_verified" if best.confidence >= 0.85 else "needs_review"
        return POIVerificationResult(
            status=status,
            provider=self.provider_name,
            confidence=best.confidence,
            verified_name=best.name,
            verified_address=best.address,
            verified_latitude=best.latitude,
            verified_longitude=best.longitude,
            opening_hours_note=logistics.opening_hours_note,
            ticketing_url=logistics.ticketing_url,
            notes=best.notes,
            metadata=self._metadata(best.confidence, best.notes),
        )

    def _result_from_poi(
        self,
        poi: POIModel,
        query: PlaceSearchQuery,
    ) -> PlaceSearchResult:
        name_score = _name_similarity(query.name, poi.name)
        coordinate_score = _coordinate_score(query.latitude, query.longitude, poi.latitude, poi.longitude)
        confidence = round((name_score * 0.7) + (coordinate_score * 0.3), 3)
        return PlaceSearchResult(
            provider=self.provider_name,
            name=poi.name,
            address=poi.address,
            latitude=poi.latitude,
            longitude=poi.longitude,
            confidence=confidence,
            source_poi_id=poi.id,
            notes=[
                "Matched against local seeded/mock POIs only.",
                f"name_score={name_score:.2f}",
                f"coordinate_score={coordinate_score:.2f}",
            ],
            metadata=self._metadata(confidence, ["Matched against local seeded/mock POIs only."]),
        )

    def _metadata(
        self,
        confidence_score: float,
        warnings: list[str] | None = None,
    ) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name=self.provider_name,
            provider_type=ProviderType.POI_VERIFICATION.value,
            provider_version="local-mock",
            request_id=f"mock-{self.provider_name}-{confidence_score:.3f}",
            confidence_score=confidence_score,
            generated_at="2026-06-12T00:00:00+00:00",
            verified_at="2026-06-12T00:00:00+00:00",
            warnings=warnings or ["Mock verification; no external provider call was made."],
        )


def verify_candidate(db: Session, candidate_id: str) -> POIVerificationResult:
    log_event(
        EventName.POI_VERIFICATION_REQUESTED,
        category="poi_verification",
        target_type="candidate",
        target_id=candidate_id,
    )
    get_usage_guard().guard_poi_verification_batch(request_count=1)
    candidate = db.get(BookLocationCandidateModel, candidate_id)
    if candidate is None:
        raise not_found("candidate", candidate_id)
    return get_poi_verification_adapter().resolve_candidate(db, candidate)


def verify_candidate_response(db: Session, candidate_id: str) -> CandidateVerificationResponse:
    log_event(
        EventName.POI_VERIFICATION_REQUESTED,
        category="poi_verification",
        target_type="candidate",
        target_id=candidate_id,
    )
    get_usage_guard().guard_poi_verification_batch(request_count=1)
    candidate = _get_candidate(db, candidate_id)
    result = get_poi_verification_adapter().resolve_candidate(db, candidate)
    return CandidateVerificationResponse(
        candidate=candidate_from_model(candidate),
        verification=verification_result_response(result),
    )


def verify_poi(db: Session, poi_id: str) -> POIVerificationResult:
    log_event(
        EventName.POI_VERIFICATION_REQUESTED,
        category="poi_verification",
        target_type="poi",
        target_id=poi_id,
    )
    get_usage_guard().guard_poi_verification_batch(request_count=1)
    poi = _get_poi(db, poi_id)
    result = get_poi_verification_adapter().verify_poi(db, poi)
    apply_verification_result(poi, result)
    db.commit()
    db.refresh(poi)
    return result


def verify_poi_response(db: Session, poi_id: str) -> POIVerificationResponse:
    log_event(
        EventName.POI_VERIFICATION_REQUESTED,
        category="poi_verification",
        target_type="poi",
        target_id=poi_id,
    )
    get_usage_guard().guard_poi_verification_batch(request_count=1)
    poi = _get_poi(db, poi_id)
    result = get_poi_verification_adapter().verify_poi(db, poi)
    apply_verification_result(poi, result)
    db.commit()
    db.refresh(poi)
    return POIVerificationResponse(
        poi=poi_from_model(poi),
        verification=verification_result_response(result),
    )


def list_unverified_pois(db: Session) -> list[POIModel]:
    return db.scalars(
        select(POIModel)
        .where(POIModel.verification_status.in_(["unverified", "needs_review", "mock"]))
        .options(selectinload(POIModel.books))
        .order_by(POIModel.name, POIModel.id)
    ).unique().all()


def list_unverified_poi_schemas(db: Session) -> list[POI]:
    return [poi_from_model(poi) for poi in list_unverified_pois(db)]


def mark_poi_reviewed(db: Session, poi_id: str) -> POIModel:
    poi = _get_poi(db, poi_id)
    poi.verification_status = "mock_verified"
    poi.verification_provider = poi.verification_provider or "manual_review"
    poi.verification_confidence = poi.verification_confidence or 1.0
    poi.verification_notes = [
        *(poi.verification_notes or []),
        "Marked reviewed by development admin endpoint.",
    ]
    poi.manual_review_status = "reviewed"
    poi.last_verified_at = _now()
    db.commit()
    db.refresh(poi)
    return poi


def mark_poi_reviewed_schema(db: Session, poi_id: str) -> POI:
    return poi_from_model(mark_poi_reviewed(db, poi_id))


def apply_verification_result(poi: POIModel, result: POIVerificationResult) -> None:
    previous_notes = poi.verification_notes or []
    previous_manual_review_status = poi.manual_review_status
    poi.verification_status = result.status
    poi.verification_provider = result.provider
    if result.metadata is not None:
        poi.provider_version = result.metadata.provider_version
        poi.provider_request_id = result.metadata.request_id
        poi.last_verified_at = result.metadata.verified_at or _now()
        poi.provenance_metadata = {
            "providerName": result.metadata.provider_name,
            "providerType": result.metadata.provider_type,
            "modelName": result.metadata.model_name,
            "sourceUrl": result.metadata.source_url,
            "latencyMs": result.metadata.latency_ms,
            "warnings": result.metadata.warnings,
            "externalProviderUsed": result.metadata.provider_version != "local-mock",
        }
    else:
        poi.last_verified_at = _now()
    poi.verification_confidence = result.confidence
    poi.verified_name = result.verified_name
    poi.verified_address = result.verified_address
    poi.verified_latitude = result.verified_latitude
    poi.verified_longitude = result.verified_longitude
    poi.opening_hours_note = result.opening_hours_note
    poi.ticketing_url = result.ticketing_url
    poi.verification_notes = _merge_notes(previous_notes, result.notes)
    if result.status == "needs_review":
        poi.manual_review_status = "needs_review"
    elif previous_manual_review_status == "reviewed":
        poi.manual_review_status = "reviewed"
    else:
        poi.manual_review_status = "not_reviewed"


@lru_cache
def get_poi_verification_adapter() -> POIVerificationAdapter:
    settings = get_settings()
    if settings.poi_verification_provider == "mock" and not settings.enable_mock_services:
        raise RuntimeError(
            "Mock POI verification services are disabled in this environment. "
            "Set ENABLE_MOCK_SERVICES=true only for intentional local/test use."
        )
    if settings.poi_verification_provider != "mock" and not settings.enable_real_poi_provider:
        raise RuntimeError(
            "Real POI verification provider "
            f"'{settings.poi_verification_provider}' is disabled by ENABLE_REAL_POI_PROVIDER."
        )
    if settings.poi_verification_provider == "google_places":
        record_provider_selection(
            provider_type=ProviderType.POI_VERIFICATION.value,
            provider_name="google_places",
            mode="real",
        )
        validate_poi_provider_startup(settings)
        from app.services.google_places_poi_adapter import (
            GooglePlacesPOIVerificationAdapter,
            GooglePlacesSettings,
        )

        return GooglePlacesPOIVerificationAdapter(
            GooglePlacesSettings(
                api_key=settings.poi_verification_api_key or "",
                base_url=settings.poi_provider_base_url,
                timeout_seconds=settings.poi_provider_timeout_seconds,
                result_limit=settings.poi_provider_result_limit,
                min_confidence=settings.poi_provider_min_confidence,
                region_code=settings.poi_provider_region_code,
                language_code=settings.poi_provider_language_code,
            )
        )
    if settings.poi_verification_provider != "mock":
        raise RuntimeError(
            "POI verification provider "
            f"'{settings.poi_verification_provider}' is configured but not implemented."
        )
    record_provider_selection(
        provider_type=ProviderType.POI_VERIFICATION.value,
        provider_name="mock",
        mode="mock",
    )
    return MockPOIVerificationAdapter()


def validate_poi_provider_startup(settings=None) -> None:
    resolved = settings or get_settings()
    if not resolved.enable_real_poi_provider:
        return
    if resolved.poi_verification_provider != "google_places":
        raise RuntimeError(
            "Real POI provider is enabled but only the Google Places adapter boundary is "
            "implemented. Set POI_PROVIDER=google_places or disable ENABLE_REAL_POI_PROVIDER."
        )
    require_external_call_allowed(
        provider_name="google_places",
        provider_type=ProviderType.POI_VERIFICATION,
        feature_flag_name="ENABLE_REAL_POI_PROVIDER",
        feature_enabled=resolved.enable_real_poi_provider,
        required_config={
            "POI_PROVIDER_API_KEY, GOOGLE_PLACES_API_KEY, or POI_VERIFICATION_API_KEY": (
                resolved.poi_verification_api_key
            )
        },
        settings=resolved,
    )
    missing = []
    if not resolved.poi_verification_api_key:
        missing.append("POI_PROVIDER_API_KEY, GOOGLE_PLACES_API_KEY, or POI_VERIFICATION_API_KEY")
    if resolved.poi_provider_timeout_seconds <= 0:
        missing.append("POI_PROVIDER_TIMEOUT_SECONDS must be positive")
    if resolved.poi_provider_result_limit <= 0:
        missing.append("POI_PROVIDER_RESULT_LIMIT must be positive")
    if not 0 <= resolved.poi_provider_min_confidence <= 1:
        missing.append("POI_PROVIDER_MIN_CONFIDENCE must be between 0 and 1")
    if missing:
        raise RuntimeError(
            "Real Google Places POI provider is enabled but configuration is incomplete: "
            + ", ".join(missing)
        )


def _get_poi(db: Session, poi_id: str) -> POIModel:
    poi = db.scalars(
        select(POIModel)
        .where(POIModel.id == poi_id)
        .options(selectinload(POIModel.books))
    ).first()
    if poi is None:
        raise not_found("POI", poi_id)
    return poi


def _get_candidate(db: Session, candidate_id: str) -> BookLocationCandidateModel:
    candidate = db.get(BookLocationCandidateModel, candidate_id)
    if candidate is None:
        raise not_found("candidate", candidate_id)
    return candidate


def _merge_notes(existing: list[str], new_notes: list[str]) -> list[str]:
    merged: list[str] = []
    for note in [*existing, *new_notes]:
        if note not in merged:
            merged.append(note)
    return merged


def _name_similarity(left: str, right: str) -> float:
    left_tokens = set(left.lower().replace(",", " ").split())
    right_tokens = set(right.lower().replace(",", " ").split())
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    return overlap / max(len(left_tokens), len(right_tokens))


def _coordinate_score(
    left_latitude: float | None,
    left_longitude: float | None,
    right_latitude: float | None,
    right_longitude: float | None,
) -> float:
    if None in {left_latitude, left_longitude, right_latitude, right_longitude}:
        return 0.0
    distance = sqrt((left_latitude - right_latitude) ** 2 + (left_longitude - right_longitude) ** 2)
    if distance <= 0.002:
        return 1.0
    if distance <= 0.02:
        return 0.75
    if distance <= 0.1:
        return 0.4
    return 0.0


def _now() -> str:
    return datetime.now(UTC).isoformat()
