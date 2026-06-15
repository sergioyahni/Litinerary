from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.auth import validate_auth_startup
from app.core.config import get_settings
from app.services.mock_ai_service import validate_llm_startup
from app.services.poi_verification import validate_poi_provider_startup
from app.services.routing_service import validate_routing_startup
from app.services.ticketing_service import validate_ticketing_startup
from app.services.affiliate_service import validate_affiliate_startup
from app.services.narration_service import validate_tts_startup
from app.services.vector_service import validate_vector_startup

settings = get_settings()
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


@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router)
