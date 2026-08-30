# 에이전트 작업 규칙

팀원 4명이 각자 AI 에이전트로 작업한다. **이 파일을 먼저 읽고 시작한다.**

사람용 규칙(브랜치·커밋·PR 상세)은 `.github/CONTRIBUTING.md` 에 있다.
여기는 **읽지 않으면 사고가 나는 것**과 **에이전트가 특히 틀리는 것**만 적는다.

---

## 1. 무엇이 기준인가

| 순위 | 문서 | 위치 |
|---|---|---|
| **1. 명세 (유일한 권위)** | `B7-1 웹 기반 AI 챗봇 서비스 개발 프로젝트.md` | 리포 밖, 팀원 로컬 |
| 2. 팀 계획서 | `chatbotteamplaybook.html` · https://chatbot-team-playbook.vercel.app | 명세의 해석물 |

**"명세가 요구한다"고 쓰기 전에 명세 원문에서 문구를 찾아 줄 번호와 함께 인용한다.**
못 찾으면 팀 재량이므로 "필수"라고 쓰지 않는다.

실제 사고 사례: 계획서의 "메시지 1,000자 제한"은 명세가 아니라 튜토리얼 가이드에서
흘러들어와 P0 요구사항처럼 굳었다. 명세는 "입력 검증 로직 최소 1개"만 요구하고
숫자를 정하지 않는다. 지금은 4,000자다.

---

## 2. 파일 소유자 — 남의 파일을 고치지 않는다

**이것이 이 문서에서 가장 중요한 규칙이다.**

| 파일 | 소유 | |
|---|---|---|
| `app/main.py` `config.py` `schemas.py` `logging_config.py` | **D** | 앱 골격 |
| `app/routers/pages.py` · `templates/base·chat·logs` · `static/` | **D** | 화면 |
| `.github/workflows/` · `vercel.json` · `.python-version` · `.env.example` | **D** | 인프라 |
| `app/deps.py` `security.py` · `models.py`(User) · `templates/login·register` | **A** | 인증 |
| `app/routers/auth.py` | **A** | |
| `app/services/ai_client.py` `chat_service.py` · `routers/chat.py` | **B** | 챗봇·AI |
| `app/database.py` `crud.py` · `models.py`(ChatLog) · `routers/logs.py` | **C** | DB·로그 |
| `scripts/check_logs.sql` · `docs/ERD.md` | **C** | |
| `README.md` | 전원 (각자 담당 절만) | |

담당은 `A yun-lim` / `B sonjehyun123-maker` / `C 00skgun` / `D zxcv718`.

**남의 파일이 어색해 보여도 고치지 않는다.** 평가항목 `31`이
`git log --format='%an' -- <파일>` 과 역할표를 대조한다. 한 번의 "도와주는 수정"이
그 대조를 깬다. 문제를 발견하면 **이슈를 열어 소유자에게 알린다.**

---

## 3. 처음이라면 — 첫 커밋 전에

**되돌릴 수 없는 것이 하나 있다.** git 이름·이메일이 GitHub 계정과 어긋난 채로 커밋하면
그 커밋들은 유령 계정으로 집계되고 **나중에 고쳐도 소급되지 않는다.**
과제 본문이 "팀원별 유의미한 커밋 최소 10회"를 요구하므로 그대로 두면 그 사람 몫이 통째로 사라진다.

```bash
git config user.name  "<GitHub 표시명>"
git config user.email "<GitHub 계정에 등록된 이메일>"

# 확인: 커밋을 push 한 뒤 GitHub 커밋 목록에서 아바타가 붙는지 본다.
# 회색 기본 아이콘이면 이메일이 계정에 등록돼 있지 않은 것이다.
```

그다음 자기 몫을 확인한다:

```bash
gh issue list --repo Teamb7-1/ai-chatbot-service --assignee @me
```

