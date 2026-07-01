import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.exceptions import MediaAssetUnavailable, MediaProbeFailed
from app.main import create_app
from app.models.studio import MediaAsset, MediaAssetKind, MediaAssetOrigin
from app.services.media_probe import MediaProbeService


def test_media_probe_parses_ffprobe_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    media = tmp_path / "storage" / "assets" / "sample.mp4"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"fake")
    settings = Settings(
        storage_dir=tmp_path / "storage" / "jobs",
        media_assets_dir=tmp_path / "storage" / "assets",
        media_studio_dir=tmp_path / "storage" / "studio",
    )

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="""{
              "format": {
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                "duration": "12.500000",
                "size": "2048",
                "bit_rate": "320000"
              },
              "streams": [
                {
                  "index": 0,
                  "codec_type": "video",
                  "codec_name": "h264",
                  "duration": "12.5",
                  "bit_rate": "250000",
                  "width": 1920,
                  "height": 1080
                },
                {
                  "index": 1,
                  "codec_type": "audio",
                  "codec_name": "aac",
                  "duration": "12.5",
                  "bit_rate": "70000",
                  "channels": 2,
                  "sample_rate": "48000"
                }
              ]
            }""",
            stderr="",
        )

    monkeypatch.setattr("app.services.media_probe.subprocess.run", fake_run)

    probe = MediaProbeService(settings).inspect_asset_path("assets/sample.mp4")

    assert probe.duration_seconds == 12.5
    assert probe.container_format == "mov,mp4,m4a,3gp,3g2,mj2"
    assert probe.size_bytes == 2048
    assert probe.has_audio is True
    assert probe.has_video is True
    assert probe.video_streams[0].codec_name == "h264"
    assert probe.video_streams[0].width == 1920
    assert probe.audio_streams[0].codec_name == "aac"
    assert probe.audio_streams[0].sample_rate == 48000


def test_media_probe_rejects_path_outside_managed_storage(tmp_path: Path) -> None:
    settings = Settings(
        storage_dir=tmp_path / "storage" / "jobs",
        media_assets_dir=tmp_path / "storage" / "assets",
        media_studio_dir=tmp_path / "storage" / "studio",
    )

    with pytest.raises(MediaAssetUnavailable):
        MediaProbeService(settings).inspect_asset_path("../outside.mp4")


def test_media_probe_turns_ffprobe_failure_into_stable_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    media = tmp_path / "storage" / "assets" / "bad.mp4"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"fake")
    settings = Settings(
        storage_dir=tmp_path / "storage" / "jobs",
        media_assets_dir=tmp_path / "storage" / "assets",
        media_studio_dir=tmp_path / "storage" / "studio",
    )

    monkeypatch.setattr(
        "app.services.media_probe.subprocess.run",
        lambda *_, **__: subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="bad",
        ),
    )

    with pytest.raises(MediaProbeFailed):
        MediaProbeService(settings).inspect_asset_path("assets/bad.mp4")


def test_inspect_asset_endpoint_returns_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'mediaforgetool.db'}",
        storage_dir=tmp_path / "storage" / "jobs",
        media_assets_dir=tmp_path / "storage" / "assets",
        media_studio_dir=tmp_path / "storage" / "studio",
        temp_dir=tmp_path / "temp" / "jobs",
        cleanup_interval_seconds=3600,
    )
    media = settings.media_assets_dir / "sample.mp4"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"fake")

    monkeypatch.setattr(
        "app.services.media_probe.subprocess.run",
        lambda *_, **__: subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='{"format":{"format_name":"mp4","duration":"4","size":"4"},"streams":[]}',
            stderr="",
        ),
    )

    app = create_app(settings)
    with TestClient(app) as client:
        with app.state.session_factory() as session:
            asset = MediaAsset(
                display_name="Sample",
                relative_path="assets/sample.mp4",
                kind=MediaAssetKind.video,
                origin=MediaAssetOrigin.upload,
                size_bytes=4,
            )
            session.add(asset)
            session.commit()
            asset_id = asset.id

        response = client.get(f"/api/studio/assets/{asset_id}/inspect")

    assert response.status_code == 200
    body = response.json()
    assert body["asset"]["id"] == asset_id
    assert body["probe"]["duration_seconds"] == 4
    assert body["probe"]["container_format"] == "mp4"


def test_inspect_asset_endpoint_returns_not_found(app_client: tuple[TestClient, object]) -> None:
    client, _ = app_client

    response = client.get("/api/studio/assets/missing/inspect")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "MEDIA_ASSET_UNAVAILABLE"
