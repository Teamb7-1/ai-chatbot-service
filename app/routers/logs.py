"""로그인한 사용자의 대화 기록 조회 API. 앱에 router 등록은 D 담당이다."""

import logging
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy.exc import SQLAlchemyError

from app import crud
from app.deps import CurrentUser, DbSession
from app.schemas import AppError, ChatLogItem, ErrorCode

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/me", tags=["logs"])


@router.get("/chats", response_model=list[ChatLogItem])
def list_my_chats(
    user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=0)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ChatLogItem]:
    """성공·실패 기록을 최신순으로 반환한다. 소유자는 쿠키 인증으로만 정한다."""
    try:
        logs = crud.list_chat_logs(db, user.id, limit=limit, offset=offset)
    except SQLAlchemyError as exc:
        # SQL 예외 본문/파라미터에 민감한 값이 있을 수 있어 종류만 남긴다.
        logger.error(
            "db_read_failed user_id=%s error_type=%s", user.id, type(exc).__name__
        )
        raise AppError(ErrorCode.INTERNAL_ERROR) from exc
    return [ChatLogItem.model_validate(log) for log in logs]
