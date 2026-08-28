"""Trigger Render deploy hooks for an exact Git ref without printing secrets."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


SAFE_REF = re.compile(r"^[0-9a-fA-F]{7,40}$")


def deploy_hook_url_with_ref(hook_url: str, ref: str) -> str:
    if not SAFE_REF.fullmatch(ref):
        raise ValueError("Render deploy ref must be a short or full Git SHA.")
    parsed = urllib.parse.urlsplit(hook_url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    filtered = [(key, value) for key, value in query if key != "ref"]
    filtered.append(("ref", ref))
    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urllib.parse.urlencode(filtered),
            parsed.fragment,
        )
    )


def trigger_deploy_hook(*, hook_url: str, ref: str) -> int:
    request_url = deploy_hook_url_with_ref(hook_url, ref)
    request = urllib.request.Request(
        request_url,
        method="POST",
        headers={"User-Agent": "litinerary-ci-render-deploy"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Render deploy hook failed with status={exc.code}.") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Trigger a Render deploy hook for one ref.")
    parser.add_argument("--hook-url", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    status = trigger_deploy_hook(hook_url=args.hook_url, ref=args.ref)
    if status not in {200, 202}:
        raise SystemExit(f"Render deploy hook returned unexpected status={status}.")
    print(json.dumps({"label": args.label, "status": status, "ref": args.ref}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise
