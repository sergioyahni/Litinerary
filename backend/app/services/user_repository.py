from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import CurrentUser
from app.core.errors import conflict, not_found
from app.models import (
    ItineraryDayModel,
    ItineraryModel,
    ItineraryStopModel,
    POIModel,
    UserModel,
    UserPreferenceModel,
    UserReviewModel,
)
from app.schemas.users import (
    UserBookmarksResponse,
    UserCreateRequest,
    UserPreference,
    UserPreferenceUpsertRequest,
    UserProfile,
    UserReview,
    UserReviewCreateRequest,
)
from app.services import database_repository
from app.services.database_repository import itinerary_from_model
from app.services.mock_ai_service import get_ai_pipeline
from app.services.vector_service import (
    find_itineraries_similar_to_user_positive_reviews,
    find_itineraries_similar_to_user_preferences,
    find_pois_similar_to_user_interests,
    save_user_preference_embedding,
    save_user_review_embedding,
    save_itinerary_embedding,
    save_poi_embedding,
)


def create_user(db: Session, request: UserCreateRequest) -> UserProfile:
    user_id = request.id or f"dev-user-{uuid4().hex[:10]}"
    if db.get(UserModel, user_id) is not None:
        raise conflict(f"User already exists: {user_id}")

    user = UserModel(
        id=user_id,
        email=request.email,
        display_name=request.displayName,
        auth_provider="dev" if user_id.startswith("dev-") else None,
        auth_subject=user_id if user_id.startswith("dev-") else None,
        role="user",
        subscription_status="none",
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_profile_from_model(user)


def sync_user_from_current_user(db: Session, current_user: CurrentUser) -> UserProfile:
    user = db.get(UserModel, current_user.id)
    now = _now()
    role = _primary_role(current_user.roles)
    if user is None:
        user = UserModel(
            id=current_user.id,
            email=current_user.email,
            display_name=current_user.display_name,
            auth_provider=current_user.auth_provider,
            auth_subject=current_user.auth_subject,
            role=role,
            subscription_status=current_user.subscription_status,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
    else:
        user.email = current_user.email or user.email
        user.display_name = current_user.display_name or user.display_name
        user.auth_provider = current_user.auth_provider
        user.auth_subject = current_user.auth_subject
        user.role = role
        user.subscription_status = current_user.subscription_status
        user.updated_at = now
    db.commit()
    db.refresh(user)
    return user_profile_from_model(user)


def get_user_profile(db: Session, user_id: str) -> UserProfile:
    user = _get_user(db, user_id)
    return user_profile_from_model(user)


def upsert_preference(
    db: Session,
    user_id: str,
    request: UserPreferenceUpsertRequest,
) -> UserPreference:
    _get_user(db, user_id)
    preference = db.scalars(
        select(UserPreferenceModel).where(
            UserPreferenceModel.user_id == user_id,
            UserPreferenceModel.key == request.key,
        )
    ).first()

    if preference is None:
        preference = UserPreferenceModel(
            id=f"pref-{uuid4().hex}",
            user_id=user_id,
            key=request.key,
            created_at=_now(),
        )
        db.add(preference)

    preference.value = request.value
    db.commit()
    db.refresh(preference)
    response = preference_from_model(preference)
    _mirror_to_vector_service(lambda: save_user_preference_embedding(response))
    return response


def bookmark_itinerary(
    db: Session,
    user_id: str,
    itinerary_id: str,
    *,
    current_user: CurrentUser | None = None,
) -> UserBookmarksResponse:
    user = _get_user(db, user_id)
    itinerary = database_repository.get_accessible_itinerary_model(
        db,
        itinerary_id,
        current_user=current_user,
    )
    if itinerary is None:
        raise not_found("itinerary", itinerary_id)

    if all(item.id != itinerary_id for item in user.bookmarked_itineraries):
        user.bookmarked_itineraries.append(itinerary)
        db.commit()
        db.refresh(user)

    return list_bookmarks(db, user_id, current_user=current_user)


def remove_bookmark(
    db: Session,
    user_id: str,
    itinerary_id: str,
    *,
    current_user: CurrentUser | None = None,
) -> UserBookmarksResponse:
    user = _get_user(db, user_id)
    user.bookmarked_itineraries = [
        itinerary for itinerary in user.bookmarked_itineraries if itinerary.id != itinerary_id
    ]
    db.commit()
    db.refresh(user)
    return list_bookmarks(db, user_id, current_user=current_user)


def list_bookmarks(
    db: Session,
    user_id: str,
    *,
    current_user: CurrentUser | None = None,
) -> UserBookmarksResponse:
    user = _get_user(db, user_id)
    itineraries = [
        itinerary_from_model(row)
        for row in sorted(user.bookmarked_itineraries, key=lambda item: item.title)
        if database_repository.itinerary_row_is_accessible(row, current_user=current_user)
    ]
    return UserBookmarksResponse(userId=user.id, itineraries=itineraries)


def save_review(
    db: Session,
    user_id: str,
    request: UserReviewCreateRequest,
    *,
    current_user: CurrentUser | None = None,
) -> UserReview:
    _get_user(db, user_id)
    itinerary = database_repository.get_accessible_itinerary(
        db,
        request.itineraryId,
        current_user=current_user,
    )
    if itinerary is None:
        raise not_found("itinerary", request.itineraryId)

    review = UserReviewModel(
        id=f"review-{uuid4().hex}",
        user_id=user_id,
        itinerary_id=request.itineraryId,
        rating=request.rating,
        comment=request.comment,
        created_at=_now(),
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    response = review_from_model(review)
    _mirror_to_vector_service(lambda: save_user_review_embedding(response, itinerary=itinerary))
    _mirror_to_ai_service(lambda: get_ai_pipeline().process_review_feedback(response))
    return response


def list_reviews(db: Session, user_id: str) -> list[UserReview]:
    user = _get_user(db, user_id)
    return [review_from_model(review) for review in user.reviews]


def get_mock_recommendations(db: Session, user_id: str, limit: int = 5) -> dict:
    """Development-only fake vector recommendation preview."""
    _get_user(db, user_id)
    from app.services.database_repository import list_itineraries, poi_from_model

    vector_service = None
    try:
        from app.services.vector_service import get_vector_service

        vector_service = get_vector_service()
    except RuntimeError:
        return {
            "developmentOnly": True,
            "userId": user_id,
            "itinerariesFromPreferences": [],
            "itinerariesFromPositiveReviews": [],
            "poisFromInterests": [],
        }

    for itinerary in list_itineraries(db):
        save_itinerary_embedding(itinerary, service=vector_service)

    poi_rows = db.scalars(
        select(POIModel).options(selectinload(POIModel.books))
    ).unique().all()
    for poi in poi_rows:
        save_poi_embedding(poi_from_model(poi), service=vector_service)

    return {
        "developmentOnly": True,
        "userId": user_id,
        "itinerariesFromPreferences": _recommendation_payload(
            find_itineraries_similar_to_user_preferences(
                user_id,
                limit=limit,
                service=vector_service,
            )
        ),
        "itinerariesFromPositiveReviews": _recommendation_payload(
            find_itineraries_similar_to_user_positive_reviews(
                user_id,
                limit=limit,
                service=vector_service,
            )
        ),
        "poisFromInterests": _recommendation_payload(
            find_pois_similar_to_user_interests(
                user_id,
                limit=limit,
                service=vector_service,
            )
        ),
    }


def user_profile_from_model(user: UserModel) -> UserProfile:
    return UserProfile(
        id=user.id,
        email=user.email,
        displayName=user.display_name,
        authProvider=user.auth_provider,
        role=user.role,
        subscriptionStatus=user.subscription_status,
        createdAt=user.created_at,
        updatedAt=user.updated_at,
        preferences=[preference_from_model(item) for item in user.preferences],
        reviews=[review_from_model(item) for item in user.reviews],
    )


def preference_from_model(preference: UserPreferenceModel) -> UserPreference:
    return UserPreference(
        id=preference.id,
        userId=preference.user_id,
        key=preference.key,
        value=preference.value,
        createdAt=preference.created_at,
    )


def review_from_model(review: UserReviewModel) -> UserReview:
    return UserReview(
        id=review.id,
        userId=review.user_id,
        itineraryId=review.itinerary_id,
        rating=review.rating,
        comment=review.comment,
        createdAt=review.created_at,
    )


def _get_user(db: Session, user_id: str) -> UserModel:
    user = db.scalars(
        select(UserModel)
        .where(UserModel.id == user_id)
        .options(
            selectinload(UserModel.preferences),
            selectinload(UserModel.reviews),
            selectinload(UserModel.bookmarked_itineraries)
            .selectinload(ItineraryModel.days)
            .selectinload(ItineraryDayModel.stops)
            .selectinload(ItineraryStopModel.poi)
            .selectinload(POIModel.books),
        )
    ).first()
    if user is None:
        raise not_found("user", user_id)
    return user


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _primary_role(roles: set[str]) -> str:
    for role in ("admin", "developer", "subscriber", "user"):
        if role in roles:
            return role
    return sorted(roles)[0] if roles else "user"


def _mirror_to_vector_service(callback) -> None:
    try:
        callback()
    except RuntimeError:
        # Vector providers are optional placeholders in Phase 2. Relational writes remain
        # the source of truth until a real provider is configured and tested.
        return


def _mirror_to_ai_service(callback) -> None:
    try:
        callback()
    except RuntimeError:
        # AI providers are optional placeholders in Phase 2. Review persistence remains
        # relational until a real feedback pipeline is configured and tested.
        return


def _recommendation_payload(results) -> list[dict]:
    return [
        {
            "id": result.record.id,
            "collection": result.record.collection,
            "score": round(result.score, 6),
            "metadata": result.record.metadata,
            "text": result.record.text,
        }
        for result in results
    ]
