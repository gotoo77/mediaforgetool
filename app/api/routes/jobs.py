from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_job_rate_limiter, get_job_runner, get_settings_from_app
from app.core.config import Settings
from app.core.exceptions import InvalidMediaUrl, MediaForgeToolError, QueueFull
from app.db.session import get_session
from app.models.job import DownloadJob, JobStatus
from app.schemas.job import (
    CleanupReportResponse,
    CreateJobRequest,
    InspectMediaRequest,
    JobResponse,
    MediaInspectionResponse,
)
from app.services.job_runner import JobRunner
from app.services.job_submission import JobSubmissionService
from app.services.media_downloader import MediaDownloader
from app.services.rate_limiter import SlidingWindowRateLimiter
from app.services.storage_service import StorageService
from app.services.url_guard import validate_public_media_url

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
ACTIVE_STATUSES = {
    JobStatus.queued,
    JobStatus.extracting,
    JobStatus.downloading,
    JobStatus.processing,
    JobStatus.paused,
}


@router.post("/inspect", response_model=MediaInspectionResponse)
def inspect_media(
    payload: InspectMediaRequest,
    request: Request,
    settings: Settings = Depends(get_settings_from_app),
    rate_limiter: SlidingWindowRateLimiter = Depends(get_job_rate_limiter),
) -> object:
    _enforce_rate_limit(request, rate_limiter)
    url = _validated_url(payload.url, settings)
    try:
        return MediaDownloader(settings).inspect(url)
    except MediaForgeToolError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_error_detail(exc, settings),
        ) from exc


@router.post("", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_job(
    payload: CreateJobRequest,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings_from_app),
    runner: JobRunner = Depends(get_job_runner),
    rate_limiter: SlidingWindowRateLimiter = Depends(get_job_rate_limiter),
) -> DownloadJob:
    _enforce_rate_limit(request, rate_limiter)
    try:
        return JobSubmissionService(
            session,
            runner,
            settings,
            url_validator=validate_public_media_url,
        ).submit(payload)
    except QueueFull as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.code, "message": exc.public_message},
        ) from exc
    except MediaForgeToolError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_error_detail(exc, settings),
        ) from exc


@router.get("", response_model=list[JobResponse])
def list_jobs(session: Session = Depends(get_session), limit: int = 20) -> list[DownloadJob]:
    safe_limit = min(max(limit, 1), 50)
    return list(
        session.scalars(
            select(DownloadJob).order_by(DownloadJob.created_at.desc()).limit(safe_limit)
        ).all()
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, session: Session = Depends(get_session)) -> DownloadJob:
    job = session.get(DownloadJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return job


@router.delete("", response_model=CleanupReportResponse)
def clear_jobs(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings_from_app),
) -> CleanupReportResponse:
    jobs = list(session.scalars(select(DownloadJob)).all())
    inactive_jobs = [job for job in jobs if job.status not in ACTIVE_STATUSES]
    report = _delete_jobs(inactive_jobs, session, settings)
    report.active_jobs_skipped = len(jobs) - len(inactive_jobs)
    return report


@router.delete("/{job_id}", response_model=CleanupReportResponse)
def delete_job(
    job_id: str,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings_from_app),
) -> CleanupReportResponse:
    job = session.get(DownloadJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    if job.status in ACTIVE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only inactive jobs can be deleted.",
        )

    return _delete_jobs([job], session, settings)


def _delete_jobs(
    jobs: list[DownloadJob],
    session: Session,
    settings: Settings,
) -> CleanupReportResponse:
    storage = StorageService(settings)
    report = CleanupReportResponse(
        jobs_deleted=0,
        output_dirs_deleted=0,
        temp_dirs_deleted=0,
        bytes_reclaimed=0,
    )
    for job in jobs:
        output_dir = settings.storage_dir / job.id
        temp_dir = settings.temp_dir / job.id
        output_exists = output_dir.exists()
        temp_exists = temp_dir.exists()
        report.bytes_reclaimed += _directory_size(output_dir) + _directory_size(temp_dir)
        if output_exists:
            report.output_dirs_deleted += 1
        if temp_exists:
            report.temp_dirs_deleted += 1
        storage.remove_temp_job_dir(job.id)
        storage.remove_output_job_dir(job.id)
        session.delete(job)
        report.jobs_deleted += 1
    session.commit()
    return report


@router.post("/{job_id}/resume", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def resume_job(
    job_id: str,
    session: Session = Depends(get_session),
    runner: JobRunner = Depends(get_job_runner),
) -> DownloadJob:
    job = session.get(DownloadJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    if job.status not in {JobStatus.interrupted, JobStatus.failed, JobStatus.paused}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only interrupted, failed or paused jobs can be resumed.",
        )

    job.status = JobStatus.queued
    job.error_code = None
    job.error_message = None
    job.progress_percent = None
    job.download_speed_bytes_per_second = None
    job.eta_seconds = None
    session.commit()
    session.refresh(job)

    if not runner.enqueue(job.id):
        job.status = JobStatus.failed
        job.error_code = "QUEUE_FULL"
        job.error_message = "This instance already has too many pending media jobs."
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "QUEUE_FULL", "message": job.error_message},
        )
    return job


@router.post("/{job_id}/pause", response_model=JobResponse)
def pause_job(job_id: str, session: Session = Depends(get_session)) -> DownloadJob:
    job = session.get(DownloadJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    if job.status not in {
        JobStatus.queued,
        JobStatus.extracting,
        JobStatus.downloading,
        JobStatus.processing,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only queued or running jobs can be paused.",
        )
    job.status = JobStatus.paused
    job.error_code = None
    job.error_message = None
    session.commit()
    session.refresh(job)
    return job


@router.get("/{job_id}/file")
def get_job_file(job_id: str, session: Session = Depends(get_session)) -> FileResponse:
    job = session.get(DownloadJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    if job.status is not JobStatus.completed or not job.output_path:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job output is not ready.")

    path = Path(job.output_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Job output has expired.")
    return FileResponse(path, filename=job.output_filename, media_type="application/octet-stream")


def _validated_url(url: object, settings: Settings) -> str:
    try:
        return validate_public_media_url(str(url), settings.max_url_length)
    except InvalidMediaUrl as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": exc.code, "message": exc.public_message},
        ) from exc


def _directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(child.stat().st_size for child in path.glob("**/*") if child.is_file())


def _error_detail(exc: MediaForgeToolError, settings: Settings) -> dict[str, str]:
    if exc.code != "SOURCE_NO_STREAMS":
        return {"code": exc.code, "message": exc.public_message}
    if _has_credentials(settings):
        message = (
            "La source ne fournit aucun flux accessible avec les credentials yt-dlp "
            "configures sur cette instance."
        )
    else:
        message = (
            "La source ne fournit aucun flux sans credentials. Configure "
            "YTDLP_COOKIES_FILE ou YTDLP_COOKIES_FROM_BROWSER, puis relance l'analyse."
        )
    return {"code": exc.code, "message": message}


def _has_credentials(settings: Settings) -> bool:
    return bool(settings.ytdlp_cookies_file or settings.ytdlp_cookies_from_browser)


def _enforce_rate_limit(request: Request, rate_limiter: SlidingWindowRateLimiter) -> None:
    client_key = request.client.host if request.client else "unknown"
    rate_limit = rate_limiter.check(client_key)
    if rate_limit.allowed:
        return
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "code": "RATE_LIMITED",
            "message": "Too many media requests were created from this client.",
        },
        headers={"Retry-After": str(rate_limit.retry_after_seconds)},
    )
