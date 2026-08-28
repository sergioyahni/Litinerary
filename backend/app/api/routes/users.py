from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fastapi import HTTPException, status

from app.core.auth import (
    CurrentUser,
    optional_current_user,
    require_current_user,
    require_user_feature_access,
    user_features_require_auth,
)
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.guards import require_debug_routes
from app.schemas.users import (
    UserBookmarksResponse,
    UserCreateRequest,
    UserPreference,
    UserPreferenceUpsertRequest,
    UserProfile,
    UserReview,
    UserReviewCreateRequest,
)
from app.services.user_repository import (
    bookmark_itinerary,
    create_user,
    get_mock_recommendations,
    get_user_profile,
    list_bookmarks,
    list_reviews,
    remove_bookmark,
    save_review,
    sync_user_from_current_user,
    upsert_preference,
)


router = APIRouter(prefix="/api/users", tags=["users"])
me_router = APIRouter(prefix="/api", tags=["users"])


@me_router.get("/me", response_model=UserProfile)
def get_current_user_profile(
    current_user: CurrentUser = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> UserProfile:
    return sync_user_from_current_user(db, current_user)


@router.post("", response_model=UserProfile, status_code=201)
def post_user(
    request: UserCreateRequest,
    current_user: CurrentUser | None = Depends(optional_current_user),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> UserProfile:
    if user_features_require_auth(settings):
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication is required for user features.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if request.id is not None and request.id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to create another user's profile.",
            )
        request = request.model_copy(update={"id": request.id or current_user.id})
    return create_user(db, request)


@router.get("/{user_id}", response_model=UserProfile)
def get_user(
    user_id: str,
    _: CurrentUser | None = Depends(require_user_feature_access),
    db: Session = Depends(get_db),
) -> UserProfile:
    return get_user_profile(db, user_id)


@router.post("/{user_id}/preferences", response_model=UserPreference)
def post_user_preference(
    user_id: str,
    request: UserPreferenceUpsertRequest,
    _: CurrentUser | None = Depends(require_user_feature_access),
    db: Session = Depends(get_db),
) -> UserPreference:
    return upsert_preference(db, user_id, request)


@router.post("/{user_id}/bookmarks/{itinerary_id}", response_model=UserBookmarksResponse)
def post_user_bookmark(
    user_id: str,
    itinerary_id: str,
    current_user: CurrentUser | None = Depends(require_user_feature_access),
    db: Session = Depends(get_db),
) -> UserBookmarksResponse:
    return bookmark_itinerary(db, user_id, itinerary_id, current_user=current_user)


@router.delete("/{user_id}/bookmarks/{itinerary_id}", response_model=UserBookmarksResponse)
def delete_user_bookmark(
    user_id: str,
    itinerary_id: str,
    current_user: CurrentUser | None = Depends(require_user_feature_access),
    db: Session = Depends(get_db),
) -> UserBookmarksResponse:
    return remove_bookmark(db, user_id, itinerary_id, current_user=current_user)


@router.get("/{user_id}/bookmarks", response_model=UserBookmarksResponse)
def get_user_bookmarks(
    user_id: str,
    current_user: CurrentUser | None = Depends(require_user_feature_access),
    db: Session = Depends(get_db),
) -> UserBookmarksResponse:
    return list_bookmarks(db, user_id, current_user=current_user)


@router.post("/{user_id}/reviews", response_model=UserReview, status_code=201)
def post_user_review(
    user_id: str,
    request: UserReviewCreateRequest,
    current_user: CurrentUser | None = Depends(require_user_feature_access),
    db: Session = Depends(get_db),
) -> UserReview:
    return save_review(db, user_id, request, current_user=current_user)


@router.get("/{user_id}/reviews", response_model=list[UserReview])
def get_user_reviews(
    user_id: str,
    _: CurrentUser | None = Depends(require_user_feature_access),
    db: Session = Depends(get_db),
) -> list[UserReview]:
    return list_reviews(db, user_id)


@router.get(
    "/{user_id}/recommendations/mock",
    tags=["development"],
    dependencies=[Depends(require_debug_routes)],
)
def get_user_mock_recommendations(
    user_id: str,
    limit: int = 5,
    _: CurrentUser | None = Depends(require_user_feature_access),
    db: Session = Depends(get_db),
) -> dict:
    """Development-only fake vector recommendations; not production AI."""
    return get_mock_recommendations(db, user_id, limit=limit)
