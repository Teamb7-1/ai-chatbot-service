"""라우터가 공유하는 DB 세션과 현재 사용자 의존성."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app import crud
from app.database import SessionLocal
from app.models import User
from app.schemas import AppError, ErrorCode
from app.security import TokenValidationError, decode_access_token

ACCESS_TOKEN_COOKIE_NAME = "access_token"


def get_db() -> Generator[Session, None, None]:
    """요청마다 Session 하나를 만들고 응답 뒤에 항상 종료한다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, db: DbSession) -> User:
    """HttpOnly 쿠키의 access token으로 현재 사용자를 조회한다."""
    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if not token:
        raise AppError(ErrorCode.NOT_AUTHENTICATED)

    try:
        user_id = decode_access_token(token)
    except TokenValidationError as exc:
        raise AppError(ErrorCode.NOT_AUTHENTICATED) from exc

    user = crud.get_user_by_id(db, user_id)
    if user is None:
        raise AppError(ErrorCode.NOT_AUTHENTICATED)

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
