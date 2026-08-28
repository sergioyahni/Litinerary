"""Validate the current npm audit result against the PLU-03 baseline.

The approved baseline accepts known Vitest/Vite/esbuild dev-test findings only.
Any high/critical finding outside that dev-test chain fails CI.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ACCEPTED_DEV_TOOLING = {
    "@vitest/mocker",
    "esbuild",
    "vite",
    "vite-node",
    "vitest",
}

BLOCKING_SEVERITIES = {"high", "critical"}
DEV_TOOLING_NODE_HINTS = (
    "node_modules/vitest",
    "node_modules/vite-node",
    "node_modules/@vitest",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce frontend npm audit policy.")
    parser.add_argument("audit_json", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.audit_json.read_text(encoding="utf-8-sig"))
    vulnerabilities = payload.get("vulnerabilities", {})
    failures: list[str] = []
    accepted: list[str] = []

    for name, item in sorted(vulnerabilities.items()):
        severity = str(item.get("severity", "")).lower()
        if severity not in BLOCKING_SEVERITIES:
            continue
        if is_accepted_dev_tooling(name, item):
            accepted.append(f"{name}:{severity}")
            continue
        failures.append(f"{name}:{severity}")

    if failures:
        print("Blocking frontend production-runtime audit findings:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    if accepted:
        print("Accepted current dev/test audit baseline:")
        for finding in accepted:
            print(f"- {finding}")
    else:
        print("No high/critical frontend audit findings present.")
    return 0


def is_accepted_dev_tooling(name: str, item: dict[str, Any]) -> bool:
    if name not in ACCEPTED_DEV_TOOLING:
        return False
    nodes = [str(node).replace("\\", "/") for node in item.get("nodes", [])]
    if not nodes:
        return True
    return all(any(hint in node for hint in DEV_TOOLING_NODE_HINTS) for node in nodes)


if __name__ == "__main__":
    raise SystemExit(main())
