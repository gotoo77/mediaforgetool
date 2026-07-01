import asyncio
import logging
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.models.job import DownloadJob, JobStatus
from app.models.studio import MediaAssetOrigin, MediaEditJob, MediaEditStatus
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
STUDIO_ACTIVE_STATUSES = {
    MediaEditStatus.queued,
    MediaEditStatus.probing,
    MediaEditStatus.processing,
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
            self._cleanup_expired_studio_jobs(session, now)
            protected_studio_job_ids = set(session.scalars(select(MediaEditJob.id)).all())
            self._cleanup_old_directories(
                self.settings.media_studio_dir,
                now - timedelta(hours=self.settings.temp_retention_hours),
                protected_studio_job_ids,
            )
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

    def _cleanup_expired_studio_jobs(self, session: Session, now: datetime) -> None:
        terminal_jobs = session.scalars(
            select(MediaEditJob).where(MediaEditJob.status.not_in(STUDIO_ACTIVE_STATUSES))
        ).all()
        for job in terminal_jobs:
            cutoff_hours = (
                self.settings.output_retention_hours
                if job.status is MediaEditStatus.completed
                else self.settings.temp_retention_hours
            )
            reference = _aware_datetime(job.completed_at or job.updated_at or job.created_at)
            if reference >= now - timedelta(hours=cutoff_hours):
                continue
            shutil.rmtree(self.settings.media_studio_dir / job.id, ignore_errors=True)
            output_assets = [
                output.asset
                for output in list(job.outputs)
                if output.asset.origin is MediaAssetOrigin.studio_output
            ]
            session.delete(job)
            session.flush()
            for asset in output_assets:
                session.delete(asset)
            logger.info(
                "Removed expired studio job",
                extra={
                    "event": "studio_job_cleaned",
                    "job_id": job.id,
                    "status": job.status.value,
                },
            )


def _aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
