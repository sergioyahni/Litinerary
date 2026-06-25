from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings


def database_status(db: Session) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return {"status": "error"}
    return {"status": "ok"}


def provider_status(settings: Settings | None = None) -> list[dict[str, Any]]:
    resolved = settings or get_settings()
    return [
        _status(
            provider_type="auth",
            provider_name=resolved.auth_provider,
            real_enabled=resolved.enable_auth and resolved.auth_provider != "dev",
            credentials_configured=bool(
                resolved.auth_jwt_issuer
                and resolved.auth_jwt_audience
                and resolved.auth_jwt_algorithms
                and (resolved.auth_jwks_url or resolved.auth_provider_metadata_url)
            ),
            external_calls_allowed=resolved.allow_external_calls,
        ),
        _status(
            provider_type="llm",
            provider_name=resolved.llm_provider,
            real_enabled=resolved.enable_real_llm,
            credentials_configured=bool(resolved.llm_api_key),
            external_calls_allowed=resolved.allow_external_calls,
            required_configured=bool(resolved.llm_api_key and resolved.llm_model_name),
            environment_allowed=(
                resolved.app_env in resolved.external_call_allowed_environments
                and resolved.app_env in resolved.llm_allowed_environments
            ),
        ),
        _status(
            provider_type="vector_db",
            provider_name=resolved.vector_db_provider,
            real_enabled=resolved.enable_real_vector_db,
            credentials_configured=bool(resolved.qdrant_api_key or resolved.vector_db_api_key),
            external_calls_allowed=resolved.allow_external_calls,
        ),
        _status(
            provider_type="poi_verification",
            provider_name=resolved.poi_verification_provider,
            real_enabled=resolved.enable_real_poi_provider,
            credentials_configured=bool(resolved.poi_verification_api_key),
            external_calls_allowed=resolved.allow_external_calls,
        ),
        _status(
            provider_type="routing",
            provider_name=resolved.routing_provider,
            real_enabled=resolved.enable_real_routing,
            credentials_configured=bool(resolved.routing_api_key),
            external_calls_allowed=resolved.allow_external_calls,
        ),
        _status(
            provider_type="ticketing",
            provider_name=resolved.ticketing_provider,
            real_enabled=resolved.enable_real_ticketing,
            credentials_configured=bool(resolved.ticketing_api_key),
            external_calls_allowed=resolved.allow_external_calls,
        ),
        _status(
            provider_type="affiliate",
            provider_name=resolved.affiliate_provider,
            real_enabled=resolved.enable_affiliate_links,
            credentials_configured=bool(resolved.affiliate_api_key),
            external_calls_allowed=resolved.allow_external_calls,
        ),
        _status(
            provider_type="tts",
            provider_name=resolved.tts_provider,
            real_enabled=resolved.enable_real_tts,
            credentials_configured=bool(resolved.tts_api_key),
            external_calls_allowed=resolved.allow_external_calls,
        ),
    ]


def readiness_payload(db: Session, settings: Settings | None = None) -> dict[str, Any]:
    resolved = settings or get_settings()
    db_status = database_status(db)
    providers = provider_status(resolved)
    ready = db_status["status"] == "ok"
    return {
        "status": "ready" if ready else "degraded",
        "appEnv": resolved.app_env,
        "checks": {
            "database": db_status,
            "providers": providers,
            "externalCalls": {
                "allowed": resolved.allow_external_calls,
                "integrationTestsEnabled": resolved.enable_integration_tests,
                "stagedInternalLlmTestingEnabled": resolved.enable_staged_internal_llm_testing,
                "internalAccessGateEnabled": resolved.enable_internal_access_gate,
            },
            "mockServices": {
                "enabled": resolved.enable_mock_services,
            },
            "llmOperationalLimits": {
                "maxInputChars": resolved.llm_max_input_chars,
                "maxOutputTokens": resolved.llm_max_output_tokens,
                "maxLiveCallsPerRequest": resolved.llm_max_live_calls_per_request,
                "dailyLiveRequestCeiling": resolved.llm_daily_live_request_ceiling,
                "dailyEstimatedSpendCeilingUsd": resolved.llm_daily_estimated_spend_ceiling_usd,
                "latencyAlertThresholdMs": resolved.llm_latency_alert_threshold_ms,
                "errorRateAlertThresholdPercent": resolved.llm_error_rate_alert_threshold_percent,
                "itineraryGenerationMaxDays": resolved.itinerary_generation_max_days,
            },
        },
    }


def _status(
    *,
    provider_type: str,
    provider_name: str,
    real_enabled: bool,
    credentials_configured: bool,
    external_calls_allowed: bool,
    required_configured: bool | None = None,
    environment_allowed: bool | None = None,
) -> dict[str, Any]:
    mode = "real" if real_enabled else "mock"
    payload = {
        "providerType": provider_type,
        "providerName": provider_name,
        "mode": mode,
        "realEnabled": real_enabled,
        "credentialsConfigured": credentials_configured,
        "requiredConfigPresent": credentials_configured
        if required_configured is None
        else required_configured,
        "externalCallsAllowed": external_calls_allowed,
        "status": "configured"
        if real_enabled and (credentials_configured if required_configured is None else required_configured)
        else "mock",
    }
    if environment_allowed is not None:
        payload["environmentAllowed"] = environment_allowed
    return payload
