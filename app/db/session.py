from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


def build_engine(settings: Settings) -> Engine:
    connect_args = (
        {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    )
    return create_engine(settings.database_url, connect_args=connect_args)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_session(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory
    with session_factory() as session:
        yield session
