from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel
import os

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


LOCAL_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


class Settings(BaseModel):
    app_env: str = "development"
    debug: bool = True
    enable_admin_routes: bool = True
    enable_debug_routes: bool = True
    enable_mock_services: bool = True
    enable_real_llm: bool = False
    enable_real_vector_db: bool = False
    enable_real_poi_provider: bool = False
    enable_real_routing: bool = False
    enable_real_ticketing: bool = False
    enable_real_tts: bool = False
    enable_affiliate_links: bool = False
    allow_external_calls: bool = False
    enable_integration_tests: bool = False
    enable_staged_internal_llm_testing: bool = False
    enable_internal_access_gate: bool = False
    external_call_allowed_environments: list[str] = ["production"]
    enable_auth: bool = False
    auth_provider: str = "dev"
    auth_jwt_issuer: str | None = None
    auth_jwt_audience: str | None = None
    auth_jwt_algorithms: list[str] = ["dev"]
    auth_jwks_url: str | None = None
    auth_provider_metadata_url: str | None = None
    auth_user_id_claim: str = "sub"
    auth_roles_claim: str = "roles"
    auth_subscription_claim: str = "subscription_status"
    auth_email_claim: str = "email"
    auth_display_name_claim: str = "name"
    auth_required_for_user_features: bool = False
    auth_allow_dev_user_fallback: bool = True
    cors_allowed_origins: list[str] = LOCAL_CORS_ORIGINS
    database_url: str = "sqlite:///./litinerary.db"
    database_url_configured: bool = False
    ai_provider: str = "fake"
    llm_provider: str = "fake"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model_name: str = "gpt-4.1-mini"
    llm_timeout_seconds: float = 20.0
    llm_max_tokens: int = 1200
    llm_output_token_parameter: str = "max_tokens"
    llm_max_input_chars: int = 12000
    llm_max_output_tokens: int = 1200
    llm_max_retries: int = 0
    llm_monthly_budget_usd: float | None = None
    llm_allowed_environments: list[str] = ["development", "production"]
    llm_max_live_calls_per_request: int = 4
    llm_daily_live_request_ceiling: int = 4
    llm_daily_estimated_spend_ceiling_usd: float = 0.0
    llm_latency_alert_threshold_ms: int = 5000
    llm_error_rate_alert_threshold_percent: float = 10.0
    poi_verification_provider: str = "mock"
    poi_verification_api_key: str | None = None
    poi_provider_base_url: str = "https://places.googleapis.com"
    poi_provider_timeout_seconds: float = 5.0
    poi_provider_result_limit: int = 5
    poi_provider_min_confidence: float = 0.82
    poi_provider_region_code: str | None = None
    poi_provider_language_code: str | None = None
    vector_provider: str = "fake"
    vector_db_provider: str = "fake"
    vector_db_api_key: str | None = None
    vector_dimension: int = 16
    vector_store_path: str | None = None
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection_prefix: str = "litinerary"
    qdrant_timeout_seconds: float = 5.0
    routing_provider: str = "mock"
    routing_api_key: str | None = None
    routing_base_url: str = "https://api.openrouteservice.org"
    routing_timeout_seconds: float = 5.0
    routing_max_stops: int = 10
    routing_supported_modes: list[str] = ["walking", "car_taxi"]
    routing_fallback_behavior: str = "mock"
    ticketing_provider: str = "mock"
    ticketing_api_key: str | None = None
    ticketing_base_url: str = "https://example.test"
    ticketing_timeout_seconds: float = 5.0
    affiliate_provider: str = "mock"
    affiliate_api_key: str | None = None
    affiliate_base_url: str = "https://example.test/books"
    affiliate_timeout_seconds: float = 5.0
    tts_provider: str = "mock"
    tts_api_key: str | None = None
    tts_base_url: str = "https://example.test/tts"
    tts_timeout_seconds: float = 5.0
    anonymous_itinerary_generations_per_day: int = 100
    registered_user_itinerary_generations_per_day: int = 250
    subscriber_chat_messages_per_day: int = 250
    anonymous_itinerary_generations_per_minute: int = 10
    registered_user_itinerary_generations_per_minute: int = 30
    subscriber_chat_messages_per_minute: int = 60
    vector_search_max_results: int = 20
    poi_verification_max_batch_size: int = 25
    ticketing_lookup_max_requests_per_itinerary: int = 10
    enable_durable_usage_controls: bool = False
    provider_daily_request_ceiling: int = 1000
    provider_daily_cost_ceiling_usd: float = 0.0
    usage_counter_retention_days: int = 90
    itinerary_generation_max_days: int = 7

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_staged_internal(self) -> bool:
        return self.app_env == "internal"

    @property
    def is_development_like(self) -> bool:
        return self.app_env in {"development", "test"}

    @property
    def is_deployed_environment(self) -> bool:
        return self.app_env in {"internal", "beta", "staging", "production"}

    @property
    def is_standard_test_mode(self) -> bool:
        return self.app_env == "test" and not self.enable_integration_tests

    def deployed_auth_validation_errors(self) -> list[str]:
        if not self.is_deployed_environment:
            return []

        errors: list[str] = []
        if not self.enable_auth:
            errors.append("ENABLE_AUTH=true is required in deployed environments.")
        if not self.auth_required_for_user_features:
            errors.append(
                "AUTH_REQUIRED_FOR_USER_FEATURES=true is required in deployed environments."
            )
        if self.auth_allow_dev_user_fallback:
            errors.append("AUTH_ALLOW_DEV_USER_FALLBACK=false is required in deployed environments.")
        if not self.auth_provider or self.auth_provider == "dev":
            errors.append("AUTH_PROVIDER must identify a managed provider and must not be dev.")
        if not self.auth_jwt_issuer:
            errors.append("AUTH_JWT_ISSUER is required in deployed environments.")
        if not self.auth_jwt_audience:
            errors.append("AUTH_JWT_AUDIENCE is required in deployed environments.")
        if (
            not self.auth_jwt_algorithms
            or "dev" in self.auth_jwt_algorithms
            or "none" in [algorithm.lower() for algorithm in self.auth_jwt_algorithms]
        ):
            errors.append(
                "AUTH_JWT_ALGORITHMS must contain production JWT algorithms, not dev or none."
            )
        if not self.auth_jwks_url and not self.auth_provider_metadata_url:
            errors.append(
                "AUTH_JWKS_URL or AUTH_PROVIDER_METADATA_URL is required in deployed environments."
            )
        if not self.allow_external_calls:
            errors.append(
                "ALLOW_EXTERNAL_CALLS=true is required so managed-auth JWKS/provider metadata "
                "can be validated."
            )
        if self.app_env not in self.external_call_allowed_environments:
            errors.append(
                f"EXTERNAL_CALL_ALLOWED_ENVIRONMENTS must include {self.app_env} for managed auth."
            )
        return errors

    def startup_validation_notes(self) -> list[str]:
        notes: list[str] = []
        provider_credentials = [
            ("LLM", self.llm_provider, self.llm_api_key),
            ("POI verification", self.poi_verification_provider, self.poi_verification_api_key),
            ("Routing", self.routing_provider, self.routing_api_key),
            ("Ticketing", self.ticketing_provider, self.ticketing_api_key),
            ("Affiliate", self.affiliate_provider, self.affiliate_api_key),
            ("TTS", self.tts_provider, self.tts_api_key),
        ]
        for label, provider, api_key in provider_credentials:
            if provider not in {"fake", "mock", "none"} and not api_key:
                notes.append(
                    f"{label} provider '{provider}' is configured without credentials; "
                    "real integration calls require the matching feature flag and credentials."
                )
        if self.is_production and "*" in self.cors_allowed_origins:
            notes.append("Wildcard CORS origin ignored in production.")
        notes.extend(self.deployed_auth_validation_errors())
        notes.extend(self.database_configuration_validation_errors())
        if self.enable_auth and self.auth_provider != "dev" and not self.allow_external_calls:
            notes.append(
                "Managed auth provider validation is configured, but "
                "ALLOW_EXTERNAL_CALLS=false blocks JWKS/provider metadata requests."
            )
        if self.is_production and self.auth_allow_dev_user_fallback:
            notes.append("Development user fallback is ignored in production.")
        if any(
            [
                self.enable_real_llm,
                self.enable_real_vector_db,
                self.enable_real_poi_provider,
                self.enable_real_routing,
                self.enable_real_ticketing,
                self.enable_real_tts,
                self.enable_affiliate_links,
            ]
        ) and not self.allow_external_calls:
            notes.append(
                "Real provider feature flags are configured, but ALLOW_EXTERNAL_CALLS=false "
                "blocks all live external requests."
            )
        if self.is_standard_test_mode and self.allow_external_calls:
            notes.append(
                "ALLOW_EXTERNAL_CALLS is ignored during standard APP_ENV=test runs unless "
                "ENABLE_INTEGRATION_TESTS=true."
            )
        if self.enable_real_llm:
            if self.is_staged_internal and not self.enable_staged_internal_llm_testing:
                notes.append(
                    "APP_ENV=internal live LLM usage requires "
                    "ENABLE_STAGED_INTERNAL_LLM_TESTING=true and remains no-go until "
                    "staged-readiness blockers are satisfied."
                )
            if self.is_staged_internal and not self.enable_internal_access_gate:
                notes.append(
                    "APP_ENV=internal live LLM usage requires "
                    "ENABLE_INTERNAL_ACCESS_GATE=true. This is a minimal fail-closed "
                    "placeholder; production-grade auth or network allowlisting remains "
                    "a staged-readiness blocker."
                )
            if self.ai_provider != "openai_compatible":
                notes.append(
                    "ENABLE_REAL_LLM=true currently requires "
                    "LLM_PROVIDER=openai_compatible or LITINERARY_AI_PROVIDER=openai_compatible."
                )
            if self.app_env == "test":
                notes.append("ENABLE_REAL_LLM must not be enabled during standard test runs.")
            if self.app_env not in self.external_call_allowed_environments:
                notes.append(
                    f"APP_ENV={self.app_env} is not allowed by "
                    "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS."
                )
            if self.app_env not in self.llm_allowed_environments:
                notes.append(
                    f"APP_ENV={self.app_env} is not allowed by LLM_ALLOWED_ENVIRONMENTS."
                )
            if not self.llm_api_key:
                notes.append("LLM_API_KEY is required when ENABLE_REAL_LLM=true.")
            if not self.llm_model_name:
                notes.append("LLM_MODEL_NAME is required when ENABLE_REAL_LLM=true.")
            if self.llm_timeout_seconds <= 0:
                notes.append("LLM_TIMEOUT_SECONDS must be positive.")
            if self.llm_max_tokens <= 0:
                notes.append("LLM_MAX_TOKENS must be positive.")
            if self.llm_output_token_parameter not in {"max_tokens", "max_completion_tokens"}:
                notes.append(
                    "LLM_OUTPUT_TOKEN_PARAMETER must be max_tokens or max_completion_tokens."
                )
            if self.llm_max_input_chars <= 0:
                notes.append("LLM_MAX_INPUT_CHARS must be positive.")
            if self.llm_max_output_tokens <= 0:
                notes.append("LLM_MAX_OUTPUT_TOKENS must be positive.")
            if self.llm_max_retries < 0:
                notes.append("LLM_MAX_RETRIES cannot be negative.")
            if self.llm_max_live_calls_per_request <= 0:
                notes.append("LLM_MAX_LIVE_CALLS_PER_REQUEST must be positive.")
            if self.llm_daily_live_request_ceiling <= 0:
                notes.append("LLM_DAILY_LIVE_REQUEST_CEILING must be positive for live LLM use.")
            if self.llm_latency_alert_threshold_ms <= 0:
                notes.append("LLM_LATENCY_ALERT_THRESHOLD_MS must be positive.")
            if not 0 <= self.llm_error_rate_alert_threshold_percent <= 100:
                notes.append("LLM_ERROR_RATE_ALERT_THRESHOLD_PERCENT must be between 0 and 100.")
        if self.itinerary_generation_max_days <= 0:
            notes.append("ITINERARY_GENERATION_MAX_DAYS must be positive.")
        notes.extend(self.usage_control_validation_errors())
        if self.enable_real_vector_db and self.vector_db_provider == "qdrant":
            if not self.qdrant_url:
                notes.append("QDRANT_URL is required when ENABLE_REAL_VECTOR_DB=true.")
            if self.vector_dimension <= 0:
                notes.append("LITINERARY_VECTOR_DIMENSION must be positive for Qdrant.")
        elif self.vector_db_provider == "qdrant" and not self.qdrant_url:
            notes.append(
                "Vector DB provider 'qdrant' is configured without QDRANT_URL; "
                "real integration calls remain disabled unless ENABLE_REAL_VECTOR_DB=true."
            )
        if self.enable_real_poi_provider:
            if self.poi_verification_provider != "google_places":
                notes.append(
                    "ENABLE_REAL_POI_PROVIDER=true currently requires "
                    "POI_PROVIDER=google_places or POI_VERIFICATION_PROVIDER=google_places."
                )
            if not self.poi_verification_api_key:
                notes.append(
                    "POI_PROVIDER_API_KEY, GOOGLE_PLACES_API_KEY, or "
                    "POI_VERIFICATION_API_KEY is required when ENABLE_REAL_POI_PROVIDER=true."
                )
            if self.poi_provider_timeout_seconds <= 0:
                notes.append("POI_PROVIDER_TIMEOUT_SECONDS must be positive.")
            if self.poi_provider_result_limit <= 0:
                notes.append("POI_PROVIDER_RESULT_LIMIT must be positive.")
            if not 0 <= self.poi_provider_min_confidence <= 1:
                notes.append("POI_PROVIDER_MIN_CONFIDENCE must be between 0 and 1.")
        if self.enable_real_routing:
            if self.routing_provider != "openrouteservice":
                notes.append(
                    "ENABLE_REAL_ROUTING=true currently requires "
                    "ROUTING_PROVIDER=openrouteservice."
                )
            if not self.routing_api_key:
                notes.append(
                    "ROUTING_API_KEY or OPENROUTESERVICE_API_KEY is required when "
                    "ENABLE_REAL_ROUTING=true."
                )
            if self.routing_timeout_seconds <= 0:
                notes.append("ROUTING_TIMEOUT_SECONDS must be positive.")
            if self.routing_max_stops <= 1:
                notes.append("ROUTING_MAX_STOPS must be greater than 1.")
            if not self.routing_supported_modes:
                notes.append("ROUTING_SUPPORTED_MODES must contain at least one mode.")
            if self.routing_fallback_behavior not in {"mock", "error"}:
                notes.append("ROUTING_FALLBACK_BEHAVIOR must be mock or error.")
        if self.enable_real_ticketing:
            if self.ticketing_provider == "mock":
                notes.append(
                    "ENABLE_REAL_TICKETING=true requires a real ticketing provider, "
                    "but no real ticketing adapter is implemented yet."
                )
            if not self.ticketing_api_key:
                notes.append("TICKETING_API_KEY is required when ENABLE_REAL_TICKETING=true.")
            if self.ticketing_timeout_seconds <= 0:
                notes.append("TICKETING_TIMEOUT_SECONDS must be positive.")
        if self.enable_real_tts:
            notes.append(
                "ENABLE_REAL_TTS=true is reserved for future TTS adapters; "
                "no real text-to-speech provider is implemented yet."
            )
            if not self.tts_api_key:
                notes.append("TTS_API_KEY is required when ENABLE_REAL_TTS=true.")
            if self.tts_timeout_seconds <= 0:
                notes.append("TTS_TIMEOUT_SECONDS must be positive.")
        if self.enable_affiliate_links:
            if self.affiliate_provider != "mock" and not self.affiliate_api_key:
                notes.append(
                    "AFFILIATE_API_KEY is required when ENABLE_AFFILIATE_LINKS=true "
                    "and AFFILIATE_PROVIDER is not mock."
                )
            if self.affiliate_timeout_seconds <= 0:
                notes.append("AFFILIATE_TIMEOUT_SECONDS must be positive.")
        return notes

    def usage_control_validation_errors(self) -> list[str]:
        errors: list[str] = []
        positive_limits = [
            ("ANONYMOUS_ITINERARY_GENERATIONS_PER_DAY", self.anonymous_itinerary_generations_per_day),
            ("REGISTERED_USER_ITINERARY_GENERATIONS_PER_DAY", self.registered_user_itinerary_generations_per_day),
            ("SUBSCRIBER_CHAT_MESSAGES_PER_DAY", self.subscriber_chat_messages_per_day),
            ("ANONYMOUS_ITINERARY_GENERATIONS_PER_MINUTE", self.anonymous_itinerary_generations_per_minute),
            ("REGISTERED_USER_ITINERARY_GENERATIONS_PER_MINUTE", self.registered_user_itinerary_generations_per_minute),
            ("SUBSCRIBER_CHAT_MESSAGES_PER_MINUTE", self.subscriber_chat_messages_per_minute),
            ("PROVIDER_DAILY_REQUEST_CEILING", self.provider_daily_request_ceiling),
            ("USAGE_COUNTER_RETENTION_DAYS", self.usage_counter_retention_days),
        ]
        for name, value in positive_limits:
            if value <= 0:
                errors.append(f"{name} must be positive.")
        if self.provider_daily_cost_ceiling_usd < 0:
            errors.append("PROVIDER_DAILY_COST_CEILING_USD cannot be negative.")
        if self.is_deployed_environment and not self.enable_durable_usage_controls:
            errors.append(
                "ENABLE_DURABLE_USAGE_CONTROLS=true is required in deployed environments."
            )
        return errors

    def database_configuration_validation_errors(self) -> list[str]:
        errors: list[str] = []
        try:
            parsed = make_url(self.database_url)
        except (ArgumentError, ValueError):
            return ["LITINERARY_DATABASE_URL is malformed or unsupported."]

        if not parsed.drivername:
            errors.append("LITINERARY_DATABASE_URL is malformed or unsupported.")

        if self.is_deployed_environment and not self.database_url_configured:
            errors.append("LITINERARY_DATABASE_URL is required in deployed environments.")

        if self.is_deployed_environment and self.database_url == "sqlite:///./litinerary.db":
            errors.append(
                "LITINERARY_DATABASE_URL must not use the default local SQLite fallback "
                "in deployed environments."
            )

        return errors

    def safe_database_dialect(self) -> str:
        try:
            return make_url(self.database_url).drivername
        except (ArgumentError, ValueError):
            return "invalid"


