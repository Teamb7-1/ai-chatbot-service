"""로깅 설정과 request_id 전파.

한 요청이 남기는 여러 줄을 하나로 묶는 것이 목적이다. 동시 요청이 섞이면
어느 줄이 한 요청인지 알 수 없어 원인 추적이 안 된다.  → 평가항목 30

request_id 는 ContextVar 에 담긴다. **B·C 는 인자로 넘기지 않아도 된다** —
같은 요청 안에서 부른 모든 logger 호출에 자동으로 같은 id 가 붙는다.

    from app.logging_config import get_request_id
    logger.info("ai_call_success latency_ms=%d", ms)   # request_id 자동
    chat_log.request_id = get_request_id()             # DB 저장용
"""

import logging
import sys
import uuid
from contextvars import ContextVar

# 요청 밖에서 찍힌 로그(기동 시점 등)는 "-" 로 남는다.
_request_id: ContextVar[str] = ContextVar("request_id", default="-")

LOG_FORMAT = "%(asctime)s %(levelname)-5s request_id=%(request_id)s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# HTTP 클라이언트 라이브러리는 요청마다 INFO 를 남긴다. AI SDK 대부분이 httpx 를 쓰므로
# 그대로 두면 AI 호출 한 번에 우리 로그 사이로 남의 줄이 끼어든다.
NOISY_LOGGERS = ("httpx", "httpcore", "urllib3")


def new_request_id() -> str:
    """요청 하나를 식별하는 짧은 id. 로그와 chat_logs.request_id 가 같은 값을 쓴다."""
    return uuid.uuid4().hex[:8]


def set_request_id(value: str):
    """요청 시작 시 미들웨어가 부른다. 반환값은 reset 용 토큰이다."""
    return _request_id.set(value)


def reset_request_id(token) -> None:
    _request_id.reset(token)


def get_request_id() -> str:
    """현재 요청의 id. DB에 저장할 때 쓴다."""
    return _request_id.get()


class _RequestIdFilter(logging.Filter):
    """모든 로그 레코드에 request_id 를 넣는다.

    필터를 쓰면 포맷 문자열이 %(request_id)s 를 참조할 수 있다.
    이게 없으면 KeyError 로 로깅 자체가 깨진다.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """stdout 으로 로그를 내보낸다. Vercel 이 함수의 stdout 을 수집한다.

    서버리스는 요청마다 기동될 수 있어 앱 시작 훅이 아니라 import 시점에 부른다.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RequestIdFilter())
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    root = logging.getLogger()
    # 여러 번 불려도 핸들러가 쌓이지 않게 한다 (서버리스에서 실제로 발생한다).
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
