from fastapi import Depends, HTTPException, status

from app.core.auth import CurrentUser, optional_current_user
from app.core.config import get_settings
from app.core.observability import EventName, log_event


def require_admin_routes() -> None:
    settings = get_settings()
    log_event(
        EventName.ADMIN_ACTION_ATTEMPTED,
        category="admin",
        action="admin_route_access",
        allowed=settings.enable_admin_routes,
        app_env=settings.app_env,
    )
    if settings.enable_admin_routes:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin/development endpoints are disabled in this environment.",
    )


def require_debug_routes() -> None:
    settings = get_settings()
    if settings.enable_debug_routes:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Debug endpoints are disabled in this environment.",
    )


def require_admin_user_when_auth_enabled(
    current_user: CurrentUser | None = Depends(optional_current_user),
) -> None:
    settings = get_settings()
    if not settings.enable_auth:
        return
    if current_user is not None and current_user.is_admin:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role is required.")


def require_destructive_development_action() -> None:
    settings = get_settings()
    log_event(
        EventName.ADMIN_ACTION_ATTEMPTED,
        category="admin",
        action="destructive_development_action",
        allowed=not settings.is_production and settings.enable_admin_routes,
        app_env=settings.app_env,
    )
    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Destructive development actions are blocked in production.",
        )
    require_admin_routes()
