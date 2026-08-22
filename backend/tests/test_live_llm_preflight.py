import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT = REPO_ROOT / "scripts" / "live_llm_smoke_preflight.ps1"
NETWORK_PREFLIGHT = REPO_ROOT / "scripts" / "live_llm_network_preflight.ps1"


def _powershell_env() -> dict[str, str]:
    allowed = {}
    for key in ("PATH", "Path", "SystemRoot", "ComSpec", "PATHEXT", "HOME", "TEMP", "TMP", "TMPDIR"):
        if key in os.environ:
            allowed[key] = os.environ[key]
    return allowed


def _powershell_command(script: Path, *args: str) -> list[str]:
    executable = "powershell.exe" if sys.platform == "win32" else "pwsh"
    if shutil.which(executable) is None:
        pytest.skip(f"{executable} is required for PowerShell preflight tests")
    command = [
        executable,
        "-NoProfile",
    ]
    if sys.platform == "win32":
        command.extend(
            [
                "-ExecutionPolicy",
                "Bypass",
            ]
        )
    command.extend(["-File", str(script), *args])
    return command


def _run_preflight(env_file: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        _powershell_command(PREFLIGHT, "-EnvFile", str(env_file)),
        cwd=REPO_ROOT,
        env=_powershell_env(),
        text=True,
        capture_output=True,
        check=False,
    )


def _run_network_preflight(env_file: Path, host: str = "127.0.0.1") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        _powershell_command(
            NETWORK_PREFLIGHT,
            "-EnvFile",
            str(env_file),
            "-HostOverride",
            host,
            "-TimeoutSeconds",
            "1",
        ),
        cwd=REPO_ROOT,
        env=_powershell_env(),
        text=True,
        capture_output=True,
        check=False,
    )


def test_live_llm_local_env_template_contains_placeholders_only() -> None:
    template = (REPO_ROOT / ".env.development.local.example").read_text(encoding="utf-8")

    assert "LLM_API_KEY=<set locally from approved secret storage>" in template
    assert "LLM_MODEL_NAME=<approved non-production model name>" in template
    assert "sk-" not in template.lower()
    assert "ENABLE_REAL_VECTOR_DB=false" in template
    assert "ENABLE_REAL_POI_PROVIDER=false" in template
    assert "ENABLE_REAL_ROUTING=false" in template
    assert "ENABLE_REAL_TICKETING=false" in template
    assert "ENABLE_AFFILIATE_LINKS=false" in template
    assert "ENABLE_REAL_TTS=false" in template


def test_preflight_reports_missing_credentials_without_secret_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.development.local"
    env_file.write_text("APP_ENV=development\n", encoding="utf-8")

    result = _run_preflight(env_file)

    assert result.returncode == 0
    assert "llmApiKeyPresent=False" in result.stdout
    assert "llmModelNamePresent=False" in result.stdout
    assert "liveLlmSmokeReady=False" in result.stdout


def test_preflight_reports_ready_with_fake_local_env_without_printing_secret(
    tmp_path: Path,
) -> None:
    sentinel = "redacted-test-key-placeholder"
    env_file = tmp_path / ".env.development.local"
    env_file.write_text(
        "\n".join(
            [
                "APP_ENV=development",
                "ENABLE_REAL_LLM=true",
                "ALLOW_EXTERNAL_CALLS=true",
                "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS=development",
                "LLM_ALLOWED_ENVIRONMENTS=development",
                "LITINERARY_AI_PROVIDER=openai_compatible",
                "LLM_PROVIDER=openai_compatible",
                f"LLM_API_KEY={sentinel}",
                "LLM_MODEL_NAME=test-model",
                "ENABLE_REAL_VECTOR_DB=false",
                "ENABLE_REAL_POI_PROVIDER=false",
                "ENABLE_REAL_ROUTING=false",
                "ENABLE_REAL_TICKETING=false",
                "ENABLE_AFFILIATE_LINKS=false",
                "ENABLE_REAL_TTS=false",
                "ENABLE_AUTH=false",
                "AUTH_PROVIDER=dev",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_preflight(env_file)

    assert result.returncode == 0
    assert sentinel not in result.stdout
    assert "llmApiKeyPresent=True" in result.stdout
    assert "llmModelNamePresent=True" in result.stdout
    assert "otherLiveProvidersDisabled=True" in result.stdout
    assert "managedAuthLiveDisabled=True" in result.stdout
    assert "liveLlmSmokeReady=True" in result.stdout


def test_preflight_does_not_treat_template_placeholders_as_credentials(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env.development.local"
    env_file.write_text(
        "\n".join(
            [
                "APP_ENV=development",
                "ENABLE_REAL_LLM=true",
                "ALLOW_EXTERNAL_CALLS=true",
                "EXTERNAL_CALL_ALLOWED_ENVIRONMENTS=development",
                "LLM_ALLOWED_ENVIRONMENTS=development",
                "LITINERARY_AI_PROVIDER=openai_compatible",
                "LLM_PROVIDER=openai_compatible",
                "LLM_API_KEY=<set locally from approved secret storage>",
                "LLM_MODEL_NAME=<approved non-production model name>",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_preflight(env_file)

    assert result.returncode == 0
    assert "llmApiKeyPresent=False" in result.stdout
    assert "llmModelNamePresent=False" in result.stdout
    assert "liveLlmSmokeReady=False" in result.stdout


def test_network_preflight_redacts_credentials_and_proxy_values(tmp_path: Path) -> None:
    sentinel = "redacted-test-key-placeholder"
    proxy = "http://user:password@proxy.example.test:8080"
    env_file = tmp_path / ".env.development.local"
    env_file.write_text(
        "\n".join(
            [
                "APP_ENV=development",
                f"LLM_API_KEY={sentinel}",
                "LLM_MODEL_NAME=test-model",
                "LLM_BASE_URL=https://api.openai.com/v1",
                f"HTTPS_PROXY={proxy}",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_network_preflight(env_file)

    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert sentinel not in combined
    assert "password" not in combined
    assert proxy not in combined
    assert "httpsProxyPresent=True" in result.stdout
    assert "endpointHost=127.0.0.1" in result.stdout
    assert "networkPreflightReady=" in result.stdout
