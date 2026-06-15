from dataclasses import dataclass
import json
from time import monotonic
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from app.models import BookLocationCandidateModel, DestinationModel, POIModel
from app.services.poi_verification import (
    LogisticsMetadata,
    POIVerificationResult,
    PlaceSearchQuery,
    PlaceSearchResult,
    _coordinate_score,
    _name_similarity,
    _now,
)
from app.services.provider_contracts import (
    ProviderError,
    ProviderErrorCode,
    ProviderMetadata,
    ProviderType,
    utc_now_iso,
)


class GooglePlacesTransport(Protocol):
    def search_text(
        self,
        payload: dict[str, Any],
        field_mask: str,
    ) -> tuple[dict[str, Any], int | None]:
        """Search Google Places and return normalized JSON plus latency."""


@dataclass(frozen=True)
class GooglePlacesSettings:
    api_key: str
    base_url: str = "https://places.googleapis.com"
    timeout_seconds: float = 5.0
    result_limit: int = 5
    min_confidence: float = 0.82
    region_code: str | None = None
    language_code: str | None = None


class GooglePlacesHttpTransport:
    def __init__(self, settings: GooglePlacesSettings) -> None:
        self.settings = settings
        self.base_url = settings.base_url.rstrip("/")

    def search_text(
        self,
        payload: dict[str, Any],
        field_mask: str,
    ) -> tuple[dict[str, Any], int | None]:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}/v1/places:searchText",
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.settings.api_key,
                "X-Goog-FieldMask": field_mask,
            },
            method="POST",
        )
        started = monotonic()
        try:
            with urlopen(request, timeout=self.settings.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            if exc.code == 429:
                raise _provider_error(
                    ProviderErrorCode.RATE_LIMITED,
                    "Google Places rate limit was exceeded.",
                ) from exc
            raise _provider_error(
                ProviderErrorCode.INVALID_RESPONSE,
                f"Google Places returned HTTP {exc.code}.",
            ) from exc
        except TimeoutError as exc:
            raise _provider_error(
                ProviderErrorCode.TIMEOUT,
                "Google Places request timed out.",
            ) from exc
        except URLError as exc:
            raise _provider_error(
                ProviderErrorCode.UNAVAILABLE,
                "Google Places is unavailable.",
            ) from exc

        latency_ms = round((monotonic() - started) * 1000)
        if not response_body:
            return {}, latency_ms
        try:
            return json.loads(response_body), latency_ms
        except json.JSONDecodeError as exc:
            raise _provider_error(
                ProviderErrorCode.INVALID_RESPONSE,
                "Google Places returned non-JSON response.",
            ) from exc


class GooglePlacesPOIVerificationAdapter:
    provider_name = "google_places"
    provider_version = "places-api-v1"
    field_mask = (
        "places.id,places.displayName,places.formattedAddress,places.location,"
        "places.googleMapsUri,places.websiteUri,places.regularOpeningHours,"
        "places.businessStatus"
    )

    def __init__(
        self,
        settings: GooglePlacesSettings,
        transport: GooglePlacesTransport | None = None,
    ) -> None:
        if not settings.api_key:
            raise _provider_error(
                ProviderErrorCode.NOT_CONFIGURED,
                "Google Places API key is required when the real POI provider is enabled.",
            )
        if settings.result_limit <= 0:
            raise _provider_error(
                ProviderErrorCode.NOT_CONFIGURED,
                "POI provider result limit must be positive.",
            )
        if settings.timeout_seconds <= 0:
            raise _provider_error(
                ProviderErrorCode.NOT_CONFIGURED,
                "POI provider timeout must be positive.",
            )
        if not 0 <= settings.min_confidence <= 1:
            raise _provider_error(
                ProviderErrorCode.NOT_CONFIGURED,
                "POI provider minimum confidence must be between 0 and 1.",
            )
        self.settings = settings
        self.transport = transport or GooglePlacesHttpTransport(settings)

    def search_places(self, db: Session, query: PlaceSearchQuery) -> list[PlaceSearchResult]:
        destination = db.get(DestinationModel, query.city_id)
        text_query = _text_query(query.name, destination)
        payload: dict[str, Any] = {
            "textQuery": text_query,
            "maxResultCount": self.settings.result_limit,
        }
        if self.settings.region_code:
            payload["regionCode"] = self.settings.region_code
        if self.settings.language_code:
            payload["languageCode"] = self.settings.language_code
        if self.validate_coordinates(query.latitude, query.longitude):
            payload["locationBias"] = {
                "circle": {
                    "center": {
                        "latitude": query.latitude,
                        "longitude": query.longitude,
                    },
                    "radius": 5000.0,
                }
            }

        response, latency_ms = self.transport.search_text(payload, self.field_mask)
        places = response.get("places")
        if places is None:
            raise _provider_error(
                ProviderErrorCode.INVALID_RESPONSE,
                "Google Places response did not contain a places list.",
                latency_ms=latency_ms,
            )
        if not isinstance(places, list):
            raise _provider_error(
                ProviderErrorCode.INVALID_RESPONSE,
                "Google Places places field was not a list.",
                latency_ms=latency_ms,
            )

        results = [
            self._result_from_place(place, query, latency_ms)
            for place in places[: self.settings.result_limit]
            if isinstance(place, dict)
        ]
        return sorted(results, key=lambda result: (-result.confidence, result.name))

    def resolve_candidate(
        self,
        db: Session,
        candidate: BookLocationCandidateModel,
    ) -> POIVerificationResult:
        return self._verification_from_query(
            db,
            PlaceSearchQuery(
                name=candidate.name,
                city_id=candidate.destination_id,
                latitude=candidate.latitude,
                longitude=candidate.longitude,
            ),
        )

    def verify_poi(self, db: Session, poi: POIModel) -> POIVerificationResult:
        return self._verification_from_query(
            db,
            PlaceSearchQuery(
                name=poi.name,
                city_id=poi.destination_id,
                latitude=poi.latitude,
                longitude=poi.longitude,
            ),
        )

    def validate_coordinates(self, latitude: float | None, longitude: float | None) -> bool:
        if latitude is None or longitude is None:
            return False
        return -90 <= latitude <= 90 and -180 <= longitude <= 180

    def fetch_logistics_metadata(self, result: PlaceSearchResult) -> LogisticsMetadata:
        return LogisticsMetadata(
            opening_hours_note=_first_note_with_prefix(result.notes, "hours:")
            or "Google Places did not return opening-hours text.",
            ticketing_url=self.fetch_ticketing_url(result),
            metadata=result.metadata,
        )

    def fetch_ticketing_url(self, result: PlaceSearchResult) -> str | None:
        # Places verification is not a ticketing provider. Only pass through a
        # reliable public place URL when Google supplies one.
        return result.metadata.source_url if result.metadata else None

    def _verification_from_query(
        self,
        db: Session,
        query: PlaceSearchQuery,
    ) -> POIVerificationResult:
        if not self.validate_coordinates(query.latitude, query.longitude):
            return self._needs_review_result(
                query=query,
                confidence=0.0,
                notes=["Missing or invalid coordinates; manual review required."],
                warnings=["Missing or invalid coordinates."],
            )

        results = self.search_places(db, query)
        best = results[0] if results else None
        if best is None:
            return self._needs_review_result(
                query=query,
                confidence=0.0,
                notes=["Google Places returned no match; keep for manual review."],
                warnings=["No Google Places match found."],
            )

        logistics = self.fetch_logistics_metadata(best)
        if best.confidence < self.settings.min_confidence:
            status = "needs_review"
            notes = [
                *best.notes,
                (
                    "Google Places match is below the configured confidence "
                    f"threshold ({self.settings.min_confidence:.2f})."
                ),
            ]
            warnings = [
                *(best.metadata.warnings if best.metadata else []),
                "Low-confidence Google Places match.",
            ]
        else:
            status = "provider_verified"
            notes = best.notes
            warnings = best.metadata.warnings if best.metadata else []

        metadata = self._metadata(
            confidence_score=best.confidence,
            request_id=best.source_poi_id,
            source_url=best.metadata.source_url if best.metadata else None,
            raw_provider_reference=best.metadata.raw_provider_reference if best.metadata else None,
            latency_ms=best.metadata.latency_ms if best.metadata else None,
            warnings=warnings,
        )
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
            notes=notes,
            metadata=metadata,
        )

    def _result_from_place(
        self,
        place: dict[str, Any],
        query: PlaceSearchQuery,
        latency_ms: int | None,
    ) -> PlaceSearchResult:
        name = _place_name(place)
        address = _string_or_none(place.get("formattedAddress"))
        location = place.get("location") if isinstance(place.get("location"), dict) else {}
        latitude = _float_or_none(location.get("latitude"))
        longitude = _float_or_none(location.get("longitude"))
        name_score = _name_similarity(query.name, name)
        coordinate_score = _coordinate_score(
            query.latitude,
            query.longitude,
            latitude,
            longitude,
        )
        confidence = round((name_score * 0.75) + (coordinate_score * 0.25), 3)
        place_id = _string_or_none(place.get("id"))
        source_url = _string_or_none(place.get("googleMapsUri")) or _string_or_none(
            place.get("websiteUri")
        )
        notes = [
            "Matched with Google Places searchText.",
            f"name_score={name_score:.2f}",
            f"coordinate_score={coordinate_score:.2f}",
        ]
        hours_note = _opening_hours_note(place)
        if hours_note:
            notes.append(f"hours:{hours_note}")
        business_status = _string_or_none(place.get("businessStatus"))
        if business_status:
            notes.append(f"business_status={business_status}")

        return PlaceSearchResult(
            provider=self.provider_name,
            name=name,
            address=address,
            latitude=latitude,
            longitude=longitude,
            confidence=confidence,
            source_poi_id=place_id,
            notes=notes,
            metadata=self._metadata(
                confidence_score=confidence,
                request_id=place_id,
                source_url=source_url,
                raw_provider_reference=place_id,
                latency_ms=latency_ms,
                warnings=["Google Places result normalized; raw payload was not exposed."],
            ),
        )

    def _needs_review_result(
        self,
        query: PlaceSearchQuery,
        confidence: float,
        notes: list[str],
        warnings: list[str],
    ) -> POIVerificationResult:
        return POIVerificationResult(
            status="needs_review",
            provider=self.provider_name,
            confidence=confidence,
            verified_name=query.name,
            verified_address=None,
            verified_latitude=query.latitude,
            verified_longitude=query.longitude,
            opening_hours_note=None,
            ticketing_url=None,
            notes=notes,
            metadata=self._metadata(confidence_score=confidence, warnings=warnings),
        )

    def _metadata(
        self,
        *,
        confidence_score: float | None = None,
        request_id: str | None = None,
        source_url: str | None = None,
        raw_provider_reference: str | None = None,
        latency_ms: int | None = None,
        warnings: list[str] | None = None,
    ) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name=self.provider_name,
            provider_type=ProviderType.POI_VERIFICATION.value,
            provider_version=self.provider_version,
            request_id=request_id,
            confidence_score=confidence_score,
            source_url=source_url,
            generated_at=utc_now_iso(),
            verified_at=_now(),
            latency_ms=latency_ms,
            warnings=warnings or [],
            raw_provider_reference=raw_provider_reference,
        )


