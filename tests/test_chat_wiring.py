"""chat 라우터가 앱에 연결됐는지 — /api/chat 의 배선만 본다 (#94).

파이프라인 자체(문맥 조회·AI 호출·저장)는 B 의 chat_service 테스트가 맡는다.
여기서는 라우트가 존재하고, 인증이 앞에 서고, 라우터가 handle_chat 에
user.id 와 message 를 그대로 넘기는지만 확인한다.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, deps
from app.main import app
from app.models import User
from app.routers import chat as chat_router
from app.schemas import ChatResponse
from app.security import create_access_token

TEST_SECRET = "test-secret-key-with-more-than-thirty-two-bytes"


@pytest.fixture(autouse=True)
def no_database(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET)
    monkeypatch.setattr(deps, "SessionLocal", Mock(return_value=Mock(spec=Session)))


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def logged_in(client, monkeypatch):
    user = User(id=7, username="alice", password_hash="already-hashed")
    monkeypatch.setattr(crud, "get_user_by_id", Mock(return_value=user))
    client.cookies.set(deps.ACCESS_TOKEN_COOKIE_NAME, create_access_token(user.id))
    return client


def test_api_chat_이_문서에_있다(client):
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/chat" in paths
    assert "post" in paths["/api/chat"]


def test_비로그인_질문은_JSON_401(client):
    response = client.post("/api/chat", json={"message": "안녕"})

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


def test_로그인_질문은_handle_chat_에_사용자와_메시지를_넘긴다(logged_in, monkeypatch):
    fake = AsyncMock(return_value=ChatResponse(answer="답", chat_id=42))
    monkeypatch.setattr(chat_router, "handle_chat", fake)

    response = logged_in.post("/api/chat", json={"message": "IndexError 는 왜 나요?"})

    assert response.status_code == 200
    assert response.json() == {"answer": "답", "chat_id": 42}
    fake.assert_awaited_once()
    _db, user_id, message = fake.await_args.args
    assert user_id == 7
    assert message == "IndexError 는 왜 나요?"


def test_빈_메시지는_422가_아니라_계약된_오류_형식(logged_in):
    """검증 실패도 {error_code, message} 한 형식으로 나간다 (main.py 핸들러)."""
    response = logged_in.post("/api/chat", json={"message": ""})

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
