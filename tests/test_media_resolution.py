import pytest
from sqlalchemy import func, select

from app.core.exceptions import MediaSearchNoResults
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
from app.services.media_resolution import MediaResolutionService
from app.services.media_search import MediaSearchProviderRegistry, SearchCandidate, TrackQuery


class FakeProvider:
    key = "fake"

    def __init__(self, candidates: list[SearchCandidate] | None = None) -> None:
        self.candidates = candidates or []
        self.searches: list[TrackQuery] = []

    def search(self, track: TrackQuery, *, limit: int) -> list[SearchCandidate]:
        self.searches.append(track)
        if not self.candidates:
            raise MediaSearchNoResults
        return self.candidates[:limit]


def test_media_resolution_persists_candidates_without_jobs(
    app_client: tuple[object, object],
) -> None:
    client, _ = app_client
    session_factory = client.app.state.session_factory
    with session_factory() as session:
        track = _stored_track(session)
        registry = MediaSearchProviderRegistry()
        provider = FakeProvider(
            [
                SearchCandidate(
                    provider_key="fake",
                    provider_media_id="one",
                    source_url="https://example.com/one",
                    title="Artist - Title",
                    creator="Creator",
                    duration_seconds=123,
                    thumbnail_url="https://example.com/thumb.jpg",
                    rank=0,
                    match_score=0.9,
                )
            ]
        )
        registry.register(provider)

        resolved = MediaResolutionService(session, registry).resolve_track(
            track,
            provider_key="fake",
            limit=5,
        )

        assert provider.searches == [
            TrackQuery(
                track_id=track.id,
                artist="Artist",
                title="Title",
                album="Album",
                duration_seconds=123,
            )
        ]
        assert resolved.track.resolution_status is TrackResolutionStatus.resolved
        assert resolved.candidates[0].provider_media_id == "one"
        assert session.scalar(select(func.count()).select_from(DownloadJob)) == 0


def test_media_resolution_replaces_previous_provider_candidates(
    app_client: tuple[object, object],
) -> None:
    client, _ = app_client
    session_factory = client.app.state.session_factory
    with session_factory() as session:
        track = _stored_track(session)
        session.add(
            ResolvedMediaCandidate(
                track_id=track.id,
                provider_key="fake",
                provider_media_id="old",
                source_url="https://example.com/old",
                title="Old",
                rank=0,
            )
        )
        session.commit()
        registry = MediaSearchProviderRegistry()
        registry.register(
            FakeProvider(
                [
                    SearchCandidate(
                        provider_key="fake",
                        provider_media_id="new",
                        source_url="https://example.com/new",
                        title="New",
                        rank=0,
                    )
                ]
            )
        )

        MediaResolutionService(session, registry).resolve_track(track, provider_key="fake", limit=5)

        candidates = session.scalars(select(ResolvedMediaCandidate)).all()
        assert [candidate.provider_media_id for candidate in candidates] == ["new"]


def test_media_resolution_keeps_queued_candidate_when_refreshing_results(
    app_client: tuple[object, object],
) -> None:
    client, _ = app_client
    session_factory = client.app.state.session_factory
    with session_factory() as session:
        track = _stored_track(session)
        old_candidate = ResolvedMediaCandidate(
            track_id=track.id,
            provider_key="fake",
            provider_media_id="old",
            source_url="https://example.com/old",
            title="Old",
            rank=0,
        )
        job = DownloadJob(source_url="https://example.com/old", requested_format=OutputFormat.mp3)
        session.add_all([old_candidate, job])
        session.commit()
        session.add(
            DownloadQueueItem(
                track_id=track.id,
                candidate_id=old_candidate.id,
                download_job_id=job.id,
                requested_format=OutputFormat.mp3,
                status=QueueItemStatus.submitted,
                idempotency_key="existing",
            )
        )
        session.commit()
        registry = MediaSearchProviderRegistry()
        registry.register(
            FakeProvider(
                [
                    SearchCandidate(
                        provider_key="fake",
                        provider_media_id="new",
                        source_url="https://example.com/new",
                        title="New",
                        rank=0,
                    )
                ]
            )
        )

        resolved = MediaResolutionService(session, registry).resolve_track(
            track,
            provider_key="fake",
            limit=5,
        )

        assert [candidate.provider_media_id for candidate in resolved.candidates] == [
            "old",
            "new",
        ]
        assert session.scalar(select(func.count()).select_from(DownloadQueueItem)) == 1


def test_media_resolution_marks_track_no_match(
    app_client: tuple[object, object],
) -> None:
    client, _ = app_client
    session_factory = client.app.state.session_factory
    with session_factory() as session:
        track = _stored_track(session)
        registry = MediaSearchProviderRegistry()
        registry.register(FakeProvider())

        with pytest.raises(MediaSearchNoResults):
            MediaResolutionService(session, registry).resolve_track(
                track,
                provider_key="fake",
                limit=5,
            )

        session.refresh(track)
        assert track.resolution_status is TrackResolutionStatus.no_match


def _stored_track(session) -> Track:
    playlist = ImportedPlaylist(
        name="Playlist",
        importer_key="test",
        status=PlaylistStatus.ready,
        track_count=1,
    )
    track = Track(
        position=0,
        artist="Artist",
        title="Title",
        album="Album",
        duration_seconds=123,
        normalization_version="1",
    )
    playlist.tracks.append(track)
    session.add(playlist)
    session.commit()
    session.refresh(track)
    return track
