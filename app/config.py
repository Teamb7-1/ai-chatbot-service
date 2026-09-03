"""설정 상수 — 환경변수가 아닌 것들이 모이는 곳.

여기 두는 기준: 비밀이 아니고, 환경마다 같아도 되고, 운영 중 바꿀 일이 없는 값.
셋 중 하나라도 아니면 환경변수로 간다(.env.example).
AI_MODEL, AI_CONTEXT_TURNS 가 그 기준으로 상수가 됐다.  → #44

경로 상수도 여기 둔다. main.py 와 routers/pages.py 가 같은 계산을 두 번
하고 있었는데, 한쪽만 고치면 배포에서만 깨지는 종류의 버그가 된다.
"""

from pathlib import Path

# ── 경로 ────────────────────────────────────────────────────────
#
# Vercel 함수의 작업 디렉터리는 이 파일이 있는 폴더가 아니라 프로젝트 루트(/var/task)다.
# 상대경로로 쓰면 /var/task/templates 를 찾다 실패한다.
# 실측 확인: cwd=/var/task, BASE_DIR=/var/task/app
BASE_DIR = Path(__file__).resolve().parent

TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


# ── AI ──────────────────────────────────────────────────────────

AI_MODEL = "gpt-5.4-mini"
AI_CONTEXT_TURNS = 5
AI_BASE_URL = "https://copa.codyssey.kr/v1"
AI_MAX_OUTPUT_TOKENS = 1000

SYSTEM_PROMPT = """너는 컴퓨터공학을 공부하는 학생들을 돕는 코딩 학습 튜터야.

역할:
- CS 개념, 알고리즘, 문법 오류, 코드 이해를 돕는다.
- 사용자가 에러 메시지나 코드를 통째로 붙여넣을 수 있으니, 그 안에서 핵심 원인을 짚어준다.

답변 방식:
- 정답만 던지지 말고, 왜 그런지 원리를 짧게 설명한다.
- 코드 예시는 필요한 부분만 짧게 보여준다. 전체 코드를 새로 짜주지 않는다.
- 이전 대화 맥락이 있다면 자연스럽게 이어서 답한다.
- 모르면 모른다고 말하고, 추측을 사실처럼 말하지 않는다.
- 답변은 한국어로 한다.
"""
