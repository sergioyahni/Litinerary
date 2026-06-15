from dataclasses import dataclass, field

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class CurrentUser:
    id: str
    auth_provider: str
    auth_subject: str
    roles: set[str] = field(default_factory=lambda: {"user"})
    subscription_status: str = "none"
    is_development_fallback: bool = False

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles or "developer" in self.roles

    @property
    def is_subscriber(self) -> bool:
        return self.subscription_status == "active" or "subscriber" in self.roles


class JWTValidationService:
    """Provider-neutral JWT validation boundary.

    The current implementation supports only local development/test tokens. Future
    Auth0, Clerk, Supabase, Firebase, or equivalent providers should plug into this
    boundary and validate issuer, audience, algorithm, signature, expiry, and claims.
    """

    def validate(self, token: str, settings: Settings) -> CurrentUser:
        if not settings.enable_auth:
            raise _unauthorized("Authentication is disabled.")
        if settings.auth_provider != "dev":
            raise _unauthorized(
                f"Auth provider '{settings.auth_provider}' is configured but not implemented."
            )
        if settings.is_production:
            raise _unauthorized("Development auth tokens are not accepted in production.")
        return _parse_dev_token(token)


def optional_current_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> CurrentUser | None:
    if not settings.enable_auth:
        return None

    if authorization is None:
        if settings.auth_allow_dev_user_fallback and settings.is_development_like:
            return CurrentUser(
                id="dev-reader",
                auth_provider="dev",
                auth_subject="dev-reader",
                is_development_fallback=True,
            )
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized("Invalid Authorization header.")
    return JWTValidationService().validate(token, settings)


def require_current_user(
    user: CurrentUser | None = Depends(optional_current_user),
) -> CurrentUser:
    if user is None:
        raise _unauthorized("Authentication is required.")
    return user


def require_user_feature_access(
    user_id: str,
    current_user: CurrentUser | None = Depends(optional_current_user),
    settings: Settings = Depends(get_settings),
) -> CurrentUser | None:
    if not settings.auth_required_for_user_features:
        return current_user
    if current_user is None:
        raise _unauthorized("Authentication is required for user features.")
    require_owner_or_admin(user_id, current_user)
    return current_user


def require_role(role: str, user: CurrentUser = Depends(require_current_user)) -> CurrentUser:
    if role not in user.roles:
        raise _forbidden(f"Role '{role}' is required.")
    return user


def require_admin_user(user: CurrentUser = Depends(require_current_user)) -> CurrentUser:
    if not user.is_admin:
        raise _forbidden("Admin role is required.")
    return user


def require_subscriber_user(user: CurrentUser = Depends(require_current_user)) -> CurrentUser:
    if not user.is_subscriber:
        raise _forbidden("Subscriber access is required.")
    return user


def require_owner_or_admin(resource_user_id: str, user: CurrentUser) -> None:
    if user.id == resource_user_id or user.is_admin:
        return
    raise _forbidden("You do not have access to this user's resources.")


def validate_auth_startup(settings: Settings | None = None) -> None:
    resolved = settings or get_settings()
    if not resolved.enable_auth:
        return
    if not resolved.is_production:
        return
    missing = []
    if not resolved.auth_provider or resolved.auth_provider == "dev":
        missing.append("AUTH_PROVIDER must be a production provider")
    if not resolved.auth_jwt_issuer:
        missing.append("AUTH_JWT_ISSUER")
    if not resolved.auth_jwt_audience:
        missing.append("AUTH_JWT_AUDIENCE")
    if missing:
        raise RuntimeError(
            "Production auth is enabled but configuration is incomplete: "
            + ", ".join(missing)
        )


def _parse_dev_token(token: str) -> CurrentUser:
    # Local/test token format:
    # dev:<user_id>[:comma-separated-roles][:subscription_status]
    parts = token.split(":")
    if len(parts) < 2 or parts[0] != "dev" or not parts[1]:
        raise _unauthorized("Invalid development auth token.")
    roles = set(parts[2].split(",")) if len(parts) >= 3 and parts[2] else {"user"}
    subscription_status = parts[3] if len(parts) >= 4 and parts[3] else "none"
    return CurrentUser(
        id=parts[1],
        auth_provider="dev",
        auth_subject=parts[1],
        roles=roles,
        subscription_status=subscription_status,
    )


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
