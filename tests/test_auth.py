"""인증 API가 shared dependency와 오류 응답 계약을 지키는지 검증한다."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app import crud, deps, security
from app.main import (
    handle_app_error,
    handle_http_exception,
    handle_unexpected,
    handle_validation_error,
)
from app.models import User
from app.routers import auth
from app.schemas import ERROR_MESSAGES, AppError, ErrorCode

TEST_SECRET = "test-secret-key-with-more-than-thirty-two-bytes"
PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def boundary(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET)
    session = Mock(spec=Session)
    monkeypatch.setattr(deps, "SessionLocal", Mock(return_value=session))
    return session


@pytest.fixture
def client(boundary):
    application = FastAPI()
    application.include_router(auth.router)
    application.add_exception_handler(RequestValidationError, handle_validation_error)
    application.add_exception_handler(AppError, handle_app_error)
    application.add_exception_handler(Exception, handle_unexpected)
    application.add_exception_handler(404, handle_http_exception)
    return TestClient(application, raise_server_exceptions=False)


@pytest.fixture
def user():
    return User(id=7, username="alice", password_hash=security.hash_password(PASSWORD))


def _duplicate_error(
    constraint_name: str = "ix_users_username", sqlstate: str = "23505"
) -> IntegrityError:
    original = SimpleNamespace(
        sqlstate=sqlstate, diag=SimpleNamespace(constraint_name=constraint_name)
    )
    return IntegrityError("INSERT", {}, original)


def _cookie_value(response) -> str:
    return response.cookies.get(deps.ACCESS_TOKEN_COOKIE_NAME)


def test_회원가입은_평문을_저장하지_않고_201을_반환한다(client, boundary, monkeypatch):
    def create_user(db, username, password_hash):
        assert db is boundary
        return User(id=7, username=username, password_hash=password_hash)

    monkeypatch.setattr(crud, "create_user", Mock(side_effect=create_user))

    response = client.post(
        "/api/auth/register", json={"username": "alice", "password": PASSWORD}
    )

    assert response.status_code == 201
    assert response.json() == {"id": 7, "username": "alice"}
    stored_hash = crud.create_user.call_args.args[2]
    assert stored_hash != PASSWORD
    assert security.verify_password(PASSWORD, stored_hash)


def test_회원가입_입력_검증은_422를_반환한다(client):
    response = client.post(
        "/api/auth/register", json={"username": "ab", "password": "short"}
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_정확한_username_중복만_409로_변환한다(client, monkeypatch):
    monkeypatch.setattr(crud, "create_user", Mock(side_effect=_duplicate_error()))

    response = client.post(
        "/api/auth/register", json={"username": "alice", "password": PASSWORD}
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "DUPLICATE_USERNAME"


@pytest.mark.parametrize(
    "error",
    [
        _duplicate_error("another_unique_constraint"),
        _duplicate_error(sqlstate="23502"),
        OperationalError("INSERT", {}, Exception("database unavailable")),
    ],
    ids=["other-unique-constraint", "other-sqlstate", "database-error"],
)
def test_그밖의_저장_오류는_500으로_유지한다(client, monkeypatch, error):
    monkeypatch.setattr(crud, "create_user", Mock(side_effect=error))

    response = client.post(
        "/api/auth/register", json={"username": "alice", "password": PASSWORD}
    )

    assert response.status_code == 500
    assert response.json()["error_code"] == "INTERNAL_ERROR"
    assert "database unavailable" not in response.text


@pytest.mark.parametrize(
    "found_user", [False, True], ids=["unknown-user", "wrong-password"]
)
def test_로그인_실패는_검증을_한번만_수행하고_같은_401을_반환한다(
    client, monkeypatch, user, found_user
):
    account = user if found_user else None
    spy = Mock(wraps=security.verify_password)
    monkeypatch.setattr(crud, "get_user_by_username", Mock(return_value=account))
    monkeypatch.setattr(auth, "verify_password", spy)

    response = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_CREDENTIALS"
    spy.assert_called_once()


def test_로그인은_HTTP쿠키와_검증가능한_JWT를_발급한다(client, monkeypatch, user):
    monkeypatch.setattr(crud, "get_user_by_username", Mock(return_value=user))

    response = client.post(
        "/api/auth/login", json={"username": "alice", "password": PASSWORD}
    )

    cookie = response.headers["set-cookie"]
    assert response.json() == {"id": 7, "username": "alice"}
    assert "HttpOnly" in cookie and "Max-Age=3600" in cookie
    assert "Path=/" in cookie and "SameSite=lax" in cookie and "Secure" not in cookie
    assert security.decode_access_token(_cookie_value(response)) == 7


def test_HTTPS_로그인은_Secure_쿠키를_발급한다(boundary, monkeypatch, user):
    monkeypatch.setattr(crud, "get_user_by_username", Mock(return_value=user))
    application = FastAPI()
    application.include_router(auth.router)
    application.add_exception_handler(AppError, handle_app_error)

    response = TestClient(application, base_url="https://testserver").post(
        "/api/auth/login", json={"username": "alice", "password": PASSWORD}
    )

    assert "Secure" in response.headers["set-cookie"]


def test_현재_사용자_조회와_로그아웃은_쿠키를_삭제한다(client, monkeypatch, user):
    monkeypatch.setattr(crud, "get_user_by_username", Mock(return_value=user))
    monkeypatch.setattr(crud, "get_user_by_id", Mock(return_value=user))
    client.post("/api/auth/login", json={"username": "alice", "password": PASSWORD})

    me = client.get("/api/me")
    logout = client.post("/api/auth/logout")
    after_logout = client.get("/api/me")

    assert me.status_code == 200 and me.json() == {"id": 7, "username": "alice"}
    assert logout.status_code == 204 and logout.content == b""
    assert "Max-Age=0" in logout.headers["set-cookie"]
    assert "HttpOnly" in logout.headers["set-cookie"]
    assert after_logout.status_code == 401
    assert after_logout.json()["error_code"] == "NOT_AUTHENTICATED"


@pytest.mark.parametrize(
    "method,path", [("GET", "/api/me"), ("POST", "/api/auth/logout")]
)
def test_미인증_사용자_조회와_로그아웃은_401_JSON이다(client, method, path):
    response = client.request(method, path)

    assert response.status_code == 401
    assert response.json() == {
        "error_code": "NOT_AUTHENTICATED",
        "message": ERROR_MESSAGES[ErrorCode.NOT_AUTHENTICATED],
    }


def test_누락된_SECRET_KEY는_500으로_유지한다(client, monkeypatch, user):
    monkeypatch.setattr(crud, "get_user_by_username", Mock(return_value=user))
    monkeypatch.delenv("SECRET_KEY")

    response = client.post(
        "/api/auth/login", json={"username": "alice", "password": PASSWORD}
    )

    assert response.status_code == 500
    assert response.json()["error_code"] == "INTERNAL_ERROR"
    assert "SECRET_KEY" not in response.text
