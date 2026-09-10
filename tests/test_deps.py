"""공유 인증 dependency의 쿠키·세션 경계를 검증한다."""

from datetime import timedelta
from unittest.mock import Mock

import jwt
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app import crud, deps
from app.main import app
from app.models import User
from app.schemas import ERROR_MESSAGES, AppError, ErrorCode
from app.security import JWT_ALGORITHM, create_access_token

TEST_SECRET = "test-secret-key-with-more-than-thirty-two-bytes"


@app.get("/api/_t/deps/current-user")
def _t_current_user(user: deps.CurrentUser, db: deps.DbSession):
    return {"id": user.id}


@app.get("/api/_t/deps/route-error")
def _t_route_error(user: deps.CurrentUser, db: deps.DbSession):
    raise RuntimeError("route failed after dependency resolution")


@pytest.fixture(autouse=True)
def authentication_boundary(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET)
    session = Mock(spec=Session)
    session_factory = Mock(return_value=session)
    monkeypatch.setattr(deps, "SessionLocal", session_factory)
    return session, session_factory


@pytest.fixture
def user():
    return User(id=7, username="alice", password_hash="already-hashed")


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _cookie_headers(token: str) -> dict[str, str]:
    return {"Cookie": f"{deps.ACCESS_TOKEN_COOKIE_NAME}={token}"}


def test_유효한_쿠키는_현재_User_객체를_반환한다(authentication_boundary, user, monkeypatch):
    session, _ = authentication_boundary
    monkeypatch.setattr(crud, "get_user_by_id", Mock(return_value=user))
    request = Request(
        {
            "type": "http",
            "headers": [(b"cookie", f"access_token={create_access_token(7)}".encode())],
        }
    )

    assert deps.get_current_user(request, session) is user
    crud.get_user_by_id.assert_called_once_with(session, 7)


def test_성공_요청은_Session_하나를_공유하고_닫는다(
    authentication_boundary, client, user, monkeypatch
):
    session, session_factory = authentication_boundary
    monkeypatch.setattr(crud, "get_user_by_id", Mock(return_value=user))

    response = client.get(
        "/api/_t/deps/current-user", headers=_cookie_headers(create_access_token(7))
    )

    assert response.json() == {"id": 7}
    assert session_factory.call_count == 1
    crud.get_user_by_id.assert_called_once_with(session, 7)
    session.close.assert_called_once_with()


def test_쿠키_없는_요청과_Bearer_헤더는_401이고_Session을_닫는다(
    authentication_boundary, client
):
    session, session_factory = authentication_boundary

    response = client.get(
        "/api/_t/deps/current-user",
        headers={"Authorization": f"Bearer {create_access_token(7)}"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error_code": "NOT_AUTHENTICATED",
        "message": ERROR_MESSAGES[ErrorCode.NOT_AUTHENTICATED],
    }
    session_factory.assert_called_once_with()
    session.close.assert_called_once_with()


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(lambda: "not-a-jwt", id="malformed"),
        pytest.param(lambda: create_access_token(7, timedelta(seconds=-1)), id="expired"),
        pytest.param(
            lambda: jwt.encode(
                {"sub": "7", "exp": 4_000_000_000},
                "another-secret-key-with-more-than-thirty-two-bytes",
                algorithm=JWT_ALGORITHM,
            ),
            id="invalid-signature",
        ),
    ],
)
def test_유효하지_않은_JWT는_401이고_Session을_닫는다(
    authentication_boundary, client, token
):
    session, session_factory = authentication_boundary

    response = client.get("/api/_t/deps/current-user", headers=_cookie_headers(token()))

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
    session_factory.assert_called_once_with()
    session.close.assert_called_once_with()


def test_사라진_사용자는_401이고_Session을_닫는다(
    authentication_boundary, client, monkeypatch
):
    session, _ = authentication_boundary
    monkeypatch.setattr(crud, "get_user_by_id", Mock(return_value=None))

    response = client.get(
        "/api/_t/deps/current-user", headers=_cookie_headers(create_access_token(7))
    )

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
    session.close.assert_called_once_with()


@pytest.mark.parametrize("failure", ["secret-key", "database"])
def test_설정과_DB_오류는_500으로_유지하고_Session을_닫는다(
    authentication_boundary, client, monkeypatch, failure
):
    session, _ = authentication_boundary
    token = create_access_token(7)
    if failure == "secret-key":
        monkeypatch.delenv("SECRET_KEY")
    else:
        monkeypatch.setattr(
            crud,
            "get_user_by_id",
            Mock(side_effect=OperationalError("SELECT", {}, Exception("db down"))),
        )

    response = client.get("/api/_t/deps/current-user", headers=_cookie_headers(token))

    assert response.status_code == 500
    assert response.json()["error_code"] == "INTERNAL_ERROR"
    session.close.assert_called_once_with()


def test_라우트_실패_뒤에도_Session을_닫는다(
    authentication_boundary, client, user, monkeypatch
):
    session, session_factory = authentication_boundary
    monkeypatch.setattr(crud, "get_user_by_id", Mock(return_value=user))

    response = client.get(
        "/api/_t/deps/route-error", headers=_cookie_headers(create_access_token(7))
    )

    assert response.status_code == 500
    assert session_factory.call_count == 1
    session.close.assert_called_once_with()


def test_비어있는_쿠키는_인증_실패다():
    request = Request({"type": "http", "headers": [(b"cookie", b"access_token=")]})

    with pytest.raises(AppError) as raised:
        deps.get_current_user(request, Mock(spec=Session))

    assert raised.value.code is ErrorCode.NOT_AUTHENTICATED
