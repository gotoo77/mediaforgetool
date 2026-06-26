from sqlalchemy import func, select

from app.models.job import DownloadJob, OutputFormat
from app.models.playlist import (
    DownloadQueueItem,
    ImportedPlaylist,
    PlaylistStatus,
    QueueItemStatus,
    ResolvedMediaCandidate,
    Track,
)
from app.schemas.playlist import SubmitCandidateRequest
from app.services.playlist_queue import PlaylistQueueService


class FakeRunner:
    def __init__(self, accepts: bool = True) -> None:
        self.accepts = accepts
        self.jobs: list[str] = []

    def enqueue(self, job_id: str) -> bool:
        self.jobs.append(job_id)
        return self.accepts


def test_playlist_queue_creates_queue_item_and_job(
    app_client: tuple[object, object],
) -> None:
    client, _ = app_client
    session_factory = client.app.state.session_factory
    runner = FakeRunner()
    with session_factory() as session:
        track, candidate = _stored_track_candidate(session)

        queued = PlaylistQueueService(session, runner, client.app.state.settings).submit_candidate(
            track,
            candidate,
            SubmitCandidateRequest(format=OutputFormat.mp3, audio_bitrate_kbps=192),
        )

        assert queued.queue_item.status is QueueItemStatus.submitted
        assert queued.queue_item.download_job_id == runner.jobs[0]
        assert queued.queue_item.requested_format is OutputFormat.mp3
        assert queued.queue_item.requested_audio_bitrate_kbps == 192
        assert candidate.selected_at is not None
        job = session.get(DownloadJob, queued.queue_item.download_job_id)
        assert job is not None
        assert job.source_url == "https://example.com/watch"
        assert job.title == "Candidate"


def test_playlist_queue_is_idempotent_for_same_candidate_and_options(
    app_client: tuple[object, object],
) -> None:
    client, _ = app_client
    session_factory = client.app.state.session_factory
    runner = FakeRunner()
    with session_factory() as session:
        track, candidate = _stored_track_candidate(session)
        request = SubmitCandidateRequest(format=OutputFormat.mp4, resolution=720)

        first = PlaylistQueueService(session, runner, client.app.state.settings).submit_candidate(
            track,
            candidate,
            request,
        )
        second = PlaylistQueueService(session, runner, client.app.state.settings).submit_candidate(
            track,
            candidate,
            request,
        )

        assert first.queue_item.id == second.queue_item.id
        assert len(runner.jobs) == 1
        assert session.scalar(select(func.count()).select_from(DownloadJob)) == 1
        assert session.scalar(select(func.count()).select_from(DownloadQueueItem)) == 1


def _stored_track_candidate(session) -> tuple[Track, ResolvedMediaCandidate]:
    playlist = ImportedPlaylist(
        name="Playlist",
        importer_key="test",
        status=PlaylistStatus.ready,
        track_count=1,
    )
    track = Track(position=0, artist="Artist", title="Title", normalization_version="1")
    candidate = ResolvedMediaCandidate(
        provider_key="fake",
        provider_media_id="candidate",
        source_url="https://example.com/watch",
        title="Candidate",
        creator="Creator",
        duration_seconds=120,
        rank=0,
    )
    track.candidates.append(candidate)
    playlist.tracks.append(track)
    session.add(playlist)
    session.commit()
    session.refresh(track)
    session.refresh(candidate)
    return track, candidate
