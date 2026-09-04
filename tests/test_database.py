"""SQLAlchemy 데이터베이스 기반의 공통 계약을 검증한다."""

import importlib
import os
import subprocess
import sys

from sqlalchemy.orm import DeclarativeBase, Session

TEST_DATABASE_URL = (
    "postgresql+psycopg://user:password@"
    "ep-example-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
)


def test_Base와_SessionLocal이_동기_Session_계약을_제공한다(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    sys.modules.pop("app.database", None)

    database = importlib.import_module("app.database")

    assert issubclass(database.Base, DeclarativeBase)
    assert database.engine.url.drivername == "postgresql+psycopg"
    assert "-pooler" in (database.engine.url.host or "")

    with database.SessionLocal() as session:
        assert isinstance(session, Session)
        assert session.bind is database.engine
        assert session.autoflush is False
        assert session.expire_on_commit is False


def test_DATABASE_URL이_없으면_명확한_설정_오류가_발생한다():
    environment = os.environ.copy()
    environment.pop("DATABASE_URL", None)

    result = subprocess.run(
        [sys.executable, "-c", "import app.database"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode != 0
    assert "DATABASE_URL environment variable is required" in result.stderr
