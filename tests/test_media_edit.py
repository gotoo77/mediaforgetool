import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.exceptions import MediaEditIncompatibleInputs
from app.main import create_app
from app.models.studio import (
    MediaAsset,
    MediaAssetKind,
    MediaAssetOrigin,
    MediaEditJob,
    MediaEditOperation,
    MediaEditStatus,
)
from app.services.media_edit import MediaEditCommandBuilder, MediaEditInput


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'mediaforgetool.db'}",
        storage_dir=tmp_path / "storage" / "jobs",
        media_assets_dir=tmp_path / "storage" / "assets",
        media_studio_dir=tmp_path / "storage" / "studio",
        temp_dir=tmp_path / "temp" / "jobs",
        cleanup_interval_seconds=3600,
    )


def test_replace_audio_command_uses_structured_ffmpeg_args(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    video = MediaAsset(
        display_name="Video",
        relative_path="assets/video.mp4",
        kind=MediaAssetKind.video,
        origin=MediaAssetOrigin.upload,
        size_bytes=1,
    )
    audio = MediaAsset(
        display_name="Audio",
        relative_path="assets/audio.mp3",
        kind=MediaAssetKind.audio,
        origin=MediaAssetOrigin.upload,
        size_bytes=1,
    )
    job = MediaEditJob(
        id="job-1",
        operation=MediaEditOperation.replace_audio,
        output_name="remux.mp4",
        options={"audio_offset_seconds": 1.5, "duration_mode": "shortest"},
    )

    command = MediaEditCommandBuilder(settings).build(
        job,
        [
            MediaEditInput(role="video", asset=video, path=tmp_path / "video.mp4"),
            MediaEditInput(role="audio", asset=audio, path=tmp_path / "audio.mp3"),
        ],
    )[0]

    assert command.args[:4] == ["ffmpeg", "-y", "-i", str(tmp_path / "video.mp4")]
    assert "-itsoffset" in command.args
    assert "1.5" in command.args
    assert command.args[-2:] == ["-shortest", str(command.outputs[0].path)]
    assert command.outputs[0].relative_path == "studio/job-1/remux.mp4"


def test_split_media_builds_two_copy_commands(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    source = MediaAsset(
        display_name="Source",
        relative_path="assets/source.mp4",
        kind=MediaAssetKind.video,
        origin=MediaAssetOrigin.upload,
        size_bytes=1,
    )
    job = MediaEditJob(
        id="job-2",
        operation=MediaEditOperation.split_media,
        output_name="source",
        options={"split_time_seconds": 42},
    )

    commands = MediaEditCommandBuilder(settings).build(
        job,
        [MediaEditInput(role="source", asset=source, path=tmp_path / "source.mp4")],
    )

    assert len(commands) == 2
    assert commands[0].args[-3:] == ["-c", "copy", str(commands[0].outputs[0].path)]
    assert commands[0].outputs[0].role == "part1"
    assert commands[1].args[2:4] == ["-ss", "42"]
    assert commands[1].outputs[0].role == "part2"


def test_concat_audio_command_writes_ordered_escaped_concat_list(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    first_path = tmp_path / "first track.mp3"
    second_path = tmp_path / "second's track.mp3"
    first = MediaAsset(
        display_name="First",
        relative_path="assets/first track.mp3",
        kind=MediaAssetKind.audio,
        origin=MediaAssetOrigin.upload,
        size_bytes=1,
    )
    second = MediaAsset(
        display_name="Second",
        relative_path="assets/second's track.mp3",
        kind=MediaAssetKind.audio,
        origin=MediaAssetOrigin.upload,
        size_bytes=1,
    )
    job = MediaEditJob(
        id="job-3",
        operation=MediaEditOperation.concat_audio,
        output_name="joined",
        options={"audio_format": "m4a"},
    )

    command = MediaEditCommandBuilder(settings).build(
        job,
        [
            MediaEditInput(role="audio", asset=first, path=first_path),
            MediaEditInput(role="audio", asset=second, path=second_path),
        ],
    )[0]

    concat_list = Path(command.args[7])
    escaped_first = str(first_path).replace("\\", "\\\\")
    escaped_second = str(second_path).replace("\\", "\\\\").replace("'", "\\'")
    assert command.args[:7] == ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i"]
    assert command.args[-4:] == ["-vn", "-c:a", "aac", str(command.outputs[0].path)]
    assert concat_list.read_text(encoding="utf-8").splitlines() == [
        f"file '{escaped_first}'",
        f"file '{escaped_second}'",
    ]
    assert command.outputs[0].relative_path == "studio/job-3/joined.m4a"


def test_concat_video_rejects_incompatible_metadata(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    first = MediaAsset(
        display_name="First",
        relative_path="assets/first.mp4",
        kind=MediaAssetKind.video,
        origin=MediaAssetOrigin.upload,
        size_bytes=1,
        width=1920,
        height=1080,
        video_codec="h264",
    )
    second = MediaAsset(
        display_name="Second",
        relative_path="assets/second.mp4",
        kind=MediaAssetKind.video,
        origin=MediaAssetOrigin.upload,
        size_bytes=1,
        width=1280,
        height=720,
        video_codec="h264",
    )
    job = MediaEditJob(
        id="job-4",
        operation=MediaEditOperation.concat_video,
        output_name="joined.mp4",
    )

    with pytest.raises(MediaEditIncompatibleInputs):
        MediaEditCommandBuilder(settings).build(
            job,
            [
                MediaEditInput(role="video", asset=first, path=tmp_path / "first.mp4"),
                MediaEditInput(role="video", asset=second, path=tmp_path / "second.mp4"),
            ],
        )


def test_create_remove_audio_job_runs_and_publishes_output(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    settings = _settings(tmp_path)
    source_file = settings.media_assets_dir / "video.mp4"
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(b"video")

    def fake_run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        Path(args[-1]).parent.mkdir(parents=True, exist_ok=True)
        Path(args[-1]).write_bytes(b"output")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.services.media_edit.subprocess.run", fake_run)

    app = create_app(settings)
    with TestClient(app) as client:
        with app.state.session_factory() as session:
            asset = MediaAsset(
                display_name="Video",
                relative_path="assets/video.mp4",
                kind=MediaAssetKind.video,
                origin=MediaAssetOrigin.upload,
                size_bytes=source_file.stat().st_size,
            )
            session.add(asset)
            session.commit()
            asset_id = asset.id

        response = client.post(
            "/api/studio/jobs",
            json={
                "operation": "remove_audio",
                "output_name": "muted.mp4",
                "inputs": [{"role": "video", "asset_id": asset_id}],
            },
        )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == MediaEditStatus.completed
    assert body["progress_percent"] == 100
    assert body["outputs"][0]["asset"]["relative_path"].startswith("studio/")


def test_create_concat_audio_job_runs_and_publishes_output(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    settings = _settings(tmp_path)
    first_file = settings.media_assets_dir / "first.mp3"
    second_file = settings.media_assets_dir / "second.mp3"
    first_file.parent.mkdir(parents=True)
    first_file.write_bytes(b"first")
    second_file.write_bytes(b"second")

    def fake_run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        Path(args[-1]).parent.mkdir(parents=True, exist_ok=True)
        Path(args[-1]).write_bytes(b"joined")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.services.media_edit.subprocess.run", fake_run)

    app = create_app(settings)
    with TestClient(app) as client:
        with app.state.session_factory() as session:
            first = MediaAsset(
                display_name="First",
                relative_path="assets/first.mp3",
                kind=MediaAssetKind.audio,
                origin=MediaAssetOrigin.upload,
                size_bytes=first_file.stat().st_size,
            )
            second = MediaAsset(
                display_name="Second",
                relative_path="assets/second.mp3",
                kind=MediaAssetKind.audio,
                origin=MediaAssetOrigin.upload,
                size_bytes=second_file.stat().st_size,
            )
            session.add_all([first, second])
            session.commit()
            first_id = first.id
            second_id = second.id

        response = client.post(
            "/api/studio/jobs",
            json={
                "operation": "concat_audio",
                "output_name": "joined.mp3",
                "audio_format": "mp3",
                "inputs": [
                    {"role": "audio", "asset_id": first_id},
                    {"role": "audio", "asset_id": second_id},
                ],
            },
        )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == MediaEditStatus.completed
    assert body["outputs"][0]["asset"]["display_name"] == "joined.mp3"
    assert body["outputs"][0]["asset"]["kind"] == MediaAssetKind.audio


def test_create_split_job_publishes_two_outputs(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    settings = _settings(tmp_path)
    source_file = settings.media_assets_dir / "video.mp4"
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(b"video")

    def fake_run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        Path(args[-1]).parent.mkdir(parents=True, exist_ok=True)
        Path(args[-1]).write_bytes(b"output")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.services.media_edit.subprocess.run", fake_run)

    app = create_app(settings)
    with TestClient(app) as client:
        with app.state.session_factory() as session:
            asset = MediaAsset(
                display_name="Video",
                relative_path="assets/video.mp4",
                kind=MediaAssetKind.video,
                origin=MediaAssetOrigin.upload,
                size_bytes=source_file.stat().st_size,
            )
            session.add(asset)
            session.commit()
            asset_id = asset.id

        response = client.post(
            "/api/studio/jobs",
            json={
                "operation": "split_media",
                "output_name": "split.mp4",
                "split_time_seconds": 12,
                "inputs": [{"role": "source", "asset_id": asset_id}],
            },
        )
        output_response = client.get(f"/api/studio/jobs/{response.json()['id']}/outputs/1/file")

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == MediaEditStatus.completed
    assert [output["role"] for output in body["outputs"]] == ["part1", "part2"]
    assert output_response.status_code == 200
    assert output_response.content == b"output"


def test_invalid_media_edit_input_fails_job(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    audio_file = settings.media_assets_dir / "audio.mp3"
    audio_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"audio")

    app = create_app(settings)
    with TestClient(app) as client:
        with app.state.session_factory() as session:
            asset = MediaAsset(
                display_name="Audio",
                relative_path="assets/audio.mp3",
                kind=MediaAssetKind.audio,
                origin=MediaAssetOrigin.upload,
                size_bytes=audio_file.stat().st_size,
            )
            session.add(asset)
            session.commit()
            asset_id = asset.id

        response = client.post(
            "/api/studio/jobs",
            json={
                "operation": "remove_audio",
                "output_name": "bad.mp4",
                "inputs": [{"role": "video", "asset_id": asset_id}],
            },
        )

    assert response.status_code == 202
    assert response.json()["status"] == MediaEditStatus.failed
    assert response.json()["error_code"] == "MEDIA_EDIT_INVALID_INPUT"


def test_incompatible_concat_video_returns_public_error(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    first_file = settings.media_assets_dir / "first.mp4"
    second_file = settings.media_assets_dir / "second.mp4"
    first_file.parent.mkdir(parents=True)
    first_file.write_bytes(b"first")
    second_file.write_bytes(b"second")

    app = create_app(settings)
    with TestClient(app) as client:
        with app.state.session_factory() as session:
            first = MediaAsset(
                display_name="First",
                relative_path="assets/first.mp4",
                kind=MediaAssetKind.video,
                origin=MediaAssetOrigin.upload,
                size_bytes=first_file.stat().st_size,
                width=1920,
                height=1080,
            )
            second = MediaAsset(
                display_name="Second",
                relative_path="assets/second.mp4",
                kind=MediaAssetKind.video,
                origin=MediaAssetOrigin.upload,
                size_bytes=second_file.stat().st_size,
                width=1280,
                height=720,
            )
            session.add_all([first, second])
            session.commit()
            first_id = first.id
            second_id = second.id

        response = client.post(
            "/api/studio/jobs",
            json={
                "operation": "concat_video",
                "output_name": "joined.mp4",
                "inputs": [
                    {"role": "video", "asset_id": first_id},
                    {"role": "video", "asset_id": second_id},
                ],
            },
        )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == MediaEditStatus.failed
    assert body["error_code"] == "MEDIA_EDIT_INCOMPATIBLE_INPUTS"
    assert body["error_message"] == "The selected media assets are not compatible for this edit."
    assert body["outputs"] == []


def test_list_studio_assets_returns_assets_when_probe_fails(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    source_file = settings.media_assets_dir / "video.mp4"
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(b"video")

    app = create_app(settings)
    with TestClient(app) as client:
        with app.state.session_factory() as session:
            asset = MediaAsset(
                display_name="Video",
                relative_path="assets/video.mp4",
                kind=MediaAssetKind.video,
                origin=MediaAssetOrigin.upload,
                size_bytes=source_file.stat().st_size,
            )
            session.add(asset)
            session.commit()

        response = client.get("/api/studio/assets")

    assert response.status_code == 200
    assert response.json()[0]["asset"]["display_name"] == "Video"
    assert response.json()[0]["probe"] is None
