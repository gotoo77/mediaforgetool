from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.playlist import PlaylistStatus, TrackResolutionStatus
from app.schemas.playlist import (
    ImportedPlaylistResponse,
    ResolvedMediaCandidateResponse,
    TrackResponse,
)


def test_playlist_and_track_response_contracts() -> None:
    now = datetime.now(UTC)
    playlist = ImportedPlaylistResponse(
        id="playlist-1",
        name="Imported tracks",
        importer_key="fake",
        status=PlaylistStatus.ready,
        track_count=1,
        rejected_row_count=0,
        created_at=now,
        updated_at=now,
    )
    track = TrackResponse(
        id="track-1",
        playlist_id=playlist.id,
        position=0,
        artist="Artist",
        title="Title",
        normalization_version="1",
        resolution_status=TrackResolutionStatus.pending,
        created_at=now,
        updated_at=now,
    )

    assert playlist.importer_key == "fake"
    assert track.playlist_id == playlist.id


def test_candidate_response_rejects_score_outside_unit_interval() -> None:
    with pytest.raises(ValidationError):
        ResolvedMediaCandidateResponse(
            id="candidate-1",
            track_id="track-1",
            provider_key="fake",
            source_url="https://example.com/media",
            title="Title",
            rank=0,
            match_score=1.1,
            created_at=datetime.now(UTC),
        )
