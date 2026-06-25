from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.db.base import Base
from app.models import (  # noqa: F401
    DownloadJob,
    DownloadQueueItem,
    ImportedPlaylist,
    ResolvedMediaCandidate,
    Track,
)


def create_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    _upgrade_sqlite_schema(engine)


def _upgrade_sqlite_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    columns = {column["name"] for column in inspect(engine).get_columns("download_jobs")}
    if "requested_height" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE download_jobs ADD COLUMN requested_height INTEGER")
            )
    if "requested_audio_bitrate_kbps" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE download_jobs ADD COLUMN requested_audio_bitrate_kbps INTEGER")
            )
    if "segment_start_seconds" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE download_jobs ADD COLUMN segment_start_seconds INTEGER")
            )
    if "segment_end_seconds" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE download_jobs ADD COLUMN segment_end_seconds INTEGER")
            )
    if "downloaded_bytes" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE download_jobs ADD COLUMN downloaded_bytes INTEGER")
            )
    if "total_bytes" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE download_jobs ADD COLUMN total_bytes INTEGER"))
    if "download_speed_bytes_per_second" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE download_jobs ADD COLUMN download_speed_bytes_per_second INTEGER")
            )
    if "eta_seconds" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE download_jobs ADD COLUMN eta_seconds INTEGER"))
