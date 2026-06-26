import pytest
from yt_dlp import DownloadError

from app.core.config import Settings
from app.core.exceptions import (
    MediaSearchAuthenticationRequired,
    MediaSearchNoResults,
    MediaSearchTimeout,
    MediaSearchUnavailable,
)
from app.services.media_search import TrackQuery
from app.services.media_search.youtube import YouTubeSearchProvider, youtube_search_query


class FakeYoutubeDL:
    def __init__(self, options: dict, result: dict | None = None, error: Exception | None = None):
        self.options = options
        self.result = result or {}
        self.error = error
        self.requests: list[tuple[str, bool]] = []

    def __enter__(self) -> "FakeYoutubeDL":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def extract_info(self, query: str, download: bool) -> dict:
        self.requests.append((query, download))
        if self.error:
            raise self.error
        return self.result


def test_youtube_provider_builds_deterministic_query_and_maps_candidates() -> None:
    instances: list[FakeYoutubeDL] = []

    def factory(options: dict) -> FakeYoutubeDL:
        instance = FakeYoutubeDL(
            options,
            {
                "entries": [
                    {
                        "id": "abc123",
                        "webpage_url": "https://www.youtube.com/watch?v=abc123",
                        "title": "Artist - Title",
                        "channel": "Channel",
                        "duration": 244,
                        "thumbnails": [{"url": "small"}, {"url": "large"}],
                    },
                    {
                        "id": "def456",
                        "title": "Other",
                        "uploader": "Uploader",
                    },
                ]
            },
        )
        instances.append(instance)
        return instance

    provider = YouTubeSearchProvider(Settings(media_search_max_candidates=3), ytdlp_factory=factory)

    candidates = provider.search(
        TrackQuery(track_id="track-1", artist="Artist", title="Title"),
        limit=2,
    )

    assert youtube_search_query(TrackQuery(track_id="track-1", artist="Artist", title="Title")) == (
        "Artist Title"
    )
    assert instances[0].requests == [("ytsearch2:Artist Title", False)]
    assert instances[0].options["skip_download"] is True
    assert candidates[0].provider_key == "youtube"
    assert candidates[0].provider_media_id == "abc123"
    assert candidates[0].source_url == "https://www.youtube.com/watch?v=abc123"
    assert candidates[0].creator == "Channel"
    assert candidates[0].duration_seconds == 244
    assert candidates[0].thumbnail_url == "large"
    assert candidates[1].source_url == "https://www.youtube.com/watch?v=def456"


def test_youtube_provider_limits_candidates_to_instance_setting() -> None:
    instances: list[FakeYoutubeDL] = []

    def factory(options: dict) -> FakeYoutubeDL:
        instance = FakeYoutubeDL(
            options,
            {
                "entries": [
                    {"id": "one", "title": "One"},
                    {"id": "two", "title": "Two"},
                ]
            },
        )
        instances.append(instance)
        return instance

    provider = YouTubeSearchProvider(Settings(media_search_max_candidates=1), ytdlp_factory=factory)

    candidates = provider.search(TrackQuery(track_id="track-1", artist="A", title="T"), limit=5)

    assert instances[0].requests == [("ytsearch1:A T", False)]
    assert [candidate.provider_media_id for candidate in candidates] == ["one"]


def test_youtube_provider_reports_no_results() -> None:
    provider = YouTubeSearchProvider(
        Settings(),
        ytdlp_factory=lambda options: FakeYoutubeDL(options, {"entries": []}),
    )

    with pytest.raises(MediaSearchNoResults):
        provider.search(TrackQuery(track_id="track-1", artist="A", title="T"), limit=5)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError(), MediaSearchTimeout),
        (DownloadError("Sign in to confirm your age"), MediaSearchAuthenticationRequired),
        (DownloadError("No video results"), MediaSearchNoResults),
        (DownloadError("Provider down"), MediaSearchUnavailable),
    ],
)
def test_youtube_provider_maps_errors(error: Exception, expected: type[Exception]) -> None:
    provider = YouTubeSearchProvider(
        Settings(),
        ytdlp_factory=lambda options: FakeYoutubeDL(options, error=error),
    )

    with pytest.raises(expected):
        provider.search(TrackQuery(track_id="track-1", artist="A", title="T"), limit=5)
