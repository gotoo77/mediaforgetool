import logging
import shutil
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import jobs, pages, studio
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, reset_request_id, set_request_id
from app.db.init_db import create_schema
from app.db.session import build_engine, build_session_factory
from app.services.cleanup_service import CleanupService
from app.services.job_runner import JobRunner
from app.services.media_downloader import MediaDownloader
from app.services.rate_limiter import SlidingWindowRateLimiter
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "img-src 'self' https: data:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    ),
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        _require_binary(app_settings.ffmpeg_binary)
        _require_binary(app_settings.ffprobe_binary)

        storage = StorageService(app_settings)
        storage.prepare_directories()
        engine = build_engine(app_settings)
        create_schema(engine)
        session_factory = build_session_factory(engine)
        runner = JobRunner(app_settings, session_factory, storage, MediaDownloader(app_settings))
        cleanup = CleanupService(app_settings, session_factory, storage)
        rate_limiter = SlidingWindowRateLimiter(
            limit=app_settings.job_create_rate_limit_count,
            window_seconds=app_settings.job_create_rate_limit_window_seconds,
        )

        app.state.settings = app_settings
        app.state.engine = engine
        app.state.session_factory = session_factory
        app.state.job_runner = runner
        app.state.cleanup_service = cleanup
        app.state.job_rate_limiter = rate_limiter

        await runner.start()
        await cleanup.start()
        logger.info("App started", extra={"event": "app_started"})
        yield
        await cleanup.stop()
        await runner.stop()
        engine.dispose()

    app = FastAPI(title=app_settings.app_name, lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=app_settings.allowed_hosts)

    @app.middleware("http")
    async def add_request_id(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = _request_id(request)
        token = set_request_id(request_id)
        try:
            response = await call_next(request)
        finally:
            reset_request_id(token)
        response.headers.setdefault("X-Request-ID", request_id)
        return response

    @app.middleware("http")
    async def add_security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        _add_security_headers(response)
        return response

    @app.middleware("http")
    async def enforce_request_body_limit(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        content_length = _content_length(request)
        if (
            content_length is not None
            and content_length > app_settings.max_request_body_bytes
        ):
            response = JSONResponse(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                content={
                    "detail": {
                        "code": "REQUEST_BODY_TOO_LARGE",
                        "message": "The request body exceeds this instance limit.",
                    }
                },
            )
            response.headers.setdefault("X-Request-ID", _request_id(request))
            _add_security_headers(response)
            return response
        return await call_next(request)

    @app.get("/healthz", tags=["health"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(pages.router)
    app.include_router(jobs.router)
    app.include_router(studio.router)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    return app


def _require_binary(binary: str) -> None:
    if shutil.which(binary) is None:
        raise RuntimeError(f"Required binary is unavailable: {binary}")


def _content_length(request: Request) -> int | None:
    raw_value = request.headers.get("content-length")
    if raw_value is None:
        return None
    try:
        return int(raw_value)
    except ValueError:
        return None


def _request_id(request: Request) -> str:
    request_id = request.headers.get("x-request-id", "").strip()
    if 0 < len(request_id) <= 128 and request_id.isprintable():
        return request_id
    return uuid.uuid4().hex


def _add_security_headers(response: Response) -> None:
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)


app = create_app()
