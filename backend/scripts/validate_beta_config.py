import argparse
import json
import sys

from app.core.config import get_settings
from app.core.provider_guards import require_external_call_allowed
from app.core.readiness import provider_status
from app.services.provider_contracts import ProviderError, ProviderErrorCode, ProviderType


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate safe Litinerary beta/deployment config.")
    parser.add_argument(
        "--profile",
        choices=["development", "test", "beta", "staging", "production"],
        default="beta",
    )
    args = parser.parse_args()
    settings = get_settings()
    errors: list[str] = []

    if settings.app_env != args.profile:
        errors.append(f"APP_ENV is {settings.app_env!r}; expected {args.profile!r}.")

    if args.profile in {"beta", "staging", "production"}:
        if settings.debug:
            errors.append("DEBUG must be false for beta/staging/production dry runs.")
        if settings.enable_admin_routes:
            errors.append("ENABLE_ADMIN_ROUTES must be false for beta/staging/production.")
        if settings.enable_debug_routes:
            errors.append("ENABLE_DEBUG_ROUTES must be false for beta/staging/production.")
        if "*" in settings.cors_allowed_origins:
            errors.append("CORS_ALLOWED_ORIGINS must not contain wildcard origins.")
        if settings.auth_allow_dev_user_fallback:
            errors.append("AUTH_ALLOW_DEV_USER_FALLBACK must be false for deployed profiles.")

    if args.profile in {"beta", "staging"}:
        if not settings.enable_mock_services:
            errors.append("Beta/staging dry run expects ENABLE_MOCK_SERVICES=true.")
        if settings.allow_external_calls:
            errors.append("Beta/staging dry run expects ALLOW_EXTERNAL_CALLS=false.")
        if any(
            [
                settings.enable_real_llm,
                settings.enable_real_vector_db,
                settings.enable_real_poi_provider,
                settings.enable_real_routing,
                settings.enable_real_ticketing,
                settings.enable_real_tts,
                settings.enable_affiliate_links,
            ]
        ):
            errors.append("Beta/staging dry run must keep all real provider flags disabled.")

    blocked = _external_call_blocked(settings)
    if args.profile in {"beta", "staging", "test"} and not blocked:
        errors.append("External-call guard did not block the dry-run provider check.")

    payload = {
        "profile": args.profile,
        "appEnv": settings.app_env,
        "debug": settings.debug,
        "adminRoutesEnabled": settings.enable_admin_routes,
        "debugRoutesEnabled": settings.enable_debug_routes,
        "mockServicesEnabled": settings.enable_mock_services,
        "externalCallsAllowed": settings.allow_external_calls,
        "externalCallGuardBlocked": blocked,
        "corsOriginCount": len(settings.cors_allowed_origins),
        "providers": provider_status(settings),
        "startupValidationNotes": settings.startup_validation_notes(),
        "errors": errors,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if errors else 0


def _external_call_blocked(settings) -> bool:
    try:
        require_external_call_allowed(
            provider_name="dry_run_provider",
            provider_type=ProviderType.LLM,
            feature_flag_name="ENABLE_REAL_LLM",
            feature_enabled=True,
            required_config={"DRY_RUN_API_KEY": "placeholder"},
            settings=settings,
        )
    except ProviderError as exc:
        return exc.code in {
            ProviderErrorCode.EXTERNAL_CALL_BLOCKED,
            ProviderErrorCode.REAL_PROVIDER_DISABLED,
            ProviderErrorCode.NOT_CONFIGURED,
        }
    return False


if __name__ == "__main__":
    sys.exit(main())
