import csv
import io
import re
from pathlib import Path
from typing import BinaryIO

from app.core.exceptions import PlaylistImportFileInvalid, PlaylistImportTooManyRows
from app.services.playlist_import.base import ImportedTrack, ImportIssue, ImportResult
from app.services.track_normalizer import TrackNormalizer

_HEADER_WHITESPACE = re.compile(r"[\s_-]+")
_TITLE_HEADERS = ("title", "track title", "song title", "track", "song")
_ARTIST_HEADERS = ("artist", "artist name", "subtitle")
_ALBUM_HEADERS = ("album", "album title")
_ISRC_HEADERS = ("isrc",)
_DURATION_HEADERS = ("duration seconds", "duration", "length")


class ShazamCsvImporter:
    key = "shazam_csv"

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
        text = _decode_csv(content)
        reader = _dict_reader(text)
        columns = _resolve_columns(reader.fieldnames)
        tracks: list[ImportedTrack] = []
        issues: list[ImportIssue] = []
        seen: set[tuple[str, str, str, str]] = set()

        for source_position, row in enumerate(_rows(reader)):
            if source_position >= self.max_tracks:
                raise PlaylistImportTooManyRows
            row_number = source_position + 2
            raw_artist = _row_value(row, columns["artist"])
            raw_title = _row_value(row, columns["title"])
            try:
                normalized = self.normalizer.normalize(
                    artist=raw_artist,
                    title=raw_title,
                    album=_row_value(row, columns.get("album")),
                    isrc=_row_value(row, columns.get("isrc")),
                )
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
                    album=normalized.album,
                    isrc=normalized.isrc,
                    duration_seconds=_duration_seconds(
                        _row_value(row, columns.get("duration"))
                    ),
                    raw_artist=raw_artist or None,
                    raw_title=raw_title or None,
                    source_payload=_bounded_source_payload(row),
                )
            )

        if not tracks:
            raise PlaylistImportFileInvalid
        return ImportResult(
            name=_playlist_name(filename),
            tracks=tuple(tracks),
            issues=tuple(issues),
        )


def _decode_csv(content: BinaryIO) -> str:
    try:
        return content.read().decode("utf-8-sig")
    except (AttributeError, UnicodeDecodeError) as exc:
        raise PlaylistImportFileInvalid from exc


def _dict_reader(text: str) -> csv.DictReader[str]:
    if not text.strip():
        raise PlaylistImportFileInvalid
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise PlaylistImportFileInvalid
    return reader


def _rows(reader: csv.DictReader[str]) -> list[dict[str, str | None]]:
    try:
        return list(reader)
    except csv.Error as exc:
        raise PlaylistImportFileInvalid from exc


def _resolve_columns(fieldnames: list[str] | None) -> dict[str, str]:
    if not fieldnames:
        raise PlaylistImportFileInvalid
    normalized = {_header_key(field): field for field in fieldnames if field}
    title = _first_column(normalized, _TITLE_HEADERS)
    artist = _first_column(normalized, _ARTIST_HEADERS)
    if title is None or artist is None:
        raise PlaylistImportFileInvalid
    return {
        "title": title,
        "artist": artist,
        **_optional_column(normalized, "album", _ALBUM_HEADERS),
        **_optional_column(normalized, "isrc", _ISRC_HEADERS),
        **_optional_column(normalized, "duration", _DURATION_HEADERS),
    }


def _header_key(value: str) -> str:
    return _HEADER_WHITESPACE.sub(" ", value.strip().casefold())


def _first_column(columns: dict[str, str], aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        if alias in columns:
            return columns[alias]
    return None


def _optional_column(
    columns: dict[str, str],
    name: str,
    aliases: tuple[str, ...],
) -> dict[str, str]:
    column = _first_column(columns, aliases)
    return {name: column} if column else {}


def _row_value(row: dict[str, str | None], column: str | None) -> str:
    if column is None:
        return ""
    return row.get(column) or ""


def _duration_seconds(value: str) -> int | None:
    stripped = value.strip()
    if not stripped:
        return None
    if stripped.isdigit():
        return int(stripped)
    parts = stripped.split(":")
    if len(parts) not in {2, 3} or not all(part.isdigit() for part in parts):
        return None
    total = 0
    for part in parts:
        total = total * 60 + int(part)
    return total


def _bounded_source_payload(row: dict[str, str | None]) -> dict[str, str | None]:
    return {
        str(key)[:120]: value[:1000] if isinstance(value, str) else None
        for key, value in list(row.items())[:40]
        if key is not None
    }


def _playlist_name(filename: str | None) -> str:
    if not filename:
        return "Shazam import"
    name = Path(filename).name
    stem = Path(name).stem.strip()
    return stem[:300] or "Shazam import"
