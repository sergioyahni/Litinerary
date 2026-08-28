import pytest

from scripts.ci.render_deploy import deploy_hook_url_with_ref


def test_deploy_hook_url_adds_ref_to_existing_secret_query() -> None:
    url = deploy_hook_url_with_ref(
        "https://api.render.com/deploy/srv-example?key=secret",
        "abcdef1234567890abcdef1234567890abcdef12",
    )

    assert url == (
        "https://api.render.com/deploy/srv-example"
        "?key=secret&ref=abcdef1234567890abcdef1234567890abcdef12"
    )


def test_deploy_hook_url_handles_existing_query_parameters() -> None:
    url = deploy_hook_url_with_ref(
        "https://api.render.com/deploy/srv-example?key=secret&clearCache=true",
        "abcdef1",
    )

    assert url.endswith("?key=secret&clearCache=true&ref=abcdef1")


def test_deploy_hook_url_replaces_existing_ref() -> None:
    url = deploy_hook_url_with_ref(
        "https://api.render.com/deploy/srv-example?key=secret&ref=old",
        "abcdef1",
    )

    assert url.endswith("?key=secret&ref=abcdef1")
    assert "old" not in url


def test_deploy_hook_url_rejects_non_sha_ref() -> None:
    with pytest.raises(ValueError):
        deploy_hook_url_with_ref("https://api.render.com/deploy/srv-example?key=secret", "main")
