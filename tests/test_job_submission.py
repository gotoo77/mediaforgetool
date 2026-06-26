import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.core.exceptions import MediaTooLong, QueueFull
from app.models.job import DownloadJob, JobStatus, OutputFormat
from app.schemas.job import CreateJobRequest
from app.services.job_submission import JobSubmissionService


class FakeRunner:
    def __init__(self, accepts: bool = True) -> None:
        self.accepts = accepts
        self.jobs: list[str] = []

    def enqueue(self, job_id: str) -> bool:
        self.jobs.append(job_id)
        return self.accepts


def test_job_submission_creates_and_enqueues_job(app_client: tuple[object, object]) -> None:
    client, _ = app_client
    runner = FakeRunner()
    session_factory = client.app.state.session_factory
    with session_factory() as session:
        job = JobSubmissionService(session, runner, client.app.state.settings).submit(
            CreateJobRequest(
                url="https://example.com/video",
                format=OutputFormat.mp4,
                resolution=720,
                title="Video",
                duration_seconds=120,
            )
        )

        assert job.status is JobStatus.queued
        assert job.requested_height == 720
        assert runner.jobs == [job.id]
        assert session.scalar(select(DownloadJob).where(DownloadJob.id == job.id)) is not None


def test_job_submission_marks_job_failed_when_queue_is_full(
    app_client: tuple[object, object],
) -> None:
    client, _ = app_client
    runner = FakeRunner(accepts=False)
    session_factory = client.app.state.session_factory
    with session_factory() as session:
        with pytest.raises(QueueFull):
            JobSubmissionService(session, runner, client.app.state.settings).submit(
                CreateJobRequest(url="https://example.com/video", format=OutputFormat.mp3)
            )

        job = session.scalar(select(DownloadJob))
        assert job is not None
        assert job.status is JobStatus.failed
        assert job.error_code == "QUEUE_FULL"


def test_job_submission_applies_segment_duration_limit(tmp_path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'db.sqlite'}",
        storage_dir=tmp_path / "storage",
        temp_dir=tmp_path / "temp",
        max_media_duration_seconds=10,
    )
    from app.db.init_db import create_schema
    from app.db.session import build_engine, build_session_factory

    engine = build_engine(settings)
    create_schema(engine)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        with pytest.raises(MediaTooLong):
            JobSubmissionService(session, FakeRunner(), settings).submit(
                CreateJobRequest(
                    url="https://example.com/video",
                    format=OutputFormat.mp4,
                    segment_start_seconds=0,
                    segment_end_seconds=11,
                )
            )
    engine.dispose()
