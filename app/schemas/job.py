from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, computed_field, model_validator

from app.models.job import JobStatus, OutputFormat


class CreateJobRequest(BaseModel):
    url: HttpUrl
    format: OutputFormat
    resolution: Literal[360, 480, 720, 1080] | None = None
    audio_bitrate_kbps: Literal[128, 192, 256, 320] | None = None
    segment_start_seconds: int | None = Field(default=None, ge=0)
    segment_end_seconds: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, max_length=500)
    platform: str | None = Field(default=None, max_length=120)
    thumbnail_url: str | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    estimated_total_bytes: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_segment(self) -> "CreateJobRequest":
        has_start = self.segment_start_seconds is not None
        has_end = self.segment_end_seconds is not None
        if has_start != has_end:
            raise ValueError("segment_start_seconds and segment_end_seconds must be sent together")
        if (
            self.segment_start_seconds is not None
            and self.segment_end_seconds is not None
            and self.segment_start_seconds >= self.segment_end_seconds
        ):
            raise ValueError("segment_start_seconds must be before segment_end_seconds")
        return self


class InspectMediaRequest(BaseModel):
    url: HttpUrl


class JobErrorResponse(BaseModel):
    code: str
    message: str


class CleanupReportResponse(BaseModel):
    jobs_deleted: int
    output_dirs_deleted: int
    temp_dirs_deleted: int
    bytes_reclaimed: int
    active_jobs_skipped: int = 0


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_url: str
    requested_format: OutputFormat
    requested_height: int | None = None
    requested_audio_bitrate_kbps: int | None = None
    segment_start_seconds: int | None = None
    segment_end_seconds: int | None = None
    status: JobStatus
    progress_percent: Annotated[float | None, Field(ge=0, le=100)] = None
    downloaded_bytes: int | None = None
    total_bytes: int | None = None
    download_speed_bytes_per_second: int | None = None
    eta_seconds: int | None = None
    platform: str | None = None
    title: str | None = None
    thumbnail_url: str | None = None
    duration_seconds: int | None = None
    output_size_bytes: int | None = None
    error_code: str | None = Field(default=None, exclude=True)
    error_message: str | None = Field(default=None, exclude=True)
    created_at: datetime
    completed_at: datetime | None = None

    @computed_field
    @property
    def download_url(self) -> str | None:
        if self.status is JobStatus.completed:
            return f"/api/jobs/{self.id}/file"
        return None

    @computed_field
    @property
    def error(self) -> JobErrorResponse | None:
        if self.error_code and self.error_message:
            return JobErrorResponse(code=self.error_code, message=self.error_message)
        return None


class VideoVariantResponse(BaseModel):
    resolution: Literal[360, 480, 720, 1080]
    selected_height: int | None = None
    estimated_size_bytes: int | None = None


class SegmentSuggestionResponse(BaseModel):
    start_seconds: int
    end_seconds: int


class MediaInspectionResponse(BaseModel):
    title: str | None = None
    platform: str | None = None
    thumbnail_url: str | None = None
    duration_seconds: int | None = None
    mp3_estimated_size_bytes: int | None = None
    mp4_variants: list[VideoVariantResponse]
    segment_suggestions: list[SegmentSuggestionResponse] = Field(default_factory=list)
