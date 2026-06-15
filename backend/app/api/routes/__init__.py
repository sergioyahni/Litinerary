from fastapi import APIRouter

from . import (
    books,
    destinations,
    ingestion,
    itineraries,
    poi_admin,
    seed_admin,
    subscriber_chat,
    users,
)


api_router = APIRouter()
api_router.include_router(destinations.router)
api_router.include_router(books.router)
api_router.include_router(itineraries.router)
api_router.include_router(users.me_router)
api_router.include_router(users.router)
api_router.include_router(subscriber_chat.router)
api_router.include_router(ingestion.router)
api_router.include_router(poi_admin.router)
api_router.include_router(seed_admin.router)
