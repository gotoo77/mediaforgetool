import logging
from collections.abc import Callable
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import InvalidMediaUrl, MediaTooLong, QueueFull
from app.models.job import DownloadJob, JobStatus
from app.schemas.job import CreateJobRequest
from app.services.url_guard import validate_public_media_url

logger = logging.getLogger(__name__)


class JobEnqueuer(Protocol):
    def enqueue(self, job_id: str) -> bool: ...


class JobSubmissionService:
    def __init__(
        self,
        session: Session,
        runner: JobEnqueuer,
        settings: Settings,
        *,
        url_validator: Callable[[str, int], str] = validate_public_media_url,
    ) -> None:
        self.session = session
        self.runner = runner
        self.settings = settings
        self.url_validator = url_validator

    def submit(self, payload: CreateJobRequest) -> DownloadJob:
        url = self._validated_url(payload.url)
        self._validate_segment_duration(payload)
        job = DownloadJob(
            source_url=url,
            requested_format=payload.format,
            requested_height=payload.resolution if payload.format.value == "mp4" else None,
            requested_audio_bitrate_kbps=(
                payload.audio_bitrate_kbps if payload.format.value == "mp3" else None
            ),
            segment_start_seconds=payload.segment_start_seconds,
            segment_end_seconds=payload.segment_end_seconds,
            title=_job_title(payload),
            platform=payload.platform,
            thumbnail_url=payload.thumbnail_url,
            duration_seconds=_job_duration(payload),
            total_bytes=payload.estimated_total_bytes,
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        if not self.runner.enqueue(job.id):
            job.status = JobStatus.failed
            job.error_code = QueueFull.code
            job.error_message = QueueFull.public_message
            self.session.commit()
            raise QueueFull()
        logger.info(
            "Job submitted",
            extra={
                "event": "job_submitted",
                "job_id": job.id,
                "status": job.status.value,
                "platform": job.platform,
            },
        )
        return job

    def _validated_url(self, url: object) -> str:
        try:
            return self.url_validator(str(url), self.settings.max_url_length)
        except InvalidMediaUrl:
            raise

    def _validate_segment_duration(self, payload: CreateJobRequest) -> None:
        if payload.segment_start_seconds is None or payload.segment_end_seconds is None:
            return
        segment_duration = payload.segment_end_seconds - payload.segment_start_seconds
        if segment_duration <= self.settings.max_media_duration_seconds:
            return
        raise MediaTooLong()


def _job_duration(payload: CreateJobRequest) -> int | None:
    if payload.segment_start_seconds is not None and payload.segment_end_seconds is not None:
        return payload.segment_end_seconds - payload.segment_start_seconds
    return payload.duration_seconds


def _job_title(payload: CreateJobRequest) -> str | None:
    title = payload.title
    if not title:
        return None
    if payload.segment_start_seconds is None or payload.segment_end_seconds is None:
        return title
    start = _time_label(payload.segment_start_seconds)
    end = _time_label(payload.segment_end_seconds)
    return f"{title} [{start}-{end}]"


def _time_label(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"
