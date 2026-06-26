import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.api.dependencies import (
    get_job_runner,
    get_media_search_provider_registry,
    get_playlist_importer_registry,
    get_session_factory,
    get_settings_from_app,
)
from app.core.config import Settings
from app.core.exceptions import (
    CandidateNotFound,
    MediaForgeToolError,
    PlaylistImportFileTooLarge,
    PlaylistImportFormatUnsupported,
    QueueFull,
)
from app.db.session import get_session
from app.models.playlist import (
    ImportedPlaylist,
    ResolvedMediaCandidate,
    Track,
    TrackResolutionStatus,
)
from app.schemas.playlist import (
    BatchOperationResponse,
    BatchQueueRequest,
    BatchResolveRequest,
    BatchTrackResult,
    CandidateQueueResponse,
    ImportedPlaylistResponse,
    PlaylistDetailResponse,
    PlaylistImportIssueResponse,
    PlaylistImportResponse,
    PlaylistListResponse,
    ResolvedMediaCandidateResponse,
    ResolveTrackRequest,
    ResolveTrackResponse,
    SubmitCandidateRequest,
    TrackResponse,
    TrackReviewResponse,
    UpdateTrackRequest,
)
from app.services.job_runner import JobRunner
from app.services.media_resolution import MediaResolutionService
from app.services.media_search import MediaSearchProviderRegistry
from app.services.playlist_import import PlaylistImporterRegistry
from app.services.playlist_import.service import PlaylistImportService
from app.services.playlist_queue import PlaylistQueueService
from app.services.track_normalizer import TrackNormalizer

router = APIRouter(prefix="/api/playlists", tags=["playlists"])
_CSV_CONTENT_TYPES = {
    "application/csv",
    "application/octet-stream",
    "application/vnd.ms-excel",
    "text/csv",
    "text/plain",
}
_TEXT_CONTENT_TYPES = {
    "application/octet-stream",
    "text/plain",
}


