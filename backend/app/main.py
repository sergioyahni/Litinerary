import logging
import json
import re

from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.routes import api_router
from app.core.auth import validate_auth_startup
from app.core.config import get_settings
from app.core.database import get_db
from app.core.database_readiness import validate_database_startup
from app.core.observability import (
    EventName,
    REQUEST_ID_HEADER,
    configure_logging,
    elapsed_ms,
    log_event,
    new_request_id,
    request_id_context,
    start_timer,
)
from app.core.readiness import readiness_payload
from app.services.mock_ai_service import validate_llm_startup
from app.services.poi_verification import validate_poi_provider_startup
from app.services.routing_service import validate_routing_startup
from app.services.ticketing_service import validate_ticketing_startup
from app.services.affiliate_service import validate_affiliate_startup
from app.services.narration_service import validate_tts_startup
from app.services.provider_contracts import ProviderError, ProviderErrorCode
from app.services.usage_policy import validate_usage_startup
from app.services.vector_service import validate_vector_startup

settings = get_settings()
configure_logging()
validate_auth_startup(settings)
validate_database_startup(settings)
validate_llm_startup(settings)
validate_vector_startup(settings)
validate_poi_provider_startup(settings)
validate_routing_startup(settings)
validate_ticketing_startup(settings)
validate_affiliate_startup(settings)
validate_tts_startup(settings)
validate_usage_startup(settings)

app = FastAPI(
    title="Litinerary API",
    description="Phase 1 API skeleton for the Litinerary literary travel app.",
    version="0.1.0",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get(REQUEST_ID_HEADER) or new_request_id()
    token = request_id_context.set(request_id)
    started_at = start_timer()
    log_event(
        EventName.API_REQUEST_STARTED,
        category="api",
        method=request.method,
        path=request.url.path,
    )
    try:
        response = await call_next(request)
    except Exception as exc:
        log_event(
            EventName.API_REQUEST_FAILED,
            level=logging.ERROR,
            category="api",
            method=request.method,
            path=request.url.path,
            status_code=500,
            latency_ms=elapsed_ms(started_at),
            error_type=exc.__class__.__name__,
            success=False,
        )
        raise
    finally:
        request_id_context.reset(token)

    response.headers[REQUEST_ID_HEADER] = request_id
    log_event(
        EventName.API_REQUEST_COMPLETED,
        category="api",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=elapsed_ms(started_at),
        request_id=request_id,
    )
    return response


@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/readiness", tags=["health"])
def readiness_check(db: Session = Depends(get_db)) -> dict:
    payload = readiness_payload(db, settings=get_settings())
    log_event(
        EventName.READINESS_CHECKED,
        category="api",
        status=payload["status"],
        database_status=payload["checks"]["database"]["status"],
    )
    return payload


@app.exception_handler(ProviderError)
def provider_error_handler(request: Request, exc: ProviderError) -> JSONResponse:
    status_code = {
        ProviderErrorCode.RATE_LIMITED: status.HTTP_429_TOO_MANY_REQUESTS,
        ProviderErrorCode.QUOTA_EXCEEDED: status.HTTP_429_TOO_MANY_REQUESTS,
        ProviderErrorCode.INPUT_TOO_LARGE: status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        ProviderErrorCode.COST_LIMIT_EXCEEDED: status.HTTP_400_BAD_REQUEST,
        ProviderErrorCode.UNSUPPORTED_BATCH_SIZE: status.HTTP_400_BAD_REQUEST,
        ProviderErrorCode.TOO_MANY_STOPS: status.HTTP_400_BAD_REQUEST,
        ProviderErrorCode.UNSAFE_INPUT: status.HTTP_400_BAD_REQUEST,
        ProviderErrorCode.EXTERNAL_CALL_BLOCKED: status.HTTP_503_SERVICE_UNAVAILABLE,
        ProviderErrorCode.REAL_PROVIDER_DISABLED: status.HTTP_503_SERVICE_UNAVAILABLE,
        ProviderErrorCode.NOT_CONFIGURED: status.HTTP_503_SERVICE_UNAVAILABLE,
        ProviderErrorCode.UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    }.get(exc.code, status.HTTP_502_BAD_GATEWAY)
    log_event(
        EventName.PROVIDER_CALL_FAILED,
        level=logging.WARNING,
        category="provider",
        path=request.url.path,
        status_code=status_code,
        error_type=exc.code.value,
        provider_type=exc.metadata.provider_type if exc.metadata else None,
        provider_name=exc.metadata.provider_name if exc.metadata else None,
        success=False,
    )
    settings = get_settings()
    detail = _safe_provider_error_detail(exc)
    headers = None
    if exc.retry_after_seconds is not None:
        headers = {"Retry-After": str(max(0, exc.retry_after_seconds))}
    if settings.app_env == "development":
        diagnostics = _provider_error_diagnostics(exc)
        if diagnostics:
            detail["diagnostics"] = diagnostics
            headers = {
                **(headers or {}),
                "X-Litinerary-Provider-Diagnostics": _diagnostics_header(diagnostics),
            }
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
        headers=headers,
    )


app.include_router(api_router)


def _provider_error_diagnostics(exc: ProviderError) -> dict[str, str]:
    metadata = exc.metadata
    if metadata is None:
        return {}
    diagnostics: dict[str, str] = {
        "provider_name": _safe_diagnostic_value(metadata.provider_name),
        "provider_type": _safe_diagnostic_value(metadata.provider_type),
    }
    if metadata.request_id:
        diagnostics["request_id"] = _safe_diagnostic_value(metadata.request_id)
    for warning in metadata.warnings:
        if "=" not in warning:
            continue
        key, value = warning.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in {
            "provider_reached",
            "provider_http_status",
            "provider_error_type",
            "provider_error_code",
            "failure_category",
            "url_error_reason_type",
            "url_error_reason_category",
            "endpoint_kind",
            "endpoint_host",
            "endpoint_path",
            "timeout_seconds",
            "proxy_http_present",
            "proxy_https_present",
            "proxy_no_proxy_present",
            "ssl_cert_file_present",
            "ssl_cert_dir_present",
            "requests_ca_bundle_present",
        }:
            diagnostics[key] = _safe_diagnostic_value(value)
    return diagnostics


def _safe_provider_error_detail(exc: ProviderError) -> dict:
    detail = exc.to_dict()
    metadata = detail.get("metadata")
    if isinstance(metadata, dict):
        warnings = metadata.get("warnings")
        if isinstance(warnings, list):
            metadata["warnings"] = [
                warning
                for warning in warnings
                if isinstance(warning, str)
                and warning.split("=", 1)[0]
                in {
                    "provider_reached",
                    "provider_http_status",
                    "provider_error_type",
                    "provider_error_code",
                    "failure_category",
                    "url_error_reason_type",
                    "url_error_reason_category",
                    "endpoint_kind",
                    "endpoint_host",
                    "endpoint_path",
                    "timeout_seconds",
                    "proxy_http_present",
                    "proxy_https_present",
                    "proxy_no_proxy_present",
                    "ssl_cert_file_present",
                    "ssl_cert_dir_present",
                    "requests_ca_bundle_present",
                    "provider_request_id_present",
                }
                and _safe_diagnostic_value(warning.split("=", 1)[-1]) == warning.split("=", 1)[-1]
            ]
    return detail


def _diagnostics_header(diagnostics: dict[str, str]) -> str:
    compact = {key: diagnostics[key] for key in sorted(diagnostics)}
    return json.dumps(compact, separators=(",", ":"))


def _safe_diagnostic_value(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:-]{1,140}", value):
        return value
    return "redacted"