@lru_cache
def get_settings() -> Settings:
    app_env = _normalized_app_env(os.getenv("APP_ENV", "development"))
    default_enabled = app_env in {"development", "test"}
    cors_allowed_origins = _parse_cors_origins(
        os.getenv("CORS_ALLOWED_ORIGINS"),
        app_env=app_env,
    )
    ai_provider = os.getenv("LITINERARY_AI_PROVIDER", os.getenv("LLM_PROVIDER", "fake"))
    vector_provider = os.getenv(
        "LITINERARY_VECTOR_PROVIDER",
        os.getenv("VECTOR_DB_PROVIDER", "fake"),
    )
    poi_provider = os.getenv(
        "LITINERARY_POI_VERIFICATION_PROVIDER",
        os.getenv("POI_PROVIDER", os.getenv("POI_VERIFICATION_PROVIDER", "mock")),
    )

    raw_database_url = os.getenv("LITINERARY_DATABASE_URL")
    database_url_configured = raw_database_url is not None and bool(raw_database_url.strip())

    return Settings(
        app_env=app_env,
        debug=_env_bool("DEBUG", default_enabled),
        enable_admin_routes=_env_bool("ENABLE_ADMIN_ROUTES", default_enabled),
        enable_debug_routes=_env_bool("ENABLE_DEBUG_ROUTES", default_enabled),
        enable_mock_services=_env_bool("ENABLE_MOCK_SERVICES", default_enabled),
        enable_real_llm=_env_bool("ENABLE_REAL_LLM", False),
        enable_real_vector_db=_env_bool("ENABLE_REAL_VECTOR_DB", False),
        enable_real_poi_provider=_env_bool("ENABLE_REAL_POI_PROVIDER", False),
        enable_real_routing=_env_bool("ENABLE_REAL_ROUTING", False),
        enable_real_ticketing=_env_bool("ENABLE_REAL_TICKETING", False),
        enable_real_tts=_env_bool("ENABLE_REAL_TTS", False),
        enable_affiliate_links=_env_bool("ENABLE_AFFILIATE_LINKS", False),
        allow_external_calls=_env_bool("ALLOW_EXTERNAL_CALLS", False),
        enable_integration_tests=_env_bool("ENABLE_INTEGRATION_TESTS", False),
        enable_staged_internal_llm_testing=_env_bool(
            "ENABLE_STAGED_INTERNAL_LLM_TESTING",
            False,
        ),
        enable_internal_access_gate=_env_bool("ENABLE_INTERNAL_ACCESS_GATE", False),
        external_call_allowed_environments=_parse_csv(
            os.getenv("EXTERNAL_CALL_ALLOWED_ENVIRONMENTS"),
            ["production"],
        ),
        enable_auth=_env_bool("ENABLE_AUTH", False),
        auth_provider=os.getenv("AUTH_PROVIDER", "dev"),
        auth_jwt_issuer=os.getenv("AUTH_JWT_ISSUER"),
        auth_jwt_audience=os.getenv("AUTH_JWT_AUDIENCE"),
        auth_jwt_algorithms=_parse_csv(os.getenv("AUTH_JWT_ALGORITHMS"), ["dev"]),
        auth_jwks_url=os.getenv("AUTH_JWKS_URL"),
        auth_provider_metadata_url=os.getenv("AUTH_PROVIDER_METADATA_URL"),
        auth_user_id_claim=os.getenv("AUTH_USER_ID_CLAIM", "sub"),
        auth_roles_claim=os.getenv("AUTH_ROLES_CLAIM", "roles"),
        auth_subscription_claim=os.getenv(
            "AUTH_SUBSCRIPTION_CLAIM",
            "subscription_status",
        ),
        auth_email_claim=os.getenv("AUTH_EMAIL_CLAIM", "email"),
        auth_display_name_claim=os.getenv("AUTH_DISPLAY_NAME_CLAIM", "name"),
        auth_required_for_user_features=_env_bool(
            "AUTH_REQUIRED_FOR_USER_FEATURES",
            _env_bool("ENABLE_AUTH", False),
        ),
        auth_allow_dev_user_fallback=_env_bool("AUTH_ALLOW_DEV_USER_FALLBACK", default_enabled),
        cors_allowed_origins=cors_allowed_origins,
        database_url=raw_database_url.strip() if database_url_configured else "sqlite:///./litinerary.db",
        database_url_configured=database_url_configured,
        ai_provider=ai_provider,
        llm_provider=os.getenv("LLM_PROVIDER", ai_provider),
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        llm_model_name=os.getenv("LLM_MODEL_NAME", "gpt-4.1-mini"),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "20")),
        llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1200")),
        llm_output_token_parameter=os.getenv("LLM_OUTPUT_TOKEN_PARAMETER", "max_tokens"),
        llm_max_input_chars=int(os.getenv("LLM_MAX_INPUT_CHARS", "12000")),
        llm_max_output_tokens=int(
            os.getenv("LLM_MAX_OUTPUT_TOKENS", os.getenv("LLM_MAX_TOKENS", "1200"))
        ),
        llm_max_retries=int(os.getenv("LLM_MAX_RETRIES", "0")),
        llm_monthly_budget_usd=_env_float("LLM_MONTHLY_BUDGET_USD"),
        llm_allowed_environments=_parse_csv(
            os.getenv("LLM_ALLOWED_ENVIRONMENTS"),
            ["development", "production"],
        ),
        llm_max_live_calls_per_request=int(os.getenv("LLM_MAX_LIVE_CALLS_PER_REQUEST", "4")),
        llm_daily_live_request_ceiling=int(os.getenv("LLM_DAILY_LIVE_REQUEST_CEILING", "4")),
        llm_daily_estimated_spend_ceiling_usd=float(
            os.getenv(
                "LLM_DAILY_ESTIMATED_SPEND_CEILING_USD",
                os.getenv("PROVIDER_DAILY_COST_CEILING_USD", "0"),
            )
        ),
        llm_latency_alert_threshold_ms=int(os.getenv("LLM_LATENCY_ALERT_THRESHOLD_MS", "5000")),
        llm_error_rate_alert_threshold_percent=float(
            os.getenv("LLM_ERROR_RATE_ALERT_THRESHOLD_PERCENT", "10")
        ),
        poi_verification_provider=poi_provider,
        poi_verification_api_key=(
            os.getenv("POI_PROVIDER_API_KEY")
            or os.getenv("GOOGLE_PLACES_API_KEY")
            or os.getenv("POI_VERIFICATION_API_KEY")
        ),
        poi_provider_base_url=os.getenv(
            "POI_PROVIDER_BASE_URL",
            "https://places.googleapis.com",
        ),
        poi_provider_timeout_seconds=float(os.getenv("POI_PROVIDER_TIMEOUT_SECONDS", "5")),
        poi_provider_result_limit=int(os.getenv("POI_PROVIDER_RESULT_LIMIT", "5")),
        poi_provider_min_confidence=float(os.getenv("POI_PROVIDER_MIN_CONFIDENCE", "0.82")),
        poi_provider_region_code=os.getenv("POI_PROVIDER_REGION_CODE") or None,
        poi_provider_language_code=os.getenv("POI_PROVIDER_LANGUAGE_CODE") or None,
        vector_provider=vector_provider,
        vector_db_provider=os.getenv("VECTOR_DB_PROVIDER", vector_provider),
        vector_db_api_key=os.getenv("VECTOR_DB_API_KEY"),
        vector_dimension=int(os.getenv("LITINERARY_VECTOR_DIMENSION", "16")),
        vector_store_path=os.getenv("LITINERARY_VECTOR_STORE_PATH"),
        qdrant_url=os.getenv("QDRANT_URL") or os.getenv("VECTOR_DB_URL"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY") or os.getenv("VECTOR_DB_API_KEY"),
        qdrant_collection_prefix=os.getenv("QDRANT_COLLECTION_PREFIX", "litinerary"),
        qdrant_timeout_seconds=float(os.getenv("QDRANT_TIMEOUT_SECONDS", "5")),
        routing_provider=os.getenv("ROUTING_PROVIDER", "mock"),
        routing_api_key=os.getenv("OPENROUTESERVICE_API_KEY") or os.getenv("ROUTING_API_KEY"),
        routing_base_url=os.getenv(
            "ROUTING_BASE_URL",
            "https://api.openrouteservice.org",
        ),
        routing_timeout_seconds=float(os.getenv("ROUTING_TIMEOUT_SECONDS", "5")),
        routing_max_stops=int(os.getenv("ROUTING_MAX_STOPS", "10")),
        routing_supported_modes=_parse_csv(
            os.getenv("ROUTING_SUPPORTED_MODES"),
            ["walking", "car_taxi"],
        ),
        routing_fallback_behavior=os.getenv("ROUTING_FALLBACK_BEHAVIOR", "mock"),
        ticketing_provider=os.getenv("TICKETING_PROVIDER", "mock"),
        ticketing_api_key=os.getenv("TICKETING_API_KEY"),
        ticketing_base_url=os.getenv("TICKETING_BASE_URL", "https://example.test"),
        ticketing_timeout_seconds=float(os.getenv("TICKETING_TIMEOUT_SECONDS", "5")),
        affiliate_provider=os.getenv("AFFILIATE_PROVIDER", "mock"),
        affiliate_api_key=os.getenv("AFFILIATE_API_KEY"),
        affiliate_base_url=os.getenv("AFFILIATE_BASE_URL", "https://example.test/books"),
        affiliate_timeout_seconds=float(os.getenv("AFFILIATE_TIMEOUT_SECONDS", "5")),
        tts_provider=os.getenv("TTS_PROVIDER", "mock"),
        tts_api_key=os.getenv("TTS_API_KEY") or os.getenv("TEXT_TO_SPEECH_API_KEY"),
        tts_base_url=os.getenv("TTS_BASE_URL", "https://example.test/tts"),
        tts_timeout_seconds=float(os.getenv("TTS_TIMEOUT_SECONDS", "5")),
        anonymous_itinerary_generations_per_day=int(
            os.getenv("ANONYMOUS_ITINERARY_GENERATIONS_PER_DAY", "100")
        ),
        registered_user_itinerary_generations_per_day=int(
            os.getenv("REGISTERED_USER_ITINERARY_GENERATIONS_PER_DAY", "250")
        ),
        subscriber_chat_messages_per_day=int(
            os.getenv("SUBSCRIBER_CHAT_MESSAGES_PER_DAY", "250")
        ),
        anonymous_itinerary_generations_per_minute=int(
            os.getenv("ANONYMOUS_ITINERARY_GENERATIONS_PER_MINUTE", "10")
        ),
        registered_user_itinerary_generations_per_minute=int(
            os.getenv("REGISTERED_USER_ITINERARY_GENERATIONS_PER_MINUTE", "30")
        ),
        subscriber_chat_messages_per_minute=int(
            os.getenv("SUBSCRIBER_CHAT_MESSAGES_PER_MINUTE", "60")
        ),
        vector_search_max_results=int(os.getenv("VECTOR_SEARCH_MAX_RESULTS", "20")),
        poi_verification_max_batch_size=int(
            os.getenv("POI_VERIFICATION_MAX_BATCH_SIZE", "25")
        ),
        ticketing_lookup_max_requests_per_itinerary=int(
            os.getenv("TICKETING_LOOKUP_MAX_REQUESTS_PER_ITINERARY", "10")
        ),
        enable_durable_usage_controls=_env_bool("ENABLE_DURABLE_USAGE_CONTROLS", False),
        provider_daily_request_ceiling=int(os.getenv("PROVIDER_DAILY_REQUEST_CEILING", "1000")),
        provider_daily_cost_ceiling_usd=float(
            os.getenv("PROVIDER_DAILY_COST_CEILING_USD", "0")
        ),
        usage_counter_retention_days=int(os.getenv("USAGE_COUNTER_RETENTION_DAYS", "90")),
        itinerary_generation_max_days=int(os.getenv("ITINERARY_GENERATION_MAX_DAYS", "7")),
    )


def database_path_from_url(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None
    return Path(database_url.replace("sqlite:///", "", 1))


def _normalized_app_env(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"internal", "staged-internal", "staged_internal"}:
        return "internal"
    if normalized in {"development", "test", "beta", "staging", "production"}:
        return normalized
    return "development"


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_cors_origins(raw_value: str | None, app_env: str) -> list[str]:
    if raw_value is None or not raw_value.strip():
        return [] if app_env == "production" else LOCAL_CORS_ORIGINS

    origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    if app_env == "production":
        origins = [origin for origin in origins if origin != "*"]
    return origins


def _parse_csv(raw_value: str | None, default: list[str]) -> list[str]:
    if raw_value is None or not raw_value.strip():
        return default
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _env_float(name: str) -> float | None:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return None
    return float(raw_value)
