"""수동 초기화: python -m scripts.create_tables --confirm (리포 루트에서 실행).

DATABASE_URL은 실행 환경에 미리 주입한다. .env 자동 로딩, 데이터 삭제,
기존 테이블 변경, 앱 시작 시 실행은 하지 않는다. 실제 Neon 실행은 D 담당.
"""

import argparse
import sys

from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError


def create_tables(bind: Engine | Connection) -> None:
    """등록된 두 테이블을 의존 순서대로 만들고 기존 테이블은 유지한다."""
    from app.models import Base, ChatLog, User

    if bind.dialect.name != "postgresql":
        raise ValueError("Table initialization requires PostgreSQL")
    Base.metadata.create_all(
        bind=bind,
        tables=[User.__table__, ChatLog.__table__],
        checkfirst=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create missing users/chat_logs tables."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        required=True,
        help="Confirm DATABASE_URL targets the intended Neon branch before running.",
    )
    parser.parse_args(argv)

    engine = None
    try:
        from app.database import engine

        create_tables(engine)
    except (SQLAlchemyError, RuntimeError, ValueError, ImportError, OSError) as exc:
        # 연결 정보나 SQL 파라미터가 포함될 수 있는 예외 본문은 표시하지 않는다.
        print(
            f"Table creation failed ({type(exc).__name__}). "
            "Check DATABASE_URL, connectivity and schema permissions.",
            file=sys.stderr,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()

    print("Schema ready: users, chat_logs. Existing tables were kept unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
