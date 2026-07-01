import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base
from app.models.job import DownloadJob, OutputFormat


def utc_now() -> datetime:
    return datetime.now(UTC)


class PlaylistStatus(StrEnum):
    importing = "importing"
    ready = "ready"
    partial = "partial"
    failed = "failed"


class TrackResolutionStatus(StrEnum):
    pending = "pending"
    searching = "searching"
    resolved = "resolved"
    no_match = "no_match"
    failed = "failed"


class QueueItemStatus(StrEnum):
    pending = "pending"
    submitted = "submitted"
    rejected = "rejected"


PLAYLIST_STATUS_TRANSITIONS = {
    PlaylistStatus.importing: {
        PlaylistStatus.ready,
        PlaylistStatus.partial,
        PlaylistStatus.failed,
    },
    PlaylistStatus.ready: set(),
    PlaylistStatus.partial: set(),
    PlaylistStatus.failed: set(),
}

TRACK_STATUS_TRANSITIONS = {
    TrackResolutionStatus.pending: {TrackResolutionStatus.searching},
    TrackResolutionStatus.searching: {
        TrackResolutionStatus.resolved,
        TrackResolutionStatus.no_match,
        TrackResolutionStatus.failed,
    },
    TrackResolutionStatus.resolved: {TrackResolutionStatus.searching},
    TrackResolutionStatus.no_match: {TrackResolutionStatus.searching},
    TrackResolutionStatus.failed: {TrackResolutionStatus.searching},
}

QUEUE_ITEM_STATUS_TRANSITIONS = {
    QueueItemStatus.pending: {QueueItemStatus.submitted, QueueItemStatus.rejected},
    QueueItemStatus.submitted: set(),
    QueueItemStatus.rejected: {QueueItemStatus.pending},
}


def _transition_status[T: StrEnum](
    current: T,
    target: T,
    allowed: dict[T, set[T]],
) -> T:
    if current == target:
        return current
    if target not in allowed[current]:
        raise ValueError(f"Invalid status transition: {current.value} -> {target.value}")
    return target


class ImportedPlaylist(Base):
    __tablename__ = "imported_playlists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(300))
    importer_key: Mapped[str] = mapped_column(String(80), index=True)
    source_filename: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[PlaylistStatus] = mapped_column(
        Enum(PlaylistStatus, native_enum=False),
        default=PlaylistStatus.importing,
        index=True,
    )
    track_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_row_count: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    tracks: Mapped[list["Track"]] = relationship(
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="Track.position",
    )
    issues: Mapped[list["PlaylistImportIssue"]] = relationship(
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistImportIssue.position",
    )

    def transition_to(self, status: PlaylistStatus) -> None:
        current = self.status or PlaylistStatus.importing
        self.status = _transition_status(current, status, PLAYLIST_STATUS_TRANSITIONS)

    @validates("name", "importer_key")
    def validate_required_text(self, key: str, value: str) -> str:
        return _required_text(key, value)

    @validates("track_count", "rejected_row_count")
    def validate_counts(self, key: str, value: int) -> int:
        return _non_negative_integer(key, value)


