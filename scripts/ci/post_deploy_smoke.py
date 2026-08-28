"""Post-deploy health, readiness, and core public API smoke checks."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test a deployed Litinerary API.")
    parser.add_argument("--base-url", required=True, help="Backend base URL, no secret values.")
    parser.add_argument("--frontend-url", help="Frontend base URL, no secret values.")
    parser.add_argument("--expected-release-sha", help="Expected deployed Git commit SHA.")
    parser.add_argument("--wait-for-release", action="store_true")
    parser.add_argument("--release-timeout-seconds", type=int, default=600)
    parser.add_argument("--release-poll-interval-seconds", type=int, default=15)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    frontend_url = args.frontend_url.rstrip("/") if args.frontend_url else None
    release_result: dict[str, str] = {}
    if args.expected_release_sha:
        if not frontend_url:
            raise SystemExit("--frontend-url is required with --expected-release-sha.")
        release_result = wait_for_release(
            backend_url=base_url,
            frontend_url=frontend_url,
            expected_sha=args.expected_release_sha,
            timeout_seconds=args.release_timeout_seconds,
            interval_seconds=args.release_poll_interval_seconds,
        )
    elif args.wait_for_release:
        raise SystemExit("--wait-for-release requires --expected-release-sha.")

    health = request_json(f"{base_url}/api/health")
    if health.get("status") != "ok":
        raise SystemExit("Health endpoint did not report ok.")

    readiness = request_json(f"{base_url}/api/readiness")
    if args.require_ready and readiness.get("status") != "ready":
        raise SystemExit("Readiness endpoint did not report ready.")
    validate_readiness(readiness)

    destinations = request_json(f"{base_url}/api/destinations")
    if not isinstance(destinations, list) or not destinations:
        raise SystemExit("Destinations smoke did not return a non-empty list.")

    books = request_json(f"{base_url}/api/books?city_id=london")
    if not isinstance(books, list):
        raise SystemExit("Books smoke did not return a list.")

    itineraries = request_json(f"{base_url}/api/itineraries")
    if not isinstance(itineraries, list):
        raise SystemExit("Public itineraries smoke did not return a list.")

    if frontend_url:
        validate_frontend(frontend_url)

    print(
        json.dumps(
            {
                **release_result,
                "health": health.get("status"),
                "readiness": readiness.get("status"),
                "destinations": len(destinations),
                "booksForLondon": len(books),
                "publicItineraries": len(itineraries),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def request_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "litinerary-ci-smoke"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Request failed: {url} status={exc.code}") from exc


def request_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "litinerary-ci-smoke"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Request failed: {url} status={exc.code}") from exc


def wait_for_release(
    *,
    backend_url: str,
    frontend_url: str,
    expected_sha: str,
    timeout_seconds: int,
    interval_seconds: int,
) -> dict[str, str]:
    expected = expected_sha.lower()
    deadline = time.monotonic() + timeout_seconds
    last_backend = "unknown"
    last_frontend = "unknown"
    while time.monotonic() <= deadline:
        backend_version = request_json(f"{backend_url}/api/version")
        frontend_version = request_json(f"{frontend_url}/release.json")
        last_backend = str(backend_version.get("releaseSha", "unknown")).lower()
        last_frontend = str(frontend_version.get("releaseSha", "unknown")).lower()
        if last_backend == expected and last_frontend == expected:
            return {
                "backendReleaseSha": last_backend,
                "frontendReleaseSha": last_frontend,
            }
        time.sleep(interval_seconds)
    raise SystemExit(
        "Timed out waiting for release SHA. "
        f"expected={expected} backend={last_backend} frontend={last_frontend}"
    )


def validate_frontend(frontend_url: str) -> None:
    index = request_text(f"{frontend_url}/")
    fallback = request_text(f"{frontend_url}/itineraries/plu-07-spa-fallback-check")
    for label, body in {"index": index, "fallback": fallback}.items():
        if "<html" not in body.lower():
            raise SystemExit(f"Frontend {label} did not return HTML.")


def validate_readiness(readiness: dict[str, Any]) -> None:
    checks = readiness.get("checks", {})
    database = checks.get("database", {})
    migrations = database.get("migrations", {})
    if database.get("configured") is not True:
        raise SystemExit("Readiness database check is not explicitly configured.")
    if database.get("connectivity") != "ok":
        raise SystemExit("Readiness database connectivity is not ok.")
    if migrations.get("status") != "current":
        raise SystemExit("Readiness migrations are not current.")
    if checks.get("usageControls", {}).get("durable") is not True:
        raise SystemExit("Readiness durable usage controls are not enabled.")
    for provider in checks.get("providers", []):
        if provider.get("providerType") == "auth":
            if provider.get("mode") != "real" or provider.get("externalCallsAllowed") is not True:
                raise SystemExit("Auth provider readiness is not production-like.")
            continue
        if provider.get("realEnabled") or provider.get("externalCallsAllowed"):
            raise SystemExit(f"Product provider is live in readiness: {provider.get('providerType')}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise
