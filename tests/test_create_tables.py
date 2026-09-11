"""수동 초기화의 안전 장치 및 PostgreSQL 반복 실행을 검증한다."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy import inspect, select

from app.models import Base, ChatLog, User
from scripts import create_tables


def test_두_테이블만_checkfirst로_초기화한다(monkeypatch):
    bind = Mock()
    bind.dialect.name = "postgresql"
    create = Mock()
    monkeypatch.setattr(Base.metadata, "create_all", create)
    create_tables.create_tables(bind)
    create.assert_called_once_with(
        bind=bind, tables=[User.__table__, ChatLog.__table__], checkfirst=True
    )


def test_PostgreSQL이_아니면_초기화를_거부한다():
    bind = Mock()
    bind.dialect.name = "sqlite"
    with pytest.raises(ValueError, match="requires PostgreSQL"):
        create_tables.create_tables(bind)


@pytest.mark.parametrize(
    "args,exit_code", [([], 2), (["--confirm"], 1), (["--help"], 0)]
)
def test_명시적_확인과_환경변수_없이는_DB를_건드리지_않는다(args, exit_code):
    environment = os.environ.copy()
    environment.pop("DATABASE_URL", None)
    result = subprocess.run(
        [sys.executable, "-m", "scripts.create_tables", *args],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == exit_code
    if args == ["--confirm"]:
        assert "Table creation failed (RuntimeError)" in result.stderr
        assert "Traceback" not in result.stderr


def test_실패는_비밀값_없이_종료코드_1로_보고한다(monkeypatch, capsys):
    from app import database

    engine = Mock()
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(
        create_tables,
        "create_tables",
        Mock(side_effect=RuntimeError("private-password")),
    )
    assert create_tables.main(["--confirm"]) == 1
    output = capsys.readouterr()
    assert "Table creation failed (RuntimeError)" in output.err
    assert "private-password" not in output.err + output.out
    engine.dispose.assert_called_once_with()


def test_성공_메시지는_초기화_완료_후에만_출력한다(monkeypatch, capsys):
    from app import database

    engine = Mock()
    monkeypatch.setattr(database, "engine", engine)
    create = Mock()
    monkeypatch.setattr(create_tables, "create_tables", create)
    assert create_tables.main(["--confirm"]) == 0
    create.assert_called_once_with(engine)
    assert "Schema ready" in capsys.readouterr().out
    engine.dispose.assert_called_once_with()


def test_PostgreSQL에서_두번_실행해도_기존_사용자와_대화를_보존한다(pg_connection):
    create_tables.create_tables(pg_connection)
    schema = pg_connection.get_execution_options()["schema_translate_map"][None]
    assert set(inspect(pg_connection).get_table_names(schema=schema)) == {
        "users",
        "chat_logs",
    }
    user_id = pg_connection.execute(
        User.__table__.insert()
        .values(username="demo", password_hash="test-only-hash")
        .returning(User.id)
    ).scalar_one()
    log_id = pg_connection.execute(
        ChatLog.__table__.insert()
        .values(
            user_id=user_id,
            request_id="test-request",
            question="질문",
            answer="답변",
            status="success",
            error_code=None,
            provider="openai",
            model="test-model",
            latency_ms=1,
        )
        .returning(ChatLog.id)
    ).scalar_one()
    create_tables.create_tables(pg_connection)
    assert (
        pg_connection.scalar(select(User.username).where(User.id == user_id)) == "demo"
    )
    assert (
        pg_connection.scalar(select(ChatLog.question).where(ChatLog.id == log_id))
        == "질문"
    )


def test_PostgreSQL에_users만_있으면_chat_logs만_추가한다(pg_connection):
    User.__table__.create(pg_connection)
    pg_connection.execute(
        User.__table__.insert().values(
            username="existing", password_hash="test-only-hash"
        )
    )
    create_tables.create_tables(pg_connection)
    schema = pg_connection.get_execution_options()["schema_translate_map"][None]
    assert set(inspect(pg_connection).get_table_names(schema=schema)) == {
        "users",
        "chat_logs",
    }
    assert pg_connection.scalar(select(User.username)) == "existing"


def test_확인_SQL을_PostgreSQL에서_실행할_수_있다(pg_connection):
    create_tables.create_tables(pg_connection)
    schema = pg_connection.get_execution_options()["schema_translate_map"][None]
    quoted = pg_connection.dialect.identifier_preparer.quote_schema(schema)
    pg_connection.exec_driver_sql(f"SET LOCAL search_path TO {quoted}")
    source = Path(__file__).resolve().parents[1] / "scripts" / "check_logs.sql"
    results = []
    for statement in source.read_text(encoding="utf-8").split(";"):
        if statement.strip():
            results.append(pg_connection.exec_driver_sql(statement).all())
    assert len(results) == 6
    assert len(results[1]) == 11
