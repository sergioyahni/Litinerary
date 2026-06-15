import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from hashlib import sha256
from typing import Any
from urllib.request import urlopen

from fastapi import Depends, Header, HTTPException, status
from jwt import ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError, InvalidTokenError
from jwt import PyJWKClient, decode as jwt_decode

from app.core.config import Settings, get_settings
from app.core.observability import EventName, log_event


@dataclass(frozen=True)
class CurrentUser:
    id: str
    auth_provider: str
    auth_subject: str
    roles: set[str] = field(default_factory=lambda: {"user"})
    subscription_status: str = "none"
    email: str | None = None
    display_name: str | None = None
    is_development_fallback: bool = False

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles or "developer" in self.roles

    @property
    def is_subscriber(self) -> bool:
        return self.subscription_status == "active" or "subscriber" in self.roles


class JWTValidationService:
    """Provider-neutral JWT validation boundary.

    Local development/test can use `dev:` bearer tokens. Managed providers use
    standard JWT validation against configured issuer, audience, algorithms, and
    JWKS/provider metadata.
    """

    def validate(self, token: str, settings: Settings) -> CurrentUser:
        if not settings.enable_auth:
            raise _unauthorized("Authentication is disabled.")
        if token.startswith("dev:"):
            if settings.auth_provider != "dev":
                raise _unauthorized("Development auth tokens are not accepted by this provider.")
            if settings.is_deployed_environment:
                raise _unauthorized("Development auth tokens are not accepted in deployed environments.")
            return _parse_dev_token(token)
        if settings.auth_provider == "dev":
            raise _unauthorized("Invalid development auth token.")
        return _validate_managed_jwt(token, settings)


def clear_auth_caches() -> None:
    _jwks_client.cache_clear()
    _provider_metadata.cache_clear()


def _validate_managed_jwt(token: str, settings: Settings) -> CurrentUser:
    _validate_managed_auth_config(settings)
    try:
        signing_key = _jwks_client(_jwks_url(settings)).get_signing_key_from_jwt(token)
        claims = jwt_decode(
            token,
            signing_key.key,
            algorithms=settings.auth_jwt_algorithms,
            audience=settings.auth_jwt_audience,
            issuer=settings.auth_jwt_issuer,
            options={"require": ["exp", "sub"]},
        )
    except ExpiredSignatureError:
        raise _unauthorized("Authentication token has expired.")
    except InvalidIssuerError:
        raise _unauthorized("Authentication token issuer is invalid.")
    except InvalidAudienceError:
        raise _unauthorized("Authentication token audience is invalid.")
    except InvalidTokenError as exc:
        raise _unauthorized(f"Authentication token is invalid: {exc.__class__.__name__}.")

    subject = _claim_as_str(claims, "sub")
    if not subject:
        raise _unauthorized("Authentication token is missing subject.")

    return CurrentUser(
        id=_local_user_id(settings, claims, subject),
        auth_provider=settings.auth_provider,
        auth_subject=subject,
        roles=_roles_from_claims(claims, settings.auth_roles_claim),
        subscription_status=_claim_as_str(claims, settings.auth_subscription_claim) or "none",
        email=_claim_as_str(claims, settings.auth_email_claim),
        display_name=_claim_as_str(claims, settings.auth_display_name_claim),
    )


def _validate_managed_auth_config(settings: Settings) -> None:
    missing = []
    if not settings.auth_provider or settings.auth_provider == "dev":
        missing.append("AUTH_PROVIDER")
    if not settings.auth_jwt_issuer:
        missing.append("AUTH_JWT_ISSUER")
    if not settings.auth_jwt_audience:
        missing.append("AUTH_JWT_AUDIENCE")
    if not settings.auth_jwt_algorithms or settings.auth_jwt_algorithms == ["dev"]:
        missing.append("AUTH_JWT_ALGORITHMS")
    if not settings.auth_jwks_url and not settings.auth_provider_metadata_url:
        missing.append("AUTH_JWKS_URL or AUTH_PROVIDER_METADATA_URL")
    if missing:
        raise _unauthorized(
            "Managed authentication is not configured: " + ", ".join(missing) + "."
        )


def _jwks_url(settings: Settings) -> str:
    if settings.auth_jwks_url:
        return settings.auth_jwks_url
    metadata = _provider_metadata(settings.auth_provider_metadata_url or "")
    jwks_uri = metadata.get("jwks_uri")
    if not isinstance(jwks_uri, str) or not jwks_uri:
        raise _unauthorized("Auth provider metadata does not include jwks_uri.")
    return jwks_uri


@lru_cache
def _jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


@lru_cache
def _provider_metadata(metadata_url: str) -> dict[str, Any]:
    with urlopen(metadata_url, timeout=5) as response:
        payload = response.read().decode("utf-8")
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise _unauthorized("Auth provider metadata response is invalid.")
    return parsed


def _local_user_id(settings: Settings, claims: dict[str, Any], subject: str) -> str:
    configured = _claim_as_str(claims, settings.auth_user_id_claim)
    raw_user_id = configured or f"{settings.auth_provider}:{subject}"
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw_user_id).strip("-")
    if not normalized:
        normalized = f"{settings.auth_provider}-{sha256(subject.encode('utf-8')).hexdigest()[:16]}"
    if len(normalized) <= 120:
        return normalized
    digest = sha256(raw_user_id.encode("utf-8")).hexdigest()[:16]
    return f"{normalized[:103]}-{digest}"


def _roles_from_claims(claims: dict[str, Any], claim_name: str) -> set[str]:
    value = claims.get(claim_name)
    roles: set[str] = {"user"}
    if isinstance(value, str):
        roles.update(role.strip() for role in value.split(",") if role.strip())
    elif isinstance(value, list):
        roles.update(str(role).strip() for role in value if str(role).strip())
    return roles


def _claim_as_str(claims: dict[str, Any], claim_name: str) -> str | None:
    value = claims.get(claim_name)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


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
    if resolved.is_deployed_environment and resolved.auth_allow_dev_user_fallback:
        raise RuntimeError("Development user fallback is not allowed in deployed environments.")
    if not resolved.is_production:
        return
    missing = []
    if not resolved.auth_provider or resolved.auth_provider == "dev":
        missing.append("AUTH_PROVIDER must be a production provider")
    if not resolved.auth_jwt_issuer:
        missing.append("AUTH_JWT_ISSUER")
    if not resolved.auth_jwt_audience:
        missing.append("AUTH_JWT_AUDIENCE")
    if not resolved.auth_jwks_url and not resolved.auth_provider_metadata_url:
        missing.append("AUTH_JWKS_URL or AUTH_PROVIDER_METADATA_URL")
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
    log_event(EventName.AUTH_UNAUTHORIZED, category="auth", reason=detail)
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden(detail: str) -> HTTPException:
    log_event(EventName.AUTH_FORBIDDEN, category="auth", reason=detail)
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
