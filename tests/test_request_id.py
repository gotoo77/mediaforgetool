from fastapi.testclient import TestClient


def test_request_id_header_is_generated(app_client: tuple[TestClient, object]) -> None:
    client, _ = app_client

    response = client.get("/healthz")

    assert response.headers["X-Request-ID"]


def test_request_id_header_is_preserved(app_client: tuple[TestClient, object]) -> None:
    client, _ = app_client

    response = client.get("/healthz", headers={"X-Request-ID": "external-request-1"})

    assert response.headers["X-Request-ID"] == "external-request-1"


def test_request_id_header_is_added_to_limit_errors(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    client.app.state.settings.max_request_body_bytes = 64

    response = client.post(
        "/api/jobs/inspect",
        content=b'{"url":"' + b"https://media.example/video" + (b"a" * 128) + b'"}',
        headers={"Content-Type": "application/json", "X-Request-ID": "too-large-1"},
    )

    assert response.status_code == 413
    assert response.headers["X-Request-ID"] == "too-large-1"
