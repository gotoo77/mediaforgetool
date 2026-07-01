import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class MediaAssetKind(StrEnum):
    audio = "audio"
    video = "video"
    image = "image"
    unknown = "unknown"


class MediaAssetOrigin(StrEnum):
    upload = "upload"
    download_job = "download_job"
    studio_output = "studio_output"
    import_file = "import_file"


class MediaEditOperation(StrEnum):
    replace_audio = "replace_audio"
    remove_audio = "remove_audio"
    extract_audio = "extract_audio"
    split_media = "split_media"
    concat_audio = "concat_audio"
    concat_video = "concat_video"


class MediaEditStatus(StrEnum):
    queued = "queued"
    probing = "probing"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


MEDIA_EDIT_STATUS_TRANSITIONS = {
    MediaEditStatus.queued: {
        MediaEditStatus.probing,
        MediaEditStatus.processing,
        MediaEditStatus.cancelled,
        MediaEditStatus.failed,
    },
    MediaEditStatus.probing: {
        MediaEditStatus.processing,
        MediaEditStatus.cancelled,
        MediaEditStatus.failed,
    },
    MediaEditStatus.processing: {
        MediaEditStatus.completed,
        MediaEditStatus.cancelled,
        MediaEditStatus.failed,
    },
    MediaEditStatus.completed: set(),
    MediaEditStatus.failed: {MediaEditStatus.queued},
    MediaEditStatus.cancelled: {MediaEditStatus.queued},
}


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    display_name: Mapped[str] = mapped_column(String(500))
    relative_path: Mapped[str] = mapped_column(Text, unique=True)
    kind: Mapped[MediaAssetKind] = mapped_column(
        Enum(MediaAssetKind, native_enum=False),
        default=MediaAssetKind.unknown,
        index=True,
    )
    origin: Mapped[MediaAssetOrigin] = mapped_column(
        Enum(MediaAssetOrigin, native_enum=False),
        index=True,
    )
    container_format: Mapped[str | None] = mapped_column(String(80), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audio_codec: Mapped[str | None] = mapped_column(String(120), nullable=True)
    video_codec: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_download_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("download_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    edit_inputs: Mapped[list["MediaEditJobInput"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
    )
    edit_outputs: Mapped[list["MediaEditJobOutput"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
    )

    @validates("display_name")
    def validate_required_text(self, key: str, value: str) -> str:
        return _required_text(key, value)

    @validates("relative_path")
    def validate_relative_path(self, key: str, value: str) -> str:
        normalized = _required_text(key, value).replace("\\", "/")
        if normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized:
            raise ValueError(f"{key} must stay inside managed storage.")
        if ":" in normalized.split("/", 1)[0]:
            raise ValueError(f"{key} must be relative.")
        return normalized

    @validates("size_bytes")
    def validate_size(self, key: str, value: int) -> int:
        return _non_negative_integer(key, value)

    @validates("duration_seconds")
    def validate_duration(self, key: str, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError(f"{key} must be non-negative.")
        return value

    @validates("width", "height")
    def validate_dimensions(self, key: str, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError(f"{key} must be positive.")
        return value


class MediaEditJob(Base):
    __tablename__ = "media_edit_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    operation: Mapped[MediaEditOperation] = mapped_column(
        Enum(MediaEditOperation, native_enum=False),
        index=True,
    )
    status: Mapped[MediaEditStatus] = mapped_column(
        Enum(MediaEditStatus, native_enum=False),
        default=MediaEditStatus.queued,
        index=True,
    )
    output_name: Mapped[str] = mapped_column(String(500))
    output_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    options: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    progress_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    inputs: Mapped[list["MediaEditJobInput"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="MediaEditJobInput.position",
    )
    outputs: Mapped[list["MediaEditJobOutput"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="MediaEditJobOutput.position",
    )
    output_asset: Mapped[MediaAsset | None] = relationship(
        foreign_keys=[output_asset_id],
    )

    def transition_to(self, status: MediaEditStatus) -> None:
        current = self.status or MediaEditStatus.queued
        if current == status:
            return
        if status not in MEDIA_EDIT_STATUS_TRANSITIONS[current]:
            raise ValueError(f"Invalid status transition: {current.value} -> {status.value}")
        self.status = status

    @validates("output_name")
    def validate_output_name(self, key: str, value: str) -> str:
        return _required_text(key, value)

    @validates("progress_percent")
    def validate_progress(self, key: str, value: float | None) -> float | None:
        if value is not None and not 0 <= value <= 100:
            raise ValueError(f"{key} must be between 0 and 100.")
        return value


class MediaEditJobInput(Base):
    __tablename__ = "media_edit_job_inputs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(
        ForeignKey("media_edit_jobs.id", ondelete="CASCADE"),
        index=True,
    )
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
        index=True,
    )
    role: Mapped[str] = mapped_column(String(80))
    position: Mapped[int] = mapped_column(Integer, default=0)

    job: Mapped[MediaEditJob] = relationship(back_populates="inputs")
    asset: Mapped[MediaAsset] = relationship(back_populates="edit_inputs")

    @validates("role")
    def validate_role(self, key: str, value: str) -> str:
        return _required_text(key, value)

    @validates("position")
    def validate_position(self, key: str, value: int) -> int:
        return _non_negative_integer(key, value)


class MediaEditJobOutput(Base):
    __tablename__ = "media_edit_job_outputs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(
        ForeignKey("media_edit_jobs.id", ondelete="CASCADE"),
        index=True,
    )
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
        index=True,
    )
    role: Mapped[str] = mapped_column(String(80))
    position: Mapped[int] = mapped_column(Integer, default=0)

    job: Mapped[MediaEditJob] = relationship(back_populates="outputs")
    asset: Mapped[MediaAsset] = relationship(back_populates="edit_outputs")

    @validates("role")
    def validate_role(self, key: str, value: str) -> str:
        return _required_text(key, value)

    @validates("position")
    def validate_position(self, key: str, value: int) -> int:
        return _non_negative_integer(key, value)


def _required_text(key: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{key} must not be empty.")
    return normalized


def _non_negative_integer(key: str, value: int) -> int:
    if value < 0:
        raise ValueError(f"{key} must be non-negative.")
    return value
