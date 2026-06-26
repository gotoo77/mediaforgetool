import logging
from dataclasses import dataclass
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.core.exceptions import MediaForgeToolError
from app.models.playlist import ImportedPlaylist, PlaylistImportIssue, PlaylistStatus, Track
from app.services.playlist_import.base import ImportIssue
from app.services.playlist_import.registry import PlaylistImporterRegistry
from app.services.track_normalizer import NORMALIZATION_VERSION

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PersistedImport:
    playlist: ImportedPlaylist
    issues: tuple[ImportIssue, ...]


class PlaylistImportService:
    def __init__(
        self,
        session: Session,
        registry: PlaylistImporterRegistry,
    ) -> None:
        self.session = session
        self.registry = registry

    def import_playlist(
        self,
        importer_key: str,
        content: BinaryIO,
        *,
        filename: str | None,
    ) -> PersistedImport:
        logger.info(
            "Playlist import started",
            extra={"event": "playlist_import_started", "importer": importer_key},
        )
        try:
            result = self.registry.get(importer_key).import_tracks(content, filename=filename)
        except MediaForgeToolError as exc:
            logger.warning(
                "Playlist import failed",
                extra={
                    "event": "playlist_import_failed",
                    "importer": importer_key,
                    "error_code": exc.code,
                },
            )
            raise
        playlist = ImportedPlaylist(
            name=result.name,
            importer_key=importer_key,
            source_filename=_safe_filename(filename),
            track_count=len(result.tracks),
            rejected_row_count=len(result.issues),
            error_summary=_error_summary(result.issues),
        )
        playlist.status = PlaylistStatus.partial if result.issues else PlaylistStatus.ready
        playlist.tracks = [
            Track(
                position=track.position,
                artist=track.artist,
                title=track.title,
                album=track.album,
                isrc=track.isrc,
                duration_seconds=track.duration_seconds,
                raw_artist=track.raw_artist,
                raw_title=track.raw_title,
                source_payload=track.source_payload,
                normalization_version=NORMALIZATION_VERSION,
            )
            for track in result.tracks
        ]
        playlist.issues = [
            PlaylistImportIssue(
                position=index,
                row_number=issue.row_number,
                code=issue.code,
                message=issue.message,
            )
            for index, issue in enumerate(result.issues)
        ]
        self.session.add(playlist)
        self.session.commit()
        self.session.refresh(playlist)
        for issue in playlist.issues:
            logger.warning(
                "Playlist import row rejected",
                extra={
                    "event": "playlist_import_row_rejected",
                    "playlist_id": playlist.id,
                    "importer": importer_key,
                    "row_number": issue.row_number,
                    "error_code": issue.code,
                },
            )
        logger.info(
            "Playlist import completed",
            extra={
                "event": (
                    "playlist_import_partial"
                    if playlist.status is PlaylistStatus.partial
                    else "playlist_import_completed"
                ),
                "playlist_id": playlist.id,
                "importer": importer_key,
                "status": playlist.status.value,
            },
        )
        return PersistedImport(playlist=playlist, issues=result.issues)


def _safe_filename(filename: str | None) -> str | None:
    if filename is None:
        return None
    normalized = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    return normalized[:300] or None


def _error_summary(issues: tuple[ImportIssue, ...]) -> str | None:
    if not issues:
        return None
    counts: dict[str, int] = {}
    for issue in issues:
        counts[issue.code] = counts.get(issue.code, 0) + 1
    return ", ".join(f"{code}: {count}" for code, count in sorted(counts.items()))[:500]
