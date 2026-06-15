from collections.abc import Mapping, Sequence

from app.core.config import Settings, get_settings
from app.core.observability import log_provider_blocked, record_provider_selection
from app.services.provider_contracts import (
    ProviderError,
    ProviderErrorCode,
    ProviderMetadata,
    ProviderType,
)


MOCK_PROVIDER_NAMES = {"fake", "mock", "none"}


def is_mock_provider(provider_name: str | None) -> bool:
    return (provider_name or "mock").strip().lower() in MOCK_PROVIDER_NAMES


def require_external_call_allowed(
    *,
    provider_name: str,
    provider_type: ProviderType | str,
    feature_flag_name: str,
    feature_enabled: bool,
    required_config: Mapping[str, object | None] | None = None,
    allowed_environments: Sequence[str] | None = None,
    settings: Settings | None = None,
) -> None:
    resolved = settings or get_settings()
    provider_type_value = (
        provider_type.value if isinstance(provider_type, ProviderType) else provider_type
    )
    metadata = ProviderMetadata(
        provider_name=provider_name,
        provider_type=provider_type_value,
        generated_at=None,
    )
    record_provider_selection(
        provider_type=provider_type_value,
        provider_name=provider_name,
        mode="mock" if is_mock_provider(provider_name) else "real",
    )

    if not feature_enabled:
        log_provider_blocked(
            provider_type=provider_type_value,
            provider_name=provider_name,
            reason=ProviderErrorCode.REAL_PROVIDER_DISABLED.value,
        )
        raise ProviderError(
            ProviderErrorCode.REAL_PROVIDER_DISABLED,
            (
                f"Provider '{provider_name}' is blocked because "
                f"{feature_flag_name}=false."
            ),
            metadata=metadata,
        )

    if resolved.is_standard_test_mode:
        log_provider_blocked(
            provider_type=provider_type_value,
            provider_name=provider_name,
            reason=ProviderErrorCode.EXTERNAL_CALL_BLOCKED.value,
        )
        raise ProviderError(
            ProviderErrorCode.EXTERNAL_CALL_BLOCKED,
            (
                "External provider calls are blocked during standard APP_ENV=test runs. "
                "Set ENABLE_INTEGRATION_TESTS=true and ALLOW_EXTERNAL_CALLS=true only for "
                "explicit live integration tests."
            ),
            metadata=metadata,
        )

    if not resolved.allow_external_calls:
        log_provider_blocked(
            provider_type=provider_type_value,
            provider_name=provider_name,
            reason=ProviderErrorCode.EXTERNAL_CALL_BLOCKED.value,
        )
        raise ProviderError(
            ProviderErrorCode.EXTERNAL_CALL_BLOCKED,
            (
                "External provider calls are blocked by ALLOW_EXTERNAL_CALLS=false. "
                "Use mock/fake providers for local development and standard tests."
            ),
            metadata=metadata,
        )

    missing = [
        name
        for name, value in (required_config or {}).items()
        if value is None or (isinstance(value, str) and not value.strip())
    ]
    if missing:
        log_provider_blocked(
            provider_type=provider_type_value,
            provider_name=provider_name,
            reason=ProviderErrorCode.NOT_CONFIGURED.value,
        )
        raise ProviderError(
            ProviderErrorCode.NOT_CONFIGURED,
            (
                f"Provider '{provider_name}' cannot make external calls because "
                "required configuration is missing: "
                + ", ".join(missing)
            ),
            metadata=metadata,
        )

    integration_test_mode = resolved.app_env == "test" and resolved.enable_integration_tests
    allowed = list(allowed_environments or resolved.external_call_allowed_environments)
    if not integration_test_mode and resolved.app_env not in allowed:
        log_provider_blocked(
            provider_type=provider_type_value,
            provider_name=provider_name,
            reason=ProviderErrorCode.EXTERNAL_CALL_BLOCKED.value,
        )
        raise ProviderError(
            ProviderErrorCode.EXTERNAL_CALL_BLOCKED,
            (
                f"External calls for provider '{provider_name}' are not allowed in "
                f"APP_ENV={resolved.app_env}. Allowed environments: {', '.join(allowed)}."
            ),
            metadata=metadata,
        )
