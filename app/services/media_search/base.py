from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TrackQuery:
    track_id: str
    artist: str
    title: str
    album: str | None = None
    duration_seconds: int | None = None


@dataclass(frozen=True)
class SearchCandidate:
    provider_key: str
    source_url: str
    title: str
    rank: int
    provider_media_id: str | None = None
    creator: str | None = None
    duration_seconds: int | None = None
    thumbnail_url: str | None = None
    match_score: float | None = None


class MediaSearchProvider(Protocol):
    key: str

    def search(
        self,
        track: TrackQuery,
        *,
        limit: int,
    ) -> list[SearchCandidate]: ...
