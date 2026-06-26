from collections.abc import Callable
from typing import Any

from yt_dlp import DownloadError, YoutubeDL

from app.core.config import Settings
from app.core.exceptions import (
    MediaSearchAuthenticationRequired,
    MediaSearchNoResults,
    MediaSearchTimeout,
    MediaSearchUnavailable,
)
from app.services.media_downloader import QuietYtdlpLogger
from app.services.media_search.base import SearchCandidate, TrackQuery

YtdlpFactory = Callable[[dict[str, Any]], Any]


class YouTubeSearchProvider:
    key = "youtube"

    def __init__(
        self,
        settings: Settings,
        *,
        ytdlp_factory: YtdlpFactory | None = None,
    ) -> None:
        self.settings = settings
        self.ytdlp_factory = ytdlp_factory or YoutubeDL

    def search(self, track: TrackQuery, *, limit: int) -> list[SearchCandidate]:
        safe_limit = max(1, min(limit, self.settings.media_search_max_candidates))
        query = youtube_search_query(track)
        try:
            with self.ytdlp_factory(self._options()) as ydl:
                info = ydl.extract_info(f"ytsearch{safe_limit}:{query}", download=False)
        except TimeoutError as exc:
            raise MediaSearchTimeout from exc
        except DownloadError as exc:
            raise _search_error_from_download_error(exc) from exc
        except OSError as exc:
            raise MediaSearchUnavailable from exc

        entries = _entries_from_info(info)
        if not entries:
            raise MediaSearchNoResults
        candidates = [
            candidate
            for rank, entry in enumerate(entries[:safe_limit])
            if (candidate := _candidate_from_entry(entry, rank)) is not None
        ]
        if not candidates:
            raise MediaSearchNoResults
        return candidates

    def _options(self) -> dict[str, Any]:
        options: dict[str, Any] = {
            "default_search": "ytsearch",
            "extract_flat": False,
            "logger": QuietYtdlpLogger(),
            "noplaylist": True,
            "quiet": True,
            "skip_download": True,
            "socket_timeout": self.settings.ytdlp_socket_timeout_seconds,
        }
        if self.settings.ytdlp_js_runtime:
            runtime_config: dict[str, str] = {}
            if self.settings.ytdlp_js_runtime_path:
                runtime_config["path"] = self.settings.ytdlp_js_runtime_path
            options["js_runtimes"] = {self.settings.ytdlp_js_runtime: runtime_config}
        if self.settings.ytdlp_cookies_file:
            cookies_file = self.settings.ytdlp_cookies_file
            if not cookies_file.is_file():
                raise MediaSearchAuthenticationRequired
            options["cookiefile"] = str(cookies_file)
        elif self.settings.ytdlp_cookies_from_browser:
            options["cookiesfrombrowser"] = _cookies_from_browser_spec(
                self.settings.ytdlp_cookies_from_browser
            )
        return options


def youtube_search_query(track: TrackQuery) -> str:
    return " ".join(part for part in (track.artist.strip(), track.title.strip()) if part)


def _entries_from_info(info: Any) -> list[Any]:
    entries = info.get("entries") if hasattr(info, "get") else None
    return entries if isinstance(entries, list) else []


def _candidate_from_entry(entry: Any, rank: int) -> SearchCandidate | None:
    source_url = _source_url(entry)
    title = _string_value(entry, "title")
    if not source_url or not title:
        return None
    return SearchCandidate(
        provider_key=YouTubeSearchProvider.key,
        provider_media_id=_string_value(entry, "id"),
        source_url=source_url,
        title=title,
        creator=_string_value(entry, "channel") or _string_value(entry, "uploader"),
        duration_seconds=_integer_value(entry, "duration"),
        thumbnail_url=_thumbnail_url(entry),
        rank=rank,
        match_score=None,
    )


def _source_url(entry: Any) -> str | None:
    webpage_url = _string_value(entry, "webpage_url")
    if webpage_url:
        return webpage_url
    media_id = _string_value(entry, "id")
    if media_id:
        return f"https://www.youtube.com/watch?v={media_id}"
    return _string_value(entry, "url")


def _thumbnail_url(entry: Any) -> str | None:
    thumbnail = _string_value(entry, "thumbnail")
    if thumbnail:
        return thumbnail
    thumbnails = entry.get("thumbnails") if hasattr(entry, "get") else None
    if not isinstance(thumbnails, list):
        return None
    for item in reversed(thumbnails):
        url = _string_value(item, "url")
        if url:
            return url
    return None


def _string_value(info: Any, key: str) -> str | None:
    value = info.get(key) if hasattr(info, "get") else None
    return value if isinstance(value, str) and value else None


def _integer_value(info: Any, key: str) -> int | None:
    value = info.get(key) if hasattr(info, "get") else None
    return int(value) if isinstance(value, (int, float)) else None


def _search_error_from_download_error(exc: DownloadError) -> Exception:
    message = str(exc).casefold()
    authentication_markers = ("authentication", "cookies", "log in", "login", "sign in")
    if any(marker in message for marker in authentication_markers):
        return MediaSearchAuthenticationRequired()
    timeout_markers = ("timed out", "timeout")
    if any(marker in message for marker in timeout_markers):
        return MediaSearchTimeout()
    no_result_markers = ("no video results", "no results")
    if any(marker in message for marker in no_result_markers):
        return MediaSearchNoResults()
    return MediaSearchUnavailable()


def _cookies_from_browser_spec(value: str) -> tuple[str, str | None, str | None, str | None]:
    parts = value.split(":", 3)
    browser = parts[0].strip()
    profile = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
    keyring = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
    container = parts[3].strip() if len(parts) > 3 and parts[3].strip() else None
    return browser, profile, keyring, container
