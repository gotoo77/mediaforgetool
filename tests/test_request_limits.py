from fastapi.testclient import TestClient


def test_large_request_body_is_rejected(app_client: tuple[TestClient, object]) -> None:
    client, _ = app_client
    client.app.state.settings.max_request_body_bytes = 64

    response = client.post(
        "/api/jobs/inspect",
        content=b'{"url":"' + b"https://media.example/video" + (b"a" * 128) + b'"}',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == {
        "code": "REQUEST_BODY_TOO_LARGE",
        "message": "The request body exceeds this instance limit.",
    }


def test_small_request_body_still_reaches_route(
    app_client: tuple[TestClient, object],
    monkeypatch: object,
) -> None:
    client, _ = app_client
    client.app.state.settings.max_request_body_bytes = 512
    monkeypatch.setattr("app.api.routes.jobs.validate_public_media_url", lambda url, _: url)
    monkeypatch.setattr(
        "app.api.routes.jobs.MediaDownloader.inspect",
        lambda self, url: {
            "title": None,
            "platform": None,
            "thumbnail_url": None,
            "duration_seconds": None,
            "mp3_estimated_size_bytes": None,
            "mp4_variants": [],
            "segment_suggestions": [],
        },
    )

    response = client.post("/api/jobs/inspect", json={"url": "https://media.example/video"})

    assert response.status_code == 200
