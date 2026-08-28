"""Validate local GitHub Actions workflow policy."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SECRET_REFERENCE = re.compile(r"\$\{\{\s*secrets\.")


class GithubActionsLoader(yaml.SafeLoader):
    """PyYAML loader adjusted for GitHub Actions syntax.

    GitHub Actions treats `on` as a string key. PyYAML's YAML 1.1 boolean
    resolver can otherwise parse an unquoted `on` key as True.
    """


for first_char, resolvers in list(GithubActionsLoader.yaml_implicit_resolvers.items()):
    GithubActionsLoader.yaml_implicit_resolvers[first_char] = [
        (tag, regexp)
        for tag, regexp in resolvers
        if tag != "tag:yaml.org,2002:bool"
    ]


def main() -> int:
    run_loader_self_check()
    failures: list[str] = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        data = load_workflow(text)
        if not isinstance(data, dict):
            failures.append(f"{path}: workflow did not parse as a mapping.")
            continue
        if "on" not in data:
            failures.append(f"{path}: workflow trigger key 'on' is missing or misparsed.")
        validate_permissions(path, data, failures)
        validate_action_pins(path, data, text, failures)
        validate_shell_injection_posture(path, text, failures)
        validate_checkout_posture(path, data, failures)
        validate_timeouts(path, data, failures)
        validate_secret_boundaries(path, data, text, failures)

    if failures:
        for failure in failures:
            print(failure)
        raise SystemExit(1)
    print("Workflow policy validation passed.")
    return 0


def load_workflow(text: str) -> Any:
    return yaml.load(text, Loader=GithubActionsLoader)


def run_loader_self_check() -> None:
    quoted = load_workflow('"on":\n  workflow_dispatch:\n')
    unquoted = load_workflow("on:\n  workflow_dispatch:\n")
    if "on" not in quoted or "on" not in unquoted:
        raise SystemExit("GitHub Actions YAML loader misparsed the 'on' trigger key.")


def validate_permissions(path: Path, data: dict[str, Any], failures: list[str]) -> None:
    permissions = data.get("permissions")
    if permissions != {"contents": "read"}:
        failures.append(f"{path}: workflow permissions must default to contents: read.")
    for job_name, job in (data.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        job_permissions = job.get("permissions")
        if job_permissions is None:
            continue
        forbidden = {
            key
            for key, value in job_permissions.items()
            if value == "write" and key in {"contents", "actions", "packages", "id-token"}
        }
        if forbidden:
            failures.append(f"{path}: job {job_name} has forbidden write permissions: {sorted(forbidden)}")


def validate_action_pins(
    path: Path,
    data: dict[str, Any],
    text: str,
    failures: list[str],
) -> None:
    for match in re.finditer(r"uses:\s+([^\s#]+)", text):
        action_ref = match.group(1)
        if "@" not in action_ref:
            failures.append(f"{path}: action reference lacks @ ref: {action_ref}")
            continue
        _action, ref = action_ref.rsplit("@", 1)
        if not FULL_SHA.match(ref):
            failures.append(f"{path}: action is not pinned to a full SHA: {action_ref}")


def validate_shell_injection_posture(path: Path, text: str, failures: list[str]) -> None:
    forbidden_contexts = (
        "github.event.pull_request.title",
        "github.event.pull_request.body",
        "github.event.head_commit.message",
    )
    for context in forbidden_contexts:
        if context in text:
            failures.append(f"{path}: untrusted context appears in workflow: {context}")


def validate_checkout_posture(path: Path, data: dict[str, Any], failures: list[str]) -> None:
    for job_name, step in iter_steps(data):
        if not isinstance(step, dict):
            continue
        uses = str(step.get("uses", ""))
        if not uses.startswith("actions/checkout@"):
            continue
        with_block = step.get("with") or {}
        if with_block.get("persist-credentials") not in {False, "false"}:
            failures.append(f"{path}: job {job_name} checkout must set persist-credentials: false.")


def validate_timeouts(path: Path, data: dict[str, Any], failures: list[str]) -> None:
    for job_name, job in (data.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        timeout = job.get("timeout-minutes")
        if not isinstance(timeout, int) or timeout <= 0 or timeout > 60:
            failures.append(f"{path}: job {job_name} needs a positive timeout-minutes <= 60.")


def validate_secret_boundaries(
    path: Path,
    data: dict[str, Any],
    text: str,
    failures: list[str],
) -> None:
    workflow_triggers = data.get("on") or {}
    if "pull_request_target" in workflow_triggers:
        failures.append(f"{path}: pull_request_target is forbidden.")
    for job_name, job in (data.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        job_text = yaml.dump(job, sort_keys=True)
        references_secrets = bool(SECRET_REFERENCE.search(job_text))
        environment = job.get("environment")
        if references_secrets and environment not in {"staging", "production"}:
            failures.append(f"{path}: job {job_name} references secrets outside deployment environments.")
        if references_secrets and "pull_request" in workflow_triggers:
            failures.append(f"{path}: pull_request workflow job {job_name} must not reference deployment secrets.")


def iter_steps(data: dict[str, Any]):
    for job_name, job in (data.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            yield job_name, step


if __name__ == "__main__":
    raise SystemExit(main())