@router.get("", response_model=PlaylistListResponse)
def list_playlists(
    limit: int = Query(default=12, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> PlaylistListResponse:
    total = session.scalar(select(func.count()).select_from(ImportedPlaylist)) or 0
    playlists = session.scalars(
        select(ImportedPlaylist)
        .order_by(ImportedPlaylist.created_at.desc(), ImportedPlaylist.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return PlaylistListResponse(
        items=[ImportedPlaylistResponse.model_validate(playlist) for playlist in playlists],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{playlist_id}", response_model=PlaylistDetailResponse)
def get_playlist(
    playlist_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, min_length=1, max_length=120),
    resolution_status: TrackResolutionStatus | None = Query(default=None),
    sort: Literal["position", "artist", "title", "album", "resolution_status"] = Query(
        default="position"
    ),
    direction: Literal["asc", "desc"] = Query(default="asc"),
    session: Session = Depends(get_session),
) -> PlaylistDetailResponse:
    playlist = session.scalar(
        select(ImportedPlaylist)
        .where(ImportedPlaylist.id == playlist_id)
        .options(selectinload(ImportedPlaylist.issues))
    )
    if playlist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PLAYLIST_NOT_FOUND", "message": "Playlist import not found."},
        )
    track_conditions = _track_filter_conditions(
        playlist_id,
        query=q,
        resolution_status=resolution_status,
    )
    total_tracks = session.scalar(
        select(func.count()).select_from(Track).where(*track_conditions)
    ) or 0
    tracks = session.scalars(
        select(Track)
        .where(*track_conditions)
        .options(selectinload(Track.candidates))
        .options(selectinload(Track.queue_items))
        .order_by(*_track_ordering(sort, direction))
        .limit(limit)
        .offset(offset)
    ).all()
    return PlaylistDetailResponse(
        playlist=ImportedPlaylistResponse.model_validate(playlist),
        tracks=[_track_review_response(track) for track in tracks],
        issues=[
            PlaylistImportIssueResponse.model_validate(issue)
            for issue in playlist.issues
        ],
        total_tracks=total_tracks,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{playlist_id}/tracks/resolve-batch",
    response_model=BatchOperationResponse,
)
def resolve_tracks_batch(
    playlist_id: str,
    payload: BatchResolveRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings_from_app),
    registry: MediaSearchProviderRegistry = Depends(get_media_search_provider_registry),
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> BatchOperationResponse:
    _require_playlist(playlist_id, session)
    concurrency = min(
        payload.max_concurrency or settings.media_resolution_max_concurrency,
        settings.media_resolution_max_concurrency,
    )
    results: list[BatchTrackResult] = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                _resolve_batch_track,
                session_factory,
                registry,
                playlist_id,
                selection.track_id,
                payload.provider_key,
                payload.limit,
            )
            for selection in payload.tracks
        ]
        for future in as_completed(futures):
            results.append(future.result())
    return _batch_response(results, concurrency_limit=concurrency)


@router.post(
    "/{playlist_id}/tracks/queue-batch",
    response_model=BatchOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def queue_tracks_batch(
    playlist_id: str,
    payload: BatchQueueRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings_from_app),
    runner: JobRunner = Depends(get_job_runner),
) -> BatchOperationResponse:
    _require_playlist(playlist_id, session)
    results: list[BatchTrackResult] = []
    stopped_on_queue_full = False
    for index, item in enumerate(payload.items):
        if stopped_on_queue_full:
            results.append(
                BatchTrackResult(
                    track_id=item.track_id,
                    phase="download",
                    status="skipped",
                    error_code=QueueFull.code,
                    message="Queue full before this track was submitted.",
                )
            )
            continue
        track = _track_in_playlist(session, playlist_id, item.track_id)
        if track is None:
            results.append(
                BatchTrackResult(
                    track_id=item.track_id,
                    phase="selection",
                    status="failed",
                    error_code="TRACK_NOT_FOUND",
                    message="Track not found in playlist.",
                )
            )
            continue
        candidate = session.scalar(
            select(ResolvedMediaCandidate).where(
                ResolvedMediaCandidate.id == item.candidate_id,
                ResolvedMediaCandidate.track_id == item.track_id,
            )
        )
        if candidate is None:
            results.append(
                BatchTrackResult(
                    track_id=item.track_id,
                    phase="selection",
                    status="failed",
                    error_code=CandidateNotFound.code,
                    message=CandidateNotFound.public_message,
                )
            )
            continue
        try:
            queued = PlaylistQueueService(session, runner, settings).submit_candidate(
                track,
                candidate,
                SubmitCandidateRequest(
                    format=item.format,
                    resolution=item.resolution,
                    audio_bitrate_kbps=item.audio_bitrate_kbps,
                ),
            )
        except QueueFull:
            stopped_on_queue_full = True
            results.append(
                BatchTrackResult(
                    track_id=item.track_id,
                    phase="download",
                    status="failed",
                    error_code=QueueFull.code,
                    message=QueueFull.public_message,
                )
            )
            for pending in payload.items[index + 1:]:
                results.append(
                    BatchTrackResult(
                        track_id=pending.track_id,
                        phase="download",
                        status="skipped",
                        error_code=QueueFull.code,
                        message="Queue full before this track was submitted.",
                    )
                )
            break
        except MediaForgeToolError as exc:
            results.append(
                BatchTrackResult(
                    track_id=item.track_id,
                    phase="download",
                    status="failed",
                    error_code=exc.code,
                    message=exc.public_message,
                )
            )
            continue
        results.append(
            BatchTrackResult(
                track_id=item.track_id,
                phase="download",
                status="queued",
                queue_item_id=queued.queue_item.id,
                job_id=queued.queue_item.download_job_id,
            )
        )
    return _batch_response(
        results,
        concurrency_limit=1,
        stopped_on_queue_full=stopped_on_queue_full,
    )


@router.post(
    "/{playlist_id}/tracks/{track_id}/candidates/{candidate_id}/queue",
    response_model=CandidateQueueResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def queue_candidate(
    playlist_id: str,
    track_id: str,
    candidate_id: str,
    payload: SubmitCandidateRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings_from_app),
    runner: JobRunner = Depends(get_job_runner),
) -> CandidateQueueResponse:
    track = session.scalar(
        select(Track)
        .where(Track.id == track_id, Track.playlist_id == playlist_id)
        .options(selectinload(Track.queue_items))
    )
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TRACK_NOT_FOUND", "message": "Track not found in playlist."},
        )
    candidate = session.scalar(
        select(ResolvedMediaCandidate).where(
            ResolvedMediaCandidate.id == candidate_id,
            ResolvedMediaCandidate.track_id == track_id,
        )
    )
    if candidate is None:
        raise _http_error(CandidateNotFound())
    try:
        queued = PlaylistQueueService(session, runner, settings).submit_candidate(
            track,
            candidate,
            payload,
        )
    except QueueFull as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.code, "message": exc.public_message},
        ) from exc
    except MediaForgeToolError as exc:
        raise _http_error(exc) from exc
    return CandidateQueueResponse(
        queue_item=queued.queue_item,
        job=queued.queue_item.download_job,
    )


