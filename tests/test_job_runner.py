import asyncio
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.exceptions import DownloadFailed
from app.db.init_db import create_schema
from app.db.session import build_engine, build_session_factory
from app.models.job import DownloadJob, JobStatus, OutputFormat
from app.services.job_runner import JobRunner, ProgressReporter
from app.services.media_downloader import DownloadedMedia, MediaMetadata, ProgressCallback
from app.services.storage_service import StorageService


class SuccessfulDownloader:
    def fetch(
        self,
        url: str,
        output_format: OutputFormat,
        requested_height: int | None,
        requested_audio_bitrate_kbps: int | None,
        segment_start_seconds: int | None,
        segment_end_seconds: int | None,
        temp_dir: Path,
        progress: ProgressCallback,
    ) -> DownloadedMedia:
        assert url == "https://media.example/video"
        assert output_format is OutputFormat.mp3
        assert requested_height is None
        assert requested_audio_bitrate_kbps is None
        assert segment_start_seconds is None
        assert segment_end_seconds is None
        progress(35, "downloading", 350, 1000, 50, 13)
        progress(100, "processing")
        artifact = temp_dir / "media.mp3"
        artifact.write_bytes(b"audio")
        return DownloadedMedia(
            metadata=MediaMetadata(
                title="Sample Track",
                platform="Example",
                thumbnail_url="https://media.example/thumb.jpg",
                duration_seconds=42,
            ),
            file_path=artifact,
        )


class FailedDownloader:
    def fetch(self, *args: object, **kwargs: object) -> DownloadedMedia:
        raise DownloadFailed


class UnexpectedDownloader:
    def fetch(self, *args: object, **kwargs: object) -> DownloadedMedia:
        raise AssertionError("paused job should not be downloaded")


class PausedAfterProcessingDownloader:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def fetch(
        self,
        url: str,
        output_format: OutputFormat,
        requested_height: int | None,
        requested_audio_bitrate_kbps: int | None,
        segment_start_seconds: int | None,
        segment_end_seconds: int | None,
        temp_dir: Path,
        progress: ProgressCallback,
    ) -> DownloadedMedia:
        progress(100, "processing")
        with self.session_factory() as session:
            job = session.get(DownloadJob, "job-processing-paused")
            assert job is not None
            job.status = JobStatus.paused
            session.commit()
        artifact = temp_dir / "media.mp3"
        artifact.write_bytes(b"audio")
        return DownloadedMedia(
            metadata=MediaMetadata(
                title="Paused Track",
                platform=None,
                thumbnail_url=None,
                duration_seconds=None,
            ),
            file_path=artifact,
        )


def test_progress_reporter_throttles_repeated_status_updates() -> None:
    persisted: list[tuple[float | None, str, int | None, int | None, int | None, int | None]] = []
    reporter = ProgressReporter(
        persist=lambda percent, status, downloaded, total, speed, eta: persisted.append(
            (percent, status, downloaded, total, speed, eta)
        ),
        deadline=float("inf"),
        min_interval_seconds=60,
    )

    reporter(1, "downloading")
    reporter(2, "downloading")
    reporter(None, "processing")

    assert persisted == [
        (1, "downloading", None, None, None, None),
        (None, "processing", None, None, None, None),
    ]


def test_runner_publishes_completed_job_and_cleans_temp(tmp_path: Path) -> None:
    settings, session_factory, storage = build_runner_dependencies(tmp_path)
    with session_factory() as session:
        session.add(
            DownloadJob(
                id="job-success",
                source_url="https://media.example/video",
                requested_format=OutputFormat.mp3,
            )
        )
        session.commit()

    runner = JobRunner(settings, session_factory, storage, SuccessfulDownloader())
    runner._process_job("job-success")

    with session_factory() as session:
        job = session.get(DownloadJob, "job-success")
        assert job is not None
        assert job.status is JobStatus.completed
        assert job.title == "Sample Track"
        assert job.downloaded_bytes == 350
        assert job.total_bytes == 1000
        assert job.download_speed_bytes_per_second == 50
        assert job.eta_seconds == 13
        assert job.output_filename == "Sample Track.mp3"
        assert job.output_size_bytes == 5
        assert Path(job.output_path).read_bytes() == b"audio"
    assert not (settings.temp_dir / "job-success").exists()


