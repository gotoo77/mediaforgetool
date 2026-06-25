import asyncio
import logging
import shutil
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.exceptions import JobPaused, JobTimeout, MediaForgeToolError
from app.models.job import DownloadJob, JobStatus
from app.services.media_downloader import MediaDownloader
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)
PersistProgress = Callable[
    [float | None, str, int | None, int | None, int | None, int | None],
    None,
]


class ProgressReporter:
    def __init__(
        self,
        persist: PersistProgress,
        deadline: float,
        min_interval_seconds: float,
    ) -> None:
        self.persist = persist
        self.deadline = deadline
        self.min_interval_seconds = min_interval_seconds
        self.last_persisted_at = 0.0
        self.last_status: str | None = None

    def __call__(
        self,
        percent: float | None,
        status: str,
        downloaded_bytes: int | None = None,
        total_bytes: int | None = None,
        speed_bytes_per_second: int | None = None,
        eta_seconds: int | None = None,
    ) -> None:
        now = time.monotonic()
        if now > self.deadline:
            raise JobTimeout

        status_changed = status != self.last_status
        if not status_changed and now - self.last_persisted_at < self.min_interval_seconds:
            return

        self.persist(
            percent,
            status,
            downloaded_bytes,
            total_bytes,
            speed_bytes_per_second,
            eta_seconds,
        )
        self.last_persisted_at = now
        self.last_status = status


