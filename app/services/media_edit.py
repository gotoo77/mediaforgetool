import logging
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.exceptions import (
    MediaAssetUnavailable,
    MediaEditFailed,
    MediaEditIncompatibleInputs,
    MediaEditInvalidInput,
)
from app.models.studio import (
    MediaAsset,
    MediaAssetKind,
    MediaAssetOrigin,
    MediaEditJob,
    MediaEditJobInput,
    MediaEditJobOutput,
    MediaEditOperation,
    MediaEditStatus,
)
from app.services.media_probe import MediaProbeService

_UNSAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MediaEditInput:
    role: str
    asset: MediaAsset
    path: Path


@dataclass(frozen=True)
class MediaEditOutput:
    role: str
    position: int
    path: Path
    relative_path: str
    display_name: str
    kind: MediaAssetKind


@dataclass(frozen=True)
class MediaEditCommand:
    args: list[str]
    outputs: list[MediaEditOutput]


class MediaEditCommandBuilder:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build(self, job: MediaEditJob, inputs: list[MediaEditInput]) -> list[MediaEditCommand]:
        output_dir = self.settings.media_studio_dir / job.id
        output_dir.mkdir(parents=True, exist_ok=True)
        match job.operation:
            case MediaEditOperation.replace_audio:
                return [self._replace_audio(job, inputs, output_dir)]
            case MediaEditOperation.remove_audio:
                return [self._remove_audio(job, inputs, output_dir)]
            case MediaEditOperation.extract_audio:
                return [self._extract_audio(job, inputs, output_dir)]
            case MediaEditOperation.split_media:
                return self._split_media(job, inputs, output_dir)
            case MediaEditOperation.concat_audio:
                return [self._concat_audio(job, inputs, output_dir)]
            case MediaEditOperation.concat_video:
                return [self._concat_video(job, inputs, output_dir)]
            case _:
                raise MediaEditInvalidInput

    def _replace_audio(
        self,
        job: MediaEditJob,
        inputs: list[MediaEditInput],
        output_dir: Path,
    ) -> MediaEditCommand:
        video = _required_input(inputs, "video", MediaAssetKind.video)
        audio = _required_input(inputs, "audio", MediaAssetKind.audio)
        output = self._output(job, output_dir, "output", 0, ".mp4", MediaAssetKind.video)
        args = [self.settings.ffmpeg_binary, "-y", "-i", str(video.path)]
        offset = float(job.options.get("audio_offset_seconds") or 0)
        if offset:
            args.extend(["-itsoffset", _format_seconds(offset)])
        args.extend(
            [
                "-i",
                str(audio.path),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
            ]
        )
        if job.options.get("duration_mode", "shortest") == "shortest":
            args.append("-shortest")
        args.append(str(output.path))
        return MediaEditCommand(args=args, outputs=[output])

    def _remove_audio(
        self,
        job: MediaEditJob,
        inputs: list[MediaEditInput],
        output_dir: Path,
    ) -> MediaEditCommand:
        video = _required_input(inputs, "video", MediaAssetKind.video)
        output = self._output(job, output_dir, "output", 0, ".mp4", MediaAssetKind.video)
        return MediaEditCommand(
            args=[
                self.settings.ffmpeg_binary,
                "-y",
                "-i",
                str(video.path),
                "-map",
                "0:v:0",
                "-c:v",
                "copy",
                "-an",
                str(output.path),
            ],
            outputs=[output],
        )

    def _extract_audio(
        self,
        job: MediaEditJob,
        inputs: list[MediaEditInput],
        output_dir: Path,
    ) -> MediaEditCommand:
        source = _required_input(inputs, "source", MediaAssetKind.video)
        audio_format = str(job.options.get("audio_format") or "mp3")
        if audio_format == "m4a":
            suffix = ".m4a"
            codec_args = ["-c:a", "aac"]
        else:
            suffix = ".mp3"
            codec_args = ["-c:a", "libmp3lame"]
        output = self._output(job, output_dir, "output", 0, suffix, MediaAssetKind.audio)
        return MediaEditCommand(
            args=[
                self.settings.ffmpeg_binary,
                "-y",
                "-i",
                str(source.path),
                "-vn",
                *codec_args,
                str(output.path),
            ],
            outputs=[output],
        )

    def _split_media(
        self,
        job: MediaEditJob,
        inputs: list[MediaEditInput],
        output_dir: Path,
    ) -> list[MediaEditCommand]:
        source = _required_input(inputs, "source")
        cut = job.options.get("split_time_seconds")
        if not isinstance(cut, int | float) or cut <= 0:
            raise MediaEditInvalidInput
        suffix = Path(source.asset.relative_path).suffix or ".mp4"
        output_kind = (
            source.asset.kind
            if source.asset.kind != MediaAssetKind.unknown
            else MediaAssetKind.video
        )
        part1 = self._output(job, output_dir, "part1", 0, suffix, output_kind)
        part2 = self._output(job, output_dir, "part2", 1, suffix, output_kind)
        return [
            MediaEditCommand(
                args=[
                    self.settings.ffmpeg_binary,
                    "-y",
                    "-i",
                    str(source.path),
                    "-t",
                    _format_seconds(float(cut)),
                    "-c",
                    "copy",
                    str(part1.path),
                ],
                outputs=[part1],
            ),
            MediaEditCommand(
                args=[
                    self.settings.ffmpeg_binary,
                    "-y",
                    "-ss",
                    _format_seconds(float(cut)),
                    "-i",
                    str(source.path),
                    "-c",
                    "copy",
                    str(part2.path),
                ],
                outputs=[part2],
            ),
        ]

    def _concat_audio(
        self,
        job: MediaEditJob,
        inputs: list[MediaEditInput],
        output_dir: Path,
    ) -> MediaEditCommand:
        audios = _required_inputs(inputs, "audio", MediaAssetKind.audio)
        concat_list = _write_concat_list(output_dir / "concat-audio.ffconcat", audios)
        audio_format = str(job.options.get("audio_format") or "mp3")
        if audio_format == "m4a":
            suffix = ".m4a"
            codec_args = ["-c:a", "aac"]
        else:
            suffix = ".mp3"
            codec_args = ["-c:a", "libmp3lame"]
        output = self._output(job, output_dir, "output", 0, suffix, MediaAssetKind.audio)
        return MediaEditCommand(
            args=[
                self.settings.ffmpeg_binary,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-vn",
                *codec_args,
                str(output.path),
            ],
            outputs=[output],
        )

    def _concat_video(
        self,
        job: MediaEditJob,
        inputs: list[MediaEditInput],
        output_dir: Path,
    ) -> MediaEditCommand:
        videos = _required_inputs(inputs, "video", MediaAssetKind.video)
        _validate_video_concat_compatibility(videos)
        concat_list = _write_concat_list(output_dir / "concat-video.ffconcat", videos)
        output = self._output(job, output_dir, "output", 0, ".mp4", MediaAssetKind.video)
        return MediaEditCommand(
            args=[
                self.settings.ffmpeg_binary,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c",
                "copy",
                str(output.path),
            ],
            outputs=[output],
        )

    def _output(
        self,
        job: MediaEditJob,
        output_dir: Path,
        role: str,
        position: int,
        suffix: str,
        kind: MediaAssetKind,
    ) -> MediaEditOutput:
        stem = _safe_stem(Path(job.output_name).stem or job.output_name)
        filename = f"{stem}-{role}{suffix}" if role != "output" else f"{stem}{suffix}"
        path = output_dir / filename
        relative = _relative_to_storage(path, self.settings)
        return MediaEditOutput(
            role=role,
            position=position,
            path=path,
            relative_path=relative,
            display_name=filename,
            kind=kind,
        )


