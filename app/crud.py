"""동기 SQLAlchemy Session으로 사용자 데이터를 조회하고 저장한다."""

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import User


def get_user_by_username(db: Session, username: str) -> User | None:
    """username이 일치하는 사용자를 반환한다. 없으면 None을 반환한다."""
    return db.scalar(select(User).where(User.username == username))


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """기본키로 사용자를 조회한다. 없으면 None을 반환한다."""
    return db.get(User, user_id)


def create_user(db: Session, username: str, password_hash: str) -> User:
    """이미 해시된 비밀번호로 사용자를 생성하고 현재 트랜잭션을 커밋한다.

    DB 오류는 rollback 후 그대로 전달한다. 호출자는 IntegrityError.orig의
    sqlstate(23505)와 diag.constraint_name(ix_users_username)으로 username
    중복을 구분할 수 있다. 해싱과 HTTP 오류 변환, Session 종료는 호출자 책임이다.
    #70의 SessionLocal(expire_on_commit=False)을 사용한다.
    """
    user = User(username=username, password_hash=password_hash)

    try:
        db.add(user)
        db.flush()
        # id와 created_at을 커밋 전에 읽어 refresh 실패도 rollback할 수 있게 한다.
        db.refresh(user)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    return user
