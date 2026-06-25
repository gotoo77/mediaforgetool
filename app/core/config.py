from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "MediaForgeTool"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8421, ge=1, le=65535)
    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"])
    database_url: str = "sqlite:///./storage/mediaforgetool.db"
    storage_dir: Path = Path("storage/jobs")
    temp_dir: Path = Path("temp/jobs")
    max_concurrent_jobs: int = Field(default=2, ge=1, le=8)
    max_queue_size: int = Field(default=32, ge=1, le=512)
    job_create_rate_limit_count: int = Field(default=10, ge=1, le=1000)
    job_create_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    max_request_body_bytes: int = Field(default=1_048_576, ge=1024, le=10_485_760)
    max_url_length: int = Field(default=2048, ge=64, le=8192)
    max_output_size_mb: int = Field(default=500, ge=1, le=10_000)
    max_media_duration_seconds: int = Field(default=3600, ge=1)
    mp3_bitrate_kbps: int = Field(default=192, ge=32, le=320)
    job_timeout_seconds: int = Field(default=1800, ge=30)
    output_retention_hours: int = Field(default=24, ge=1)
    temp_retention_hours: int = Field(default=2, ge=1)
    cleanup_interval_seconds: int = Field(default=900, ge=60)
    progress_update_interval_seconds: float = Field(default=0.5, ge=0.1, le=10)
    ytdlp_socket_timeout_seconds: int = Field(default=20, ge=1)
    ytdlp_js_runtime: str = "node"
    ytdlp_js_runtime_path: str | None = None
    ytdlp_cookies_file: Path | None = None
    ytdlp_cookies_from_browser: str | None = None
    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"
    log_level: str = "INFO"

    @property
    def max_output_size_bytes(self) -> int:
        return self.max_output_size_mb * 1024 * 1024

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
