from fastapi.testclient import TestClient


def test_security_headers_are_applied_to_pages(app_client: tuple[TestClient, object]) -> None:
    client, _ = app_client

    response = client.get("/")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert "img-src 'self' https: data:" in response.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_security_headers_are_applied_to_api(app_client: tuple[TestClient, object]) -> None:
    client, _ = app_client

    response = client.get("/healthz")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
