"""High-confidence repository secret hygiene check for CI.

This is a fallback/complement to GitHub Secret Protection. It intentionally
prints only file paths and categories, never matching values.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PATTERNS: dict[str, re.Pattern[str]] = {
    "openai_api_key_like": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
    "github_token": re.compile(r"gh[opsu]_[A-Za-z0-9_]{20,}"),
    "aws_access_key": re.compile(r"AKIA[A-Z0-9]{16}"),
    "google_api_key": re.compile(r"AIza[A-Za-z0-9_-]{20,}"),
    "private_key_block": re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    "auth0_client_secret": re.compile(
        r"AUTH0(?:_|-)?CLIENT(?:_|-)?SECRET\s*[:=]\s*['\"]?[^<\s#'\"]+",
        re.IGNORECASE,
    ),
    "database_url_with_credentials": re.compile(
        r"(?:postgres|postgresql|mysql)://[^:/\s]+:[^@\s]+@[^/\s]+",
        re.IGNORECASE,
    ),
}

ALLOWLIST_SNIPPETS = (
    "<",
    "example.test",
    "example.com",
    "localhost",
    "127.0.0.1",
    "user:pass@db.example.test",
)

EXCLUDED_PARTS = {
    ".git",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    "venv",
}

EXCLUDED_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".db",
    ".sqlite",
    ".pyc",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repository files for likely secrets.")
    parser.add_argument(
        "--all-files",
        action="store_true",
        help="scan all non-excluded files instead of git-tracked files",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="scan reachable Git history blobs instead of the working tree",
    )
    args = parser.parse_args()

    if args.history:
        return scan_history()

    findings: list[str] = []
    for path in candidate_files(all_files=args.all_files):
        text = read_text(path)
        if text is None:
            continue
        relative = path.relative_to(ROOT).as_posix()
        for category, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                value = match.group(0)
                if is_allowlisted(value):
                    continue
                findings.append(f"{relative}: {category}")
                break

    if findings:
        for finding in sorted(set(findings)):
            print(finding)
        raise SystemExit("Secret hygiene scan failed. Values were not printed.")

    print("Secret hygiene scan passed; no high-confidence secret patterns found.")
    return 0


def scan_history() -> int:
    findings: list[str] = []
    for blob_sha, path in history_objects():
        if is_excluded(Path(path)):
            continue
        data = git_bytes(["cat-file", "-p", blob_sha])
        if is_binary(data):
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for category, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                value = match.group(0)
                if is_allowlisted(value):
                    continue
                commit = first_commit_for_blob(blob_sha)
                findings.append(
                    f"{path}: {category} blob={blob_sha} commit={commit or 'unknown'}"
                )
                break

    if findings:
        for finding in sorted(set(findings)):
            print(finding)
        raise SystemExit("Git history secret scan failed. Values were not printed.")

    print("Git history secret scan passed; no high-confidence secret patterns found.")
    return 0


def candidate_files(*, all_files: bool) -> list[Path]:
    if all_files:
        return [
            path
            for path in ROOT.rglob("*")
            if path.is_file() and not is_excluded(path)
        ]

    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [
        ROOT / line
        for line in result.stdout.splitlines()
        if line and not is_excluded(ROOT / line)
    ]


def history_objects() -> list[tuple[str, str]]:
    result = subprocess.run(
        ["git", "rev-list", "--objects", "--all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    objects: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        if " " not in line:
            continue
        sha, path = line.split(" ", 1)
        if git_text(["cat-file", "-t", sha]).strip() == "blob":
            objects.append((sha, path))
    return objects


def first_commit_for_blob(blob_sha: str) -> str | None:
    result = subprocess.run(
        ["git", "log", "--all", "--find-object", blob_sha, "--format=%H", "-n", "1"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()[0] if result.stdout.splitlines() else None


def git_text(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def git_bytes(args: list[str]) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def is_excluded(path: Path) -> bool:
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        relative = path
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return True
    return path.suffix.lower() in EXCLUDED_SUFFIXES


def is_binary(data: bytes) -> bool:
    return b"\x00" in data[:8192]


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def is_allowlisted(value: str) -> bool:
    lower = value.lower()
    return any(snippet.lower() in lower for snippet in ALLOWLIST_SNIPPETS)


if __name__ == "__main__":
    raise SystemExit(main())
