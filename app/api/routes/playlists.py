import io
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_playlist_importer_registry, get_settings_from_app
from app.core.config import Settings
from app.core.exceptions import (
    MediaForgeToolError,
    PlaylistImportFileTooLarge,
    PlaylistImportFormatUnsupported,
)
from app.db.session import get_session
from app.schemas.playlist import (
    ImportedPlaylistResponse,
    PlaylistImportIssueResponse,
    PlaylistImportResponse,
    TrackResponse,
)
from app.services.playlist_import import PlaylistImporterRegistry
from app.services.playlist_import.service import PlaylistImportService

router = APIRouter(prefix="/api/playlists", tags=["playlists"])
_CSV_CONTENT_TYPES = {
    "application/csv",
    "application/octet-stream",
    "application/vnd.ms-excel",
    "text/csv",
    "text/plain",
}


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
    _validate_upload_type(file)
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
            PlaylistImportIssueResponse(
                row_number=issue.row_number,
                code=issue.code,
                message=issue.message,
            )
            for issue in imported.issues
        ],
    )


def _validate_upload_type(file: UploadFile) -> None:
    suffix = Path(file.filename or "").suffix.casefold()
    content_type = (file.content_type or "").split(";", 1)[0].strip().casefold()
    if suffix == ".csv" and content_type in _CSV_CONTENT_TYPES:
        return
    raise _http_error(PlaylistImportFormatUnsupported())


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
