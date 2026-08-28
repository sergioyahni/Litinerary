"""Validate safe local, staging-shaped, and production-shaped config profiles."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping

from app.core.config import get_settings
from app.core.readiness import provider_status


ENV_KEYS = {
    "APP_ENV",
    "DEBUG",
    "ENABLE_ADMIN_ROUTES",
    "ENABLE_DEBUG_ROUTES",
    "ENABLE_MOCK_SERVICES",
    "ALLOW_EXTERNAL_CALLS",
    "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS",
    "ENABLE_AUTH",
    "AUTH_PROVIDER",
    "AUTH_REQUIRED_FOR_USER_FEATURES",
    "AUTH_ALLOW_DEV_USER_FALLBACK",
    "AUTH_JWT_ISSUER",
    "AUTH_JWT_AUDIENCE",
    "AUTH_JWT_ALGORITHMS",
    "AUTH_JWKS_URL",
    "AUTH_PROVIDER_METADATA_URL",
    "CORS_ALLOWED_ORIGINS",
    "LITINERARY_DATABASE_URL",
    "ENABLE_DURABLE_USAGE_CONTROLS",
    "ENABLE_REAL_LLM",
    "ENABLE_REAL_VECTOR_DB",
    "ENABLE_REAL_POI_PROVIDER",
    "ENABLE_REAL_ROUTING",
    "ENABLE_REAL_TICKETING",
    "ENABLE_REAL_TTS",
    "ENABLE_AFFILIATE_LINKS",
    "LITINERARY_AI_PROVIDER",
    "LLM_PROVIDER",
    "LITINERARY_VECTOR_PROVIDER",
    "VECTOR_DB_PROVIDER",
    "LITINERARY_POI_VERIFICATION_PROVIDER",
    "POI_VERIFICATION_PROVIDER",
    "POI_PROVIDER",
    "ROUTING_PROVIDER",
    "TICKETING_PROVIDER",
    "AFFILIATE_PROVIDER",
    "TTS_PROVIDER",
    "PROVIDER_DAILY_COST_CEILING_USD",
    "PROVIDER_DAILY_REQUEST_CEILING",
    "USAGE_COUNTER_RETENTION_DAYS",
}


BASE_PROVIDER_LOCKS = {
    "ENABLE_REAL_LLM": "false",
    "ENABLE_REAL_VECTOR_DB": "false",
    "ENABLE_REAL_POI_PROVIDER": "false",
    "ENABLE_REAL_ROUTING": "false",
    "ENABLE_REAL_TICKETING": "false",
    "ENABLE_REAL_TTS": "false",
    "ENABLE_AFFILIATE_LINKS": "false",
    "LITINERARY_AI_PROVIDER": "fake",
    "LLM_PROVIDER": "fake",
    "LITINERARY_VECTOR_PROVIDER": "fake",
    "VECTOR_DB_PROVIDER": "fake",
    "LITINERARY_POI_VERIFICATION_PROVIDER": "mock",
    "POI_VERIFICATION_PROVIDER": "mock",
    "POI_PROVIDER": "mock",
    "ROUTING_PROVIDER": "mock",
    "TICKETING_PROVIDER": "mock",
    "AFFILIATE_PROVIDER": "mock",
    "TTS_PROVIDER": "mock",
    "PROVIDER_DAILY_COST_CEILING_USD": "0",
    "PROVIDER_DAILY_REQUEST_CEILING": "100",
    "USAGE_COUNTER_RETENTION_DAYS": "90",
}


DEPLOYED_COMMON = {
    **BASE_PROVIDER_LOCKS,
    "DEBUG": "false",
    "ENABLE_ADMIN_ROUTES": "false",
    "ENABLE_DEBUG_ROUTES": "false",
    "ALLOW_EXTERNAL_CALLS": "true",
    "ENABLE_AUTH": "true",
    "AUTH_PROVIDER": "auth0",
    "AUTH_REQUIRED_FOR_USER_FEATURES": "true",
    "AUTH_ALLOW_DEV_USER_FALLBACK": "false",
    "AUTH_JWT_ISSUER": "https://auth0-ci.example.test/",
    "AUTH_JWT_AUDIENCE": "litinerary-ci-api",
    "AUTH_JWT_ALGORITHMS": "RS256",
    "AUTH_JWKS_URL": "https://auth0-ci.example.test/.well-known/jwks.json",
    "CORS_ALLOWED_ORIGINS": "https://litinerary-ci.example.test",
    "LITINERARY_DATABASE_URL": "postgresql://user:pass@db.example.test:5432/litinerary",
    "ENABLE_DURABLE_USAGE_CONTROLS": "true",
}


PROFILES = {
    "development": {
        **BASE_PROVIDER_LOCKS,
        "APP_ENV": "development",
        "DEBUG": "true",
        "ENABLE_ADMIN_ROUTES": "true",
        "ENABLE_DEBUG_ROUTES": "true",
        "ENABLE_MOCK_SERVICES": "true",
        "ALLOW_EXTERNAL_CALLS": "false",
        "ENABLE_AUTH": "false",
        "AUTH_PROVIDER": "dev",
        "AUTH_REQUIRED_FOR_USER_FEATURES": "false",
        "AUTH_ALLOW_DEV_USER_FALLBACK": "true",
        "LITINERARY_DATABASE_URL": "sqlite:///./litinerary.db",
        "ENABLE_DURABLE_USAGE_CONTROLS": "false",
    },
    "test": {
        **BASE_PROVIDER_LOCKS,
        "APP_ENV": "test",
        "DEBUG": "true",
        "ENABLE_ADMIN_ROUTES": "true",
        "ENABLE_DEBUG_ROUTES": "true",
        "ENABLE_MOCK_SERVICES": "true",
        "ALLOW_EXTERNAL_CALLS": "false",
        "ENABLE_AUTH": "false",
        "AUTH_PROVIDER": "dev",
        "AUTH_REQUIRED_FOR_USER_FEATURES": "false",
        "AUTH_ALLOW_DEV_USER_FALLBACK": "true",
        "LITINERARY_DATABASE_URL": "sqlite:///./litinerary.db",
        "ENABLE_DURABLE_USAGE_CONTROLS": "false",
    },
    "staging": {
        **DEPLOYED_COMMON,
        "APP_ENV": "staging",
        "ENABLE_MOCK_SERVICES": "true",
        "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS": "staging",
    },
    "production": {
        **DEPLOYED_COMMON,
        "APP_ENV": "production",
        "ENABLE_MOCK_SERVICES": "false",
        "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS": "production",
    },
}


def main() -> int:
    results = []
    for profile, values in PROFILES.items():
        apply_env(values)
        settings = get_settings()
        providers = provider_status(settings)
        validate_profile(profile, settings, providers)
        results.append(
            {
                "profile": profile,
                "appEnv": settings.app_env,
                "authProvider": settings.auth_provider,
                "databaseConfigured": settings.database_url_configured,
                "durableUsage": settings.enable_durable_usage_controls,
            }
        )
    print(json.dumps({"profiles": results, "errors": []}, indent=2, sort_keys=True))
    return 0


def apply_env(values: Mapping[str, str]) -> None:
    for key in ENV_KEYS:
        os.environ.pop(key, None)
    os.environ.update(values)
    get_settings.cache_clear()


def validate_profile(profile: str, settings, providers: list[dict]) -> None:
    deployed = profile in {"staging", "production"}
    if settings.app_env != profile:
        raise SystemExit(f"{profile}: APP_ENV mismatch.")
    if deployed:
        errors = (
            settings.deployed_auth_validation_errors()
            + settings.database_configuration_validation_errors()
            + settings.usage_control_validation_errors()
        )
        if errors:
            raise SystemExit(f"{profile}: validation errors: {errors}")
        if settings.auth_provider == "dev" or settings.auth_allow_dev_user_fallback:
            raise SystemExit(f"{profile}: dev auth must be rejected.")
        if not settings.enable_durable_usage_controls:
            raise SystemExit(f"{profile}: durable usage controls required.")
        auth = next(provider for provider in providers if provider["providerType"] == "auth")
        if auth["mode"] != "real" or not auth["externalCallsAllowed"]:
            raise SystemExit(f"{profile}: Auth0 must be the only real external provider.")
    else:
        if settings.allow_external_calls:
            raise SystemExit(f"{profile}: local/test must not allow external calls by default.")
    for provider in providers:
        if deployed and provider["providerType"] == "auth":
            continue
        if provider["realEnabled"] or provider["externalCallsAllowed"]:
            raise SystemExit(f"{profile}: product provider {provider['providerType']} is live.")


if __name__ == "__main__":
    raise SystemExit(main())
