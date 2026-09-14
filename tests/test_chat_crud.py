"""DB 없이 대화 CRUD의 호출 계약, SQL 조건, 예외 전파를 검사한다."""

import logging
from datetime import datetime, timezone
from inspect import iscoroutinefunction, signature
from unittest.mock import Mock, call

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app import crud
from app.config import AI_CONTEXT_TURNS
from app.models import ChatLog
from app.schemas import ErrorCode


@pytest.fixture
def db():
    return Mock(spec=Session)


@pytest.fixture
def values():
    return {
        "user_id": 7,
        "request_id": "req-test",
        "question": "  private question\n" + "x" * 1200,
        "answer": "private answer",
        "status": "success",
        "error_code": None,
        "provider": "openai",
        "model": "test-model",
        "latency_ms": 42,
    }


def test_세_함수는_동기이고_문맥_기본값은_팀_상수다():
    for function in (crud.create_chat_log, crud.recent_turns, crud.list_chat_logs):
        assert not iscoroutinefunction(function)
    assert signature(crud.recent_turns).parameters["n"].default == AI_CONTEXT_TURNS


@pytest.mark.parametrize("status", ["success", "error"])
def test_저장은_성공과_실패_원문을_보존하고_ChatLog를_반환한다(
    db, values, caplog, status
):
    caplog.set_level(logging.INFO, logger="app.crud")
    if status == "error":
        values.update(status="error", answer="", error_code=ErrorCode.AI_TIMEOUT)

    def refresh(log):
        log.id = 10
        log.created_at = datetime(2026, 9, 9, tzinfo=timezone.utc)

    db.refresh.side_effect = refresh
    log = crud.create_chat_log(db, **values)
    assert isinstance(log, ChatLog)
    assert log.chat_id == log.id == 10
    for key, value in values.items():
        assert getattr(log, key) == value
    assert db.method_calls == [
        call.add(log),
        call.flush(),
        call.refresh(log),
        call.commit(),
    ]
    assert "db_save_success" in caplog.text
    assert "private question" not in caplog.text
    assert "private answer" not in caplog.text


@pytest.mark.parametrize("stage", ["flush", "refresh", "commit"])
@pytest.mark.parametrize("error_type", [IntegrityError, OperationalError])
def test_저장_실패는_롤백하고_원본_예외를_유지한다(
    db, values, caplog, stage, error_type
):
    error = error_type("private question", values, Exception("private answer"))
    getattr(db, stage).side_effect = error
    with pytest.raises(error_type) as raised:
        crud.create_chat_log(db, **values)
    assert raised.value is error
    db.rollback.assert_called_once_with()
    assert db.method_calls[-1] == call.rollback()
    if stage != "commit":
        db.commit.assert_not_called()
    db.close.assert_not_called()
    assert "db_save_failed" in caplog.text
    assert "db_save_success" not in caplog.text
    assert "private question" not in caplog.text
    assert "private answer" not in caplog.text


@pytest.mark.parametrize("empty", [False, True])
def test_recent_turns는_사용자와_성공을_필터하고_최근_n개를_뒤집는다(db, empty):
    rows = [] if empty else [ChatLog(id=3), ChatLog(id=2)]
    db.scalars.return_value.all.return_value = rows
    assert crud.recent_turns(db, 7, n=2) == list(reversed(rows))
    statement = db.scalars.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    assert (
        "WHERE chat_logs.user_id = %(user_id_1)s AND chat_logs.status = %(status_1)s"
        in str(compiled)
    )
    assert "ORDER BY chat_logs.created_at DESC, chat_logs.id DESC" in str(compiled)
    assert compiled.params == {"user_id_1": 7, "status_1": "success", "param_1": 2}
    db.commit.assert_not_called()


def test_list_chat_logs는_상태_필터_없이_사용자별_최신순_페이지를_반환한다(db):
    rows = [ChatLog(id=3, status="error"), ChatLog(id=2, status="success")]
    db.scalars.return_value.all.return_value = rows
    assert crud.list_chat_logs(db, 7, limit=2, offset=4) == rows
    statement = db.scalars.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    assert "status" not in str(statement.whereclause)
    assert "ORDER BY chat_logs.created_at DESC, chat_logs.id DESC" in str(compiled)
    assert compiled.params == {"user_id_1": 7, "param_1": 2, "param_2": 4}
    db.commit.assert_not_called()


@pytest.mark.parametrize(
    "function,kwargs",
    [
        (crud.recent_turns, {"n": -1}),
        (crud.list_chat_logs, {"limit": -1}),
        (crud.list_chat_logs, {"offset": -1}),
    ],
)
def test_음수_조회_범위는_거부한다(db, function, kwargs):
    with pytest.raises(ValueError):
        function(db, 7, **kwargs)
    db.scalars.assert_not_called()


@pytest.mark.parametrize(
    "function,kwargs",
    [
        (crud.recent_turns, {"n": 0}),
        (crud.list_chat_logs, {"limit": 0}),
    ],
)
def test_0개_요청은_빈_목록이다(db, function, kwargs):
    assert function(db, 7, **kwargs) == []
    db.scalars.assert_not_called()


@pytest.mark.parametrize("function", [crud.recent_turns, crud.list_chat_logs])
def test_DB_조회_장애를_빈_기록으로_숨기지_않는다(db, function):
    error = OperationalError("SELECT", {}, Exception("connection failed"))
    db.scalars.side_effect = error
    with pytest.raises(OperationalError) as raised:
        function(db, 7)
    assert raised.value is error
