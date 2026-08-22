import os
import re

from app.core.config import Settings, get_settings


UNKNOWN_RELEASE = "unknown"
_SAFE_SHA = re.compile(r"^[0-9a-fA-F]{7,40}$")


def release_sha() -> str:
    for name in ("RENDER_GIT_COMMIT", "APP_RELEASE_SHA", "GITHUB_SHA"):
        value = os.getenv(name)
        if value and _SAFE_SHA.fullmatch(value.strip()):
            return value.strip().lower()
    return UNKNOWN_RELEASE


def release_payload(settings: Settings | None = None) -> dict[str, str]:
    resolved = settings or get_settings()
    return {
        "releaseSha": release_sha(),
        "environment": resolved.app_env,
    }
