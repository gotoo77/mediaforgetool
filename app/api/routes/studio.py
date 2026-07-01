import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_settings_from_app
from app.core.config import Settings
from app.core.exceptions import MediaAssetUnavailable, MediaForgeToolError
from app.db.session import get_session
from app.models.studio import (
    MediaAsset,
    MediaEditJob,
    MediaEditJobInput,
    MediaEditJobOutput,
    MediaEditStatus,
)
from app.schemas.studio import (
    CreateMediaEditJobRequest,
    MediaAssetInspectionResponse,
    MediaEditJobResponse,
)
from app.services.media_edit import MediaEditRunner
from app.services.media_probe import MediaProbeService

router = APIRouter(prefix="/api/studio", tags=["studio"])
logger = logging.getLogger(__name__)


@router.get("/assets", response_model=list[MediaAssetInspectionResponse])
def list_assets(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings_from_app),
) -> list[MediaAssetInspectionResponse]:
    assets = session.query(MediaAsset).order_by(MediaAsset.created_at.desc()).limit(100).all()
    responses: list[MediaAssetInspectionResponse] = []
    probe_service = MediaProbeService(settings)
    for asset in assets:
        try:
            probe = probe_service.inspect_asset_path(asset.relative_path)
        except MediaForgeToolError as exc:
            logger.warning(
                "Studio asset probe failed",
                extra={
                    "event": "studio_probe_failed",
                    "asset_id": asset.id,
                    "error_code": exc.code,
                },
            )
            probe = None
        responses.append(MediaAssetInspectionResponse(asset=asset, probe=probe))
    return responses


@router.post("/jobs", response_model=MediaEditJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_edit_job(
    payload: CreateMediaEditJobRequest,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings_from_app),
) -> MediaEditJob:
    assets = _assets_by_id([item.asset_id for item in payload.inputs], session)
    job = MediaEditJob(
        operation=payload.operation,
        output_name=payload.output_name,
        options={
            "audio_offset_seconds": payload.audio_offset_seconds,
            "duration_mode": payload.duration_mode,
            "audio_format": payload.audio_format,
            "split_time_seconds": payload.split_time_seconds,
        },
        inputs=[
            MediaEditJobInput(
                asset=assets[item.asset_id],
                role=item.role,
                position=index,
            )
            for index, item in enumerate(payload.inputs)
        ],
    )
    session.add(job)
    session.commit()
    job_id = job.id
    logger.info(
        "Studio job started",
        extra={
            "event": "studio_job_started",
            "job_id": job_id,
            "operation": job.operation.value,
        },
    )

    MediaEditRunner(settings, request.app.state.session_factory).run(job_id)

    session.expire_all()
    refreshed = session.get(MediaEditJob, job_id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Studio job not found.")
    return refreshed


@router.get("/assets/{asset_id}/inspect", response_model=MediaAssetInspectionResponse)
def inspect_asset(
    asset_id: str,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings_from_app),
) -> MediaAssetInspectionResponse:
    asset = session.get(MediaAsset, asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail(MediaAssetUnavailable()),
        )
    try:
        probe = MediaProbeService(settings).inspect_asset_path(asset.relative_path)
    except MediaForgeToolError as exc:
        logger.warning(
            "Studio asset probe failed",
            extra={"event": "studio_probe_failed", "asset_id": asset.id, "error_code": exc.code},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_error_detail(exc),
        ) from exc
    return MediaAssetInspectionResponse(asset=asset, probe=probe)


@router.get("/jobs/{job_id}", response_model=MediaEditJobResponse)
def get_edit_job(job_id: str, session: Session = Depends(get_session)) -> MediaEditJob:
    job = session.get(MediaEditJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Studio job not found.")
    return job


@router.get("/jobs/{job_id}/file")
def get_edit_job_file(
    job_id: str,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings_from_app),
) -> FileResponse:
    job = session.get(MediaEditJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Studio job not found.")
    if job.status is not MediaEditStatus.completed or job.output_asset is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Studio output is not ready.",
        )
    path = MediaProbeService(settings).resolve_asset_path(job.output_asset.relative_path).absolute
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Studio output has expired.")
    return FileResponse(path, filename=job.output_asset.display_name)


@router.get("/jobs/{job_id}/outputs/{position}/file")
def get_edit_job_output_file(
    job_id: str,
    position: int,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings_from_app),
) -> FileResponse:
    job = session.get(MediaEditJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Studio job not found.")
    if job.status is not MediaEditStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Studio output is not ready.",
        )
    output = (
        session.query(MediaEditJobOutput)
        .filter(MediaEditJobOutput.job_id == job_id, MediaEditJobOutput.position == position)
        .one_or_none()
    )
    if output is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Studio output not found.",
        )
    path = MediaProbeService(settings).resolve_asset_path(output.asset.relative_path).absolute
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Studio output has expired.")
    return FileResponse(path, filename=output.asset.display_name)


def _assets_by_id(asset_ids: list[str], session: Session) -> dict[str, MediaAsset]:
    assets = {asset_id: session.get(MediaAsset, asset_id) for asset_id in asset_ids}
    missing = [asset_id for asset_id, asset in assets.items() if asset is None]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_error_detail(MediaAssetUnavailable()),
        )
    return {asset_id: asset for asset_id, asset in assets.items() if asset is not None}


def _error_detail(exc: MediaForgeToolError) -> dict[str, str]:
    return {"code": exc.code, "message": exc.public_message}
