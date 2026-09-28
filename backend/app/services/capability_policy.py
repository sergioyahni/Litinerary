from dataclasses import dataclass

from fastapi import Depends, HTTPException, status

from app.core.auth import CurrentUser, optional_current_user
from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class UserCapabilities:
    can_use_external_discovery: bool
    can_generate_itinerary: bool
    can_adapt_itinerary: bool


def capabilities_for_user(
    user: CurrentUser | None,
    *,
    settings: Settings | None = None,
) -> UserCapabilities:
    resolved = settings or get_settings()
    generation_capable = _is_generation_capable(user, settings=resolved)
    return UserCapabilities(
        can_use_external_discovery=generation_capable,
        can_generate_itinerary=generation_capable,
        can_adapt_itinerary=generation_capable,
    )


def require_external_discovery_capability(
    current_user: CurrentUser | None = Depends(optional_current_user),
) -> CurrentUser | None:
    if capabilities_for_user(current_user).can_use_external_discovery:
        return current_user
    raise _capability_denied("External discovery requires an authenticated Litinerary account.")


def require_generation_capability(
    current_user: CurrentUser | None = Depends(optional_current_user),
) -> CurrentUser | None:
    if capabilities_for_user(current_user).can_generate_itinerary:
        return current_user
    raise _capability_denied("Itinerary generation requires an authenticated Litinerary account.")


def require_adaptation_capability(
    current_user: CurrentUser | None = Depends(optional_current_user),
) -> CurrentUser | None:
    if capabilities_for_user(current_user).can_adapt_itinerary:
        return current_user
    raise _capability_denied("Itinerary adaptation requires an authenticated Litinerary account.")


def _is_generation_capable(user: CurrentUser | None, *, settings: Settings) -> bool:
    if user is not None and not user.is_development_fallback:
        return True
    if not settings.enable_auth:
        return True
    return False


def _capability_denied(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