def test_runner_marks_failure_and_cleans_temp(tmp_path: Path) -> None:
    settings, session_factory, storage = build_runner_dependencies(tmp_path)
    with session_factory() as session:
        session.add(
            DownloadJob(
                id="job-failed",
                source_url="https://media.example/video",
                requested_format=OutputFormat.mp4,
            )
        )
        session.commit()
    storage.temp_job_dir("job-failed")

    runner = JobRunner(settings, session_factory, storage, FailedDownloader())
    runner._process_job("job-failed")

    with session_factory() as session:
        job = session.get(DownloadJob, "job-failed")
        assert job is not None
        assert job.status is JobStatus.failed
        assert job.error_code == "DOWNLOAD_FAILED"
        assert job.output_path is None
    assert not (settings.temp_dir / "job-failed").exists()


def test_runner_skips_job_paused_before_worker_starts(tmp_path: Path) -> None:
    settings, session_factory, storage = build_runner_dependencies(tmp_path)
    with session_factory() as session:
        session.add(
            DownloadJob(
                id="job-paused",
                source_url="https://media.example/video",
                requested_format=OutputFormat.mp3,
                status=JobStatus.paused,
            )
        )
        session.commit()

    runner = JobRunner(settings, session_factory, storage, UnexpectedDownloader())
    runner._process_job("job-paused")

    with session_factory() as session:
        job = session.get(DownloadJob, "job-paused")
        assert job is not None
        assert job.status is JobStatus.paused
        assert job.output_path is None
    assert not (settings.temp_dir / "job-paused").exists()


def test_runner_preserves_processing_job_paused_before_publish(tmp_path: Path) -> None:
    settings, session_factory, storage = build_runner_dependencies(tmp_path)
    with session_factory() as session:
        session.add(
            DownloadJob(
                id="job-processing-paused",
                source_url="https://media.example/video",
                requested_format=OutputFormat.mp3,
            )
        )
        session.commit()

    runner = JobRunner(
        settings,
        session_factory,
        storage,
        PausedAfterProcessingDownloader(session_factory),
    )
    runner._process_job("job-processing-paused")

    with session_factory() as session:
        job = session.get(DownloadJob, "job-processing-paused")
        assert job is not None
        assert job.status is JobStatus.paused
        assert job.output_path is None
    assert (settings.temp_dir / "job-processing-paused" / "media.mp3").is_file()
    assert not (settings.storage_dir / "job-processing-paused").exists()


def test_runner_estimates_progress_from_known_total(tmp_path: Path) -> None:
    settings, session_factory, storage = build_runner_dependencies(tmp_path)
    with session_factory() as session:
        session.add(
            DownloadJob(
                id="job-progress",
                source_url="https://media.example/video",
                requested_format=OutputFormat.mp4,
                status=JobStatus.downloading,
                total_bytes=600,
            )
        )
        session.commit()

    runner = JobRunner(settings, session_factory, storage, SuccessfulDownloader())
    runner._progress("job-progress", None, "downloading", 200, None, None, None, False)

    with session_factory() as session:
        job = session.get(DownloadJob, "job-progress")
        assert job is not None
        assert job.progress_percent == 200 / 600 * 100


def test_runner_recovers_queued_job_on_start(tmp_path: Path) -> None:
    settings, session_factory, storage = build_runner_dependencies(tmp_path)
    with session_factory() as session:
        session.add(
            DownloadJob(
                id="job-recovered",
                source_url="https://media.example/video",
                requested_format=OutputFormat.mp3,
            )
        )
        session.commit()

    runner = JobRunner(settings, session_factory, storage, SuccessfulDownloader())

    async def recover_job() -> None:
        await runner.start()
        try:
            await runner.queue.join()
        finally:
            await runner.stop()

    asyncio.run(recover_job())

    with session_factory() as session:
        job = session.get(DownloadJob, "job-recovered")
        assert job is not None
        assert job.status is JobStatus.completed
        assert job.output_path is not None


def build_runner_dependencies(
    tmp_path: Path,
) -> tuple[Settings, sessionmaker[Session], StorageService]:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'runner.db'}",
        storage_dir=tmp_path / "storage",
        temp_dir=tmp_path / "temp",
    )
    storage = StorageService(settings)
    storage.prepare_directories()
    engine = build_engine(settings)
    create_schema(engine)
    return settings, build_session_factory(engine), storage
