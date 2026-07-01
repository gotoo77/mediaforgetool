import sqlite3
import tarfile

import pytest

from scripts.storage_backup import create_backup, restore_backup


def test_create_backup_copies_sqlite_jobs_assets_and_studio(tmp_path):
    database = tmp_path / "storage" / "mediaforgetool.db"
    jobs_dir = tmp_path / "storage" / "jobs"
    assets_dir = tmp_path / "storage" / "assets"
    studio_dir = tmp_path / "storage" / "studio"
    jobs_dir.mkdir(parents=True)
    assets_dir.mkdir()
    studio_dir.mkdir()
    output = tmp_path / "backup.tar.gz"

    with sqlite3.connect(database) as connection:
        connection.execute("create table sample (name text)")
        connection.execute("insert into sample values ('mediaforgetool')")
    (jobs_dir / "job-1").mkdir()
    (jobs_dir / "job-1" / "final.mp3").write_bytes(b"media")
    (assets_dir / "source.mp4").write_bytes(b"asset")
    (studio_dir / "edit-1").mkdir()
    (studio_dir / "edit-1" / "output.mp4").write_bytes(b"studio")

    backup_path = create_backup(database, jobs_dir, output)

    assert backup_path == output
    with tarfile.open(output, "r:gz") as archive:
        names = set(archive.getnames())
    assert "storage/mediaforgetool.db" in names
    assert "storage/jobs/job-1/final.mp3" in names
    assert "storage/assets/source.mp4" in names
    assert "storage/studio/edit-1/output.mp4" in names


def test_restore_backup_requires_force_for_non_empty_target(tmp_path):
    database = tmp_path / "source" / "storage" / "mediaforgetool.db"
    jobs_dir = tmp_path / "source" / "storage" / "jobs"
    jobs_dir.mkdir(parents=True)
    with sqlite3.connect(database) as connection:
        connection.execute("create table sample (name text)")
    backup = create_backup(database, jobs_dir, tmp_path / "backup.tar.gz")

    target = tmp_path / "storage"
    target.mkdir()
    (target / "existing.txt").write_text("keep")

    with pytest.raises(RuntimeError, match="Target storage is not empty"):
        restore_backup(backup, target)


def test_restore_backup_restores_database_and_jobs(tmp_path):
    database = tmp_path / "source" / "storage" / "mediaforgetool.db"
    jobs_dir = tmp_path / "source" / "storage" / "jobs"
    assets_dir = tmp_path / "source" / "storage" / "assets"
    studio_dir = tmp_path / "source" / "storage" / "studio"
    jobs_dir.mkdir(parents=True)
    assets_dir.mkdir()
    studio_dir.mkdir()
    with sqlite3.connect(database) as connection:
        connection.execute("create table sample (name text)")
        connection.execute("insert into sample values ('restored')")
    (jobs_dir / "job-1").mkdir()
    (jobs_dir / "job-1" / "final.mp4").write_bytes(b"video")
    (assets_dir / "source.mp4").write_bytes(b"asset")
    (studio_dir / "edit-1").mkdir()
    (studio_dir / "edit-1" / "output.mp4").write_bytes(b"studio")
    backup = create_backup(database, jobs_dir, tmp_path / "backup.tar.gz")

    target = tmp_path / "target-storage"
    restore_backup(backup, target)

    with sqlite3.connect(target / "mediaforgetool.db") as connection:
        value = connection.execute("select name from sample").fetchone()[0]
    assert value == "restored"
    assert (target / "jobs" / "job-1" / "final.mp4").read_bytes() == b"video"
    assert (target / "assets" / "source.mp4").read_bytes() == b"asset"
    assert (target / "studio" / "edit-1" / "output.mp4").read_bytes() == b"studio"
