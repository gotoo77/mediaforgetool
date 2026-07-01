import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.playlist import (
    DownloadQueueItem,
    QueueItemStatus,
    ResolvedMediaCandidate,
    Track,
    utc_now,
)
from app.schemas.job import CreateJobRequest
from app.schemas.playlist import SubmitCandidateRequest
from app.services.job_submission import JobEnqueuer, JobSubmissionService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QueuedCandidate:
    queue_item: DownloadQueueItem


class PlaylistQueueService:
    def __init__(
        self,
        session: Session,
        runner: JobEnqueuer,
        settings: Settings,
    ) -> None:
        self.session = session
        self.runner = runner
        self.settings = settings

    def submit_candidate(
        self,
        track: Track,
        candidate: ResolvedMediaCandidate,
        request: SubmitCandidateRequest,
    ) -> QueuedCandidate:
        idempotency_key = _idempotency_key(track.id, candidate.id, request)
        existing = self.session.scalar(
            select(DownloadQueueItem).where(
                DownloadQueueItem.idempotency_key == idempotency_key
            )
        )
        if existing is not None:
            return QueuedCandidate(queue_item=existing)

        job = JobSubmissionService(self.session, self.runner, self.settings).submit(
            CreateJobRequest(
                url=candidate.source_url,
                format=request.format,
                resolution=request.resolution,
                audio_bitrate_kbps=request.audio_bitrate_kbps,
                title=candidate.title,
                platform=candidate.provider_key,
                thumbnail_url=candidate.thumbnail_url,
                duration_seconds=candidate.duration_seconds,
            )
        )
        candidate.selected_at = utc_now()
        queue_item = DownloadQueueItem(
            track_id=track.id,
            candidate_id=candidate.id,
            download_job_id=job.id,
            requested_format=request.format,
            requested_height=request.resolution if request.format.value == "mp4" else None,
            requested_audio_bitrate_kbps=(
                request.audio_bitrate_kbps if request.format.value == "mp3" else None
            ),
            status=QueueItemStatus.submitted,
            idempotency_key=idempotency_key,
            submitted_at=utc_now(),
        )
        self.session.add(queue_item)
        self.session.commit()
        self.session.refresh(queue_item)
        logger.info(
            "Media candidate selected",
            extra={
                "event": "media_candidate_selected",
                "playlist_id": track.playlist_id,
                "track_id": track.id,
                "candidate_id": candidate.id,
                "queue_item_id": queue_item.id,
                "job_id": job.id,
                "provider": candidate.provider_key,
                "status": queue_item.status.value,
            },
        )
        return QueuedCandidate(queue_item=queue_item)


def _idempotency_key(
    track_id: str,
    candidate_id: str,
    request: SubmitCandidateRequest,
) -> str:
    return ":".join(
        [
            track_id,
            candidate_id,
            request.format.value,
            str(request.resolution or ""),
            str(request.audio_bitrate_kbps or ""),
        ]
    )
