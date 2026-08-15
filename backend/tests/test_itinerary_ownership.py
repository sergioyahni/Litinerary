from copy import deepcopy

import pytest

from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.models import UserModel
from app.services import database_repository
from app.services.user_repository import sync_user_from_current_user


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_public_itinerary_generation_ignores_ownership_injection(client, monkeypatch) -> None:
    _enable_dev_auth(monkeypatch)

    response = client.post(
        "/api/itinerary/generate",
        headers=_auth_header("reader-b"),
        json={
            "destinationId": "paris",
            "bookId": "les-miserables",
            "durationDays": 2,
            "transportationMode": "walking",
            "ownerUserId": "reader-a",
            "user_id": "reader-a",
            "createdByUserId": "reader-a",
            "visibility": "private",
            "isPublic": False,
        },
    )

    assert response.status_code == 200
    itinerary = response.json()["itinerary"]
    assert itinerary["isPublic"] is True
    assert itinerary["visibility"] == "public"
    assert itinerary["ownerUserId"] is None
    assert itinerary["createdByUserId"] is None

    public_detail = client.get(f"/api/itineraries/{itinerary['id']}")
    assert public_detail.status_code == 200


def test_private_itinerary_detail_and_narration_are_owner_or_admin_only(
    client,
    db_session,
    monkeypatch,
) -> None:
    _enable_dev_auth(monkeypatch)
    private_id = _save_private_itinerary(db_session, owner_id="reader-a")
    _sync_user(db_session, "reader-b")
    _sync_user(db_session, "admin", roles={"admin"})

    anonymous = client.get(f"/api/itineraries/{private_id}")
    other_user = client.get(f"/api/itineraries/{private_id}", headers=_auth_header("reader-b"))
    owner = client.get(f"/api/itineraries/{private_id}", headers=_auth_header("reader-a"))
    admin = client.get(
        f"/api/itineraries/{private_id}",
        headers=_auth_header("admin", roles="admin"),
    )
    owner_narration = client.get(
        f"/api/itineraries/{private_id}/narration",
        headers=_auth_header("reader-a"),
    )
    other_narration = client.post(
        f"/api/itineraries/{private_id}/narration",
        headers=_auth_header("reader-b"),
        json={"includePlaceholderAudio": False},
    )
    missing = client.get("/api/itineraries/not-a-real-itinerary", headers=_auth_header("reader-a"))

    assert anonymous.status_code == 404
    assert other_user.status_code == 404
    assert owner.status_code == 200
    assert owner.json()["id"] == private_id
    assert owner.json()["ownerUserId"] == "reader-a"
    assert admin.status_code == 200
    assert owner_narration.status_code == 200
    assert owner_narration.json()["itineraryId"] == private_id
    assert other_narration.status_code == 404
    assert missing.status_code == 404
    assert anonymous.json()["detail"] == other_user.json()["detail"]


def test_private_itinerary_cannot_be_bookmarked_or_reviewed_cross_user(
    client,
    db_session,
    monkeypatch,
) -> None:
    _enable_dev_auth(monkeypatch)
    private_id = _save_private_itinerary(db_session, owner_id="reader-a")
    _sync_user(db_session, "reader-b")

    owner_bookmark = client.post(
        f"/api/users/reader-a/bookmarks/{private_id}",
        headers=_auth_header("reader-a"),
    )
    other_bookmark = client.post(
        f"/api/users/reader-b/bookmarks/{private_id}",
        headers=_auth_header("reader-b"),
    )
    owner_review = client.post(
        "/api/users/reader-a/reviews",
        headers=_auth_header("reader-a"),
        json={"itineraryId": private_id, "rating": 5, "comment": "Private useful route."},
    )
    other_review = client.post(
        "/api/users/reader-b/reviews",
        headers=_auth_header("reader-b"),
        json={"itineraryId": private_id, "rating": 4, "comment": "Trying an ID."},
    )
    anonymous_bookmark = client.post(f"/api/users/reader-a/bookmarks/{private_id}")

    assert owner_bookmark.status_code == 200
    assert private_id in {item["id"] for item in owner_bookmark.json()["itineraries"]}
    assert other_bookmark.status_code == 404
    assert owner_review.status_code == 201
    assert other_review.status_code == 404
    assert anonymous_bookmark.status_code == 401


