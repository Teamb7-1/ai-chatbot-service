"""ChatLog의 PostgreSQL 테이블 구조와 기존 응답 형식을 검증한다."""

from datetime import datetime, timezone

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.models import ChatLog, User
from app.schemas import ChatLogItem, ErrorCode


def test_ChatLog는_11개_컬럼과_사용자_외래키를_가진다():
    table = ChatLog.__table__
    assert table.name == "chat_logs"
    assert list(table.columns.keys()) == [
        "id",
        "user_id",
        "request_id",
        "question",
        "answer",
        "status",
        "error_code",
        "provider",
        "model",
        "latency_ms",
        "created_at",
    ]
    assert next(iter(table.c.user_id.foreign_keys)).column is User.__table__.c.id
    assert [column.name for column in table.columns if column.nullable] == [
        "error_code"
    ]


def test_ChatLog는_PostgreSQL_자료형과_제약조건을_정의한다():
    table = ChatLog.__table__
    ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
    assert "id BIGSERIAL NOT NULL" in ddl
    assert "question TEXT NOT NULL" in ddl
    assert "answer TEXT NOT NULL" in ddl
    assert "created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL" in ddl
    assert "FOREIGN KEY(user_id) REFERENCES users (id)" in ddl
    assert "CHECK (status IN ('success', 'error'))" in ddl
    assert "CHECK (latency_ms >= 0)" in ddl
    assert any(
        [column.name for column in index.columns] == ["user_id", "created_at", "id"]
        for index in table.indexes
    )


def test_ChatLog의_id는_ChatLogItem의_chat_id로_변환된다():
    log = ChatLog(
        id=7,
        user_id=1,
        request_id="req-test",
        question="질문 원문",
        answer="",
        status="error",
        error_code=ErrorCode.AI_TIMEOUT.value,
        provider="openai",
        model="test-model",
        latency_ms=10000,
        created_at=datetime(2026, 9, 9, tzinfo=timezone.utc),
    )
    item = ChatLogItem.model_validate(log)
    assert item.chat_id == log.id == 7
    assert item.answer == ""
    assert item.status == "error"
    assert item.error_code is ErrorCode.AI_TIMEOUT
    assert "user_id" not in item.model_dump()
