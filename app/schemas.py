"""요청/응답 스키마 — 계약 ①.

바깥 경계(HTTP)의 입출력 형식을 여기 한 곳에서 정의한다.
라우터에서 dict 를 즉석 조립하지 않는다.  → 평가항목 19

DB 테이블 정의는 여기가 아니라 `models.py` 다. 같은 "스키마"라는 말을 쓰지만
이 파일은 JSON 형식을, models.py 는 테이블 구조를 다룬다.
"""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ErrorCode(StrEnum):
    """오류 코드 8종 — 계획서 7장 표와 1:1 대응.

    B가 AI 실패를 이 코드로 옮기고, D가 화면 문구로 옮긴다.
    문자열을 직접 쓰지 말고 이 enum 을 import 해서 쓴다.
    """

    VALIDATION_ERROR = "VALIDATION_ERROR"        # 422
    NOT_AUTHENTICATED = "NOT_AUTHENTICATED"      # 401
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"  # 401
    DUPLICATE_USERNAME = "DUPLICATE_USERNAME"    # 409
    AI_TIMEOUT = "AI_TIMEOUT"                    # 503
    RATE_LIMITED = "RATE_LIMITED"                # 503
    AI_ERROR = "AI_ERROR"                        # 503
    AI_UNKNOWN = "AI_UNKNOWN"                    # 503


class ErrorResponse(BaseModel):
    """모든 오류 응답의 공통 형식."""

    error_code: ErrorCode
    message: str


# ─────────────────────────────  인증 (A가 사용)  ─────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    # ORM 객체에서 바로 만들 수 있게 한다: UserResponse.model_validate(user)
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


# ─────────────────────────────  챗봇 (B가 사용)  ─────────────────────────────

# 과제 명세는 "입력 검증 로직 최소 1개"만 요구하고 길이 숫자를 정하지 않는다(L90·L211).
# 이 값은 팀이 고른 것이다 — 코딩 학습 챗봇이라 사용자가 에러와 코드를 통째로
# 붙여넣는 것이 주 사용례이므로 파일 하나가 들어갈 크기로 잡았다.
MESSAGE_MAX_LENGTH = 4000


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MESSAGE_MAX_LENGTH)

    @field_validator("message")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        """공백만 입력된 메시지를 막는다.  → 평가항목 16

        검사만 하고 원본을 그대로 돌려준다. strip 한 값을 반환하면
        DB에 저장된 질문이 사용자가 실제로 보낸 것과 달라지는데,
        chat_logs 는 "무슨 일이 있었는지"를 남기는 테이블이므로
        입력을 손대지 않는 쪽을 택했다.
        """
        if not value.strip():
            raise ValueError("메시지를 입력해 주세요.")
        return value


class ChatResponse(BaseModel):
    answer: str
    chat_id: int


# ─────────────────────────  대화 로그 조회 (C가 사용)  ─────────────────────────

class ChatLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chat_id: int
    request_id: str
    question: str
    answer: str
    status: Literal["success", "error"]
    error_code: ErrorCode | None = None
    latency_ms: int
    created_at: datetime
