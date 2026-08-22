from scripts.ci import post_deploy_smoke


def test_wait_for_release_observes_backend_and_frontend(monkeypatch) -> None:
    calls = {"backend": 0, "frontend": 0}

    def fake_request_json(url: str):
        if url.endswith("/api/version"):
            calls["backend"] += 1
            return {"releaseSha": "abcdef1" if calls["backend"] > 1 else "old"}
        if url.endswith("/release.json"):
            calls["frontend"] += 1
            return {"releaseSha": "abcdef1"}
        raise AssertionError(url)

    monkeypatch.setattr(post_deploy_smoke, "request_json", fake_request_json)
    monkeypatch.setattr(post_deploy_smoke.time, "sleep", lambda _seconds: None)

    result = post_deploy_smoke.wait_for_release(
        backend_url="https://api.example.test",
        frontend_url="https://app.example.test",
        expected_sha="abcdef1",
        timeout_seconds=5,
        interval_seconds=1,
    )

    assert result == {"backendReleaseSha": "abcdef1", "frontendReleaseSha": "abcdef1"}


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
