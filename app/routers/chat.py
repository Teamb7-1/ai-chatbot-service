"""POST /api/chat — 질문 수신 → chat_service 호출 → 응답 반환."""

from fastapi import APIRouter

from app.deps import CurrentUser, DbSession
from app.schemas import ChatRequest, ChatResponse
from app.services.chat_service import handle_chat

router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, user: CurrentUser, db: DbSession):
    return await handle_chat(db, user.id, payload.message)