class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (UniqueConstraint("playlist_id", "position"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    playlist_id: Mapped[str] = mapped_column(
        ForeignKey("imported_playlists.id", ondelete="CASCADE"),
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer)
    artist: Mapped[str] = mapped_column(String(300))
    title: Mapped[str] = mapped_column(String(500))
    album: Mapped[str | None] = mapped_column(String(500), nullable=True)
    isrc: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_artist: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_title: Mapped[str | None] = mapped_column(String(700), nullable=True)
    source_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    normalization_version: Mapped[str] = mapped_column(String(40), default="1")
    resolution_status: Mapped[TrackResolutionStatus] = mapped_column(
        Enum(TrackResolutionStatus, native_enum=False),
        default=TrackResolutionStatus.pending,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    playlist: Mapped[ImportedPlaylist] = relationship(back_populates="tracks")
    candidates: Mapped[list["ResolvedMediaCandidate"]] = relationship(
        back_populates="track",
        cascade="all, delete-orphan",
    )
    queue_items: Mapped[list["DownloadQueueItem"]] = relationship(
        back_populates="track",
        cascade="all, delete-orphan",
    )

    def transition_resolution_to(self, status: TrackResolutionStatus) -> None:
        current = self.resolution_status or TrackResolutionStatus.pending
        self.resolution_status = _transition_status(
            current,
            status,
            TRACK_STATUS_TRANSITIONS,
        )

    @validates("artist", "title", "normalization_version")
    def validate_required_text(self, key: str, value: str) -> str:
        return _required_text(key, value)

    @validates("position")
    def validate_position(self, key: str, value: int) -> int:
        return _non_negative_integer(key, value)

    @validates("duration_seconds")
    def validate_duration(self, key: str, value: int | None) -> int | None:
        return _optional_non_negative_integer(key, value)


class PlaylistImportIssue(Base):
    __tablename__ = "playlist_import_issues"
    __table_args__ = (UniqueConstraint("playlist_id", "position"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    playlist_id: Mapped[str] = mapped_column(
        ForeignKey("imported_playlists.id", ondelete="CASCADE"),
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer)
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    playlist: Mapped[ImportedPlaylist] = relationship(back_populates="issues")

    @validates("position")
    def validate_position(self, key: str, value: int) -> int:
        return _non_negative_integer(key, value)

    @validates("row_number")
    def validate_row_number(self, key: str, value: int | None) -> int | None:
        return _optional_non_negative_integer(key, value)

    @validates("code", "message")
    def validate_required_text(self, key: str, value: str) -> str:
        return _required_text(key, value)


class ResolvedMediaCandidate(Base):
    __tablename__ = "resolved_media_candidates"
    __table_args__ = (
        UniqueConstraint("track_id", "provider_key", "provider_media_id"),
        UniqueConstraint("track_id", "provider_key", "rank"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    track_id: Mapped[str] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"),
        index=True,
    )
    provider_key: Mapped[str] = mapped_column(String(80), index=True)
    provider_media_id: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(700))
    creator: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    rank: Mapped[int] = mapped_column(Integer)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    track: Mapped[Track] = relationship(back_populates="candidates")
    queue_items: Mapped[list["DownloadQueueItem"]] = relationship(back_populates="candidate")

    @validates("provider_key", "source_url", "title")
    def validate_required_text(self, key: str, value: str) -> str:
        return _required_text(key, value)

    @validates("rank")
    def validate_rank(self, key: str, value: int) -> int:
        return _non_negative_integer(key, value)

    @validates("duration_seconds")
    def validate_duration(self, key: str, value: int | None) -> int | None:
        return _optional_non_negative_integer(key, value)

    @validates("match_score")
    def validate_match_score(self, key: str, value: float | None) -> float | None:
        if value is not None and not 0 <= value <= 1:
            raise ValueError(f"{key} must be between 0 and 1.")
        return value


class DownloadQueueItem(Base):
    """Trace a selected candidate submitted to the existing download job queue."""

    __tablename__ = "download_queue_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id"), index=True)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("resolved_media_candidates.id"),
        index=True,
    )
    download_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("download_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requested_format: Mapped[OutputFormat] = mapped_column(Enum(OutputFormat, native_enum=False))
    requested_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requested_audio_bitrate_kbps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[QueueItemStatus] = mapped_column(
        Enum(QueueItemStatus, native_enum=False),
        default=QueueItemStatus.pending,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    track: Mapped[Track] = relationship(back_populates="queue_items")
    candidate: Mapped[ResolvedMediaCandidate] = relationship(back_populates="queue_items")
    download_job: Mapped[DownloadJob | None] = relationship()

    def transition_to(self, status: QueueItemStatus) -> None:
        current = self.status or QueueItemStatus.pending
        self.status = _transition_status(current, status, QUEUE_ITEM_STATUS_TRANSITIONS)

    @validates("idempotency_key")
    def validate_idempotency_key(self, key: str, value: str) -> str:
        return _required_text(key, value)

    @validates("requested_height", "requested_audio_bitrate_kbps")
    def validate_positive_options(self, key: str, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError(f"{key} must be positive.")
        return value


def _required_text(key: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{key} must not be empty.")
    return normalized


def _non_negative_integer(key: str, value: int) -> int:
    if value < 0:
        raise ValueError(f"{key} must be non-negative.")
    return value


def _optional_non_negative_integer(key: str, value: int | None) -> int | None:
    if value is None:
        return None
    return _non_negative_integer(key, value)