def _text_query(name: str, destination: DestinationModel | None) -> str:
    if destination is None:
        return name
    parts = [name, destination.name, destination.country]
    return ", ".join(part for part in parts if part)


def _place_name(place: dict[str, Any]) -> str:
    display_name = place.get("displayName")
    if isinstance(display_name, dict):
        text = display_name.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    fallback = place.get("name")
    if isinstance(fallback, str) and fallback.strip():
        return fallback.strip()
    return "Unknown place"


def _opening_hours_note(place: dict[str, Any]) -> str | None:
    opening_hours = place.get("regularOpeningHours")
    if not isinstance(opening_hours, dict):
        return None
    weekday_descriptions = opening_hours.get("weekdayDescriptions")
    if isinstance(weekday_descriptions, list) and weekday_descriptions:
        safe_values = [value for value in weekday_descriptions if isinstance(value, str)]
        return "; ".join(safe_values[:2]) if safe_values else None
    return None


def _first_note_with_prefix(notes: list[str], prefix: str) -> str | None:
    for note in notes:
        if note.startswith(prefix):
            return note.removeprefix(prefix)
    return None


def _float_or_none(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _string_or_none(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _provider_error(
    code: ProviderErrorCode,
    message: str,
    *,
    latency_ms: int | None = None,
) -> ProviderError:
    return ProviderError(
        code,
        message,
        metadata=ProviderMetadata(
            provider_name="google_places",
            provider_type=ProviderType.POI_VERIFICATION.value,
            provider_version="places-api-v1",
            generated_at=utc_now_iso(),
            latency_ms=latency_ms,
        ),
    )
