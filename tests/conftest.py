from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


class FakeRunner:
    def __init__(self) -> None:
        self.jobs: list[str] = []

    def enqueue(self, job_id: str) -> bool:
        self.jobs.append(job_id)
        return True


@pytest.fixture
def app_client(tmp_path: Path) -> Iterator[tuple[TestClient, FakeRunner]]:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'mediaforgetool.db'}",
        storage_dir=tmp_path / "storage",
        temp_dir=tmp_path / "temp",
        cleanup_interval_seconds=3600,
    )
    app = create_app(settings)
    fake_runner = FakeRunner()
    with TestClient(app) as client:
        app.state.job_runner = fake_runner
        yield client, fake_runner
