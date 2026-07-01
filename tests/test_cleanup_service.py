import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.init_db import create_schema
from app.db.session import build_engine, build_session_factory
from app.models.job import DownloadJob, JobStatus, OutputFormat
from app.models.studio import (
    MediaAsset,
    MediaAssetKind,
    MediaAssetOrigin,
    MediaEditJob,
    MediaEditJobOutput,
    MediaEditOperation,
    MediaEditStatus,
)
from app.services.cleanup_service import CleanupService
from app.services.storage_service import StorageService


def test_cleanup_preserves_resumable_temp_dirs(tmp_path: Path) -> None:
    settings, session_factory, storage = build_cleanup_dependencies(tmp_path)
    with session_factory() as session:
        session.add_all(
            [
                DownloadJob(
                    id="paused",
                    source_url="https://media.example/paused",
                    requested_format=OutputFormat.mp3,
                    status=JobStatus.paused,
                ),
                DownloadJob(
                    id="interrupted",
                    source_url="https://media.example/interrupted",
                    requested_format=OutputFormat.mp4,
                    status=JobStatus.interrupted,
                ),
                DownloadJob(
                    id="failed",
                    source_url="https://media.example/failed",
                    requested_format=OutputFormat.mp4,
                    status=JobStatus.failed,
                ),
            ]
        )
        session.commit()
    for job_id in ("paused", "interrupted", "failed", "orphan"):
        temp_dir = settings.temp_dir / job_id
        temp_dir.mkdir(parents=True)
        (temp_dir / "media.part").write_bytes(b"partial")
        age_directory(temp_dir)

    CleanupService(settings, session_factory, storage).cleanup_now()

    assert (settings.temp_dir / "paused").exists()
    assert (settings.temp_dir / "interrupted").exists()
    assert not (settings.temp_dir / "failed").exists()
    assert not (settings.temp_dir / "orphan").exists()


def test_cleanup_removes_expired_studio_outputs_and_orphans(tmp_path: Path) -> None:
    settings, session_factory, storage = build_cleanup_dependencies(tmp_path)
    expired_dir = settings.media_studio_dir / "expired-studio"
    active_dir = settings.media_studio_dir / "active-studio"
    orphan_dir = settings.media_studio_dir / "orphan-studio"
    for directory in (expired_dir, active_dir, orphan_dir):
        directory.mkdir(parents=True)
        (directory / "media.mp4").write_bytes(b"media")
        age_directory(directory)

    with session_factory() as session:
        expired_asset = MediaAsset(
            display_name="Expired",
            relative_path="studio/expired-studio/media.mp4",
            kind=MediaAssetKind.video,
            origin=MediaAssetOrigin.studio_output,
            size_bytes=5,
        )
        expired_job = MediaEditJob(
            id="expired-studio",
            operation=MediaEditOperation.remove_audio,
            status=MediaEditStatus.completed,
            output_name="expired.mp4",
            output_asset=expired_asset,
            completed_at=datetime.now(UTC) - timedelta(hours=3),
            updated_at=datetime.now(UTC) - timedelta(hours=3),
        )
        expired_job.outputs.append(
            MediaEditJobOutput(
                asset=expired_asset,
                role="output",
                position=0,
            )
        )
        active_job = MediaEditJob(
            id="active-studio",
            operation=MediaEditOperation.remove_audio,
            status=MediaEditStatus.processing,
            output_name="active.mp4",
        )
        session.add_all([expired_job, active_job])
        session.commit()

    CleanupService(settings, session_factory, storage).cleanup_now()

    assert not expired_dir.exists()
    assert active_dir.exists()
    assert not orphan_dir.exists()
    with session_factory() as session:
        assert session.get(MediaEditJob, "expired-studio") is None
        assert session.get(MediaEditJob, "active-studio") is not None


def age_directory(path: Path) -> None:
    old_timestamp = time.time() - 3 * 3600
    os.utime(path, (old_timestamp, old_timestamp))


def build_cleanup_dependencies(
    tmp_path: Path,
) -> tuple[Settings, sessionmaker[Session], StorageService]:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'cleanup.db'}",
        storage_dir=tmp_path / "storage" / "jobs",
        media_assets_dir=tmp_path / "storage" / "assets",
        media_studio_dir=tmp_path / "storage" / "studio",
        temp_dir=tmp_path / "temp" / "jobs",
        temp_retention_hours=1,
        output_retention_hours=1,
    )
    storage = StorageService(settings)
    storage.prepare_directories()
    engine = build_engine(settings)
    create_schema(engine)
    return settings, build_session_factory(engine), storage
