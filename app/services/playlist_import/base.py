from dataclasses import dataclass, field
from typing import BinaryIO, Protocol


@dataclass(frozen=True)
class ImportedTrack:
    position: int
    artist: str
    title: str
    album: str | None = None
    isrc: str | None = None
    duration_seconds: int | None = None
    raw_artist: str | None = None
    raw_title: str | None = None
    source_payload: dict[str, str | int | float | bool | None] = field(default_factory=dict)


@dataclass(frozen=True)
class ImportIssue:
    row_number: int | None
    code: str
    message: str


@dataclass(frozen=True)
class ImportResult:
    name: str
    tracks: tuple[ImportedTrack, ...]
    issues: tuple[ImportIssue, ...] = ()


class PlaylistImporter(Protocol):
    key: str

    def import_tracks(
        self,
        content: BinaryIO,
        *,
        filename: str | None,
    ) -> ImportResult: ...
