from pathlib import Path

from fastapi.testclient import TestClient

from app.core.exceptions import SourceNoStreams
from app.models.job import DownloadJob, JobStatus, OutputFormat
from app.services.media_downloader import MediaInspection, SegmentSuggestion, VideoVariant
from app.services.rate_limiter import SlidingWindowRateLimiter


class FullRunner:
    def __init__(self) -> None:
        self.jobs: list[str] = []

    def enqueue(self, job_id: str) -> bool:
        self.jobs.append(job_id)
        return False


def test_healthz_returns_process_status(app_client: tuple[TestClient, object]) -> None:
    client, _ = app_client

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home_versions_static_assets(app_client: tuple[TestClient, object]) -> None:
    client, _ = app_client

    response = client.get("/")

    assert response.status_code == 200
    assert "/static/app.css?v=" in response.text
    assert "/static/app.js?v=" in response.text
    assert "Atelier" in response.text
    assert "Concatener audios" in response.text


def test_create_job_queues_valid_request(
    app_client: tuple[TestClient, object],
    monkeypatch: object,
) -> None:
    client, runner = app_client
    monkeypatch.setattr("app.api.routes.jobs.validate_public_media_url", lambda url, _: url)

    response = client.post(
        "/api/jobs",
        json={"url": "https://media.example/video", "format": "mp3"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["source_url"] == "https://media.example/video"
    assert body["requested_format"] == "mp3"
    assert body["requested_audio_bitrate_kbps"] is None
    assert body["status"] == "queued"
    assert runner.jobs == [body["id"]]


def test_create_mp3_job_persists_requested_bitrate(
    app_client: tuple[TestClient, object],
    monkeypatch: object,
) -> None:
    client, _ = app_client
    monkeypatch.setattr("app.api.routes.jobs.validate_public_media_url", lambda url, _: url)

    response = client.post(
        "/api/jobs",
        json={
            "url": "https://media.example/video",
            "format": "mp3",
            "audio_bitrate_kbps": 320,
        },
    )

    assert response.status_code == 202
    assert response.json()["requested_audio_bitrate_kbps"] == 320


def test_create_mp4_job_persists_requested_resolution(
    app_client: tuple[TestClient, object],
    monkeypatch: object,
) -> None:
    client, _ = app_client
    monkeypatch.setattr("app.api.routes.jobs.validate_public_media_url", lambda url, _: url)
    client.app.state.settings.ytdlp_cookies_file = None
    client.app.state.settings.ytdlp_cookies_from_browser = None

    response = client.post(
        "/api/jobs",
        json={"url": "https://media.example/video", "format": "mp4", "resolution": 720},
    )

    assert response.status_code == 202
    assert response.json()["requested_height"] == 720


def test_create_job_persists_requested_segment(
    app_client: tuple[TestClient, object],
    monkeypatch: object,
) -> None:
    client, _ = app_client
    monkeypatch.setattr("app.api.routes.jobs.validate_public_media_url", lambda url, _: url)

    response = client.post(
        "/api/jobs",
        json={
            "url": "https://media.example/video",
            "format": "mp3",
            "segment_start_seconds": 60,
            "segment_end_seconds": 120,
            "title": "Sample Video",
            "estimated_total_bytes": 600,
        },
    )

    assert response.status_code == 202
    assert response.json()["segment_start_seconds"] == 60
    assert response.json()["segment_end_seconds"] == 120
    assert response.json()["title"] == "Sample Video [01:00-02:00]"
    assert response.json()["total_bytes"] == 600


def test_create_job_rejects_oversized_segment(
    app_client: tuple[TestClient, object],
    monkeypatch: object,
) -> None:
    client, _ = app_client
    monkeypatch.setattr("app.api.routes.jobs.validate_public_media_url", lambda url, _: url)
    client.app.state.settings.max_media_duration_seconds = 60

    response = client.post(
        "/api/jobs",
        json={
            "url": "https://media.example/video",
            "format": "mp3",
            "segment_start_seconds": 0,
            "segment_end_seconds": 61,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "MEDIA_TOO_LONG"


def test_inspect_media_returns_estimates(
    app_client: tuple[TestClient, object],
    monkeypatch: object,
) -> None:
    client, _ = app_client
    monkeypatch.setattr("app.api.routes.jobs.validate_public_media_url", lambda url, _: url)
    monkeypatch.setattr(
        "app.api.routes.jobs.MediaDownloader.inspect",
        lambda self, url: MediaInspection(
            title="Sample",
            platform="Example",
            thumbnail_url=None,
            duration_seconds=20,
            mp3_estimated_size_bytes=480_000,
            mp4_variants=[
                VideoVariant(resolution=720, selected_height=720, estimated_size_bytes=8_000_000)
            ],
            segment_suggestions=[],
        ),
    )

    response = client.post("/api/jobs/inspect", json={"url": "https://media.example/video"})

    assert response.status_code == 200
    assert response.json()["mp3_estimated_size_bytes"] == 480_000
    assert response.json()["mp4_variants"] == [
        {"resolution": 720, "selected_height": 720, "estimated_size_bytes": 8_000_000}
    ]


def test_inspect_media_returns_segment_suggestions_for_long_media(
    app_client: tuple[TestClient, object],
    monkeypatch: object,
) -> None:
    client, _ = app_client
    monkeypatch.setattr("app.api.routes.jobs.validate_public_media_url", lambda url, _: url)
    monkeypatch.setattr(
        "app.api.routes.jobs.MediaDownloader.inspect",
        lambda self, url: MediaInspection(
            title="Long Sample",
            platform="Example",
            thumbnail_url=None,
            duration_seconds=125,
            mp3_estimated_size_bytes=3_000_000,
            mp4_variants=[],
            segment_suggestions=[
                SegmentSuggestion(start_seconds=0, end_seconds=60),
                SegmentSuggestion(start_seconds=60, end_seconds=120),
                SegmentSuggestion(start_seconds=120, end_seconds=125),
            ],
        ),
    )

    response = client.post("/api/jobs/inspect", json={"url": "https://media.example/video"})

    assert response.status_code == 200
    assert response.json()["segment_suggestions"] == [
        {"start_seconds": 0, "end_seconds": 60},
        {"start_seconds": 60, "end_seconds": 120},
        {"start_seconds": 120, "end_seconds": 125},
    ]


def test_inspect_media_no_streams_points_to_credentials(
    app_client: tuple[TestClient, object],
    monkeypatch: object,
) -> None:
    client, _ = app_client
    monkeypatch.setattr("app.api.routes.jobs.validate_public_media_url", lambda url, _: url)
    client.app.state.settings.ytdlp_cookies_file = None
    client.app.state.settings.ytdlp_cookies_from_browser = None

    def fail_inspection(self: object, url: str) -> object:
        raise SourceNoStreams()

    monkeypatch.setattr("app.api.routes.jobs.MediaDownloader.inspect", fail_inspection)

    response = client.post("/api/jobs/inspect", json={"url": "https://media.example/video"})

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "SOURCE_NO_STREAMS",
        "message": (
            "La source ne fournit aucun flux sans credentials. Configure "
            "YTDLP_COOKIES_FILE ou YTDLP_COOKIES_FROM_BROWSER, puis relance l'analyse."
        ),
    }


def test_inspect_media_no_streams_mentions_configured_credentials(
    app_client: tuple[TestClient, object],
    monkeypatch: object,
) -> None:
    client, _ = app_client
    monkeypatch.setattr("app.api.routes.jobs.validate_public_media_url", lambda url, _: url)
    client.app.state.settings.ytdlp_cookies_from_browser = "firefox:default"

    def fail_inspection(self: object, url: str) -> object:
        raise SourceNoStreams()

    monkeypatch.setattr("app.api.routes.jobs.MediaDownloader.inspect", fail_inspection)

    response = client.post("/api/jobs/inspect", json={"url": "https://media.example/video"})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "SOURCE_NO_STREAMS"
    assert "avec les credentials yt-dlp configures" in response.json()["detail"]["message"]


def test_create_job_rejects_local_address(app_client: tuple[TestClient, object]) -> None:
    client, _ = app_client

    response = client.post("/api/jobs", json={"url": "http://127.0.0.1/video", "format": "mp4"})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_URL"


def test_create_job_rate_limits_client(
    app_client: tuple[TestClient, object],
    monkeypatch: object,
) -> None:
    client, runner = app_client
    monkeypatch.setattr("app.api.routes.jobs.validate_public_media_url", lambda url, _: url)
    client.app.state.job_rate_limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60)

    accepted = client.post(
        "/api/jobs",
        json={"url": "https://media.example/one", "format": "mp3"},
    )
    limited = client.post(
        "/api/jobs",
        json={"url": "https://media.example/two", "format": "mp4"},
    )

    assert accepted.status_code == 202
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "60"
    assert limited.json()["detail"]["code"] == "RATE_LIMITED"
    assert runner.jobs == [accepted.json()["id"]]


def test_create_job_returns_service_unavailable_when_queue_is_full(
    app_client: tuple[TestClient, object],
    monkeypatch: object,
) -> None:
    client, _ = app_client
    full_runner = FullRunner()
    client.app.state.job_runner = full_runner
    monkeypatch.setattr("app.api.routes.jobs.validate_public_media_url", lambda url, _: url)

    response = client.post(
        "/api/jobs",
        json={"url": "https://media.example/video", "format": "mp3"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "QUEUE_FULL",
        "message": "This instance already has too many pending media jobs.",
    }
    assert len(full_runner.jobs) == 1


def test_resume_interrupted_job_requeues_existing_job(
    app_client: tuple[TestClient, object],
) -> None:
    client, runner = app_client
    with client.app.state.session_factory() as session:
        session.add(
            DownloadJob(
                id="interrupted",
                source_url="https://media.example/video",
                requested_format=OutputFormat.mp4,
                status=JobStatus.interrupted,
                progress_percent=0,
                downloaded_bytes=120,
                error_code="JOB_INTERRUPTED",
                error_message="The app restarted while this job was running.",
            )
        )
        session.commit()

    response = client.post("/api/jobs/interrupted/resume")

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["error"] is None
    assert body["downloaded_bytes"] == 120
    assert runner.jobs == ["interrupted"]


def test_resume_running_job_returns_conflict(app_client: tuple[TestClient, object]) -> None:
    client, runner = app_client
    with client.app.state.session_factory() as session:
        session.add(
            DownloadJob(
                id="running",
                source_url="https://media.example/video",
                requested_format=OutputFormat.mp4,
                status=JobStatus.downloading,
            )
        )
        session.commit()

    response = client.post("/api/jobs/running/resume")

    assert response.status_code == 409
    assert runner.jobs == []


def test_pause_running_job_marks_job_paused(app_client: tuple[TestClient, object]) -> None:
    client, _ = app_client
    with client.app.state.session_factory() as session:
        session.add(
            DownloadJob(
                id="running",
                source_url="https://media.example/video",
                requested_format=OutputFormat.mp4,
                status=JobStatus.downloading,
            )
        )
        session.commit()

    response = client.post("/api/jobs/running/pause")

    assert response.status_code == 200
    assert response.json()["status"] == "paused"


def test_pause_processing_job_marks_job_paused(app_client: tuple[TestClient, object]) -> None:
    client, _ = app_client
    with client.app.state.session_factory() as session:
        session.add(
            DownloadJob(
                id="processing",
                source_url="https://media.example/video",
                requested_format=OutputFormat.mp3,
                status=JobStatus.processing,
            )
        )
        session.commit()

    response = client.post("/api/jobs/processing/pause")

    assert response.status_code == 200
    assert response.json()["status"] == "paused"


def test_get_missing_job_returns_not_found(app_client: tuple[TestClient, object]) -> None:
    client, _ = app_client

    response = client.get("/api/jobs/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found."


def test_job_file_returns_conflict_when_output_is_not_ready(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    with client.app.state.session_factory() as session:
        session.add(
            DownloadJob(
                id="queued",
                source_url="https://media.example/video",
                requested_format=OutputFormat.mp3,
                status=JobStatus.queued,
            )
        )
        session.commit()

    response = client.get("/api/jobs/queued/file")

    assert response.status_code == 409
    assert response.json()["detail"] == "Job output is not ready."


def test_job_file_returns_gone_when_completed_output_is_missing(
    app_client: tuple[TestClient, object],
    tmp_path: Path,
) -> None:
    client, _ = app_client
    missing_output = tmp_path / "storage" / "expired" / "final.mp3"
    with client.app.state.session_factory() as session:
        session.add(
            DownloadJob(
                id="expired",
                source_url="https://media.example/video",
                requested_format=OutputFormat.mp3,
                status=JobStatus.completed,
                output_path=str(missing_output),
                output_filename="track.mp3",
            )
        )
        session.commit()

    response = client.get("/api/jobs/expired/file")

    assert response.status_code == 410
    assert response.json()["detail"] == "Job output has expired."


def test_completed_job_serves_output(app_client: tuple[TestClient, object], tmp_path: Path) -> None:
    client, _ = app_client
    output = tmp_path / "storage" / "done" / "final.mp3"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"media")
    with client.app.state.session_factory() as session:
        job = DownloadJob(
            id="done",
            source_url="https://media.example/video",
            requested_format=OutputFormat.mp3,
            status=JobStatus.completed,
            output_path=str(output),
            output_filename="track.mp3",
            output_size_bytes=5,
        )
        session.add(job)
        session.commit()

    status_response = client.get("/api/jobs/done")
    file_response = client.get("/api/jobs/done/file")

    assert status_response.json()["download_url"] == "/api/jobs/done/file"
    assert file_response.status_code == 200
    assert file_response.content == b"media"


def test_delete_completed_job_removes_history_and_files(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    storage_dir = client.app.state.settings.storage_dir / "done"
    temp_dir = client.app.state.settings.temp_dir / "done"
    output = storage_dir / "final.mp3"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"media")
    temp_dir.mkdir(parents=True)
    (temp_dir / "media.part").write_bytes(b"partial")
    with client.app.state.session_factory() as session:
        session.add(
            DownloadJob(
                id="done",
                source_url="https://media.example/video",
                requested_format=OutputFormat.mp3,
                status=JobStatus.completed,
                output_path=str(output),
                output_filename="track.mp3",
            )
        )
        session.commit()

    response = client.delete("/api/jobs/done")

    assert response.status_code == 200
    assert response.json() == {
        "jobs_deleted": 1,
        "output_dirs_deleted": 1,
        "temp_dirs_deleted": 1,
        "bytes_reclaimed": 12,
        "active_jobs_skipped": 0,
    }
    assert not storage_dir.exists()
    assert not temp_dir.exists()
    with client.app.state.session_factory() as session:
        assert session.get(DownloadJob, "done") is None


def test_delete_running_job_returns_conflict(app_client: tuple[TestClient, object]) -> None:
    client, _ = app_client
    with client.app.state.session_factory() as session:
        session.add(
            DownloadJob(
                id="running",
                source_url="https://media.example/video",
                requested_format=OutputFormat.mp4,
                status=JobStatus.downloading,
            )
        )
        session.commit()

    response = client.delete("/api/jobs/running")

    assert response.status_code == 409
    assert response.json()["detail"] == "Only inactive jobs can be deleted."


def test_delete_paused_job_returns_conflict(app_client: tuple[TestClient, object]) -> None:
    client, _ = app_client
    with client.app.state.session_factory() as session:
        session.add(
            DownloadJob(
                id="paused",
                source_url="https://media.example/video",
                requested_format=OutputFormat.mp3,
                status=JobStatus.paused,
            )
        )
        session.commit()

    response = client.delete("/api/jobs/paused")

    assert response.status_code == 409
    assert response.json()["detail"] == "Only inactive jobs can be deleted."


def test_clear_history_removes_inactive_jobs_and_skips_active(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    done_storage = client.app.state.settings.storage_dir / "done"
    done_temp = client.app.state.settings.temp_dir / "done"
    failed_temp = client.app.state.settings.temp_dir / "failed"
    running_storage = client.app.state.settings.storage_dir / "running"
    paused_temp = client.app.state.settings.temp_dir / "paused"
    done_storage.mkdir(parents=True)
    done_temp.mkdir(parents=True)
    failed_temp.mkdir(parents=True)
    running_storage.mkdir(parents=True)
    paused_temp.mkdir(parents=True)
    (done_storage / "final.mp3").write_bytes(b"media")
    (done_temp / "media.part").write_bytes(b"partial")
    (failed_temp / "leftover.part").write_bytes(b"temp")
    (running_storage / "active.part").write_bytes(b"running")
    (paused_temp / "paused.part").write_bytes(b"paused")
    with client.app.state.session_factory() as session:
        session.add_all(
            [
                DownloadJob(
                    id="done",
                    source_url="https://media.example/done",
                    requested_format=OutputFormat.mp3,
                    status=JobStatus.completed,
                ),
                DownloadJob(
                    id="failed",
                    source_url="https://media.example/failed",
                    requested_format=OutputFormat.mp4,
                    status=JobStatus.failed,
                ),
                DownloadJob(
                    id="running",
                    source_url="https://media.example/running",
                    requested_format=OutputFormat.mp4,
                    status=JobStatus.downloading,
                ),
                DownloadJob(
                    id="paused",
                    source_url="https://media.example/paused",
                    requested_format=OutputFormat.mp3,
                    status=JobStatus.paused,
                ),
            ]
        )
        session.commit()

    response = client.delete("/api/jobs")

    assert response.status_code == 200
    assert response.json() == {
        "jobs_deleted": 2,
        "output_dirs_deleted": 1,
        "temp_dirs_deleted": 2,
        "bytes_reclaimed": 16,
        "active_jobs_skipped": 2,
    }
    assert not done_storage.exists()
    assert not done_temp.exists()
    assert not failed_temp.exists()
    assert running_storage.exists()
    assert paused_temp.exists()
    with client.app.state.session_factory() as session:
        assert session.get(DownloadJob, "done") is None
        assert session.get(DownloadJob, "failed") is None
        assert session.get(DownloadJob, "running") is not None
        assert session.get(DownloadJob, "paused") is not None