class MediaEditRunner:
    def __init__(self, settings: Settings, session_factory: sessionmaker[Session]) -> None:
        self.settings = settings
        self.session_factory = session_factory

    def run(self, job_id: str) -> None:
        try:
            with self.session_factory() as session:
                job = session.get(MediaEditJob, job_id)
                if job is None or job.status is not MediaEditStatus.queued:
                    return
                job.transition_to(MediaEditStatus.processing)
                job.progress_percent = 0
                logger.info(
                    "Studio job processing",
                    extra={
                        "event": "studio_job_processing",
                        "job_id": job_id,
                        "operation": job.operation.value,
                        "status": job.status.value,
                    },
                )
                session.commit()
                inputs = self._resolve_inputs(list(job.inputs))
                commands = MediaEditCommandBuilder(self.settings).build(job, inputs)
            for command in commands:
                result = subprocess.run(
                    command.args,
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=self.settings.job_timeout_seconds,
                )
                if result.returncode != 0:
                    raise MediaEditFailed
            self._complete(job_id, [output for command in commands for output in command.outputs])
        except Exception as exc:
            self._fail(job_id, exc)

    def _resolve_inputs(self, input_rows: list[MediaEditJobInput]) -> list[MediaEditInput]:
        resolver = MediaProbeService(self.settings)
        inputs: list[MediaEditInput] = []
        for row in input_rows:
            path = resolver.resolve_asset_path(row.asset.relative_path).absolute
            if not path.is_file():
                raise MediaAssetUnavailable
            inputs.append(MediaEditInput(role=row.role, asset=row.asset, path=path))
        return inputs

    def _complete(self, job_id: str, outputs: list[MediaEditOutput]) -> None:
        with self.session_factory() as session:
            job = session.get(MediaEditJob, job_id)
            if job is None:
                return
            output_assets: list[MediaAsset] = []
            for output in outputs:
                if not output.path.is_file():
                    raise MediaEditFailed
                asset = MediaAsset(
                    display_name=output.display_name,
                    relative_path=output.relative_path,
                    kind=output.kind,
                    origin=MediaAssetOrigin.studio_output,
                    size_bytes=output.path.stat().st_size,
                )
                output_assets.append(asset)
                job.outputs.append(
                    MediaEditJobOutput(
                        asset=asset,
                        role=output.role,
                        position=output.position,
                    )
                )
                logger.info(
                    "Studio asset imported",
                    extra={
                        "event": "studio_asset_imported",
                        "job_id": job_id,
                        "asset_id": asset.id,
                        "operation": job.operation.value,
                    },
                )
            job.output_asset = output_assets[0] if output_assets else None
            job.progress_percent = 100
            job.status = MediaEditStatus.completed
            job.completed_at = datetime.now(UTC)
            logger.info(
                "Studio job completed",
                extra={
                    "event": "studio_job_completed",
                    "job_id": job_id,
                    "operation": job.operation.value,
                    "status": job.status.value,
                    "outputs": len(output_assets),
                },
            )
            session.commit()

    def _fail(self, job_id: str, exc: Exception) -> None:
        with self.session_factory() as session:
            job = session.get(MediaEditJob, job_id)
            if job is None:
                return
            job.status = MediaEditStatus.failed
            if isinstance(
                exc,
                MediaEditInvalidInput | MediaEditIncompatibleInputs | MediaAssetUnavailable,
            ):
                job.error_code = exc.code
                job.error_message = exc.public_message
            else:
                job.error_code = MediaEditFailed.code
                job.error_message = MediaEditFailed.public_message
            logger.warning(
                "Studio job failed",
                extra={
                    "event": "studio_job_failed",
                    "job_id": job_id,
                    "operation": job.operation.value,
                    "status": job.status.value,
                    "error_code": job.error_code,
                },
            )
            session.commit()


