from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.studio import (
    MediaAssetKind,
    MediaAssetOrigin,
    MediaEditOperation,
    MediaEditStatus,
)


class MediaStreamProbeResponse(BaseModel):
    index: int
    codec_type: str
    codec_name: str | None = None
    duration_seconds: float | None = None
    bitrate: int | None = None
    width: int | None = None
    height: int | None = None
    channels: int | None = None
    sample_rate: int | None = None


class MediaProbeResponse(BaseModel):
    duration_seconds: float | None = None
    container_format: str | None = None
    size_bytes: int | None = None
    bitrate: int | None = None
    has_audio: bool
    has_video: bool
    audio_streams: list[MediaStreamProbeResponse] = Field(default_factory=list)
    video_streams: list[MediaStreamProbeResponse] = Field(default_factory=list)


class StudioErrorResponse(BaseModel):
    code: str
    message: str


class MediaAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    relative_path: str
    kind: MediaAssetKind
    origin: MediaAssetOrigin
    container_format: str | None = None
    mime_type: str | None = None
    size_bytes: int
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    audio_codec: str | None = None
    video_codec: str | None = None
    created_at: datetime
    updated_at: datetime


class MediaAssetInspectionResponse(BaseModel):
    asset: MediaAssetResponse
    probe: MediaProbeResponse | None = None


class MediaEditJobInputRequest(BaseModel):
    role: str = Field(max_length=80)
    asset_id: str


class CreateMediaEditJobRequest(BaseModel):
    operation: MediaEditOperation
    inputs: list[MediaEditJobInputRequest] = Field(min_length=1, max_length=12)
    output_name: str = Field(min_length=1, max_length=500)
    audio_offset_seconds: float = 0
    duration_mode: Literal["shortest", "full"] = "shortest"
    audio_format: Literal["mp3", "m4a"] = "mp3"
    split_time_seconds: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_operation_options(self) -> "CreateMediaEditJobRequest":
        if self.operation is MediaEditOperation.split_media and self.split_time_seconds is None:
            raise ValueError("split_time_seconds is required for split_media")
        if self.operation in {
            MediaEditOperation.concat_audio,
            MediaEditOperation.concat_video,
        } and len(self.inputs) < 2:
            raise ValueError("concat operations require at least two inputs")
        return self


class MediaEditJobOutputResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    position: int
    asset: MediaAssetResponse


class MediaEditJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    operation: MediaEditOperation
    status: MediaEditStatus
    output_name: str
    progress_percent: Annotated[float | None, Field(ge=0, le=100)] = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    outputs: list[MediaEditJobOutputResponse] = Field(default_factory=list)


class MediaEditJobProgressResponse(BaseModel):
    progress_percent: Annotated[float | None, Field(ge=0, le=100)] = None
