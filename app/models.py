"""서비스의 SQLAlchemy ORM 모델을 정의한다."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """인증과 사용자별 데이터 소유권의 기준이 되는 사용자."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(Text, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ChatLog(Base):
    """질문 한 번의 답변 또는 AI 오류를 사용자별로 보관한다."""

    __tablename__ = "chat_logs"
    __table_args__ = (
        CheckConstraint("status IN ('success', 'error')", name="ck_chat_logs_status"),
        CheckConstraint("latency_ms >= 0", name="ck_chat_logs_latency_ms"),
        Index("ix_chat_logs_user_created_id", "user_id", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    request_id: Mapped[str] = mapped_column(Text, index=True)
    question: Mapped[str] = mapped_column(Text)
    # AI 실패 시에도 화면 계약에 맞춰 빈 문자열을 저장한다 (NULL 아님).
    answer: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    @property
    def chat_id(self) -> int:
        """B의 .id와 API ChatLogItem의 .chat_id가 같은 번호를 읽도록 한다."""
        return self.id
