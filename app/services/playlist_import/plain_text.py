from pathlib import Path
from typing import BinaryIO

from app.core.exceptions import PlaylistImportFileInvalid, PlaylistImportTooManyRows
from app.services.playlist_import.base import ImportedTrack, ImportIssue, ImportResult
from app.services.track_normalizer import TrackNormalizer

_SEPARATOR = " - "


class PlainTextImporter:
    key = "text"

    def __init__(
        self,
        *,
        max_tracks: int,
        normalizer: TrackNormalizer | None = None,
    ) -> None:
        self.max_tracks = max_tracks
        self.normalizer = normalizer or TrackNormalizer()

    def import_tracks(
        self,
        content: BinaryIO,
        *,
        filename: str | None,
    ) -> ImportResult:
        text = _decode_text(content)
        tracks: list[ImportedTrack] = []
        issues: list[ImportIssue] = []
        seen: set[tuple[str, str, str, str]] = set()
        source_rows = 0
        for row_number, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if source_rows >= self.max_tracks:
                raise PlaylistImportTooManyRows
            source_rows += 1
            parsed = _parse_line(line)
            if parsed is None:
                issues.append(
                    ImportIssue(
                        row_number=row_number,
                        code="TEXT_TRACK_FORMAT_INVALID",
                        message="Use one track per line as 'Artist - Title'.",
                    )
                )
                continue
            raw_artist, raw_title = parsed
            try:
                normalized = self.normalizer.normalize(artist=raw_artist, title=raw_title)
            except ValueError:
                issues.append(
                    ImportIssue(
                        row_number=row_number,
                        code="TRACK_METADATA_MISSING",
                        message="Artist and title are required.",
                    )
                )
                continue
            if normalized.duplicate_key in seen:
                issues.append(
                    ImportIssue(
                        row_number=row_number,
                        code="DUPLICATE_TRACK",
                        message="This track duplicates an earlier normalized row.",
                    )
                )
                continue
            seen.add(normalized.duplicate_key)
            tracks.append(
                ImportedTrack(
                    position=len(tracks),
                    artist=normalized.artist,
                    title=normalized.title,
                    raw_artist=raw_artist,
                    raw_title=raw_title,
                    source_payload={"line": row_number},
                )
            )
        if not tracks:
            raise PlaylistImportFileInvalid
        return ImportResult(
            name=_playlist_name(filename),
            tracks=tuple(tracks),
            issues=tuple(issues),
        )


def _decode_text(content: BinaryIO) -> str:
    try:
        return content.read().decode("utf-8-sig")
    except (AttributeError, UnicodeDecodeError) as exc:
        raise PlaylistImportFileInvalid from exc


def _parse_line(line: str) -> tuple[str, str] | None:
    if line.count(_SEPARATOR) != 1:
        return None
    artist, title = line.split(_SEPARATOR, 1)
    if not artist.strip() or not title.strip():
        return None
    return artist, title


def _playlist_name(filename: str | None) -> str:
    if not filename:
        return "Text import"
    return Path(filename).stem[:300] or "Text import"
