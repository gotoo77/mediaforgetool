import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.exceptions import MediaAssetUnavailable, MediaProbeFailed
from app.schemas.studio import MediaProbeResponse, MediaStreamProbeResponse

PROBE_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class ManagedMediaPath:
    absolute: Path
    relative: str


class MediaProbeService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def inspect_asset_path(self, relative_path: str) -> MediaProbeResponse:
        media_path = self.resolve_asset_path(relative_path)
        if not media_path.absolute.is_file():
            raise MediaAssetUnavailable
        return self.inspect_file(media_path.absolute)

    def inspect_file(self, path: Path) -> MediaProbeResponse:
        try:
            result = subprocess.run(
                [
                    self.settings.ffprobe_binary,
                    "-v",
                    "error",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    str(path),
                ],
                capture_output=True,
                check=False,
                text=True,
                timeout=PROBE_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise MediaProbeFailed from exc
        if result.returncode != 0:
            raise MediaProbeFailed
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise MediaProbeFailed from exc
        return _probe_from_payload(payload)

    def resolve_asset_path(self, relative_path: str) -> ManagedMediaPath:
        normalized = relative_path.replace("\\", "/").strip()
        if not normalized or normalized.startswith("/") or normalized.startswith("../"):
            raise MediaAssetUnavailable
        if "/../" in normalized or ":" in normalized.split("/", 1)[0]:
            raise MediaAssetUnavailable

        roots = [
            self.settings.storage_dir.parent,
            self.settings.media_assets_dir,
            self.settings.media_studio_dir,
        ]
        candidates = [(root / normalized).resolve() for root in roots]
        resolved_roots = [root.resolve() for root in roots]
        for candidate, root in zip(candidates, resolved_roots, strict=True):
            if _is_relative_to(candidate, root):
                return ManagedMediaPath(absolute=candidate, relative=normalized)
        raise MediaAssetUnavailable


def _probe_from_payload(payload: dict[str, Any]) -> MediaProbeResponse:
    raw_format = payload.get("format") if isinstance(payload.get("format"), dict) else {}
    raw_streams = payload.get("streams") if isinstance(payload.get("streams"), list) else []
    streams = [
        _stream_from_payload(stream)
        for stream in raw_streams
        if isinstance(stream, dict) and stream.get("codec_type") in {"audio", "video"}
    ]
    audio_streams = [stream for stream in streams if stream.codec_type == "audio"]
    video_streams = [stream for stream in streams if stream.codec_type == "video"]
    return MediaProbeResponse(
        duration_seconds=_optional_float(raw_format.get("duration")),
        container_format=_optional_string(raw_format.get("format_name")),
        size_bytes=_optional_int(raw_format.get("size")),
        bitrate=_optional_int(raw_format.get("bit_rate")),
        has_audio=bool(audio_streams),
        has_video=bool(video_streams),
        audio_streams=audio_streams,
        video_streams=video_streams,
    )


def _stream_from_payload(stream: dict[str, Any]) -> MediaStreamProbeResponse:
    return MediaStreamProbeResponse(
        index=_optional_int(stream.get("index")) or 0,
        codec_type=str(stream.get("codec_type") or "unknown"),
        codec_name=_optional_string(stream.get("codec_name")),
        duration_seconds=_optional_float(stream.get("duration")),
        bitrate=_optional_int(stream.get("bit_rate")),
        width=_optional_int(stream.get("width")),
        height=_optional_int(stream.get("height")),
        channels=_optional_int(stream.get("channels")),
        sample_rate=_optional_int(stream.get("sample_rate")),
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
