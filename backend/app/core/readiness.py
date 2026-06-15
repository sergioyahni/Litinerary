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
            provider_type="llm",
            provider_name=resolved.llm_provider,
            real_enabled=resolved.enable_real_llm,
            credentials_configured=bool(resolved.llm_api_key),
            external_calls_allowed=resolved.allow_external_calls,
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
            },
            "mockServices": {
                "enabled": resolved.enable_mock_services,
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
) -> dict[str, Any]:
    mode = "real" if real_enabled else "mock"
    return {
        "providerType": provider_type,
        "providerName": provider_name,
        "mode": mode,
        "realEnabled": real_enabled,
        "credentialsConfigured": credentials_configured,
        "externalCallsAllowed": external_calls_allowed,
        "status": "configured" if real_enabled and credentials_configured else "mock",
    }