class JobRunner:
    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        storage: StorageService,
        downloader: MediaDownloader,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.storage = storage
        self.downloader = downloader
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=settings.max_queue_size)
        self.workers: list[asyncio.Task[None]] = []

    async def start(self) -> None:
        queued_job_ids: list[str]
        with self.session_factory() as session:
            session.execute(
                update(DownloadJob)
                .where(
                    DownloadJob.status.in_(
                        [JobStatus.extracting, JobStatus.downloading, JobStatus.processing]
                    )
                )
                .values(
                    status=JobStatus.interrupted,
                    error_code="JOB_INTERRUPTED",
                    error_message="The app restarted while this job was running.",
                )
            )
            queued_job_ids = list(
                session.scalars(
                    select(DownloadJob.id)
                    .where(DownloadJob.status == JobStatus.queued)
                    .order_by(DownloadJob.created_at.asc())
                ).all()
            )
            session.commit()
        self._recover_queued_jobs(queued_job_ids)
        self.workers = [
            asyncio.create_task(self._worker(), name=f"mediaforgetool-job-worker-{index}")
            for index in range(self.settings.max_concurrent_jobs)
        ]

    async def stop(self) -> None:
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

    def enqueue(self, job_id: str) -> bool:
        try:
            self.queue.put_nowait(job_id)
        except asyncio.QueueFull:
            return False
        return True

    def _recover_queued_jobs(self, job_ids: list[str]) -> None:
        for job_id in job_ids:
            if self.enqueue(job_id):
                logger.info(
                    "Queued job recovered",
                    extra={"event": "queued_job_recovered", "job_id": job_id},
                )
                continue
            with self.session_factory() as session:
                job = session.get(DownloadJob, job_id)
                if job is None or job.status is not JobStatus.queued:
                    continue
                job.status = JobStatus.failed
                job.error_code = "QUEUE_FULL"
                job.error_message = "This instance could not recover all queued media jobs."
                session.commit()

    async def _worker(self) -> None:
        while True:
            job_id = await self.queue.get()
            try:
                await asyncio.to_thread(self._process_job, job_id)
            finally:
                self.queue.task_done()

    def _process_job(self, job_id: str) -> None:
        with self.session_factory() as session:
            job = session.get(DownloadJob, job_id)
            if job is None or job.status is not JobStatus.queued:
                return
            self._set_status(session, job, JobStatus.extracting, 0)
            url = job.source_url
            output_format = job.requested_format
            requested_height = job.requested_height
            requested_audio_bitrate_kbps = job.requested_audio_bitrate_kbps
            segment_start_seconds = job.segment_start_seconds
            segment_end_seconds = job.segment_end_seconds

        temp_dir = self.storage.temp_job_dir(job_id)
        stop_monitor = threading.Event()
        monitor = threading.Thread(
            target=self._monitor_temp_download,
            args=(job_id, temp_dir, stop_monitor),
            name=f"mediaforgetool-temp-monitor-{job_id}",
            daemon=True,
        )
        report_progress = ProgressReporter(
            persist=lambda percent, status, downloaded, total, speed, eta: self._progress(
                job_id,
                percent,
                status,
                downloaded,
                total,
                speed,
                eta,
            ),
            deadline=time.monotonic() + self.settings.job_timeout_seconds,
            min_interval_seconds=self.settings.progress_update_interval_seconds,
        )

        try:
            monitor.start()
            result = self.downloader.fetch(
                url,
                output_format,
                requested_height,
                requested_audio_bitrate_kbps,
                segment_start_seconds,
                segment_end_seconds,
                temp_dir,
                report_progress,
            )
            self._raise_if_paused(job_id)
            report_progress(100, "processing")
            target, filename, size = self.storage.publish_file(
                job_id,
                result.file_path,
                result.metadata.title,
            )
            with self.session_factory() as session:
                job = session.get(DownloadJob, job_id)
                if job is None:
                    return
                job.title = job.title or result.metadata.title
                job.platform = job.platform or result.metadata.platform
                job.thumbnail_url = job.thumbnail_url or result.metadata.thumbnail_url
                if segment_start_seconds is not None and segment_end_seconds is not None:
                    job.duration_seconds = segment_end_seconds - segment_start_seconds
                else:
                    job.duration_seconds = result.metadata.duration_seconds
                job.output_path = str(target)
                job.output_filename = filename
                job.output_size_bytes = size
                job.progress_percent = 100
                job.status = JobStatus.completed
                job.completed_at = datetime.now(UTC)
                job.expires_at = job.completed_at + timedelta(
                    hours=self.settings.output_retention_hours
                )
                session.commit()
                logger.info(
                    "Job completed",
                    extra={"event": "job_completed", "job_id": job_id, "status": job.status.value},
                )
        except JobPaused:
            self._pause(job_id)
        except MediaForgeToolError as exc:
            self._fail(job_id, exc)
        except Exception:
            logger.exception(
                "Unhandled job failure",
                extra={"event": "job_failed", "job_id": job_id},
            )
            self._fail(job_id, MediaForgeToolError())
        finally:
            stop_monitor.set()
            monitor.join(timeout=1)
            if not self._preserve_temp_dir(job_id):
                self.storage.remove_temp_job_dir(job_id)

    def _monitor_temp_download(
        self,
        job_id: str,
        temp_dir: Path,
        stop_monitor: threading.Event,
    ) -> None:
        last_size = 0
        last_seen_at = time.monotonic()
        interval = self.settings.progress_update_interval_seconds
        while not stop_monitor.wait(interval):
            current_size = _temp_file_size(temp_dir)
            if self._is_paused(job_id):
                continue
            if current_size <= 0:
                continue
            now = time.monotonic()
            elapsed = max(now - last_seen_at, 0.001)
            speed = int((current_size - last_size) / elapsed) if current_size > last_size else None
            last_size = current_size
            last_seen_at = now
            self._progress(
                job_id,
                None,
                "downloading",
                current_size,
                None,
                speed,
                None,
                update_percent=False,
            )

    def _progress(
        self,
        job_id: str,
        percent: float | None,
        status: str,
        downloaded_bytes: int | None,
        total_bytes: int | None,
        speed_bytes_per_second: int | None,
        eta_seconds: int | None,
        update_percent: bool = True,
    ) -> None:
        status_value = JobStatus(status)
        with self.session_factory() as session:
            job = session.get(DownloadJob, job_id)
            if job is None or job.status in {JobStatus.failed, JobStatus.completed}:
                return
            if job.status is JobStatus.paused:
                raise JobPaused
            if update_percent:
                self._set_status(session, job, status_value, percent)
            else:
                job.status = status_value
                total = total_bytes or job.total_bytes
                if downloaded_bytes is not None and total:
                    job.progress_percent = min(max(downloaded_bytes / total * 100, 0), 100)
            if downloaded_bytes is not None:
                job.downloaded_bytes = downloaded_bytes
            if total_bytes is not None:
                job.total_bytes = total_bytes
            if speed_bytes_per_second is not None:
                job.download_speed_bytes_per_second = speed_bytes_per_second
            if eta_seconds is not None:
                job.eta_seconds = eta_seconds
            if percent is None and downloaded_bytes is not None and job.total_bytes:
                job.progress_percent = min(max(downloaded_bytes / job.total_bytes * 100, 0), 100)
            session.commit()

    def _is_paused(self, job_id: str) -> bool:
        with self.session_factory() as session:
            job = session.get(DownloadJob, job_id)
            return job is not None and job.status is JobStatus.paused

    def _raise_if_paused(self, job_id: str) -> None:
        if self._is_paused(job_id):
            raise JobPaused

    def _pause(self, job_id: str) -> None:
        with self.session_factory() as session:
            job = session.get(DownloadJob, job_id)
            if job is None:
                return
            job.status = JobStatus.paused
            job.error_code = None
            job.error_message = None
            session.commit()

    def _preserve_temp_dir(self, job_id: str) -> bool:
        with self.session_factory() as session:
            job = session.get(DownloadJob, job_id)
            return job is not None and job.status in {JobStatus.paused, JobStatus.interrupted}

    def _fail(self, job_id: str, exc: MediaForgeToolError) -> None:
        with self.session_factory() as session:
            job = session.scalar(select(DownloadJob).where(DownloadJob.id == job_id))
            if job is None:
                return
            job.status = JobStatus.failed
            job.error_code = exc.code
            job.error_message = exc.public_message
            session.commit()
            logger.warning(
                "Job failed",
                extra={
                    "event": "job_failed",
                    "job_id": job_id,
                    "status": job.status.value,
                    "error_code": exc.code,
                },
            )
        shutil.rmtree(self.settings.temp_dir / job_id, ignore_errors=True)

    @staticmethod
    def _set_status(
        session: Session,
        job: DownloadJob,
        status: JobStatus,
        percent: float | None,
    ) -> None:
        job.status = status
        job.progress_percent = min(max(percent, 0), 100) if percent is not None else None
        session.commit()


def _temp_file_size(temp_dir: Path) -> int:
    try:
        return sum(path.stat().st_size for path in temp_dir.glob("**/*") if path.is_file())
    except OSError:
        return 0
