from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class ProviderType(StrEnum):
    LLM = "llm"
    EMBEDDING = "embedding"
    VECTOR_DB = "vector_db"
    POI_VERIFICATION = "poi_verification"
    ROUTING = "routing"
    TICKETING = "ticketing"
    AFFILIATE = "affiliate"
    TTS = "tts"


class ProviderErrorCode(StrEnum):
    NOT_CONFIGURED = "provider_not_configured"
    EXTERNAL_CALL_BLOCKED = "external_call_blocked"
    UNAVAILABLE = "provider_unavailable"
    TIMEOUT = "provider_timeout"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"
    INPUT_TOO_LARGE = "input_too_large"
    UNSUPPORTED_BATCH_SIZE = "unsupported_batch_size"
    TOO_MANY_STOPS = "too_many_stops"
    INVALID_RESPONSE = "invalid_provider_response"
    LOW_CONFIDENCE = "low_confidence_result"
    UNSAFE_INPUT = "unsafe_or_copyright_restricted_input"
    UNSUPPORTED_LOCATION = "unsupported_location"
    NO_MATCH = "no_match_found"
    COST_LIMIT_EXCEEDED = "cost_limit_exceeded"
    REAL_PROVIDER_DISABLED = "real_provider_disabled"


@dataclass(frozen=True)
class ProviderMetadata:
    provider_name: str
    provider_type: str
    provider_version: str | None = None
    request_id: str | None = None
    confidence_score: float | None = None
    source_url: str | None = None
    generated_at: str | None = None
    verified_at: str | None = None
    model_name: str | None = None
    embedding_dimension: int | None = None
    cost_estimate: float | None = None
    latency_ms: int | None = None
    warnings: list[str] = field(default_factory=list)
    raw_provider_reference: str | None = None

    @classmethod
    def mock(
        cls,
        *,
        provider_name: str,
        provider_type: ProviderType,
        confidence_score: float | None = None,
        model_name: str | None = None,
        embedding_dimension: int | None = None,
        warnings: list[str] | None = None,
    ) -> "ProviderMetadata":
        return cls(
            provider_name=provider_name,
            provider_type=provider_type.value,
            provider_version="local-mock",
            request_id=f"mock-{uuid4().hex}",
            confidence_score=confidence_score,
            generated_at=utc_now_iso(),
            verified_at=utc_now_iso()
            if provider_type == ProviderType.POI_VERIFICATION
            else None,
            model_name=model_name,
            embedding_dimension=embedding_dimension,
            warnings=warnings or [],
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "provider_type": self.provider_type,
            "provider_version": self.provider_version,
            "request_id": self.request_id,
            "confidence_score": self.confidence_score,
            "source_url": self.source_url,
            "generated_at": self.generated_at,
            "verified_at": self.verified_at,
            "model_name": self.model_name,
            "embedding_dimension": self.embedding_dimension,
            "cost_estimate": self.cost_estimate,
            "latency_ms": self.latency_ms,
            "warnings": self.warnings,
        }


class ProviderError(RuntimeError):
    def __init__(
        self,
        code: ProviderErrorCode,
        message: str,
        *,
        metadata: ProviderMetadata | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.metadata = metadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "metadata": self.metadata.public_dict() if self.metadata else None,
        }


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def disabled_real_provider_error(provider_name: str, provider_type: ProviderType) -> ProviderError:
    return ProviderError(
        ProviderErrorCode.REAL_PROVIDER_DISABLED,
        (
            f"Real {provider_type.value} provider '{provider_name}' is configured, "
            "but real provider calls are disabled by feature flag."
        ),
        metadata=ProviderMetadata(
            provider_name=provider_name,
            provider_type=provider_type.value,
            generated_at=utc_now_iso(),
        ),
    )
