from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.job import OutputFormat
from app.models.playlist import PlaylistStatus, QueueItemStatus, TrackResolutionStatus
from app.schemas.job import JobResponse


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


class TrackReviewResponse(TrackResponse):
    candidates: list[ResolvedMediaCandidateResponse] = Field(default_factory=list)
    queue_items: list[DownloadQueueItemResponse] = Field(default_factory=list)


class PlaylistImportIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    row_number: int | None = None
    code: str
    message: str


class PlaylistImportResponse(BaseModel):
    playlist: ImportedPlaylistResponse
    tracks: list[TrackResponse]
    issues: list[PlaylistImportIssueResponse]


class PlaylistListResponse(BaseModel):
    items: list[ImportedPlaylistResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class PlaylistDetailResponse(BaseModel):
    playlist: ImportedPlaylistResponse
    tracks: list[TrackReviewResponse]
    issues: list[PlaylistImportIssueResponse]
    total_tracks: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class ResolveTrackRequest(BaseModel):
    provider_key: str = Field(default="youtube", min_length=1, max_length=80)
    limit: int = Field(default=5, ge=1, le=20)


class ResolveTrackResponse(BaseModel):
    track: TrackReviewResponse
    candidates: list[ResolvedMediaCandidateResponse]


class UpdateTrackRequest(BaseModel):
    artist: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=500)
    album: str | None = Field(default=None, max_length=500)
    isrc: str | None = Field(default=None, max_length=20)


class SubmitCandidateRequest(BaseModel):
    format: OutputFormat
    resolution: Literal[360, 480, 720, 1080] | None = None
    audio_bitrate_kbps: Literal[128, 192, 256, 320] | None = None


class CandidateQueueResponse(BaseModel):
    queue_item: DownloadQueueItemResponse
    job: JobResponse | None = None


class BatchTrackSelection(BaseModel):
    track_id: str = Field(min_length=1)


class BatchResolveRequest(BaseModel):
    tracks: list[BatchTrackSelection] = Field(min_length=1)
    provider_key: str = Field(default="youtube", min_length=1, max_length=80)
    limit: int = Field(default=5, ge=1, le=20)
    max_concurrency: int | None = Field(default=None, ge=1, le=8)


class BatchQueueSelection(BaseModel):
    track_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    format: OutputFormat
    resolution: Literal[360, 480, 720, 1080] | None = None
    audio_bitrate_kbps: Literal[128, 192, 256, 320] | None = None


class BatchQueueRequest(BaseModel):
    items: list[BatchQueueSelection] = Field(min_length=1)


class BatchTrackResult(BaseModel):
    track_id: str
    phase: Literal["search", "selection", "download"]
    status: Literal["resolved", "no_match", "queued", "skipped", "failed"]
    candidate_count: int = Field(default=0, ge=0)
    queue_item_id: str | None = None
    job_id: str | None = None
    error_code: str | None = None
    message: str | None = None


class BatchOperationResponse(BaseModel):
    results: list[BatchTrackResult]
    requested_count: int = Field(ge=0)
    completed_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    concurrency_limit: int = Field(default=1, ge=1)
    stopped_on_queue_full: bool = False
