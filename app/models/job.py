import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class OutputFormat(StrEnum):
    mp3 = "mp3"
    mp4 = "mp4"


class JobStatus(StrEnum):
    queued = "queued"
    extracting = "extracting"
    downloading = "downloading"
    processing = "processing"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    expired = "expired"
    interrupted = "interrupted"


class DownloadJob(Base):
    __tablename__ = "download_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_url: Mapped[str] = mapped_column(Text)
    requested_format: Mapped[OutputFormat] = mapped_column(Enum(OutputFormat))
    requested_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requested_audio_bitrate_kbps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    segment_start_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    segment_end_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.queued, index=True)
    progress_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    downloaded_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    download_speed_bytes_per_second: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    eta_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    platform: Mapped[str | None] = mapped_column(String(120), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_filename: Mapped[str | None] = mapped_column(String(600), nullable=True)
    output_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
