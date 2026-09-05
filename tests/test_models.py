"""인증 User ORM 모델의 PostgreSQL 테이블 계약을 검증한다."""

from sqlalchemy import BigInteger, DateTime, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.database import Base
from app.models import User


def test_User가_users_테이블과_합의된_필드만_정의한다():
    table = User.__table__

    assert issubclass(User, Base)
    assert table.name == "users"
    assert list(table.columns.keys()) == [
        "id",
        "username",
        "password_hash",
        "created_at",
    ]
    assert "password" not in table.columns


def test_User_id와_username이_식별_계약을_지킨다():
    table = User.__table__
    username_index = next(iter(table.indexes))

    assert isinstance(table.c.id.type, BigInteger)
    assert table.c.id.primary_key is True
    assert isinstance(table.c.username.type, Text)
    assert table.c.username.unique is True
    assert table.c.username.index is True
    assert username_index.unique is True
    assert [column.name for column in username_index.columns] == ["username"]


def test_User가_hash와_timezone_생성시각을_DB에_저장한다():
    table = User.__table__
    created_at = table.c.created_at

    assert isinstance(table.c.password_hash.type, Text)
    assert isinstance(created_at.type, DateTime)
    assert created_at.type.timezone is True
    assert created_at.server_default is not None

    dialect = postgresql.dialect()
    table_ddl = str(CreateTable(table).compile(dialect=dialect))
    index_ddl = str(CreateIndex(next(iter(table.indexes))).compile(dialect=dialect))

    assert "id BIGSERIAL NOT NULL" in table_ddl
    assert "password_hash TEXT NOT NULL" in table_ddl
    assert "created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL" in table_ddl
    assert "CREATE UNIQUE INDEX ix_users_username ON users (username)" == index_ddl
