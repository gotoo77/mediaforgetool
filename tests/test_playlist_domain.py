from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.init_db import create_schema
from app.db.session import build_engine, build_session_factory
from app.main import create_app
from app.models.job import DownloadJob, OutputFormat
from app.models.playlist import (
    DownloadQueueItem,
    ImportedPlaylist,
    PlaylistStatus,
    QueueItemStatus,
    ResolvedMediaCandidate,
    Track,
    TrackResolutionStatus,
)


def _session(tmp_path: Path) -> Session:
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'playlist.db'}")
    engine = build_engine(settings)
    create_schema(engine)
    return build_session_factory(engine)()


def test_playlist_domain_persists_relations(tmp_path: Path) -> None:
    with _session(tmp_path) as session:
        playlist = ImportedPlaylist(name="My tracks", importer_key="fake")
        track = Track(position=0, artist="Artist", title="Title", normalization_version="1")
        candidate = ResolvedMediaCandidate(
            provider_key="fake",
            provider_media_id="media-1",
            source_url="https://example.com/media-1",
            title="Artist - Title",
            rank=0,
            match_score=0.95,
        )
        job = DownloadJob(
            source_url=candidate.source_url,
            requested_format=OutputFormat.mp3,
        )
        queue_item = DownloadQueueItem(
            candidate=candidate,
            requested_format=OutputFormat.mp3,
            idempotency_key="track-1:candidate-1:mp3",
            download_job=job,
        )
        track.candidates.append(candidate)
        track.queue_items.append(queue_item)
        playlist.tracks.append(track)

        session.add(playlist)
        session.commit()
        session.expire_all()

        stored = session.get(ImportedPlaylist, playlist.id)
        assert stored is not None
        assert stored.status is PlaylistStatus.importing
        assert stored.tracks[0].artist == "Artist"
        assert stored.tracks[0].candidates[0].provider_media_id == "media-1"
        assert stored.tracks[0].queue_items[0].download_job_id == job.id


def test_status_transitions_are_explicit() -> None:
    playlist = ImportedPlaylist(name="List", importer_key="fake")
    playlist.transition_to(PlaylistStatus.ready)
    assert playlist.status is PlaylistStatus.ready
    with pytest.raises(ValueError, match="ready -> failed"):
        playlist.transition_to(PlaylistStatus.failed)

    track = Track(position=0, artist="Artist", title="Title")
    track.transition_resolution_to(TrackResolutionStatus.searching)
    track.transition_resolution_to(TrackResolutionStatus.no_match)
    track.transition_resolution_to(TrackResolutionStatus.searching)
    assert track.resolution_status is TrackResolutionStatus.searching

    queue_item = DownloadQueueItem(
        track_id="track",
        candidate_id="candidate",
        requested_format=OutputFormat.mp3,
        idempotency_key="key",
    )
    queue_item.transition_to(QueueItemStatus.submitted)
    with pytest.raises(ValueError, match="submitted -> rejected"):
        queue_item.transition_to(QueueItemStatus.rejected)


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: ImportedPlaylist(name=" ", importer_key="fake"), "name must not be empty"),
        (lambda: Track(position=-1, artist="Artist", title="Title"), "position"),
        (
            lambda: ResolvedMediaCandidate(
                track_id="track",
                provider_key="fake",
                source_url="https://example.com",
                title="Title",
                rank=0,
                match_score=1.1,
            ),
            "match_score",
        ),
        (
            lambda: DownloadQueueItem(
                track_id="track",
                candidate_id="candidate",
                requested_format=OutputFormat.mp3,
                idempotency_key=" ",
            ),
            "idempotency_key",
        ),
    ],
)
def test_domain_rejects_invalid_values(factory: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        factory()


def test_queue_item_idempotency_key_is_unique(tmp_path: Path) -> None:
    with _session(tmp_path) as session:
        playlist = ImportedPlaylist(name="List", importer_key="fake")
        track = Track(position=0, artist="Artist", title="Title")
        candidate = ResolvedMediaCandidate(
            provider_key="fake",
            source_url="https://example.com/media",
            title="Title",
            rank=0,
        )
        track.candidates.append(candidate)
        playlist.tracks.append(track)
        session.add(playlist)
        session.flush()
        session.add_all(
            [
                DownloadQueueItem(
                    track_id=track.id,
                    candidate_id=candidate.id,
                    requested_format=OutputFormat.mp3,
                    idempotency_key="same-key",
                ),
                DownloadQueueItem(
                    track_id=track.id,
                    candidate_id=candidate.id,
                    requested_format=OutputFormat.mp4,
                    idempotency_key="same-key",
                ),
            ]
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_create_schema_adds_playlist_tables_to_existing_database(tmp_path: Path) -> None:
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'existing.db'}")
    engine = build_engine(settings)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE download_jobs (id VARCHAR(36) PRIMARY KEY)"))

    create_schema(engine)

    tables = set(inspect(engine).get_table_names())
    assert {
        "download_jobs",
        "imported_playlists",
        "tracks",
        "resolved_media_candidates",
        "download_queue_items",
    } <= tables


def test_only_playlist_import_route_is_registered() -> None:
    paths = {route.path for route in create_app().routes}

    assert {path for path in paths if path.startswith("/api/playlists")} == {
        "/api/playlists/import"
    }
    assert not any(path.startswith("/api/tracks") for path in paths)
