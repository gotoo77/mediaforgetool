import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from yt_dlp import DownloadError, YoutubeDL
from yt_dlp.utils import download_range_func

from app.core.config import Settings
from app.core.exceptions import (
    ConversionFailed,
    CookiesUnavailable,
    DownloadFailed,
    MediaForgeToolError,
    MediaTooLong,
    OutputFormatUnavailable,
    SegmentOutOfBounds,
    SourceAuthenticationRequired,
    SourceNoStreams,
)
from app.models.job import OutputFormat

logger = logging.getLogger(__name__)
ProgressCallback = Callable[
    [float | None, str, int | None, int | None, int | None, int | None],
    None,
]
SUPPORTED_VIDEO_HEIGHTS = (360, 480, 720, 1080)


@dataclass(frozen=True)
class MediaMetadata:
    title: str | None
    platform: str | None
    thumbnail_url: str | None
    duration_seconds: int | None


@dataclass(frozen=True)
class DownloadedMedia:
    metadata: MediaMetadata
    file_path: Path


@dataclass(frozen=True)
class VideoVariant:
    resolution: int
    selected_height: int | None
    estimated_size_bytes: int | None


@dataclass(frozen=True)
class SegmentSuggestion:
    start_seconds: int
    end_seconds: int


@dataclass(frozen=True)
class MediaInspection:
    title: str | None
    platform: str | None
    thumbnail_url: str | None
    duration_seconds: int | None
    mp3_estimated_size_bytes: int | None
    mp4_variants: list[VideoVariant]
    segment_suggestions: list[SegmentSuggestion]


class QuietYtdlpLogger:
    def debug(self, message: str) -> None:
        if message.startswith("[debug]"):
            logger.debug(message)

    def warning(self, message: str) -> None:
        logger.warning(message)

    def error(self, message: str) -> None:
        logger.error(message)


