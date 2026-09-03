# 코딩 학습 Q&A 도우미

로그인한 학습자가 언제든 코딩 질문을 던지고, 직전 대화의 문맥을 이어 답을 받는 웹 챗봇.
대화는 전부 DB에 남겨 나중에 되짚어 볼 수 있게 한다.

**서비스 URL — https://b7-ai-chatbot.vercel.app**

---

## 1. 개요

<!-- 담당 A — 문제 정의 · 타겟 사용자 · 핵심 시나리오 (평가항목 1) -->
> 작성 예정

## 2. 기술 스택

| 구분 | 선택 | 비고 |
|---|---|---|
| 언어 · 프레임워크 | Python 3.12 · FastAPI | 과제 지정 |
| 화면 | Jinja2 서버 템플릿 + 채팅 송수신만 `fetch` | 새로고침 없이 대화 유지 |
| DB | 관리형 PostgreSQL · SQLAlchemy 2.x · psycopg | 제공자 9/1 확정 |
| 인증 | JWT + HttpOnly 쿠키 (라이브러리 사용) | |
| AI | 9/1 확정 | 타임아웃 10초 |
| 배포 | Vercel (GitHub Actions에서 CLI 배포) | |

## 3. 시스템 구조

```
브라우저 ──HTTPS──▶ Vercel Edge/CDN ──▶ Vercel Function (FastAPI 앱 전체가 단일 함수)
                                          │
                                routers/ ─┼─ services/ ─── crud.py
                                          │       │            │
                                          │       ▼            ▼
                                          │   AI API      관리형 PostgreSQL
                                          │  (서버에서만 호출)  (외부 · 영속)
```

| 계층 | 책임 | 해서는 안 되는 것 |
|---|---|---|
| `routers/` | 요청 검증 후 서비스로 전달. HTTP 통역 | SQL 직접 실행, AI SDK 직접 호출 |
| `services/` | 컨텍스트 구성, AI 호출, 파이프라인 제어 | HTTP 상태코드·Request 객체 다루기 |
| `crud.py` | DB 접근 전담. 모든 쿼리가 여기를 통과 | 비즈니스 판단, 예외를 HTTP로 변환 |
| `deps.py` | 인증·DB 세션을 모든 라우터가 재사용 | 라우터마다 쿠키 파싱 복붙 |
| `schemas.py` | 요청/응답 형식을 한 곳에서 정의 | 라우터에서 dict 즉석 조립 |

**DB가 함수 밖에 있는 것이 이 구조의 핵심이다.** Vercel 함수는 파일시스템이 읽기 전용이고
`/tmp` 도 호출 간 잔존이 보장되지 않아 SQLite 파일 DB를 쓸 수 없다.

## 4. 실행 방법

```bash
git clone https://github.com/Teamb7-1/ai-chatbot-service.git
cd ai-chatbot-service

python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt

cp .env.example .env        # 값을 채운다 (아래 5절)
./.venv/bin/uvicorn app.main:app --reload --env-file .env
```

| 확인 | URL |
|---|---|
| 헬스체크 | http://localhost:8000/healthz → `{"status":"ok"}` |
| 자동 API 문서 | http://localhost:8000/docs |

테스트·린트:

```bash
./.venv/bin/pip install ruff pytest httpx
./.venv/bin/ruff check .
./.venv/bin/pytest -q
```

## 5. 환경 변수

`.env.example` 을 복사해 사용한다. **실제 값은 리포에 커밋하지 않는다** — 공개 저장소다.

| 이름 | 설명 |
|---|---|
| `SECRET_KEY` | JWT 서명 키. `python -c "import secrets;print(secrets.token_hex(32))"` |
| `DATABASE_URL` | Neon PostgreSQL 의 **pooled** 엔드포인트 (`postgresql+psycopg://…?sslmode=require`) |
| `AI_API_KEY` | 코디세이 OpenAI 호환 엔드포인트 키 |
| `AI_TIMEOUT_SECONDS` | AI 호출 타임아웃 (기본 10) |

환경변수에 두는 기준: **비밀이거나, 환경마다 달라야 하거나, 운영 중 값을 바꿔야 하는 것.**
그 셋에 해당하지 않는 값(모델명·문맥 턴 수·엔드포인트 URL)은 `app/config.py` 상수다 —
환경변수 하나는 스테이징에 빠뜨릴 수 있는 곳 하나다.

배포 환경의 값은 **Vercel 대시보드 환경변수**에만 저장한다. Hobby 플랜이라 접근이
계정 소유자로 제한되므로 변경이 필요하면 D에게 요청한다.

## 6. API 명세

<!-- 담당 B — 요청/응답 예시 포함 (평가항목 3) -->
> 작성 예정

## 7. DB 구조

<!-- 담당 C — 테이블·필드 또는 ERD (평가항목 4) -->
> 작성 예정

## 8. DB 확인 방법

<!-- 담당 C — 평가자가 직접 조회하는 절차 (평가항목 5) -->
> 작성 예정

## 9. 팀 역할 및 개인별 작업 요약

<!-- 담당 A — 매주 금요일 갱신, Git 이력과 일치시킬 것 (평가항목 6·31) -->
> 작성 예정

## 10. 트러블슈팅

<!-- 전원 — 막혔던 것과 해결 방법 -->
> 작성 예정
