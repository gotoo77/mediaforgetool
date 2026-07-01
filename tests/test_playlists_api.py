import logging
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import Settings
from app.core.exceptions import MediaSearchNoResults
from app.main import create_app
from app.models.job import DownloadJob
from app.models.playlist import DownloadQueueItem, ImportedPlaylist, PlaylistStatus, Track
from app.services.media_search import MediaSearchProviderRegistry, SearchCandidate, TrackQuery

FIXTURES = Path(__file__).parent / "fixtures" / "shazam"


class FakeSearchProvider:
    key = "fake"

    def __init__(
        self,
        candidates: list[SearchCandidate] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.candidates = candidates or []
        self.error = error
        self.searches: list[TrackQuery] = []

    def search(self, track: TrackQuery, *, limit: int) -> list[SearchCandidate]:
        self.searches.append(track)
        if self.error:
            raise self.error
        return self.candidates[:limit]


class RejectingRunner:
    def enqueue(self, job_id: str) -> bool:
        return False


class FirstOnlyRunner:
    def __init__(self) -> None:
        self.jobs: list[str] = []

    def enqueue(self, job_id: str) -> bool:
        self.jobs.append(job_id)
        return len(self.jobs) == 1


class MixedSearchProvider:
    key = "mixed"

    def __init__(self) -> None:
        self.searches: list[TrackQuery] = []

    def search(self, track: TrackQuery, *, limit: int) -> list[SearchCandidate]:
        self.searches.append(track)
        if track.title.startswith("Deuxième"):
            raise MediaSearchNoResults()
        return [
            SearchCandidate(
                provider_key=self.key,
                provider_media_id=f"candidate-{track.track_id}",
                source_url=f"https://example.com/{track.track_id}",
                title=f"{track.artist} - {track.title}",
                rank=0,
            )
        ][:limit]


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


def test_import_plain_text_persists_playlist_without_jobs(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client

    response = client.post(
        "/api/playlists/import",
        data={"importer_key": "text"},
        files={
            "file": (
                "favorites.txt",
                (
                    b"# comment\n"
                    b"M83 - Midnight City\n"
                    b"Invalid line\n"
                    b"Daft Punk - Harder Better Faster Stronger\n"
                ),
                "text/plain",
            )
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["playlist"]["name"] == "favorites"
    assert payload["playlist"]["status"] == "partial"
    assert payload["playlist"]["track_count"] == 2
    assert [track["artist"] for track in payload["tracks"]] == ["M83", "Daft Punk"]
    assert [issue["code"] for issue in payload["issues"]] == [
        "TEXT_TRACK_FORMAT_INVALID"
    ]

    session_factory = client.app.state.session_factory
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Track)) == 2
        assert session.scalar(select(func.count()).select_from(DownloadJob)) == 0


def test_import_logs_rejected_rows_without_raw_payload(
    app_client: tuple[TestClient, object],
    caplog,
) -> None:
    client, _ = app_client
    caplog.set_level(logging.INFO)

    response = client.post(
        "/api/playlists/import",
        files={
            "file": (
                "partial_semicolon.csv",
                (FIXTURES / "partial_semicolon.csv").read_bytes(),
                "text/csv",
            )
        },
    )

    assert response.status_code == 201
    row_events = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "playlist_import_row_rejected"
    ]
    assert [record.error_code for record in row_events] == [
        "TRACK_METADATA_MISSING",
        "DUPLICATE_TRACK",
    ]
    assert [record.row_number for record in row_events] == [3, 4]
    messages = "\n".join(record.getMessage() for record in row_events)
    assert "Missing Title" not in messages
    assert "Song One" not in messages


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


def test_list_playlists_returns_recent_imports(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    first = _import_fixture(client, "basic.csv")
    second = _import_fixture(client, "partial_semicolon.csv")

    response = client.get("/api/playlists?limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["limit"] == 1
    assert payload["offset"] == 0
    assert [item["id"] for item in payload["items"]] == [second["playlist"]["id"]]
    assert first["playlist"]["id"] != second["playlist"]["id"]


def test_get_playlist_returns_paged_tracks_and_persisted_issues(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    imported = _import_fixture(client, "partial_semicolon.csv")

    response = client.get(f"/api/playlists/{imported['playlist']['id']}?limit=1&offset=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["playlist"]["id"] == imported["playlist"]["id"]
    assert payload["total_tracks"] == 2
    assert payload["limit"] == 1
    assert payload["offset"] == 1
    assert [track["title"] for track in payload["tracks"]] == ["Deuxième chanson"]
    assert [issue["code"] for issue in payload["issues"]] == [
        "TRACK_METADATA_MISSING",
        "DUPLICATE_TRACK",
    ]
    assert payload["issues"][0]["row_number"] == 3
    assert payload["issues"][0]["message"] == "Artist and title are required."


def test_get_playlist_filters_tracks_by_query_and_resolution_status(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    imported = _import_fixture(client, "basic.csv")
    track = imported["tracks"][0]
    registry = MediaSearchProviderRegistry()
    registry.register(
        FakeSearchProvider(
            [
                SearchCandidate(
                    provider_key="fake",
                    provider_media_id="candidate-1",
                    source_url="https://example.com/candidate-1",
                    title="M83 - Midnight City",
                    rank=0,
                )
            ]
        )
    )
    client.app.state.media_search_provider_registry = registry
    resolve_response = client.post(
        f"/api/playlists/{imported['playlist']['id']}/tracks/{track['id']}/resolve",
        json={"provider_key": "fake"},
    )
    assert resolve_response.status_code == 200

    query_response = client.get(
        f"/api/playlists/{imported['playlist']['id']}?q=midnight&limit=25"
    )
    resolved_response = client.get(
        f"/api/playlists/{imported['playlist']['id']}?resolution_status=resolved&limit=25"
    )
    pending_response = client.get(
        f"/api/playlists/{imported['playlist']['id']}?resolution_status=pending&limit=25"
    )

    assert query_response.status_code == 200
    assert query_response.json()["total_tracks"] == 1
    assert [item["title"] for item in query_response.json()["tracks"]] == [
        "Midnight City"
    ]
    assert resolved_response.status_code == 200
    assert [item["id"] for item in resolved_response.json()["tracks"]] == [track["id"]]
    assert pending_response.status_code == 200
    assert pending_response.json()["total_tracks"] == 1
    assert pending_response.json()["tracks"][0]["id"] != track["id"]


def test_get_playlist_sorts_filtered_tracks(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    imported = _import_fixture(client, "basic.csv")

    by_artist = client.get(
        f"/api/playlists/{imported['playlist']['id']}?sort=artist&direction=asc"
    )
    by_title_desc = client.get(
        f"/api/playlists/{imported['playlist']['id']}?sort=title&direction=desc"
    )

    assert by_artist.status_code == 200
    assert [track["artist"] for track in by_artist.json()["tracks"]] == ["Grimes", "M83"]
    assert by_title_desc.status_code == 200
    assert [track["title"] for track in by_title_desc.json()["tracks"]] == [
        "Midnight City",
        "Genesis",
    ]


def test_update_playlist_track_normalizes_metadata_and_resets_unqueued_status(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    imported = _import_fixture(client, "basic.csv")
    track = imported["tracks"][0]
    registry = MediaSearchProviderRegistry()
    registry.register(
        FakeSearchProvider(
            [
                SearchCandidate(
                    provider_key="fake",
                    provider_media_id="candidate-1",
                    source_url="https://example.com/candidate-1",
                    title="M83 - Midnight City",
                    rank=0,
                )
            ]
        )
    )
    client.app.state.media_search_provider_registry = registry
    resolve_response = client.post(
        f"/api/playlists/{imported['playlist']['id']}/tracks/{track['id']}/resolve",
        json={"provider_key": "fake"},
    )
    assert resolve_response.status_code == 200

    response = client.patch(
        f"/api/playlists/{imported['playlist']['id']}/tracks/{track['id']}",
        json={
            "artist": "  M83  ",
            "title": "  Midnight City Remix  ",
            "album": "  Hurry Up  ",
            "isrc": " FRU701100120 ",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["artist"] == "M83"
    assert payload["title"] == "Midnight City Remix"
    assert payload["album"] == "Hurry Up"
    assert payload["isrc"] == "FRU701100120"
    assert payload["resolution_status"] == "pending"

    detail = client.get(f"/api/playlists/{imported['playlist']['id']}?q=remix").json()
    assert detail["total_tracks"] == 1
    assert detail["tracks"][0]["id"] == track["id"]


def test_update_playlist_track_returns_not_found(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    imported = _import_fixture(client, "basic.csv")

    response = client.patch(
        f"/api/playlists/{imported['playlist']['id']}/tracks/missing",
        json={"artist": "Artist", "title": "Title"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "TRACK_NOT_FOUND"


def test_get_playlist_returns_not_found(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client

    response = client.get("/api/playlists/missing")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PLAYLIST_NOT_FOUND"


def test_resolve_track_persists_candidates_without_jobs(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    imported = _import_fixture(client, "basic.csv")
    track = imported["tracks"][0]
    provider = FakeSearchProvider(
        [
            SearchCandidate(
                provider_key="fake",
                provider_media_id="candidate-1",
                source_url="https://example.com/candidate-1",
                title="M83 - Midnight City",
                creator="Channel",
                duration_seconds=244,
                thumbnail_url="https://example.com/thumb.jpg",
                rank=0,
                match_score=0.8,
            )
        ]
    )
    registry = MediaSearchProviderRegistry()
    registry.register(provider)
    client.app.state.media_search_provider_registry = registry

    response = client.post(
        f"/api/playlists/{imported['playlist']['id']}/tracks/{track['id']}/resolve",
        json={"provider_key": "fake", "limit": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["track"]["resolution_status"] == "resolved"
    assert payload["candidates"][0]["provider_media_id"] == "candidate-1"
    assert provider.searches == [
        TrackQuery(
            track_id=track["id"],
            artist="M83",
            title="Midnight City",
            album="Hurry Up We Are Dreaming",
            duration_seconds=244,
        )
    ]

    detail = client.get(f"/api/playlists/{imported['playlist']['id']}").json()
    assert detail["tracks"][0]["candidates"][0]["provider_media_id"] == "candidate-1"
    session_factory = client.app.state.session_factory
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(DownloadJob)) == 0


def test_resolve_track_maps_no_results_to_public_error(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    imported = _import_fixture(client, "basic.csv")
    track = imported["tracks"][0]
    registry = MediaSearchProviderRegistry()
    registry.register(FakeSearchProvider(error=MediaSearchNoResults()))
    client.app.state.media_search_provider_registry = registry

    response = client.post(
        f"/api/playlists/{imported['playlist']['id']}/tracks/{track['id']}/resolve",
        json={"provider_key": "fake", "limit": 5},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "MEDIA_SEARCH_NO_RESULTS"


def test_resolve_track_returns_not_found(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    imported = _import_fixture(client, "basic.csv")

    response = client.post(
        f"/api/playlists/{imported['playlist']['id']}/tracks/missing/resolve",
        json={"provider_key": "fake", "limit": 5},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "TRACK_NOT_FOUND"


def test_queue_candidate_creates_job_and_queue_item(
    app_client: tuple[TestClient, object],
) -> None:
    client, runner = app_client
    resolved = _resolve_fixture_candidate(client)

    response = client.post(
        (
            f"/api/playlists/{resolved['playlist_id']}/tracks/{resolved['track_id']}"
            f"/candidates/{resolved['candidate_id']}/queue"
        ),
        json={"format": "mp3", "audio_bitrate_kbps": 192},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["queue_item"]["track_id"] == resolved["track_id"]
    assert payload["queue_item"]["candidate_id"] == resolved["candidate_id"]
    assert payload["queue_item"]["status"] == "submitted"
    assert payload["queue_item"]["requested_format"] == "mp3"
    assert payload["job"]["source_url"] == "https://example.com/candidate-1"
    assert runner.jobs == [payload["job"]["id"]]

    detail = client.get(f"/api/playlists/{resolved['playlist_id']}").json()
    assert detail["tracks"][0]["queue_items"][0]["download_job_id"] == payload["job"]["id"]
    session_factory = client.app.state.session_factory
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(DownloadJob)) == 1
        assert session.scalar(select(func.count()).select_from(DownloadQueueItem)) == 1


def test_queue_candidate_logs_selection_and_job_submission(
    app_client: tuple[TestClient, object],
    caplog,
) -> None:
    client, _ = app_client
    caplog.set_level(logging.INFO)
    resolved = _resolve_fixture_candidate(client)

    response = client.post(
        (
            f"/api/playlists/{resolved['playlist_id']}/tracks/{resolved['track_id']}"
            f"/candidates/{resolved['candidate_id']}/queue"
        ),
        json={"format": "mp3", "audio_bitrate_kbps": 192},
    )

    assert response.status_code == 202
    payload = response.json()
    selection_events = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "media_candidate_selected"
    ]
    assert len(selection_events) == 1
    event = selection_events[0]
    assert event.playlist_id == resolved["playlist_id"]
    assert event.track_id == resolved["track_id"]
    assert event.candidate_id == resolved["candidate_id"]
    assert event.job_id == payload["job"]["id"]
    assert event.provider == "fake"

    submitted_events = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "job_submitted"
    ]
    assert submitted_events[-1].job_id == payload["job"]["id"]


def test_queue_candidate_is_idempotent_for_repeated_request(
    app_client: tuple[TestClient, object],
) -> None:
    client, runner = app_client
    resolved = _resolve_fixture_candidate(client)
    url = (
        f"/api/playlists/{resolved['playlist_id']}/tracks/{resolved['track_id']}"
        f"/candidates/{resolved['candidate_id']}/queue"
    )

    first = client.post(url, json={"format": "mp4", "resolution": 720})
    second = client.post(url, json={"format": "mp4", "resolution": 720})

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["queue_item"]["id"] == second.json()["queue_item"]["id"]
    assert len(runner.jobs) == 1


def test_queue_candidate_maps_full_queue_to_existing_error(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    client.app.state.job_runner = RejectingRunner()
    resolved = _resolve_fixture_candidate(client)

    response = client.post(
        (
            f"/api/playlists/{resolved['playlist_id']}/tracks/{resolved['track_id']}"
            f"/candidates/{resolved['candidate_id']}/queue"
        ),
        json={"format": "mp4", "resolution": 720},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "QUEUE_FULL"


def test_queue_candidate_rejects_candidate_outside_track(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    resolved = _resolve_fixture_candidate(client)

    response = client.post(
        (
            f"/api/playlists/{resolved['playlist_id']}/tracks/{resolved['track_id']}"
            "/candidates/missing/queue"
        ),
        json={"format": "mp3"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CANDIDATE_NOT_FOUND"


def test_resolve_batch_uses_bounded_concurrency_and_keeps_track_errors_local(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    imported = _import_fixture(client, "partial_semicolon.csv")
    provider = MixedSearchProvider()
    registry = MediaSearchProviderRegistry()
    registry.register(provider)
    client.app.state.media_search_provider_registry = registry
    client.app.state.settings.media_resolution_max_concurrency = 2

    response = client.post(
        f"/api/playlists/{imported['playlist']['id']}/tracks/resolve-batch",
        json={
            "provider_key": "mixed",
            "limit": 5,
            "max_concurrency": 8,
            "tracks": [{"track_id": track["id"]} for track in imported["tracks"]],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["requested_count"] == 2
    assert payload["completed_count"] == 2
    assert payload["failed_count"] == 0
    assert payload["concurrency_limit"] == 2
    assert sorted(result["status"] for result in payload["results"]) == [
        "no_match",
        "resolved",
    ]

    detail = client.get(f"/api/playlists/{imported['playlist']['id']}").json()
    statuses = {track["title"]: track["resolution_status"] for track in detail["tracks"]}
    assert statuses["Song One (Live)"] == "resolved"
    assert statuses["Deuxième chanson"] == "no_match"


def test_queue_batch_stops_on_queue_full_and_reports_skipped_tracks(
    app_client: tuple[TestClient, object],
) -> None:
    client, _ = app_client
    client.app.state.job_runner = FirstOnlyRunner()
    imported = _import_fixture(client, "basic.csv")
    registry = MediaSearchProviderRegistry()
    registry.register(
        FakeSearchProvider(
            [
                SearchCandidate(
                    provider_key="fake",
                    provider_media_id="candidate",
                    source_url="https://example.com/candidate",
                    title="Candidate",
                    rank=0,
                )
            ]
        )
    )
    client.app.state.media_search_provider_registry = registry
    resolve_response = client.post(
        f"/api/playlists/{imported['playlist']['id']}/tracks/resolve-batch",
        json={
            "provider_key": "fake",
            "tracks": [{"track_id": track["id"]} for track in imported["tracks"]],
        },
    )
    assert resolve_response.status_code == 200
    detail = client.get(f"/api/playlists/{imported['playlist']['id']}").json()
    items = [
        {
            "track_id": track["id"],
            "candidate_id": track["candidates"][0]["id"],
            "format": "mp3",
            "audio_bitrate_kbps": 192,
        }
        for track in detail["tracks"]
    ]

    response = client.post(
        f"/api/playlists/{imported['playlist']['id']}/tracks/queue-batch",
        json={"items": items},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["stopped_on_queue_full"] is True
    assert [result["status"] for result in payload["results"]] == ["queued", "failed"]
    assert payload["results"][1]["error_code"] == "QUEUE_FULL"


def _resolve_fixture_candidate(client: TestClient) -> dict[str, str]:
    imported = _import_fixture(client, "basic.csv")
    track = imported["tracks"][0]
    registry = MediaSearchProviderRegistry()
    registry.register(
        FakeSearchProvider(
            [
                SearchCandidate(
                    provider_key="fake",
                    provider_media_id="candidate-1",
                    source_url="https://example.com/candidate-1",
                    title="M83 - Midnight City",
                    creator="Channel",
                    duration_seconds=244,
                    rank=0,
                )
            ]
        )
    )
    client.app.state.media_search_provider_registry = registry
    response = client.post(
        f"/api/playlists/{imported['playlist']['id']}/tracks/{track['id']}/resolve",
        json={"provider_key": "fake", "limit": 5},
    )
    assert response.status_code == 200
    return {
        "playlist_id": imported["playlist"]["id"],
        "track_id": track["id"],
        "candidate_id": response.json()["candidates"][0]["id"],
    }


def _import_fixture(client: TestClient, fixture_name: str) -> dict:
    response = client.post(
        "/api/playlists/import",
        files={
            "file": (
                fixture_name,
                (FIXTURES / fixture_name).read_bytes(),
                "text/csv",
            )
        },
    )
    assert response.status_code == 201
    return response.json()
