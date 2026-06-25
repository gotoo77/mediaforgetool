from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import Settings
from app.main import create_app
from app.models.job import DownloadJob
from app.models.playlist import ImportedPlaylist, PlaylistStatus, Track

FIXTURES = Path(__file__).parent / "fixtures" / "shazam"


def test_import_shazam_csv_persists_playlist_without_jobs(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client

    response = client.post(
        "/api/playlists/import",
        data={"importer_key": "shazam_csv"},
        files={
            "file": (
                "shazam.csv",
                (FIXTURES / "partial_semicolon.csv").read_bytes(),
                "text/csv",
            )
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["playlist"]["status"] == "partial"
    assert payload["playlist"]["track_count"] == 2
    assert payload["playlist"]["rejected_row_count"] == 2
    assert [track["title"] for track in payload["tracks"]] == [
        "Song One (Live)",
        "Deuxième chanson",
    ]
    assert [issue["code"] for issue in payload["issues"]] == [
        "TRACK_METADATA_MISSING",
        "DUPLICATE_TRACK",
    ]

    session_factory = client.app.state.session_factory
    with session_factory() as session:
        playlist = session.scalar(select(ImportedPlaylist))
        assert playlist is not None
        assert playlist.status is PlaylistStatus.partial
        assert session.scalar(select(func.count()).select_from(Track)) == 2
        assert session.scalar(select(func.count()).select_from(DownloadJob)) == 0


def test_import_rejects_unsupported_file_type(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client

    response = client.post(
        "/api/playlists/import",
        files={"file": ("tracks.txt", b"Title,Artist\nOne,A\n", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "IMPORT_FORMAT_UNSUPPORTED"


def test_import_rejects_file_above_instance_limit(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    max_bytes = client.app.state.settings.playlist_import_max_bytes

    response = client.post(
        "/api/playlists/import",
        files={"file": ("large.csv", b"x" * (max_bytes + 1), "text/csv")},
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "IMPORT_FILE_TOO_LARGE"


def test_import_rejects_unknown_importer(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client

    response = client.post(
        "/api/playlists/import",
        data={"importer_key": "missing"},
        files={"file": ("tracks.csv", b"Title,Artist\nOne,A\n", "text/csv")},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "PLAYLIST_IMPORTER_UNKNOWN"


def test_import_rejects_csv_without_valid_tracks(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client

    response = client.post(
        "/api/playlists/import",
        files={"file": ("tracks.csv", b"Title,Artist\n,Missing\n", "text/csv")},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "IMPORT_FILE_INVALID"


def test_import_rejects_more_rows_than_instance_limit(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'mediaforgetool.db'}",
        storage_dir=tmp_path / "storage",
        temp_dir=tmp_path / "temp",
        playlist_import_max_tracks=2,
        cleanup_interval_seconds=3600,
    )

    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/playlists/import",
            files={
                "file": (
                    "tracks.csv",
                    b"Title,Artist\nOne,A\nTwo,B\nThree,C\n",
                    "text/csv",
                )
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "IMPORT_TOO_MANY_ROWS"
