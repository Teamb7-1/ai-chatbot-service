"""SQLAlchemy 데이터베이스 연결 기반을 제공한다."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _database_url() -> str:
    """환경변수에서 데이터베이스 연결 문자열을 가져온다."""
    database_url = os.environ.get("DATABASE_URL")

    if database_url is None or not database_url.strip():
        raise RuntimeError("DATABASE_URL environment variable is required")

    return database_url.strip()


class Base(DeclarativeBase):
    """모든 SQLAlchemy ORM 모델이 상속하는 기본 클래스."""


engine = create_engine(
    _database_url(),
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)
