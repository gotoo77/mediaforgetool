import re
import unicodedata
from dataclasses import dataclass

NORMALIZATION_VERSION = "1"
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class NormalizedTrackMetadata:
    artist: str
    title: str
    album: str | None
    isrc: str | None

    @property
    def duplicate_key(self) -> tuple[str, str, str, str]:
        return (
            self.artist.casefold(),
            self.title.casefold(),
            (self.album or "").casefold(),
            (self.isrc or "").casefold(),
        )


class TrackNormalizer:
    version = NORMALIZATION_VERSION

    def normalize(
        self,
        *,
        artist: str,
        title: str,
        album: str | None = None,
        isrc: str | None = None,
    ) -> NormalizedTrackMetadata:
        return NormalizedTrackMetadata(
            artist=_normalize_required(artist),
            title=_normalize_required(title),
            album=_normalize_optional(album),
            isrc=_normalize_optional(isrc),
        )


def _normalize_required(value: str) -> str:
    normalized = _normalize_text(value)
    if not normalized:
        raise ValueError("Required track metadata is empty.")
    return normalized


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    return _normalize_text(value) or None


def _normalize_text(value: str) -> str:
    unicode_value = unicodedata.normalize("NFKC", value)
    return _WHITESPACE.sub(" ", unicode_value).strip()
