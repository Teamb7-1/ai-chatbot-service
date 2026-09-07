"""실제 DB 연결 없이 사용자 CRUD의 쿼리·반환값·트랜잭션 계약을 검증한다."""

from datetime import datetime, timezone
from inspect import iscoroutinefunction
from unittest.mock import Mock, call

import pytest
from psycopg.errors import NotNullViolation, UniqueViolation
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app import crud
from app.models import User


@pytest.fixture
def db():
    return Mock(spec=Session)


@pytest.mark.parametrize(
    "function",
    [crud.get_user_by_username, crud.get_user_by_id, crud.create_user],
)
def test_사용자_CRUD는_동기_함수다(function):
    assert not iscoroutinefunction(function)


@pytest.mark.parametrize("exists", [True, False])
def test_username_조회는_User_또는_None을_반환한다(db, exists):
    username = "o'reilly'; --"
    expected = User(id=7, username=username, password_hash="already-hashed")
    db.scalar.return_value = expected if exists else None

    result = crud.get_user_by_username(db, username)

    assert result is db.scalar.return_value
    db.scalar.assert_called_once()
    statement = db.scalar.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    assert statement.column_descriptions[0]["entity"] is User
    assert "WHERE users.username = %(username_1)s" in str(compiled)
    assert compiled.params == {"username_1": username}
    assert username not in str(compiled)
    db.commit.assert_not_called()
    db.close.assert_not_called()


@pytest.mark.parametrize("exists", [True, False])
def test_id_조회는_User_또는_None을_반환한다(db, exists):
    expected = User(id=7, username="alice", password_hash="already-hashed")
    db.get.return_value = expected if exists else None

    result = crud.get_user_by_id(db, 7)

    assert result is db.get.return_value
    db.get.assert_called_once_with(User, 7)
    db.commit.assert_not_called()
    db.close.assert_not_called()


def test_생성은_hash를_그대로_저장하고_커밋한_User를_반환한다(db):
    created_at = datetime(2026, 9, 7, tzinfo=timezone.utc)

    def refresh(user):
        user.id = 7
        user.created_at = created_at

    db.refresh.side_effect = refresh

    user = crud.create_user(db, "alice", "already-hashed")

    assert isinstance(user, User)
    assert user.username == "alice"
    assert user.password_hash == "already-hashed"
    assert user.id == 7
    assert user.created_at == created_at
    assert db.method_calls == [
        call.add(user),
        call.flush(),
        call.refresh(user),
        call.commit(),
    ]


@pytest.mark.parametrize("stage", ["flush", "refresh", "commit"])
@pytest.mark.parametrize(
    "error",
    [
        IntegrityError("INSERT", {}, UniqueViolation("duplicate username")),
        IntegrityError("INSERT", {}, NotNullViolation("missing password_hash")),
        OperationalError("INSERT", {}, Exception("connection failed")),
    ],
)
def test_저장_오류는_rollback_후_원본_예외를_전달한다(db, stage, error):
    getattr(db, stage).side_effect = error

    with pytest.raises(type(error)) as raised:
        crud.create_user(db, "alice", "already-hashed")

    assert raised.value is error
    assert raised.value.orig is error.orig
    db.rollback.assert_called_once_with()
    assert db.method_calls[-1] == call.rollback()
    if stage != "commit":
        db.commit.assert_not_called()
    db.close.assert_not_called()


@pytest.mark.parametrize("lookup", ["username", "id"])
def test_조회_장애를_사용자_없음으로_숨기지_않는다(db, lookup):
    error = OperationalError("SELECT", {}, Exception("connection failed"))
    if lookup == "username":
        db.scalar.side_effect = error
        function, value = crud.get_user_by_username, "alice"
    else:
        db.get.side_effect = error
        function, value = crud.get_user_by_id, 7

    with pytest.raises(OperationalError) as raised:
        function(db, value)

    assert raised.value is error
