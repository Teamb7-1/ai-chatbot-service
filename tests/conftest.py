"""pytest 전역 설정.

database.py(#70)는 import 시점에 DATABASE_URL 을 요구한다 — fail-fast 설계다.
그 파일을 직·간접으로 import 하는 테스트 모듈이 하나라도 생기면, 값이 없을 때
수집 단계에서 통째로 죽는다. 여기서 더미를 깔아 import 는 통과하게 한다.

create_engine() 은 첫 connect() 까지 실제로 연결하지 않으므로 더미 URL 은 안전하다.
실제 DB 가 필요한 테스트는 스스로 monkeypatch 하거나 skip 한다.

setdefault 라서 진짜 값이 이미 있으면 건드리지 않는다. 그리고 C 의
test_DATABASE_URL이_없으면_… 는 서브프로세스에서 environ.pop 하므로 영향 없다.
"""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test"
)


@pytest.fixture
def pg_connection():
    """명시한 테스트 DB의 고유 스키마에서만 실행하고 DDL/데이터를 롤백한다.

    #66/#36 테스트가 공유한다. 앱의 DATABASE_URL은
    사용하지 않는다. TEST_DATABASE_URL에는 운영 DB를 지정하지 않는다.
    """
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL 미설정: 실제 PostgreSQL 검증은 실행하지 않음")
    url = make_url(database_url)
    if url.drivername != "postgresql+psycopg":
        pytest.fail("TEST_DATABASE_URL은 postgresql+psycopg:// 형식이어야 함")

    engine = create_engine(
        url,
        poolclass=NullPool,
        hide_parameters=True,
        connect_args={"connect_timeout": 5},
    )
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                schema = f"test_crud_{uuid4().hex}"
                connection.execute(CreateSchema(schema))
                connection = connection.execution_options(
                    schema_translate_map={None: schema}
                )
                yield connection
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


@pytest.fixture
def pg_db(pg_connection):
    """격리 스키마 안에서 ORM 테스트에 필요한 테이블과 Session을 준비한다."""
    from app.models import ChatLog, User

    User.__table__.create(pg_connection)
    ChatLog.__table__.create(pg_connection)
    with Session(
        bind=pg_connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    ) as db:
        yield db
