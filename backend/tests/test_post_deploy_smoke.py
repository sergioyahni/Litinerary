import urllib.error

import pytest

from scripts.ci import post_deploy_smoke


def test_wait_for_release_observes_backend_and_frontend(monkeypatch) -> None:
    calls = {"backend": 0, "frontend": 0}

    def fake_read_json(url: str):
        if url.endswith("/api/version"):
            calls["backend"] += 1
            return {"releaseSha": "abcdef1" if calls["backend"] > 1 else "old"}
        if url.endswith("/release.json"):
            calls["frontend"] += 1
            return {"releaseSha": "abcdef1"}
        raise AssertionError(url)

    monkeypatch.setattr(post_deploy_smoke, "_read_json", fake_read_json)
    monkeypatch.setattr(post_deploy_smoke.time, "sleep", lambda _seconds: None)

    result = post_deploy_smoke.wait_for_release(
        backend_url="https://api.example.test",
        frontend_url="https://app.example.test",
        expected_sha="abcdef1",
        timeout_seconds=5,
        interval_seconds=1,
    )

    assert result == {"backendReleaseSha": "abcdef1", "frontendReleaseSha": "abcdef1"}


def test_wait_for_release_retries_backend_transient_502(monkeypatch) -> None:
    calls = {"backend": 0}

    def fake_read_json(url: str):
        if url.endswith("/api/version"):
            calls["backend"] += 1
            if calls["backend"] == 1:
                raise _http_error(502)
        return {"releaseSha": "abcdef1"}

    monkeypatch.setattr(post_deploy_smoke, "_read_json", fake_read_json)
    monkeypatch.setattr(post_deploy_smoke.time, "sleep", lambda _seconds: None)

    result = post_deploy_smoke.wait_for_release(
        backend_url="https://api.example.test",
        frontend_url="https://app.example.test",
        expected_sha="abcdef1",
        timeout_seconds=5,
        interval_seconds=1,
    )

    assert result == {"backendReleaseSha": "abcdef1", "frontendReleaseSha": "abcdef1"}
    assert calls["backend"] == 2


def test_wait_for_release_retries_frontend_transient_503(monkeypatch) -> None:
    calls = {"frontend": 0}

    def fake_read_json(url: str):
        if url.endswith("/release.json"):
            calls["frontend"] += 1
            if calls["frontend"] == 1:
                raise _http_error(503)
        return {"releaseSha": "abcdef1"}

    monkeypatch.setattr(post_deploy_smoke, "_read_json", fake_read_json)
    monkeypatch.setattr(post_deploy_smoke.time, "sleep", lambda _seconds: None)

    result = post_deploy_smoke.wait_for_release(
        backend_url="https://api.example.test",
        frontend_url="https://app.example.test",
        expected_sha="abcdef1",
        timeout_seconds=5,
        interval_seconds=1,
    )

    assert result == {"backendReleaseSha": "abcdef1", "frontendReleaseSha": "abcdef1"}
    assert calls["frontend"] == 2


def test_wait_for_release_retries_temporary_url_error(monkeypatch) -> None:
    calls = {"backend": 0}

    def fake_read_json(url: str):
        if url.endswith("/api/version"):
            calls["backend"] += 1
            if calls["backend"] == 1:
                raise urllib.error.URLError(TimeoutError())
        return {"releaseSha": "abcdef1"}

    monkeypatch.setattr(post_deploy_smoke, "_read_json", fake_read_json)
    monkeypatch.setattr(post_deploy_smoke.time, "sleep", lambda _seconds: None)

    result = post_deploy_smoke.wait_for_release(
        backend_url="https://api.example.test",
        frontend_url="https://app.example.test",
        expected_sha="abcdef1",
        timeout_seconds=5,
        interval_seconds=1,
    )

    assert result == {"backendReleaseSha": "abcdef1", "frontendReleaseSha": "abcdef1"}
    assert calls["backend"] == 2


def test_wait_for_release_retries_stale_release_sha(monkeypatch) -> None:
    calls = {"backend": 0, "frontend": 0}

    def fake_read_json(url: str):
        if url.endswith("/api/version"):
            calls["backend"] += 1
            return {"releaseSha": "abcdef1" if calls["backend"] > 1 else "old"}
        if url.endswith("/release.json"):
            calls["frontend"] += 1
            return {"releaseSha": "abcdef1" if calls["frontend"] > 1 else "old"}
        raise AssertionError(url)

    monkeypatch.setattr(post_deploy_smoke, "_read_json", fake_read_json)
    monkeypatch.setattr(post_deploy_smoke.time, "sleep", lambda _seconds: None)

    result = post_deploy_smoke.wait_for_release(
        backend_url="https://api.example.test",
        frontend_url="https://app.example.test",
        expected_sha="abcdef1",
        timeout_seconds=5,
        interval_seconds=1,
    )

    assert result == {"backendReleaseSha": "abcdef1", "frontendReleaseSha": "abcdef1"}
    assert calls == {"backend": 2, "frontend": 2}


def test_wait_for_release_times_out_after_persistent_transient_failures(monkeypatch) -> None:
    clock = {"now": 0.0}

    def fake_read_json(url: str):
        if url.endswith("/api/version"):
            raise _http_error(502)
        if url.endswith("/release.json"):
            raise _http_error(503)
        raise AssertionError(url)

    def fake_sleep(seconds: int) -> None:
        clock["now"] += seconds

    monkeypatch.setattr(post_deploy_smoke, "_read_json", fake_read_json)
    monkeypatch.setattr(post_deploy_smoke.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(post_deploy_smoke.time, "sleep", fake_sleep)

    with pytest.raises(SystemExit) as exc_info:
        post_deploy_smoke.wait_for_release(
            backend_url="https://api.example.test",
            frontend_url="https://app.example.test",
            expected_sha="abcdef1",
            timeout_seconds=2,
            interval_seconds=1,
        )

    message = str(exc_info.value)
    assert "Timed out waiting for release SHA." in message
    assert "expected=abcdef1" in message
    assert "backend=http_status=502" in message
    assert "frontend=http_status=503" in message
    assert "api.example.test" not in message
    assert "app.example.test" not in message


def test_request_json_still_fails_immediately_on_http_error(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        raise _http_error(502)

    monkeypatch.setattr(post_deploy_smoke.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(SystemExit) as exc_info:
        post_deploy_smoke.request_json(
            "https://user:secret@api.example.test/api/health?token=secret"
        )

    message = str(exc_info.value)
    assert calls["count"] == 1
    assert "status=502" in message
    assert "secret" not in message
    assert "token" not in message


def test_validate_frontend_requires_index_and_spa_fallback(monkeypatch) -> None:
    requested = []

    def fake_request_text(url: str) -> str:
        requested.append(url)
        return "<!doctype html><html></html>"

    monkeypatch.setattr(post_deploy_smoke, "request_text", fake_request_text)

    post_deploy_smoke.validate_frontend("https://app.example.test")

    assert requested == [
        "https://app.example.test/",
        "https://app.example.test/itineraries/plu-07-spa-fallback-check",
    ]


def _http_error(status: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://example.test/redacted",
        code=status,
        msg="transient",
        hdrs=None,
        fp=None,
    )