**9/1까지 정해야 하는 것이 둘 있다.** 둘 다 D의 배포 환경변수를 막고 있다.

| 누가 | 무엇 | 어떻게 전달 |
|---|---|---|
| **B** | AI 프로바이더 | 모델명·SDK 패키지명을 배정된 이슈에 댓글로 |
| **C** | 관리형 PostgreSQL 제공자 | **연결 문자열만 D에게 DM으로** (공개 리포라 채팅방 금지) |

---

## 4. 작업 방법

```bash
gh issue create          # 먼저 이슈. 브랜치 이름에 번호가 들어간다
git checkout -b feature/{이슈번호}-{설명}
# ... 작업 ...
git push                 # 끝. PR 생성 → CI → develop 머지 → 스테이징 배포가 전부 자동
```

**PR 을 직접 만들지 않는다.** `autopr` 이 만든다.
자동 머지를 피하려면 커밋 메시지에 `[wip]` 를 넣거나 브랜치를 `wip/...` 로 둔다.

커밋: `<type>(<범위>): <요약> (#이슈번호)` · type 은 `feat` `fix` `docs` `refactor` `test` `chore` 6개.
**"완성 단위"가 아니라 "진행 단위"로 쪼갠다** — 팀원별 커밋 10회가 개인 하한이다.
단, `.` 만 찍은 커밋은 감점이다.

프로덕션 배포만 수동: `gh workflow run release.yml`

---

## 5. 하지 말 것

| 금지 | 이유 |
|---|---|
| **남의 파일 수정** | 평가항목 `31` 이 작성자를 대조한다 |
| `.env` 커밋 | 공개 리포다. 한 번 올라가면 키 재발급 외에 방법이 없다 |
| **Squash 머지** | 커밋 author 가 머지 주체로 바뀌어 나머지 3인의 커밋이 0이 된다 (리포 설정에서 차단됨) |
| 라우터에서 `request.cookies` 직접 읽기 | 인증은 `deps.py` 한 곳. 평가항목 `20` |
| 라우터에서 SQL 실행 | DB 접근은 `crud.py` 한 곳. 평가항목 `21` |
| 라우터에서 상태코드·문구 직접 선택 | `raise AppError(ErrorCode.XXX)` 를 쓴다. 평가항목 `15` |
| 응답을 dict 로 즉석 조립 | `schemas.py` 의 Pydantic 모델을 쓴다. 평가항목 `19` |
| 상대경로로 템플릿·정적파일 지정 | Vercel 의 cwd 는 프로젝트 루트(`/var/task`)다. `Path(__file__).resolve().parent` 기준 절대경로만 |
| SQLite 사용 | Vercel 함수는 파일 쓰기가 불가. 대화 로그가 사라진다 |
| 예외를 조용히 삼키기 | `continue-on-error`, `if ! cmd; then echo; fi` 로 세 번 당했다. 초록불인데 아무것도 안 하는 상태가 된다 |

---

## 6. 계약 3종 — 여기를 import 한다

```python
from app.schemas import ChatRequest, ErrorCode, AppError   # ① 요청/응답 (D)
from app.deps import CurrentUser, DbSession                # ② 인증·세션 (A)
from app import crud                                       # ③ DB 접근 (C)
```

오류를 낼 때는 상태코드를 고르지 말고:

```python
raise AppError(ErrorCode.DUPLICATE_USERNAME)   # → 409 + 확정 문구
```

---

## 7. 작업 후 반드시 확인

```bash
./.venv/bin/ruff check .
./.venv/bin/pytest -q
```

둘 다 CI 에서 머지를 막는다. 로컬에서 먼저 돌린다.

| 환경 | URL | 갱신 |
|---|---|---|
| 스테이징 | https://b7-ai-chatbot-dev.vercel.app | `develop` 머지 시 자동 |
| 프로덕션 | https://b7-ai-chatbot.vercel.app | `release` 워크플로 실행 시 |
