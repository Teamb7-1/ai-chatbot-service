"""실제 PostgreSQL 검증. TEST_DATABASE_URL과 격리 방식은 conftest.pg_db 참고."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app import crud
from app.models import ChatLog
from app.schemas import ChatLogItem, ErrorCode


def save(db, owner_id, **overrides):
    values = {
        "user_id": owner_id,
        "request_id": "req-test",
        "question": "  질문\n" + "x" * 1200,
        "answer": "답변\n",
        "status": "success",
        "error_code": None,
        "provider": "openai",
        "model": "test-model",
        "latency_ms": 42,
    }
    values.update(overrides)
    return crud.create_chat_log(db, **values)


@pytest.mark.parametrize("status", ["success", "error"])
def test_PostgreSQL에_성공과_실패_대화를_원문대로_저장한다(pg_db, status):
    user = crud.create_user(pg_db, "alice", "hashed")
    answer = "답변\n" if status == "success" else ""
    code = None if status == "success" else ErrorCode.AI_TIMEOUT
    log = save(pg_db, user.id, status=status, answer=answer, error_code=code)
    log_id = log.id
    assert log_id > 0
    pg_db.expunge_all()
    stored = pg_db.get(ChatLog, log_id)
    assert stored.question == "  질문\n" + "x" * 1200
    assert stored.answer == answer
    assert stored.request_id == "req-test"
    assert stored.provider == "openai"
    assert stored.model == "test-model"
    assert stored.latency_ms == 42
    assert stored.created_at.utcoffset() is not None
    response = ChatLogItem.model_validate(stored)
    assert response.chat_id == log_id
    assert response.status == status
    assert response.error_code == code


@pytest.fixture
def history(pg_db):
    alice = crud.create_user(pg_db, "alice", "hashed")
    bob = crud.create_user(pg_db, "bob", "hashed")
    start = datetime(2026, 9, 9, tzinfo=timezone.utc)
    rows = []
    # 첫 두 행은 id 순서와 시각 순서를 다르게 하여 시각 기준 정렬을 검사한다.
    for i, second in enumerate([1, 0, 2, 3, 4, 5, 6, 7]):
        failed = i in (3, 7)
        log = save(
            pg_db,
            alice.id,
            status="error" if failed else "success",
            answer="" if failed else f"answer-{i}",
            error_code=ErrorCode.AI_TIMEOUT if failed else None,
        )
        log.created_at = start + timedelta(seconds=second)
        rows.append(log)
    # 다른 사용자의 더 최신 기록이 LIMIT보다 먼저 걸러지는지도 검사한다.
    for i in range(6):
        other = save(pg_db, bob.id)
        other.created_at = start + timedelta(seconds=10 + i)
    pg_db.flush()
    return alice.id, rows


def test_recent_turns는_남의_기록과_실패를_제외한_최근_5개다(pg_db, history):
    user_id, rows = history
    assert [log.id for log in crud.recent_turns(pg_db, user_id)] == [
        rows[i].id for i in (0, 2, 4, 5, 6)
    ]
    assert [log.id for log in crud.recent_turns(pg_db, user_id, n=2)] == [
        rows[5].id,
        rows[6].id,
    ]
    assert len(crud.recent_turns(pg_db, user_id, n=20)) == 6


def test_list_chat_logs는_자신의_성공과_실패를_최신순으로_페이지_조회한다(
    pg_db, history
):
    user_id, rows = history
    assert [log.id for log in crud.list_chat_logs(pg_db, user_id)] == [
        rows[i].id for i in (7, 6, 5, 4, 3, 2, 0, 1)
    ]
    page = crud.list_chat_logs(pg_db, user_id, limit=2, offset=4)
    assert [log.id for log in page] == [rows[3].id, rows[2].id]
    assert [log.status for log in page] == ["error", "success"]
    assert crud.list_chat_logs(pg_db, user_id, offset=100) == []


def test_같은_시각에도_id로_조회_순서가_고정된다(pg_db, history):
    user_id, rows = history
    rows[6].created_at = rows[5].created_at
    pg_db.flush()
    assert [log.id for log in crud.recent_turns(pg_db, user_id, n=2)] == [
        rows[5].id,
        rows[6].id,
    ]
    assert crud.list_chat_logs(pg_db, user_id, limit=1, offset=1)[0].id == rows[6].id
    assert crud.list_chat_logs(pg_db, user_id, limit=1, offset=2)[0].id == rows[5].id


def test_대화가_없는_사용자와_0개_조회는_빈_목록이다(pg_db):
    user = crud.create_user(pg_db, "empty", "hashed")
    assert crud.recent_turns(pg_db, user.id) == []
    assert crud.list_chat_logs(pg_db, user.id) == []
    save(pg_db, user.id)
    assert crud.recent_turns(pg_db, user.id, n=0) == []
    assert crud.list_chat_logs(pg_db, user.id, limit=0) == []


@pytest.mark.parametrize(
    "overrides,sqlstate",
    [
        ({"user_id": -1}, "23503"),
        ({"status": "unknown"}, "23514"),
        ({"latency_ms": -1}, "23514"),
    ],
)
def test_잘못된_대화_저장_실패_후에도_같은_세션을_재사용한다(
    pg_db, overrides, sqlstate
):
    user = crud.create_user(pg_db, "alice", "hashed")
    user_id = user.id
    with pytest.raises(IntegrityError) as raised:
        save(pg_db, user_id, **overrides)
    assert raised.value.orig.sqlstate == sqlstate
    assert pg_db.is_active
    assert crud.list_chat_logs(pg_db, user_id) == []
    created = save(pg_db, user_id)
    assert crud.recent_turns(pg_db, user_id)[0].id == created.id