def _required_input(
    inputs: list[MediaEditInput],
    role: str,
    kind: MediaAssetKind | None = None,
) -> MediaEditInput:
    for item in inputs:
        if item.role == role and (kind is None or item.asset.kind is kind):
            return item
    raise MediaEditInvalidInput


def _required_inputs(
    inputs: list[MediaEditInput],
    role: str,
    kind: MediaAssetKind,
) -> list[MediaEditInput]:
    items = [item for item in inputs if item.role == role and item.asset.kind is kind]
    if len(items) < 2:
        raise MediaEditInvalidInput
    return items


def _validate_video_concat_compatibility(inputs: list[MediaEditInput]) -> None:
    comparable_fields = ("container_format", "video_codec", "audio_codec", "width", "height")
    reference = inputs[0].asset
    for item in inputs[1:]:
        for field in comparable_fields:
            left = getattr(reference, field)
            right = getattr(item.asset, field)
            if left is not None and right is not None and left != right:
                raise MediaEditIncompatibleInputs


def _write_concat_list(path: Path, inputs: list[MediaEditInput]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"file '{_ffconcat_escape(item.path)}'\n" for item in inputs),
        encoding="utf-8",
    )
    return path


def _ffconcat_escape(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace("'", "\\'")


def _format_seconds(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _safe_stem(value: str) -> str:
    stem = _UNSAFE_NAME.sub("_", value).strip(" ._")
    return stem[:120] or "mediaforgetool-studio"


def _relative_to_storage(path: Path, settings: Settings) -> str:
    try:
        return path.resolve().relative_to(settings.storage_dir.parent.resolve()).as_posix()
    except ValueError:
        return path.resolve().relative_to(settings.media_studio_dir.resolve()).as_posix()
