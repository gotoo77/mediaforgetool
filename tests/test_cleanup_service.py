import os
import time
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.init_db import create_schema
from app.db.session import build_engine, build_session_factory
from app.models.job import DownloadJob, JobStatus, OutputFormat
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


def age_directory(path: Path) -> None:
    old_timestamp = time.time() - 3 * 3600
    os.utime(path, (old_timestamp, old_timestamp))


def build_cleanup_dependencies(
    tmp_path: Path,
) -> tuple[Settings, sessionmaker[Session], StorageService]:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'cleanup.db'}",
        storage_dir=tmp_path / "storage",
        temp_dir=tmp_path / "temp",
        temp_retention_hours=1,
    )
    storage = StorageService(settings)
    storage.prepare_directories()
    engine = build_engine(settings)
    create_schema(engine)
    return settings, build_session_factory(engine), storage
