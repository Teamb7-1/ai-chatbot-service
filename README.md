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
| DB | Neon PostgreSQL · SQLAlchemy 2.x · psycopg 3 | pooled 연결, development·production 분리 |
| 인증 | JWT + HttpOnly 쿠키 (라이브러리 사용) | |
| AI | 9/1 확정 | 타임아웃 10초 |
| 배포 | Vercel (GitHub Actions에서 CLI 배포) | |

DB 제공자는 **Neon Free**로 확정하고 두 브랜치의 pooled 연결 문자열을 D에게 비공개 전달했다.
유휴 상태에서 연결 시 자동 기동하고, pooled 엔드포인트를 제공하므로 이 서비스에 선택했다.
근거: [연결·자동 기동 안내](https://neon.com/docs/connect/connection-errors),
[연결 풀링 안내](https://neon.com/docs/connect/connection-pooling).

2026-09-12 확인한 [공식 Free 요금표](https://neon.com/pricing): 프로젝트당 저장 공간 0.5 GB,
컴퓨트 월 100 CU-hours, 복원 이력은 최대 6시간 또는 변경 데이터 1 GB 한도다.
복원 이력 창은 대화 행의 자동 삭제 주기가 아니다. 요금·한도는 변할 수 있으므로 시연 전 D가
콘솔의 실제 플랜·사용량과 development 브랜치의 자동 삭제 설정을 다시 확인한다.

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

### 배포

배포는 GitHub Actions 가 Vercel CLI 로 수행한다. 사람이 누르는 건 프로덕션 릴리스 하나뿐이다.

| 환경 | 트리거 | 워크플로 | URL |
|---|---|---|---|
| 스테이징 | `develop` 에 머지되면 자동 | `deploy-dev.yml` | https://b7-ai-chatbot-dev.vercel.app |
| 프로덕션 | `gh workflow run release.yml` | `release.yml` → `main` 머지 → `deploy.yml` | https://b7-ai-chatbot.vercel.app |

`vercel.json` 이 `app/main.py` 를 단일 서버리스 함수(`maxDuration: 60`)로 지정한다.
환경 변수는 Vercel 프로젝트에 둔다(5절) — `scripts/vercel-env-push.sh` 가 `.env.local` 을 읽어
production·preview 양쪽에 등록하고, 스테이징은 `.env.preview` 로 다른 DB 를 본다.

처음부터 재현하려면 GitHub 리포 시크릿 넷이 필요하다:

| 시크릿 | 용도 |
|---|---|
| `VERCEL_TOKEN` `VERCEL_ORG_ID` `VERCEL_PROJECT_ID` | Actions 가 Vercel 에 배포 |
| `GH_PAT` | 자동 PR·머지가 후속 워크플로를 깨우게 (기본 토큰은 못 깨운다) |

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

`users`(A)와 `chat_logs`(C)는 사용자 1명 대 대화 여러 건의 관계다.
`chat_logs.user_id`가 `users.id`를 참조한다. 전체 필드·제약·인덱스는 [ERD 문서](docs/ERD.md)에 정리했다.

대화 테이블은 `id`, `user_id`, `request_id`, `question`, `answer`, `status`,
`error_code`, `provider`, `model`, `latency_ms`, `created_at`의 11개 컬럼이다.
질문·답변 원문뿐 아니라 성공 여부, 오류 코드, 제공자·모델, 소요 시간을 함께 저장한다.
`request_id`로 서버 로그와 DB 기록을 연결해 어느 요청에서 실패했는지 추적한다.

DB 접근은 동기 SQLAlchemy `Session`과 `app/crud.py`로 통일한다.

- `create_chat_log`: 성공·실패 기록을 저장하고 commit. DB 오류는 rollback 후 전파한다.
- `recent_turns`: 자신의 최근 성공 5개(설정 상수)를 선택해 과거 → 현재 순서로 반환한다.
- `list_chat_logs`: 자신의 성공·실패 기록을 최신순으로 반환한다. 기본 `limit=20`, `offset=0`.

ORM 객체의 `id`는 `chat_id` 속성을 통해 API의 `ChatLogItem`으로 변환한다.
`GET /api/me/chats`는 로그인한 사용자 ID만 사용한다. URL의 `user_id`로 남의 기록을 요청할 수 없다.
API·화면 등록은 D의 `main.py`·`routers/pages.py` 연동이 필요하다.

## 8. DB 확인 방법

<!-- 담당 C — 평가자가 직접 조회하는 절차 (평가항목 5) -->

### 테이블 초기화 — D가 두 브랜치에 각각 실행

1. 최신 코드를 받고 의존성을 설치한다. Neon 콘솔에서 대상이 **development**인지 확인한다.
2. 해당 브랜치의 `DATABASE_URL`을 실행 프로세스에 안전하게 주입한다.
   값은 `postgresql+psycopg://` 형식이고 pooled 호스트·TLS 옵션을 유지한다.
   실제 URL을 소스·이슈·터미널 캡처에 붙이지 않는다. 스크립트는 `.env`를 자동으로 읽지 않는다.
3. 리포 루트에서 실행한다. 가상환경 활성화 후:

   ```bash
   python -m scripts.create_tables --confirm
   ```

   Windows에서 가상환경을 활성화하지 않았다면:

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.create_tables --confirm
   ```

4. 성공 메시지와 종료 코드 0을 확인한다. 실패는 종료 코드 1이며 DB 주소·비밀번호는 출력하지 않는다.
   `--confirm` 없이는 실행되지 않는다. 연결·설정·권한 오류가 있으면 해결 후 재실행한다.
5. **production** 연결 정보로 바꿔 대상 브랜치를 다시 확인하고 동일 명령을 실행한다.

`Base.metadata.create_all(checkfirst=True)`로 없는 테이블을 생성한다.
development에 이미 있는 `users`와 기존 데이터를 유지한다. 데이터 삭제·초기 데이터 삽입은 하지 않는다.
기존 테이블 구조를 수정하는 기능은 없으므로 컬럼 변경 시 별도 마이그레이션이 필요하다.
앱 시작 훅이나 자동 배포 과정에서 이 명령을 실행하지 않는다.

### SQL 확인과 증빙

Neon 콘솔에서 대상 브랜치·DB를 선택한 뒤 **SQL Editor**에
[`scripts/check_logs.sql`](scripts/check_logs.sql)을 붙여 넣어 실행한다.
`psql`을 사용한다면 `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGSSLMODE` 등
접속 설정을 안전하게 주입한 상태에서 실행한다. SQLAlchemy 전용 `+psycopg` URL을 psql에 넣지 않는다.

```bash
psql -X -v ON_ERROR_STOP=1 -f scripts/check_logs.sql
```

SQL은 테이블 존재, 11개 컬럼, 최근 기록, 사용자별 성공·실패 건수,
최근 성공 5건, 특정 대화 보존 여부를 조회한다. 마지막 두 조회의 `0`은 시연용 `user_id`와
확인하려는 `chat_id`로 각각 바꾼다. 데이터 변경 SQL은 포함하지 않는다.
질문·답변이 없는 초기 DB는 빈 결과가 정상이며, 그것만으로 대화 저장이 검증된 것은 아니다.

검증 순서(D/B 연동 후):

1. D가 `logs.router`를 앱에 등록하고 `/logs` 화면을 실제 CRUD에 연결한다.
2. 시연 계정 A로 로그인해 질문하고, SQL의 `chat_id`, `request_id`, 질문·답변·시각을 기록한다.
3. 브라우저에서 `/api/me/chats?limit=20&offset=0`과 `/logs`를 열어 자신의 기록을 확인한다.
4. 계정 B에서는 A의 기록이 보이지 않는지, 비로그인은 API 401인지 확인한다.
5. D가 **같은 환경으로 재배포**한 후, 같은 브랜치에서 기록한 `chat_id`를 재조회한다.
   이전 질문·답변·시각이 그대로 남아 있어야 한다. development와 production을 서로 비교하지 않는다.
6. 브랜치명·확인 시각·배포 커밋·조회 결과를 캡처한다. DB 비밀번호, 키, 쿠키,
   실제 사용자의 개인정보는 포함하지 않고 시연용 가상 데이터만 사용한다.

### 검증 상태와 로컬 테스트

아래 실제 환경 항목은 **실행 후 증빙을 붙일 때만** 완료 표시한다.

2026-09-12 로컬 검증: 임시 PostgreSQL 17.11을 이용해 전체 테스트 **168개 통과**
(실제 DB 테스트 17개 포함), `ruff check .` 통과. 기존 Starlette 의존성의
DeprecationWarning 1건이 있다. 이 결과는 실제 Neon·배포 환경 검증을 대체하지 않는다.

- [ ] D: 두 Neon 브랜치의 `users`·`chat_logs` 생성 확인
- [ ] D: API 라우터 등록 및 `/logs` 화면 연결
- [ ] B/D/C: 실제 질문 → AI 응답 → DB 저장 → 본인 기록 조회
- [ ] C/D: SQL 콘솔 실행 결과 캡처
- [ ] C/D: 재배포 전후 동일 대화 보존 캡처

```bash
python -m pytest -q
```

실제 DB 테스트는 **별도 테스트용 PostgreSQL**의 `TEST_DATABASE_URL`을 주입한 경우에만 실행한다.
없으면 해당 테스트는 명시적으로 skip한다. 앱의 `DATABASE_URL`을 대신 사용하지 않는다.
테스트 계정에는 스키마 생성 권한이 필요하며, 테스트마다 고유 스키마와 외부 트랜잭션을 만든 뒤
테이블·데이터를 rollback한다. **운영 Neon URL을 테스트용으로 지정하지 않는다.**

## 9. 팀 역할 및 개인별 작업 요약

<!-- 담당 A — 매주 금요일 갱신, Git 이력과 일치시킬 것 (평가항목 6·31) -->
> 작성 예정

## 10. 트러블슈팅

<!-- 전원 — 막혔던 것과 해결 방법 -->
> 작성 예정