@router.post(
    "/{playlist_id}/tracks/{track_id}/resolve",
    response_model=ResolveTrackResponse,
)
def resolve_track(
    playlist_id: str,
    track_id: str,
    payload: ResolveTrackRequest | None = None,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings_from_app),
    registry: MediaSearchProviderRegistry = Depends(get_media_search_provider_registry),
) -> ResolveTrackResponse:
    request = payload or ResolveTrackRequest(limit=settings.media_search_max_candidates)
    track = session.scalar(
        select(Track)
        .where(Track.id == track_id, Track.playlist_id == playlist_id)
        .options(selectinload(Track.candidates))
    )
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TRACK_NOT_FOUND", "message": "Track not found in playlist."},
        )
    try:
        resolved = MediaResolutionService(session, registry).resolve_track(
            track,
            provider_key=request.provider_key,
            limit=request.limit,
        )
    except MediaForgeToolError as exc:
        raise _http_error(exc) from exc
    candidates = _track_candidates(session, resolved.track.id, request.provider_key)
    return ResolveTrackResponse(
        track=_track_review_response(resolved.track, candidates),
        candidates=[
            ResolvedMediaCandidateResponse.model_validate(candidate)
            for candidate in candidates
        ],
    )


@router.patch(
    "/{playlist_id}/tracks/{track_id}",
    response_model=TrackReviewResponse,
)
def update_track(
    playlist_id: str,
    track_id: str,
    payload: UpdateTrackRequest,
    session: Session = Depends(get_session),
) -> TrackReviewResponse:
    track = _track_in_playlist(session, playlist_id, track_id)
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TRACK_NOT_FOUND", "message": "Track not found in playlist."},
        )
    try:
        normalized = TrackNormalizer().normalize(
            artist=payload.artist,
            title=payload.title,
            album=payload.album,
            isrc=payload.isrc,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "TRACK_METADATA_INVALID",
                "message": "Artist and title are required.",
            },
        ) from exc
    track.artist = normalized.artist
    track.title = normalized.title
    track.album = normalized.album
    track.isrc = normalized.isrc
    track.raw_artist = payload.artist
    track.raw_title = payload.title
    if not track.queue_items:
        track.resolution_status = TrackResolutionStatus.pending
    session.commit()
    session.refresh(track)
    return _track_review_response(track)


@router.post(
    "/import",
    response_model=PlaylistImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_playlist(
    file: UploadFile = File(...),
    importer_key: str = Form(default="shazam_csv"),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings_from_app),
    registry: PlaylistImporterRegistry = Depends(get_playlist_importer_registry),
) -> PlaylistImportResponse:
    _validate_upload_type(file, importer_key)
    content = await file.read(settings.playlist_import_max_bytes + 1)
    await file.close()
    if len(content) > settings.playlist_import_max_bytes:
        raise _http_error(PlaylistImportFileTooLarge())

    try:
        imported = PlaylistImportService(session, registry).import_playlist(
            importer_key,
            io.BytesIO(content),
            filename=file.filename,
        )
    except MediaForgeToolError as exc:
        raise _http_error(exc) from exc

    return PlaylistImportResponse(
        playlist=ImportedPlaylistResponse.model_validate(imported.playlist),
        tracks=[TrackResponse.model_validate(track) for track in imported.playlist.tracks],
        issues=[
            PlaylistImportIssueResponse.model_validate(issue)
            for issue in imported.playlist.issues
        ],
    )


def _track_review_response(
    track: Track,
    candidates: list[ResolvedMediaCandidate] | None = None,
) -> TrackReviewResponse:
    return TrackReviewResponse(
        **TrackResponse.model_validate(track).model_dump(),
        candidates=[
            ResolvedMediaCandidateResponse.model_validate(candidate)
            for candidate in (candidates if candidates is not None else track.candidates)
        ],
        queue_items=track.queue_items,
    )


def _require_playlist(playlist_id: str, session: Session) -> ImportedPlaylist:
    playlist = session.get(ImportedPlaylist, playlist_id)
    if playlist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PLAYLIST_NOT_FOUND", "message": "Playlist import not found."},
        )
    return playlist


