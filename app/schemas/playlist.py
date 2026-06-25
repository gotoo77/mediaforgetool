from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.job import OutputFormat
from app.models.playlist import PlaylistStatus, QueueItemStatus, TrackResolutionStatus


class ImportedPlaylistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    importer_key: str
    source_filename: str | None = None
    status: PlaylistStatus
    track_count: int = Field(ge=0)
    rejected_row_count: int = Field(ge=0)
    error_summary: str | None = None
    created_at: datetime
    updated_at: datetime


class TrackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    playlist_id: str
    position: int = Field(ge=0)
    artist: str
    title: str
    album: str | None = None
    isrc: str | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    normalization_version: str
    resolution_status: TrackResolutionStatus
    created_at: datetime
    updated_at: datetime


class ResolvedMediaCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    track_id: str
    provider_key: str
    provider_media_id: str | None = None
    source_url: str
    title: str
    creator: str | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    thumbnail_url: str | None = None
    rank: int = Field(ge=0)
    match_score: float | None = Field(default=None, ge=0, le=1)
    selected_at: datetime | None = None
    created_at: datetime


class DownloadQueueItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    track_id: str
    candidate_id: str
    download_job_id: str | None = None
    requested_format: OutputFormat
    requested_height: int | None = Field(default=None, ge=1)
    requested_audio_bitrate_kbps: int | None = Field(default=None, ge=1)
    status: QueueItemStatus
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    submitted_at: datetime | None = None
