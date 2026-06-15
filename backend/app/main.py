import logging

from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.routes import api_router
from app.core.auth import validate_auth_startup
from app.core.config import get_settings
from app.core.database import get_db
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
from app.services.vector_service import validate_vector_startup

settings = get_settings()
configure_logging()
validate_auth_startup(settings)
validate_llm_startup(settings)
validate_vector_startup(settings)
validate_poi_provider_startup(settings)
validate_routing_startup(settings)
validate_ticketing_startup(settings)
validate_affiliate_startup(settings)
validate_tts_startup(settings)

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
            latency_ms=elapsed_ms(started_at),
            error_type=exc.__class__.__name__,
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
    }.get(exc.code, status.HTTP_502_BAD_GATEWAY)
    log_event(
        EventName.PROVIDER_CALL_FAILED,
        level=logging.WARNING,
        category="provider",
        path=request.url.path,
        error_type=exc.code.value,
        provider_type=exc.metadata.provider_type if exc.metadata else None,
        provider_name=exc.metadata.provider_name if exc.metadata else None,
    )
    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.to_dict()},
    )


app.include_router(api_router)
