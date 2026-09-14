"""동기 SQLAlchemy Session으로 사용자와 대화 데이터를 조회하고 저장한다."""

import logging
from typing import Literal

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import AI_CONTEXT_TURNS
from app.models import ChatLog, User

logger = logging.getLogger(__name__)


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


def create_chat_log(
    db: Session,
    user_id: int,
    request_id: str,
    question: str,
    answer: str,
    status: Literal["success", "error"],
    error_code: str | None,
    provider: str,
    model: str,
    latency_ms: int,
) -> ChatLog:
    """AI 성공/실패 결과를 원문 그대로 저장하고 현재 트랜잭션을 커밋한다.

    실패한 AI 응답의 answer는 빈 문자열, 정상 응답의 error_code는 None이다.
    DB 오류는 rollback 후 그대로 전달하며, Session 종료는 호출자가 담당한다.
    #70의 SessionLocal(expire_on_commit=False)을 사용한다.
    """
    chat_log = ChatLog(
        user_id=user_id,
        request_id=request_id,
        question=question,
        answer=answer,
        status=status,
        error_code=error_code,
        provider=provider,
        model=model,
        latency_ms=latency_ms,
    )
    try:
        db.add(chat_log)
        db.flush()
        db.refresh(chat_log)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        # SQL 예외 문자열에는 질문/답변이 들어갈 수 있으므로 타입만 기록한다.
        logger.error(
            "db_save_failed user_id=%s chat_request_id=%s error_type=%s",
            user_id,
            request_id,
            type(exc).__name__,
        )
        raise

    logger.info(
        "db_save_success chat_id=%s user_id=%s chat_request_id=%s",
        chat_log.id,
        user_id,
        request_id,
    )
    return chat_log


def recent_turns(
    db: Session,
    user_id: int,
    n: int = AI_CONTEXT_TURNS,
) -> list[ChatLog]:
    """해당 사용자의 최근 성공 n개를 골라 과거→현재 순서로 반환한다."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return []
    statement = (
        select(ChatLog)
        .where(ChatLog.user_id == user_id, ChatLog.status == "success")
        .order_by(ChatLog.created_at.desc(), ChatLog.id.desc())
        .limit(n)
    )
    # 시각이 같으면 id로 순서를 고정해 페이지/문맥의 순서가 흔들리지 않게 한다.
    return list(reversed(db.scalars(statement).all()))


def list_chat_logs(
    db: Session,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[ChatLog]:
    """해당 사용자의 성공/실패 기록을 최신순으로 페이지 조회한다."""
    if limit < 0 or offset < 0:
        raise ValueError("limit and offset must be non-negative")
    if limit == 0:
        return []
    statement = (
        select(ChatLog)
        .where(ChatLog.user_id == user_id)
        .order_by(ChatLog.created_at.desc(), ChatLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement).all())