class MediaDownloader:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def fetch(
        self,
        url: str,
        output_format: OutputFormat,
        requested_height: int | None,
        requested_audio_bitrate_kbps: int | None,
        segment_start_seconds: int | None,
        segment_end_seconds: int | None,
        temp_dir: Path,
        progress: ProgressCallback,
    ) -> DownloadedMedia:
        try:
            metadata = self.extract_metadata(url)
            self._enforce_duration(metadata, segment_start_seconds, segment_end_seconds)
            progress(None, "downloading", None, None, None, None)
            with YoutubeDL(
                self._download_options(
                    output_format,
                    requested_height,
                    requested_audio_bitrate_kbps,
                    segment_start_seconds,
                    segment_end_seconds,
                    temp_dir,
                    progress,
                )
            ) as ydl:
                info = ydl.extract_info(url, download=True)
        except MediaTooLong:
            raise
        except DownloadError as exc:
            raise _media_error_from_download_error(exc) from exc
        except OSError as exc:
            raise ConversionFailed from exc

        result = self._final_file_from_info(info, temp_dir, output_format)
        if result is None:
            if any(temp_dir.glob("*.part")):
                raise DownloadFailed
            raise ConversionFailed
        return DownloadedMedia(metadata=metadata, file_path=result)

    def inspect(self, url: str) -> MediaInspection:
        options = self._common_options()
        options.update({"skip_download": True, "noplaylist": True})
        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
        except DownloadError as exc:
            raise _media_error_from_download_error(exc) from exc

        metadata = self._metadata_from_info(info)
        formats = info.get("formats") if hasattr(info, "get") else None
        mp4_variants = self._video_variants(formats if isinstance(formats, list) else [])
        return MediaInspection(
            title=metadata.title,
            platform=metadata.platform,
            thumbnail_url=metadata.thumbnail_url,
            duration_seconds=metadata.duration_seconds,
            mp3_estimated_size_bytes=self._mp3_estimate(metadata.duration_seconds),
            mp4_variants=mp4_variants,
            segment_suggestions=self._segment_suggestions(metadata.duration_seconds),
        )

    def extract_metadata(self, url: str) -> MediaMetadata:
        options = self._common_options()
        options.update({"skip_download": True, "noplaylist": True})
        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
        except DownloadError as exc:
            raise _media_error_from_download_error(exc) from exc

        return self._metadata_from_info(info)

    def _metadata_from_info(self, info: Any) -> MediaMetadata:
        duration = info.get("duration") if hasattr(info, "get") else None
        return MediaMetadata(
            title=_string_value(info, "title"),
            platform=_string_value(info, "extractor_key") or _string_value(info, "extractor"),
            thumbnail_url=_string_value(info, "thumbnail"),
            duration_seconds=int(duration) if isinstance(duration, (int, float)) else None,
        )

    def _download_options(
        self,
        output_format: OutputFormat,
        requested_height: int | None,
        requested_audio_bitrate_kbps: int | None,
        segment_start_seconds: int | None,
        segment_end_seconds: int | None,
        temp_dir: Path,
        progress: ProgressCallback,
    ) -> dict[str, Any]:
        options = self._common_options()
        options.update(
            {
                "outtmpl": str(temp_dir / "media.%(ext)s"),
                "noplaylist": True,
                "max_filesize": self.settings.max_output_size_bytes,
                "progress_hooks": [lambda status: self._on_progress(status, progress)],
            }
        )
        if segment_start_seconds is not None and segment_end_seconds is not None:
            options.update(
                {
                    "download_ranges": download_range_func(
                        None,
                        [(segment_start_seconds, segment_end_seconds)],
                    ),
                    "force_keyframes_at_cuts": False,
                }
            )
        size_limit = self.settings.max_output_size_bytes
        size_filter = f"[filesize<?{size_limit}][filesize_approx<?{size_limit}]"
        if output_format is OutputFormat.mp3:
            options.update(
                {
                    "format": f"bestaudio{size_filter}/best{size_filter}",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": str(
                                requested_audio_bitrate_kbps or self.settings.mp3_bitrate_kbps
                            ),
                        }
                    ],
                }
            )
        else:
            height_filter = f"[height<=?{requested_height}]" if requested_height else ""
            options.update(
                {
                    "format": (
                        f"bestvideo[ext=mp4]{height_filter}{size_filter}+bestaudio[ext=m4a]"
                        f"/best[ext=mp4]{height_filter}{size_filter}"
                    ),
                    "merge_output_format": "mp4",
                }
            )
        return options

    def _common_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {
            "logger": QuietYtdlpLogger(),
            "socket_timeout": self.settings.ytdlp_socket_timeout_seconds,
            "ffmpeg_location": shutil.which(self.settings.ffmpeg_binary)
            or self.settings.ffmpeg_binary,
            "restrictfilenames": True,
            "continuedl": True,
            "quiet": True,
            "no_warnings": False,
        }
        if self.settings.ytdlp_js_runtime:
            runtime_config: dict[str, str] = {}
            if self.settings.ytdlp_js_runtime_path:
                runtime_config["path"] = self.settings.ytdlp_js_runtime_path
            options["js_runtimes"] = {self.settings.ytdlp_js_runtime: runtime_config}
        if self.settings.ytdlp_cookies_file:
            cookies_file = self.settings.ytdlp_cookies_file
            if not cookies_file.is_file():
                raise CookiesUnavailable()
            options["cookiefile"] = str(cookies_file)
        elif self.settings.ytdlp_cookies_from_browser:
            options["cookiesfrombrowser"] = _cookies_from_browser_spec(
                self.settings.ytdlp_cookies_from_browser
            )
        return options

    def _enforce_duration(
        self,
        metadata: MediaMetadata,
        segment_start_seconds: int | None = None,
        segment_end_seconds: int | None = None,
    ) -> None:
        if segment_start_seconds is not None and segment_end_seconds is not None:
            if (
                metadata.duration_seconds is not None
                and segment_end_seconds > metadata.duration_seconds
            ):
                raise SegmentOutOfBounds
            duration_seconds = segment_end_seconds - segment_start_seconds
        else:
            duration_seconds = metadata.duration_seconds
        if (
            duration_seconds is not None
            and duration_seconds > self.settings.max_media_duration_seconds
        ):
            raise MediaTooLong

    def _segment_suggestions(self, duration_seconds: int | None) -> list[SegmentSuggestion]:
        segment_duration = self.settings.max_media_duration_seconds
        if duration_seconds is None or duration_seconds <= segment_duration:
            return []
        return [
            SegmentSuggestion(
                start_seconds=start,
                end_seconds=min(start + segment_duration, duration_seconds),
            )
            for start in range(0, duration_seconds, segment_duration)
        ]

    def _video_variants(self, formats: list[Any]) -> list[VideoVariant]:
        audio = self._best_audio_format(formats)
        variants: list[VideoVariant] = []
        for resolution in SUPPORTED_VIDEO_HEIGHTS:
            video = self._best_video_format(formats, resolution)
            if video is None:
                continue
            variants.append(
                VideoVariant(
                    resolution=resolution,
                    selected_height=_integer_value(video, "height"),
                    estimated_size_bytes=_combined_size(video, audio),
                )
            )
        return variants

    def _best_video_format(self, formats: list[Any], height_limit: int) -> Any | None:
        combined_fallback: Any | None = None
        for candidate in reversed(formats):
            if not _is_mp4_with_video(candidate):
                continue
            height = _integer_value(candidate, "height")
            if height is not None and height > height_limit:
                continue
            if not _fits_size_limit(candidate, self.settings.max_output_size_bytes):
                continue
            if _is_video_only(candidate):
                return candidate
            if combined_fallback is None:
                combined_fallback = candidate
        return combined_fallback

    def _best_audio_format(self, formats: list[Any]) -> Any | None:
        for candidate in reversed(formats):
            if not _is_m4a_audio(candidate):
                continue
            if not _fits_size_limit(candidate, self.settings.max_output_size_bytes):
                continue
            return candidate
        return None

    def _mp3_estimate(self, duration_seconds: int | None) -> int | None:
        if duration_seconds is None:
            return None
        return int(duration_seconds * self.settings.mp3_bitrate_kbps * 1000 / 8)

    @staticmethod
    def _on_progress(status: dict[str, Any], progress: ProgressCallback) -> None:
        state = status.get("status")
        if state == "finished":
            progress(100, "processing", None, None, None, None)
            return
        if state != "downloading":
            return
        downloaded = status.get("downloaded_bytes")
        total = status.get("total_bytes") or status.get("total_bytes_estimate")
        percent = (downloaded / total * 100) if downloaded and total else None
        progress(
            percent,
            "downloading",
            int(downloaded) if isinstance(downloaded, (int, float)) else None,
            int(total) if isinstance(total, (int, float)) else None,
            _integer_value(status, "speed"),
            _integer_value(status, "eta"),
        )

    @staticmethod
    def _final_file_from_info(
        info: Any,
        temp_dir: Path,
        output_format: OutputFormat,
    ) -> Path | None:
        filepath = info.get("filepath") if hasattr(info, "get") else None
        if isinstance(filepath, str):
            candidate = Path(filepath)
            if candidate.is_file():
                return candidate

        expected = temp_dir / f"media.{output_format.value}"
        if expected.is_file():
            return expected
        candidates = sorted(
            (path for path in temp_dir.glob(f"*.{output_format.value}") if path.is_file()),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        return candidates[0] if candidates else None


def _string_value(info: Any, key: str) -> str | None:
    value = info.get(key) if hasattr(info, "get") else None
    return value if isinstance(value, str) else None


def _integer_value(info: Any, key: str) -> int | None:
    value = info.get(key) if hasattr(info, "get") else None
    return int(value) if isinstance(value, (int, float)) else None


def _known_size(info: Any) -> int | None:
    return _integer_value(info, "filesize") or _integer_value(info, "filesize_approx")


def _combined_size(video: Any, audio: Any | None) -> int | None:
    video_size = _known_size(video)
    if not _is_video_only(video):
        return video_size
    audio_size = _known_size(audio)
    if video_size is None or audio_size is None:
        return None
    return video_size + audio_size


def _fits_size_limit(info: Any, size_limit: int) -> bool:
    size = _known_size(info)
    return size is None or size <= size_limit


def _is_mp4_with_video(info: Any) -> bool:
    return (
        _string_value(info, "ext") == "mp4"
        and _string_value(info, "vcodec") not in {None, "none"}
    )


def _is_video_only(info: Any) -> bool:
    return _string_value(info, "acodec") == "none"


def _is_m4a_audio(info: Any) -> bool:
    return (
        _string_value(info, "ext") == "m4a"
        and _string_value(info, "vcodec") == "none"
        and _string_value(info, "acodec") not in {None, "none"}
    )


def _media_error_from_download_error(exc: DownloadError) -> MediaForgeToolError:
    message = str(exc).casefold()
    authentication_markers = (
        "authentication",
        "cookies",
        "log in",
        "login",
        "registered users",
        "sign in",
    )
    if any(marker in message for marker in authentication_markers):
        return SourceAuthenticationRequired()

    if "no video formats found" in message:
        return SourceNoStreams()
    unavailable_format_markers = ("requested format is not available",)
    if any(marker in message for marker in unavailable_format_markers):
        return OutputFormatUnavailable()
    return DownloadFailed()


def _cookies_from_browser_spec(value: str) -> tuple[str, str | None, str | None, str | None]:
    parts = value.split(":", 3)
    browser = parts[0].strip()
    profile = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
    keyring = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
    container = parts[3].strip() if len(parts) > 3 and parts[3].strip() else None
    return browser, profile, keyring, container
