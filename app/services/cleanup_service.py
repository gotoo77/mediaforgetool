import asyncio
import logging
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.models.job import DownloadJob, JobStatus
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)
TEMP_PROTECTED_STATUSES = {
    JobStatus.queued,
    JobStatus.extracting,
    JobStatus.downloading,
    JobStatus.processing,
    JobStatus.paused,
    JobStatus.interrupted,
}


class CleanupService:
    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        storage: StorageService,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.storage = storage
        self._task: asyncio.Task[None] | None = None

    def cleanup_now(self) -> None:
        now = datetime.now(UTC)
        with self.session_factory() as session:
            protected_temp_job_ids = set(
                session.scalars(
                    select(DownloadJob.id).where(DownloadJob.status.in_(TEMP_PROTECTED_STATUSES))
                ).all()
            )
            self._cleanup_old_directories(
                self.settings.temp_dir,
                now - timedelta(hours=self.settings.temp_retention_hours),
                protected_temp_job_ids,
            )
            expired = session.scalars(
                select(DownloadJob).where(
                    DownloadJob.expires_at.is_not(None),
                    DownloadJob.expires_at <= now,
                    DownloadJob.status == JobStatus.completed,
                )
            ).all()
            for job in expired:
                self.storage.remove_output_job_dir(job.id)
                job.status = JobStatus.expired
                job.output_path = None
            session.commit()

    async def start(self) -> None:
        self.cleanup_now()
        self._task = asyncio.create_task(self._loop(), name="mediaforgetool-cleanup")

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)
        self._task = None

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self.settings.cleanup_interval_seconds)
            await asyncio.to_thread(self.cleanup_now)

    @staticmethod
    def _cleanup_old_directories(
        root: Path,
        cutoff: datetime,
        protected_names: set[str] | None = None,
    ) -> None:
        if not root.exists():
            return
        protected_names = protected_names or set()
        for path in root.iterdir():
            if not path.is_dir():
                continue
            if path.name in protected_names:
                continue
            modified = datetime.fromtimestamp(path.stat().st_mtime, UTC)
            if modified < cutoff:
                shutil.rmtree(path, ignore_errors=True)
                logger.info("Removed stale directory", extra={"event": "stale_directory_removed"})
