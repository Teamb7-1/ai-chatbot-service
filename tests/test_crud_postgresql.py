"""테스트 전용 PostgreSQL에서 사용자 CRUD를 검증한다.

TEST_DATABASE_URL에 postgresql+psycopg:// 형식의 테스트용 주소를 설정한 뒤
python -m pytest -q tests/test_crud_postgresql.py 로 실행한다.
설정이 없으면 명시적으로 skip하며, 앱의 DATABASE_URL로 대체하지 않는다.
운영 URL은 사용하지 않는다. 테스트 계정에는 CREATE SCHEMA 권한이 필요하다.

각 테스트는 고유 스키마와 외부 트랜잭션으로 격리한다. CRUD의 commit/rollback은
SAVEPOINT에만 적용하고, 종료 시 스키마와 데이터를 외부 rollback으로 되돌린다.
기존 users 테이블이나 데이터는 변경하지 않는다.
"""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app import crud
from app.models import User


def test_PostgreSQL에서_생성한_User를_두_키로_다시_조회한다(pg_db):
    user = crud.create_user(pg_db, "alice", "already-hashed")
    assert isinstance(user, User)
    assert isinstance(user.id, int) and user.id > 0
    assert isinstance(user.created_at, datetime)
    assert user.created_at.utcoffset() is not None
    user_id = user.id
    pg_db.expunge_all()

    by_username = crud.get_user_by_username(pg_db, "alice")
    assert by_username.id == user_id
    assert by_username.password_hash == "already-hashed"
    pg_db.expunge_all()

    by_id = crud.get_user_by_id(pg_db, user_id)
    assert by_id.username == "alice"
    assert by_id.password_hash == "already-hashed"


def test_PostgreSQL에서_존재하지_않는_User는_None을_반환한다(pg_db):
    crud.create_user(pg_db, "alice", "already-hashed")

    assert crud.get_user_by_username(pg_db, "missing") is None
    assert crud.get_user_by_id(pg_db, -1) is None


def test_PostgreSQL에서_username중복_후에도_같은_Session으로_읽고_쓴다(pg_db):
    original = crud.create_user(pg_db, "alice", "original-hash")
    original_id = original.id

    with pytest.raises(IntegrityError) as raised:
        crud.create_user(pg_db, "alice", "duplicate-hash")

    assert raised.value.orig.sqlstate == "23505"
    assert raised.value.orig.diag.constraint_name == "ix_users_username"
    assert pg_db.is_active
    pg_db.expunge_all()
    saved = crud.get_user_by_username(pg_db, "alice")
    assert saved.id == original_id
    assert saved.password_hash == "original-hash"
    another = crud.create_user(pg_db, "bob", "another-hash")
    assert another.id != original_id
    assert crud.get_user_by_id(pg_db, another.id) is another


def test_PostgreSQL에서_다른_제약_위반을_username중복과_혼동하지_않는다(pg_db):
    with pytest.raises(IntegrityError) as raised:
        crud.create_user(pg_db, "alice", None)

    assert raised.value.orig.sqlstate == "23502"
    assert pg_db.is_active
    assert crud.get_user_by_username(pg_db, "alice") is None
    assert crud.create_user(pg_db, "alice", "valid-hash").username == "alice"
