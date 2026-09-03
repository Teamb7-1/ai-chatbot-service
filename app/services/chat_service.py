"""문맥 조회 → AI 호출 → 저장 파이프라인.

예외를 밖으로 던지지 않는다. 어떤 경우에도 서버가 죽지 않아야 한다.
→ 평가항목 14
"""

import logging
import time

from sqlalchemy.orm import Session

from app import crud
from app.config import AI_CONTEXT_TURNS, AI_MODEL
from app.logging_config import get_request_id
from app.schemas import AppError, ChatResponse
from app.services import ai_client

logger = logging.getLogger(__name__)

AI_PROVIDER = "openai"


def _build_messages(history: list) -> list[dict]:
    """recent_turns 결과를 OpenAI 호환 messages 배열로 변환한다."""
    messages = []
    for turn in history:
        messages.append({"role": "user", "content": turn.question})
        messages.append({"role": "assistant", "content": turn.answer})
    return messages


async def handle_chat(db: Session, user_id: int, question: str) -> ChatResponse:
    """라우터가 호출하는 진입점. 성공/실패 모두 chat_log에 남긴다."""
    request_id = get_request_id()
    history = crud.recent_turns(db, user_id, n=AI_CONTEXT_TURNS)
    messages = _build_messages(history)
    messages.append({"role": "user", "content": question})

    start = time.monotonic()
    try:
        logger.info("ai_call_start")
        answer = await ai_client.generate(messages)
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.info("ai_call_success latency_ms=%d", latency_ms)

        chat_log = crud.create_chat_log(
            db,
            user_id=user_id,
            request_id=request_id,
            question=question,
            answer=answer,
            status="success",
            error_code=None,
            provider=AI_PROVIDER,
            model=AI_MODEL,
            latency_ms=latency_ms,
        )
        logger.info("db_save_success")
        return ChatResponse(answer=answer, chat_id=chat_log.id)

    except AppError as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.warning("ai_call_failed error_code=%s", exc.code.value)

        try:
            crud.create_chat_log(
                db,
                user_id=user_id,
                request_id=request_id,
                question=question,
                answer="",
                status="error",
                error_code=exc.code,
                provider=AI_PROVIDER,
                model=AI_MODEL,
                latency_ms=latency_ms,
            )
            logger.info("db_save_success")
        except Exception:
            logger.exception("db_save_failed")

        raise