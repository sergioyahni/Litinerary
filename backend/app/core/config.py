from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel
import os


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
    ai_provider: str = "fake"
    llm_provider: str = "fake"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model_name: str = "gpt-4.1-mini"
    llm_timeout_seconds: float = 20.0
    llm_max_tokens: int = 1200
    llm_max_input_chars: int = 12000
    llm_max_output_tokens: int = 1200
    llm_max_retries: int = 0
    llm_monthly_budget_usd: float | None = None
    llm_allowed_environments: list[str] = ["development", "production"]
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
    vector_search_max_results: int = 20
    poi_verification_max_batch_size: int = 25
    ticketing_lookup_max_requests_per_itinerary: int = 10
    provider_daily_cost_ceiling_usd: float = 0.0

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development_like(self) -> bool:
        return self.app_env in {"development", "test"}

    @property
    def is_deployed_environment(self) -> bool:
        return self.app_env in {"beta", "staging", "production"}

    @property
    def is_standard_test_mode(self) -> bool:
        return self.app_env == "test" and not self.enable_integration_tests

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
        if self.enable_auth and self.is_production:
            if not self.auth_jwt_issuer:
                notes.append("AUTH_JWT_ISSUER is required when production auth is enabled.")
            if not self.auth_jwt_audience:
                notes.append("AUTH_JWT_AUDIENCE is required when production auth is enabled.")
            if not self.auth_jwks_url and not self.auth_provider_metadata_url:
                notes.append(
                    "AUTH_JWKS_URL or AUTH_PROVIDER_METADATA_URL is required when "
                    "production auth is enabled."
                )
            if self.auth_provider == "dev":
                notes.append("AUTH_PROVIDER=dev is not a production authentication provider.")
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
            if self.ai_provider != "openai_compatible":
                notes.append(
                    "ENABLE_REAL_LLM=true currently requires "
                    "LLM_PROVIDER=openai_compatible or LITINERARY_AI_PROVIDER=openai_compatible."
                )
            if self.app_env == "test":
                notes.append("ENABLE_REAL_LLM must not be enabled during standard test runs.")
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
            if self.llm_max_input_chars <= 0:
                notes.append("LLM_MAX_INPUT_CHARS must be positive.")
            if self.llm_max_output_tokens <= 0:
                notes.append("LLM_MAX_OUTPUT_TOKENS must be positive.")
            if self.llm_max_retries < 0:
                notes.append("LLM_MAX_RETRIES cannot be negative.")
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
        database_url=os.getenv("LITINERARY_DATABASE_URL", "sqlite:///./litinerary.db"),
        ai_provider=ai_provider,
        llm_provider=os.getenv("LLM_PROVIDER", ai_provider),
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        llm_model_name=os.getenv("LLM_MODEL_NAME", "gpt-4.1-mini"),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "20")),
        llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1200")),
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
        vector_search_max_results=int(os.getenv("VECTOR_SEARCH_MAX_RESULTS", "20")),
        poi_verification_max_batch_size=int(
            os.getenv("POI_VERIFICATION_MAX_BATCH_SIZE", "25")
        ),
        ticketing_lookup_max_requests_per_itinerary=int(
            os.getenv("TICKETING_LOOKUP_MAX_REQUESTS_PER_ITINERARY", "10")
        ),
        provider_daily_cost_ceiling_usd=float(
            os.getenv("PROVIDER_DAILY_COST_CEILING_USD", "0")
        ),
    )


def database_path_from_url(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None
    return Path(database_url.replace("sqlite:///", "", 1))


def _normalized_app_env(value: str) -> str:
    normalized = value.strip().lower()
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
