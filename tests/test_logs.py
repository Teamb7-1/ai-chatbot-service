"""C 라우터를 격리 등록해 검사한다. 실제 main.py의 등록 여부와는 별개다."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app import crud, deps
from app.main import app as main_app
from app.models import ChatLog, User
from app.routers.logs import router
from app.schemas import ERROR_MESSAGES, ErrorCode
from app.security import create_access_token


@pytest.fixture
def logs_app():
    # D의 공통 오류 처리를 재사용하되 전역 앱의 routes를 변경하지 않는다.
    app = FastAPI(exception_handlers=dict(main_app.exception_handlers))
    app.include_router(router)
    return app


@pytest.fixture
def boundary(monkeypatch):
    monkeypatch.setenv(
        "SECRET_KEY", "logs-tests-only-secret-with-more-than-thirty-two-bytes"
    )
    session = Mock(spec=Session)
    factory = Mock(return_value=session)
    monkeypatch.setattr(deps, "SessionLocal", factory)
    user = User(id=7, username="alice", password_hash="test-only-hash")
    lookup = Mock(return_value=user)
    listing = Mock(return_value=[])
    monkeypatch.setattr(crud, "get_user_by_id", lookup)
    monkeypatch.setattr(crud, "list_chat_logs", listing)
    return session, factory, lookup, listing


@pytest.fixture
def client(logs_app, boundary):
    return TestClient(logs_app, raise_server_exceptions=False)


def cookie(user_id=7, *, expired=False):
    duration = timedelta(seconds=-1) if expired else timedelta(minutes=5)
    token = create_access_token(user_id, duration)
    return {"Cookie": f"access_token={token}"}


def test_기본_조회는_현재_사용자로만_Crud를_호출하고_세션을_닫는다(client, boundary):
    session, factory, lookup, listing = boundary
    response = client.get("/api/me/chats?user_id=999", headers=cookie())
    assert response.status_code == 200
    assert response.json() == []
    lookup.assert_called_once_with(session, 7)
    listing.assert_called_once_with(session, 7, limit=20, offset=0)
    factory.assert_called_once_with()
    session.close.assert_called_once_with()


def test_성공과_실패_모두_ChatLogItem_형식으로_반환한다(client, boundary):
    listing = boundary[3]
    listing.return_value = [
        ChatLog(
            id=i,
            user_id=7,
            request_id=f"req-{i}",
            question="  질문\n",
            answer="답변" if status == "success" else "",
            status=status,
            error_code=None if status == "success" else "AI_TIMEOUT",
            provider="openai",
            model="test-model",
            latency_ms=42,
            created_at=datetime(2026, 9, 12, tzinfo=timezone.utc),
        )
        for i, status in [(2, "error"), (1, "success")]
    ]
    response = client.get("/api/me/chats?limit=2&offset=3", headers=cookie())
    assert response.status_code == 200
    listing.assert_called_once_with(boundary[0], 7, limit=2, offset=3)
    rows = response.json()
    assert [row["chat_id"] for row in rows] == [2, 1]
    assert rows[0]["error_code"] == "AI_TIMEOUT"
    assert rows[0]["answer"] == ""
    assert rows[1]["error_code"] is None
    assert rows[1]["question"] == "  질문\n"
    assert set(rows[0]) == {
        "chat_id",
        "request_id",
        "question",
        "answer",
        "status",
        "error_code",
        "latency_ms",
        "created_at",
    }


@pytest.mark.parametrize("query", ["limit=-1", "offset=-1", "limit=no", "offset=1.5"])
def test_잘못된_페이지_인자는_공통_422를_반환한다(client, boundary, query):
    response = client.get(f"/api/me/chats?{query}", headers=cookie())
    assert response.status_code == 422
    assert response.json() == {
        "error_code": "VALIDATION_ERROR",
        "message": ERROR_MESSAGES[ErrorCode.VALIDATION_ERROR],
    }
    boundary[3].assert_not_called()
    boundary[0].close.assert_called_once_with()


def test_0개_조회도_허용한다(client, boundary):
    response = client.get("/api/me/chats?limit=0", headers=cookie())
    assert response.status_code == 200
    assert response.json() == []
    boundary[3].assert_called_once_with(boundary[0], 7, limit=0, offset=0)


@pytest.mark.parametrize("kind", ["missing", "malformed", "expired", "deleted-user"])
def test_비로그인과_유효하지_않은_인증은_401이다(client, boundary, kind):
    if kind == "missing":
        headers = {}
    elif kind == "malformed":
        headers = {"Cookie": "access_token=not-a-jwt"}
    else:
        headers = cookie(expired=kind == "expired")
    if kind == "deleted-user":
        boundary[2].return_value = None
    response = client.get("/api/me/chats", headers=headers)
    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
    boundary[3].assert_not_called()
    boundary[0].close.assert_called_once_with()


def test_DB_실패를_빈_성공으로_숨기거나_내부_정보를_노출하지_않는다(
    client, boundary, caplog
):
    boundary[3].side_effect = OperationalError(
        "SELECT private-question", {"secret": "private-password"}, Exception("db down")
    )
    response = client.get("/api/me/chats", headers=cookie())
    assert response.status_code == 500
    assert response.json() == {
        "error_code": "INTERNAL_ERROR",
        "message": ERROR_MESSAGES[ErrorCode.INTERNAL_ERROR],
    }
    assert "db_read_failed" in caplog.text
    assert "private-question" not in response.text + caplog.text
    assert "private-password" not in response.text + caplog.text
    boundary[0].close.assert_called_once_with()


def test_PostgreSQL과_실제_인증으로_남의_기록을_제외한다(logs_app, pg_db, monkeypatch):
    monkeypatch.setenv(
        "SECRET_KEY", "logs-tests-only-secret-with-more-than-thirty-two-bytes"
    )
    alice = crud.create_user(pg_db, "alice", "test-only-hash")
    bob = crud.create_user(pg_db, "bob", "test-only-hash")
    rows = []
    for user in [alice, alice, bob]:
        rows.append(
            crud.create_chat_log(
                pg_db,
                user.id,
                "test-request",
                "질문",
                "답변",
                "success",
                None,
                "openai",
                "test-model",
                10,
            )
        )

    def database_override():
        yield pg_db

    logs_app.dependency_overrides[deps.get_db] = database_override
    with TestClient(logs_app) as client:
        response = client.get(
            f"/api/me/chats?limit=1&offset=1&user_id={bob.id}",
            headers=cookie(alice.id),
        )
        assert response.status_code == 200
        assert [row["chat_id"] for row in response.json()] == [rows[0].id]
        other = client.get("/api/me/chats", headers=cookie(bob.id))
        assert [row["chat_id"] for row in other.json()] == [rows[2].id]
