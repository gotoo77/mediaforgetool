import re
import shutil
from pathlib import Path

from app.core.config import Settings
from app.core.exceptions import MediaTooLarge

_UNSAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")


class StorageService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def prepare_directories(self) -> None:
        self.settings.storage_dir.mkdir(parents=True, exist_ok=True)
        self.settings.media_assets_dir.mkdir(parents=True, exist_ok=True)
        self.settings.media_studio_dir.mkdir(parents=True, exist_ok=True)
        self.settings.temp_dir.mkdir(parents=True, exist_ok=True)

    def temp_job_dir(self, job_id: str) -> Path:
        directory = self.settings.temp_dir / job_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def output_job_dir(self, job_id: str) -> Path:
        directory = self.settings.storage_dir / job_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def remove_temp_job_dir(self, job_id: str) -> None:
        shutil.rmtree(self.settings.temp_dir / job_id, ignore_errors=True)

    def publish_file(self, job_id: str, source: Path, title: str | None) -> tuple[Path, str, int]:
        size = source.stat().st_size
        if size > self.settings.max_output_size_bytes:
            raise MediaTooLarge

        extension = source.suffix.lower()
        download_name = f"{self._safe_stem(title or 'mediaforgetool-download')}{extension}"
        target = self.output_job_dir(job_id) / f"final{extension}"
        if target.exists():
            target.unlink()
        shutil.move(str(source), target)
        return target, download_name, size

    def remove_output_job_dir(self, job_id: str) -> None:
        shutil.rmtree(self.settings.storage_dir / job_id, ignore_errors=True)

    @staticmethod
    def _safe_stem(value: str) -> str:
        stem = _UNSAFE_NAME.sub("_", value).strip(" ._")
        return stem[:120] or "mediaforgetool-download"
