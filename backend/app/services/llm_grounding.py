from app.schemas.domain import Itinerary, POI
from app.services.ai_types import GroundedLLMRequest, GroundingSource
from app.services.ingestion_service import UNSAFE_METADATA_KEYS
from app.services.provider_contracts import (
    ProviderError,
    ProviderErrorCode,
    ProviderMetadata,
    ProviderType,
    utc_now_iso,
)


SAFE_SOURCE_TYPES = {
    "public_domain_text_reference",
    "summary_document",
    "manually_curated_location_list",
    "metadata_only",
}
SAFE_PROCESSING_MODES = {
    "full_text",
    "summary_only",
    "metadata_only",
    "manual_curation",
}
SAFE_COPYRIGHT_STATUSES = {
    "public_domain",
    "copyrighted",
    "unknown",
    "metadata_only",
}
USABLE_POI_STATUSES = {
    "unverified",
    "mock_verified",
    "provider_verified",
    "needs_review",
}


def validate_grounded_request(request: GroundedLLMRequest) -> None:
    if request.task in {"summary_location_extraction", "poi_extraction"}:
        _validate_sources(request.sources)
    if request.task in {"itinerary_generation", "itinerary_adaptation", "judge_validation"}:
        _validate_pois(request.pois or _pois_from_itinerary(request.itinerary))
    if request.task in {"itinerary_generation", "itinerary_adaptation"} and not request.sources:
        raise _unsafe_error("Real LLM itinerary tasks require at least one grounding source.")


def validate_source(source: GroundingSource) -> None:
    if source.source_type not in SAFE_SOURCE_TYPES:
        raise _unsafe_error(f"Unsupported source type for real LLM grounding: {source.source_type}")
    unsafe_keys = sorted(key for key in source.metadata if key in UNSAFE_METADATA_KEYS)
    if unsafe_keys:
        raise _unsafe_error(
            "Unsafe source metadata includes full-text fields: " + ", ".join(unsafe_keys)
        )
    if source.copyright_status not in SAFE_COPYRIGHT_STATUSES:
        raise _unsafe_error(
            f"Unsupported copyright status for real LLM grounding: {source.copyright_status}"
        )
    if source.allowed_processing_mode not in SAFE_PROCESSING_MODES:
        raise _unsafe_error(
            "Unsupported processing mode for real LLM grounding: "
            + source.allowed_processing_mode
        )
    if (
        source.copyright_status == "copyrighted"
        and source.allowed_processing_mode == "full_text"
    ):
        raise _unsafe_error("Copyrighted full text cannot be sent to a real LLM provider.")
    if source.source_type in {"summary_document", "public_domain_text_reference"}:
        if not source.source_license and source.copyright_status == "unknown":
            raise _unsafe_error(
                "Real LLM grounding requires source license or known copyright status."
            )


def validate_poi_for_grounding(poi: POI) -> None:
    if poi.verificationStatus not in USABLE_POI_STATUSES:
        raise _unsafe_error(
            f"POI '{poi.id}' has unsupported verification status '{poi.verificationStatus}'."
        )
    if poi.latitude == 0 or poi.longitude == 0:
        raise _unsafe_error(f"POI '{poi.id}' is missing usable coordinates.")
    notes = poi.verificationNotes or []
    provenance = poi.provenanceMetadata or {}
    if not notes and not provenance:
        raise _unsafe_error(f"POI '{poi.id}' is missing provenance or candidate source notes.")


def _validate_sources(sources: list[GroundingSource]) -> None:
    if not sources:
        raise _unsafe_error("Real LLM extraction tasks require grounding sources.")
    for source in sources:
        validate_source(source)


def _validate_pois(pois: list[POI]) -> None:
    if not pois:
        raise _unsafe_error("Real LLM itinerary tasks require grounded POIs.")
    for poi in pois:
        validate_poi_for_grounding(poi)


def _pois_from_itinerary(itinerary: Itinerary | None) -> list[POI]:
    if itinerary is None:
        return []
    return [stop.poi for day in itinerary.days for stop in day.stops]


def _unsafe_error(message: str) -> ProviderError:
    return ProviderError(
        ProviderErrorCode.UNSAFE_INPUT,
        message,
        metadata=ProviderMetadata(
            provider_name="llm_grounding",
            provider_type=ProviderType.LLM.value,
            generated_at=utc_now_iso(),
            warnings=["Real LLM provider call was blocked before any external request."],
        ),
    )