def test_user_path_cannot_be_used_to_access_another_users_private_itinerary(
    client,
    db_session,
    monkeypatch,
) -> None:
    _enable_dev_auth(monkeypatch)
    private_id = _save_private_itinerary(db_session, owner_id="reader-a")
    _sync_user(db_session, "reader-b")

    response = client.post(
        f"/api/users/reader-a/bookmarks/{private_id}",
        headers=_auth_header("reader-b"),
    )

    assert response.status_code == 403


def test_bookmark_list_filters_inaccessible_private_records(
    client,
    db_session,
    monkeypatch,
) -> None:
    _enable_dev_auth(monkeypatch)
    private_id = _save_private_itinerary(db_session, owner_id="reader-a")
    reader_b = _sync_user(db_session, "reader-b")
    private_row = db_session.get(database_repository.ItineraryModel, private_id)
    assert private_row is not None
    reader_b.bookmarked_itineraries.append(private_row)
    db_session.commit()

    response = client.get("/api/users/reader-b/bookmarks", headers=_auth_header("reader-b"))

    assert response.status_code == 200
    assert private_id not in {item["id"] for item in response.json()["itineraries"]}


def test_public_listing_and_adaptation_ignore_private_source_ids(
    client,
    db_session,
    monkeypatch,
) -> None:
    _enable_dev_auth(monkeypatch)
    private_id = _save_private_itinerary(db_session, owner_id="reader-a")

    listing = client.get("/api/itineraries")
    public_detail = client.get("/api/itineraries/it-london-oliver-twist-1-walking")
    private_adapt = client.post(
        "/api/itineraries/adapt",
        headers=_auth_header("reader-a"),
        json={
            "sourceItineraryId": private_id,
            "durationDays": 2,
            "transportationMode": "walking",
        },
    )

    assert listing.status_code == 200
    assert private_id not in {item["id"] for item in listing.json()}
    assert public_detail.status_code == 200
    assert private_adapt.status_code == 404


def _enable_dev_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "dev")
    monkeypatch.setenv("AUTH_REQUIRED_FOR_USER_FEATURES", "true")
    monkeypatch.setenv("AUTH_ALLOW_DEV_USER_FALLBACK", "false")
    get_settings.cache_clear()


def _auth_header(user_id: str, *, roles: str = "user", subscription: str = "none") -> dict[str, str]:
    return {"Authorization": f"Bearer dev:{user_id}:{roles}:{subscription}"}


def _sync_user(
    db_session,
    user_id: str,
    *,
    roles: set[str] | None = None,
    subscription: str = "none",
) -> UserModel:
    sync_user_from_current_user(
        db_session,
        CurrentUser(
            id=user_id,
            auth_provider="dev",
            auth_subject=user_id,
            roles=roles or {"user"},
            subscription_status=subscription,
        ),
    )
    user = db_session.get(UserModel, user_id)
    assert user is not None
    return user


def _save_private_itinerary(db_session, *, owner_id: str) -> str:
    _sync_user(db_session, owner_id)
    source = database_repository.get_itinerary(db_session, "it-london-oliver-twist-1-walking")
    assert source is not None
    private_id = f"it-private-{owner_id}"
    private = source.model_copy(
        update={
            "id": private_id,
            "title": f"Private itinerary for {owner_id}",
            "isPublic": False,
            "ownerUserId": owner_id,
            "visibility": "private",
            "createdByMode": "registered_user",
            "createdByUserId": owner_id,
            "subscriberOnly": False,
            "sourceItineraryId": source.id,
            "days": [
                day.model_copy(
                    update={
                        "id": f"{private_id}-day-{day.dayNumber}",
                        "stops": [
                            stop.model_copy(
                                update={
                                    "id": (
                                        f"{private_id}-day-{day.dayNumber}-"
                                        f"stop-{stop.order}"
                                    )
                                },
                                deep=True,
                            )
                            for stop in day.stops
                        ],
                    },
                    deep=True,
                )
                for day in deepcopy(source.days)
            ],
        },
        deep=True,
    )
    database_repository.save_itinerary(db_session, private)
    return private_id
