from pydantic import BaseModel, Field

from app.schemas.domain import Itinerary


class UserCreateRequest(BaseModel):
    id: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    displayName: str | None = Field(default=None, max_length=255)


class UserPreferenceUpsertRequest(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: dict


class UserPreference(BaseModel):
    id: str
    userId: str
    key: str
    value: dict
    createdAt: str


class UserReviewCreateRequest(BaseModel):
    itineraryId: str
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = None


class UserReview(BaseModel):
    id: str
    userId: str
    itineraryId: str | None = None
    rating: int | None = None
    comment: str | None = None
    createdAt: str


class UserProfile(BaseModel):
    id: str
    email: str | None = None
    displayName: str | None = None
    authProvider: str | None = None
    role: str = "user"
    subscriptionStatus: str = "none"
    createdAt: str
    updatedAt: str | None = None
    preferences: list[UserPreference] = Field(default_factory=list)
    reviews: list[UserReview] = Field(default_factory=list)


class UserBookmarksResponse(BaseModel):
    userId: str
    itineraries: list[Itinerary]
