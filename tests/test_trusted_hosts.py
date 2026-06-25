from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_allowed_host_reaches_app(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path, ["allowed.local"]))

    with TestClient(app) as client:
        response = client.get("/healthz", headers={"Host": "allowed.local"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_disallowed_host_is_rejected(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path, ["allowed.local"]))

    with TestClient(app) as client:
        response = client.get("/healthz", headers={"Host": "unexpected.local"})

    assert response.status_code == 400
    assert response.text == "Invalid host header"


def test_allowed_hosts_can_be_comma_separated() -> None:
    settings = Settings(allowed_hosts="mediaforgetool.local, localhost")

    assert settings.allowed_hosts == ["mediaforgetool.local", "localhost"]


def _settings(tmp_path: Path, allowed_hosts: list[str]) -> Settings:
    return Settings(
        allowed_hosts=allowed_hosts,
        database_url=f"sqlite:///{tmp_path / 'mediaforgetool.db'}",
        storage_dir=tmp_path / "storage",
        temp_dir=tmp_path / "temp",
        cleanup_interval_seconds=3600,
    )
