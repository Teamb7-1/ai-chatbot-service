"""AI 호출이 모여 있는 유일한 파일.

Codyssey 공개 API(OpenAI 호환)를 호출한다. API 키는 이 파일 밖으로
나가지 않는다.  → 평가항목 27
"""

import os

from openai import AsyncOpenAI

from app.config import AI_MODEL

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    """지연 초기화. import 시점이 아니라 첫 호출 시점에 키를 읽는다."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=os.environ["AI_API_KEY"],
            timeout=float(os.environ.get("AI_TIMEOUT_SECONDS", "10")),
        )
    return _client


async def generate(messages: list[dict]) -> str:
    """messages를 받아 AI 응답 텍스트를 반환한다.

    타임아웃·재시도·오류 매핑은 다음 커밋에서 추가한다.
    """
    client = _get_client()
    response = await client.chat.completions.create(
        model=AI_MODEL,
        messages=messages,
    )
    return response.choices[0].message.content
    