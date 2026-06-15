from fastapi import HTTPException, status

from app.core.config import get_settings


def require_admin_routes() -> None:
    settings = get_settings()
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


def require_destructive_development_action() -> None:
    settings = get_settings()
    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Destructive development actions are blocked in production.",
        )
    require_admin_routes()
