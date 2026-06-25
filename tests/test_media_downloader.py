from pathlib import Path

from yt_dlp import DownloadError

from app.core.config import Settings
from app.core.exceptions import (
    CookiesUnavailable,
    OutputFormatUnavailable,
    SegmentOutOfBounds,
    SourceAuthenticationRequired,
    SourceNoStreams,
)
from app.models.job import OutputFormat
from app.services.media_downloader import (
    MediaDownloader,
    MediaMetadata,
    SegmentSuggestion,
    _media_error_from_download_error,
)


def test_common_ytdlp_options_resolve_ffmpeg_and_enable_js_runtime(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'mediaforgetool.db'}",
        storage_dir=tmp_path / "storage",
        temp_dir=tmp_path / "temp",
        ytdlp_js_runtime="node",
        ytdlp_js_runtime_path="/opt/node/bin/node",
    )
    monkeypatch.setattr(
        "app.services.media_downloader.shutil.which",
        lambda _: "/usr/bin/ffmpeg",
    )

    options = MediaDownloader(settings)._common_options()

    assert options["ffmpeg_location"] == "/usr/bin/ffmpeg"
    assert options["js_runtimes"] == {"node": {"path": "/opt/node/bin/node"}}


def test_common_ytdlp_options_enable_cookie_file(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    cookies = tmp_path / "cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'mediaforgetool.db'}",
        storage_dir=tmp_path / "storage",
        temp_dir=tmp_path / "temp",
        ytdlp_cookies_file=cookies,
    )
    monkeypatch.setattr(
        "app.services.media_downloader.shutil.which",
        lambda _: "/usr/bin/ffmpeg",
    )

    options = MediaDownloader(settings)._common_options()

    assert options["cookiefile"] == str(cookies)


def test_common_ytdlp_options_reject_missing_cookie_file(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'mediaforgetool.db'}",
        storage_dir=tmp_path / "storage",
        temp_dir=tmp_path / "temp",
        ytdlp_cookies_file=tmp_path / "missing.txt",
    )

    try:
        MediaDownloader(settings)._common_options()
    except CookiesUnavailable as exc:
        assert exc.code == "COOKIES_UNAVAILABLE"
    else:
        raise AssertionError("Expected missing cookie file to fail")


def test_common_ytdlp_options_enable_browser_cookies(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'mediaforgetool.db'}",
        storage_dir=tmp_path / "storage",
        temp_dir=tmp_path / "temp",
        ytdlp_cookies_from_browser="firefox:default",
        ytdlp_cookies_file=None,
    )

    options = MediaDownloader(settings)._common_options()

    assert options["cookiesfrombrowser"] == ("firefox", "default", None, None)


def test_final_file_prefers_ytdlp_filepath(tmp_path: Path) -> None:
    final_file = tmp_path / "merged.mp4"
    final_file.write_bytes(b"video")

    result = MediaDownloader._final_file_from_info(
        {"filepath": str(final_file)},
        tmp_path,
        OutputFormat.mp4,
    )

    assert result == final_file


def test_mp4_format_selector_filters_large_streams(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'mediaforgetool.db'}",
        storage_dir=tmp_path / "storage",
        temp_dir=tmp_path / "temp",
        max_output_size_mb=1,
    )

    options = MediaDownloader(settings)._download_options(
        OutputFormat.mp4,
        720,
        None,
        None,
        None,
        tmp_path,
        lambda percent, status: None,
    )

    assert (
        "bestvideo[ext=mp4][height<=?720][filesize<?1048576][filesize_approx<?1048576]"
        in options["format"]
    )
    assert (
        "/best[ext=mp4][height<=?720][filesize<?1048576][filesize_approx<?1048576]"
        in options["format"]
    )


def test_mp3_format_selector_filters_large_streams(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'mediaforgetool.db'}",
        storage_dir=tmp_path / "storage",
        temp_dir=tmp_path / "temp",
        max_output_size_mb=1,
    )

    options = MediaDownloader(settings)._download_options(
        OutputFormat.mp3,
        None,
        256,
        None,
        None,
        tmp_path,
        lambda percent, status: None,
    )

    assert options["format"] == (
        "bestaudio[filesize<?1048576][filesize_approx<?1048576]"
        "/best[filesize<?1048576][filesize_approx<?1048576]"
    )
    assert options["postprocessors"][0]["preferredquality"] == "256"


def test_download_options_can_limit_to_segment(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'mediaforgetool.db'}",
        storage_dir=tmp_path / "storage",
        temp_dir=tmp_path / "temp",
    )

    options = MediaDownloader(settings)._download_options(
        OutputFormat.mp3,
        None,
        None,
        60,
        120,
        tmp_path,
        lambda percent, status: None,
    )

    assert list(options["download_ranges"]({}, None)) == [
        {"start_time": 60, "end_time": 120}
    ]
    assert options["force_keyframes_at_cuts"] is False


def test_duration_enforcement_rejects_segment_beyond_real_duration(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'mediaforgetool.db'}",
        storage_dir=tmp_path / "storage",
        temp_dir=tmp_path / "temp",
    )
    metadata = MediaMetadata(
        title="Short video",
        platform="Example",
        thumbnail_url=None,
        duration_seconds=19,
    )

    try:
        MediaDownloader(settings)._enforce_duration(metadata, 0, 20)
    except SegmentOutOfBounds as exc:
        assert exc.code == "SEGMENT_OUT_OF_BOUNDS"
    else:
        raise AssertionError("Expected segment beyond media duration to fail")


def test_progress_hook_reports_transfer_details() -> None:
    updates: list[tuple[float | None, str, int | None, int | None, int | None, int | None]] = []

    MediaDownloader._on_progress(
        {
            "status": "downloading",
            "downloaded_bytes": 256,
            "total_bytes": 1024,
            "speed": 128,
            "eta": 6,
        },
        lambda percent, status, downloaded, total, speed, eta: updates.append(
            (percent, status, downloaded, total, speed, eta)
        ),
    )

    assert updates == [(25, "downloading", 256, 1024, 128, 6)]


def test_segment_suggestions_split_media_by_duration_limit(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'mediaforgetool.db'}",
        storage_dir=tmp_path / "storage",
        temp_dir=tmp_path / "temp",
        max_media_duration_seconds=60,
    )

    suggestions = MediaDownloader(settings)._segment_suggestions(125)

    assert suggestions == [
        SegmentSuggestion(start_seconds=0, end_seconds=60),
        SegmentSuggestion(start_seconds=60, end_seconds=120),
        SegmentSuggestion(start_seconds=120, end_seconds=125),
    ]


def test_ytdlp_login_failure_maps_to_authentication_error() -> None:
    error = _media_error_from_download_error(
        DownloadError("You need to log in to access this content")
    )

    assert isinstance(error, SourceAuthenticationRequired)
    assert error.code == "SOURCE_AUTH_REQUIRED"


def test_ytdlp_missing_format_maps_to_output_format_error() -> None:
    error = _media_error_from_download_error(
        DownloadError("Requested format is not available")
    )

    assert isinstance(error, OutputFormatUnavailable)
    assert error.code == "OUTPUT_FORMAT_UNAVAILABLE"


def test_ytdlp_no_video_formats_maps_to_source_stream_error() -> None:
    error = _media_error_from_download_error(DownloadError("No video formats found!"))

    assert isinstance(error, SourceNoStreams)
    assert error.code == "SOURCE_NO_STREAMS"
