from fastapi import Request
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.services.job_runner import JobRunner
from app.services.media_search import MediaSearchProviderRegistry
from app.services.playlist_import import PlaylistImporterRegistry
from app.services.rate_limiter import SlidingWindowRateLimiter


def get_settings_from_app(request: Request) -> Settings:
    return request.app.state.settings


def get_job_runner(request: Request) -> JobRunner:
    return request.app.state.job_runner


def get_job_rate_limiter(request: Request) -> SlidingWindowRateLimiter:
    return request.app.state.job_rate_limiter


def get_playlist_importer_registry(request: Request) -> PlaylistImporterRegistry:
    return request.app.state.playlist_importer_registry


def get_media_search_provider_registry(request: Request) -> MediaSearchProviderRegistry:
    return request.app.state.media_search_provider_registry


def get_session_factory(request: Request) -> sessionmaker[Session]:
    return request.app.state.session_factory
