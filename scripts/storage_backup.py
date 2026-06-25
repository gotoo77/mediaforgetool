import argparse
import shutil
import sqlite3
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_DATABASE = Path("storage/mediaforgetool.db")
DEFAULT_JOBS_DIR = Path("storage/jobs")


def create_backup(database: Path, jobs_dir: Path, output: Path | None = None) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = output or Path(f"mediaforgetool-backup-{timestamp}.tar.gz")
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_name:
        temp_dir = Path(temp_name)
        payload_dir = temp_dir / "storage"
        payload_dir.mkdir()

        if database.exists():
            _backup_sqlite(database, payload_dir / "mediaforgetool.db")
        if jobs_dir.exists():
            shutil.copytree(jobs_dir, payload_dir / "jobs")
        else:
            (payload_dir / "jobs").mkdir()

        with tarfile.open(backup_path, "w:gz") as archive:
            archive.add(payload_dir, arcname="storage")

    return backup_path


def restore_backup(archive_path: Path, target_storage: Path, force: bool = False) -> None:
    if not archive_path.is_file():
        raise RuntimeError(f"Backup archive not found: {archive_path}")
    if target_storage.exists() and any(target_storage.iterdir()) and not force:
        raise RuntimeError("Target storage is not empty. Re-run with --force to replace it.")

    with tempfile.TemporaryDirectory() as temp_name:
        temp_dir = Path(temp_name)
        with tarfile.open(archive_path, "r:gz") as archive:
            _safe_extract(archive, temp_dir)

        extracted_storage = temp_dir / "storage"
        if not extracted_storage.is_dir():
            raise RuntimeError("Backup archive does not contain a storage directory.")

        if target_storage.exists():
            shutil.rmtree(target_storage)
        shutil.copytree(extracted_storage, target_storage)


def _backup_sqlite(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(destination) as destination_connection:
            source_connection.backup(destination_connection)


def _safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    destination = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if destination not in target.parents and target != destination:
            raise RuntimeError(f"Unsafe path in backup archive: {member.name}")
    archive.extractall(destination)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backup or restore MediaForgeTool storage.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a compressed storage backup.")
    create.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    create.add_argument("--jobs-dir", type=Path, default=DEFAULT_JOBS_DIR)
    create.add_argument("--output", type=Path)

    restore = subparsers.add_parser("restore", help="Restore a compressed storage backup.")
    restore.add_argument("archive", type=Path)
    restore.add_argument("--target-storage", type=Path, default=Path("storage"))
    restore.add_argument("--force", action="store_true")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "create":
        backup_path = create_backup(args.database, args.jobs_dir, args.output)
        print(backup_path)
        return
    restore_backup(args.archive, args.target_storage, args.force)


if __name__ == "__main__":
    main()