def _track_in_playlist(
    session: Session,
    playlist_id: str,
    track_id: str,
) -> Track | None:
    return session.scalar(
        select(Track)
        .where(Track.id == track_id, Track.playlist_id == playlist_id)
        .options(selectinload(Track.queue_items))
    )


def _track_filter_conditions(
    playlist_id: str,
    *,
    query: str | None,
    resolution_status: TrackResolutionStatus | None,
) -> list:
    conditions = [Track.playlist_id == playlist_id]
    normalized_query = query.strip() if query else ""
    if normalized_query:
        pattern = f"%{normalized_query}%"
        conditions.append(
            or_(
                Track.artist.ilike(pattern),
                Track.title.ilike(pattern),
                Track.album.ilike(pattern),
                Track.isrc.ilike(pattern),
            )
        )
    if resolution_status is not None:
        conditions.append(Track.resolution_status == resolution_status)
    return conditions


def _track_ordering(
    sort: str,
    direction: str,
) -> list:
    columns = {
        "position": Track.position,
        "artist": Track.artist,
        "title": Track.title,
        "album": Track.album,
        "resolution_status": Track.resolution_status,
    }
    column = columns.get(sort, Track.position)
    ordered = column.desc() if direction == "desc" else column.asc()
    if sort == "position":
        return [ordered]
    return [ordered, Track.position.asc()]


def _resolve_batch_track(
    session_factory: sessionmaker[Session],
    registry: MediaSearchProviderRegistry,
    playlist_id: str,
    track_id: str,
    provider_key: str,
    limit: int,
) -> BatchTrackResult:
    with session_factory() as session:
        track = _track_in_playlist(session, playlist_id, track_id)
        if track is None:
            return BatchTrackResult(
                track_id=track_id,
                phase="search",
                status="failed",
                error_code="TRACK_NOT_FOUND",
                message="Track not found in playlist.",
            )
        try:
            resolved = MediaResolutionService(session, registry).resolve_track(
                track,
                provider_key=provider_key,
                limit=limit,
            )
        except MediaForgeToolError as exc:
            status_value = "no_match" if exc.code == "MEDIA_SEARCH_NO_RESULTS" else "failed"
            return BatchTrackResult(
                track_id=track_id,
                phase="search",
                status=status_value,
                error_code=exc.code,
                message=exc.public_message,
            )
        return BatchTrackResult(
            track_id=track_id,
            phase="search",
            status="resolved" if resolved.candidates else "no_match",
            candidate_count=len(resolved.candidates),
        )


def _batch_response(
    results: list[BatchTrackResult],
    *,
    concurrency_limit: int,
    stopped_on_queue_full: bool = False,
) -> BatchOperationResponse:
    failed_count = len([result for result in results if result.status == "failed"])
    skipped_count = len([result for result in results if result.status == "skipped"])
    return BatchOperationResponse(
        results=results,
        requested_count=len(results),
        completed_count=len(results) - failed_count - skipped_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        concurrency_limit=concurrency_limit,
        stopped_on_queue_full=stopped_on_queue_full,
    )


def _track_candidates(
    session: Session,
    track_id: str,
    provider_key: str,
) -> list[ResolvedMediaCandidate]:
    return list(
        session.scalars(
            select(ResolvedMediaCandidate)
            .where(
                ResolvedMediaCandidate.track_id == track_id,
                ResolvedMediaCandidate.provider_key == provider_key,
            )
            .order_by(ResolvedMediaCandidate.rank)
        ).all()
    )


def _validate_upload_type(file: UploadFile, importer_key: str) -> None:
    suffix = Path(file.filename or "").suffix.casefold()
    content_type = (file.content_type or "").split(";", 1)[0].strip().casefold()
    if importer_key == "shazam_csv":
        if suffix == ".csv" and content_type in _CSV_CONTENT_TYPES:
            return
        raise _http_error(PlaylistImportFormatUnsupported())
    if importer_key == "text":
        if suffix in {".txt", ".text"} and content_type in _TEXT_CONTENT_TYPES:
            return
        raise _http_error(PlaylistImportFormatUnsupported())
    if not importer_key:
        raise _http_error(PlaylistImportFormatUnsupported())
    if suffix == ".csv" and content_type in _CSV_CONTENT_TYPES:
        return


def _http_error(exc: MediaForgeToolError) -> HTTPException:
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    if isinstance(exc, PlaylistImportFileTooLarge):
        status_code = status.HTTP_413_CONTENT_TOO_LARGE
    elif isinstance(exc, PlaylistImportFormatUnsupported):
        status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.public_message},
    )
