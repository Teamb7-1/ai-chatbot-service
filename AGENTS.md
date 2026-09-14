# 에이전트 작업 규칙

팀원 4명이 각자 AI 에이전트로 작업한다. 여기는 **리포를 읽어서는 알 수 없는 것**만 적는다 —
관례, 함정, 그 이유. 절차(브랜치·커밋·PR·CI·비밀값)는 `.github/CONTRIBUTING.md` 가 기준이다.

---

## 1. 근거는 명세 원문, L번호로

`B7-1 웹 기반 AI 챗봇 서비스 개발 프로젝트.md`(리포 밖, 각자 로컬)가 유일한 권위다.
"명세가 요구한다"고 쓸 땐 원문에서 문구를 찾아 **L번호**를 단다. 못 찾으면 팀 재량이다.

계획서(https://chatbot-team-playbook.vercel.app)는 해석물이라 근거가 못 된다 — 거기 적혔던
"메시지 1,000자 제한"이 명세엔 없는 숫자였고, 지금은 상한이 없다 (#46).

---

## 2. 파일 소유자 — 가장 중요한 표

| 파일 | 소유 | |
|---|---|---|
| `app/main.py` `config.py` `schemas.py` `logging_config.py` | **D** | 앱 골격 |
| `app/routers/pages.py` · `templates/base·chat·logs` · `static/` | **D** | 화면 |
| `.github/` · `vercel.json` · `.python-version` · `.env.example` · `scripts/vercel-env-push.sh` | **D** | 인프라 |
| `app/deps.py` `security.py` · `models.py`(User) · `templates/login·register·_auth_submit` | **A** | 인증 |
| `app/routers/auth.py` | **A** | |
| `app/services/ai_client.py` `chat_service.py` · `routers/chat.py` | **B** | 챗봇·AI |
| `app/database.py` `crud.py` · `models.py`(ChatLog) · `routers/logs.py` | **C** | DB·로그 |
| `scripts/check_logs.sql` · `docs/ERD.md` | **C** | |
| `README.md` · `requirements.txt` · `tests/conftest.py` | 전원 | 각자 담당 절·의존성 |

담당 `A yun-lim` · `B sonjehyun123-maker` · `C 00skgun` · `D zxcv718`.

평가항목 `31` 이 파일별 `git log --format='%an'` 을 이 표와 대조한다. 남의 파일에서 고칠 게
보이면 **이슈를 열어 소유자에게 넘긴다** — 그게 이 리포의 리뷰 방식이다. 필요한 상수·함수가
남의 파일에 있어야 하면 이슈로 요청한다 (#49 · #50 이 그 예).

---

## 3. 작업 순서

```bash
gh issue create                              # 템플릿이 담당·평가항목·완료 기준·선행 조건을 받는다
git checkout -b feature/{이슈번호}-{설명}
# ... 작업 ...
./.venv/bin/ruff check . && ./.venv/bin/pytest -q
git push                                     # PR → CI → develop 머지 → 스테이징 → 이슈 닫힘. 전부 자동
```

한 이슈에 브랜치 하나다 — 첫 머지에서 이슈가 닫힌다. 큰 이슈에서 지금 되는 조각을 떼려면
하위 이슈를 새로 판다 (#73 · #75). 아직 머지되면 안 되는 작업은 `wip/` 브랜치에 둔다.

첫 커밋 전에 `git config user.email` 이 GitHub 계정 이메일인지 본다. 어긋난 커밋은 **유령**으로
집계되고 나중에 고쳐도 소급되지 않는다 (CONTRIBUTING "커밋").

---

## 4. 한 곳에서만 — 계약 3종

```python
from app.schemas import ChatRequest, ErrorCode, AppError   # 요청·응답·오류 (D)
from app.deps import CurrentUser, DbSession                # 인증·세션 (A)
from app import crud                                       # DB 접근 (C)
```

오류는 `raise AppError(ErrorCode.XXX)` — 상태코드와 문구는 `schemas.py` 가 정한다.
응답은 `schemas.py` 의 Pydantic 모델로 만든다. 인증은 `deps.py` **한 곳**, 쿼리는 `crud.py` **한 곳**.
평가항목 `15` `19` `20` `21` 이 이 "한 곳"을 본다. 정확한 형태는 `tests/test_schemas.py` 가 정의한다.

---

## 5. Vercel 서버리스 함정

- **cwd 는 프로젝트 루트**(`/var/task`)다. 템플릿·정적 파일은 `config.py` 의 `BASE_DIR` 기준 절대경로로
  가리킨다. `tests/test_pages.py` 가 `os.chdir` 로 이 회귀를 잡는다.
- **파일 쓰기가 안 된다.** 저장은 Neon Postgres 로.
- **환경변수는 CI·테스트에 없을 수 있다.** import 때 읽는 모듈(`database.py`)은 `conftest.py`·`ci.yml` 이
  더미를 준다. 첫 호출 때 읽으면(`ai_client.py` `security.py`) 그것도 필요 없다.
- 로컬은 `uvicorn app.main:app --reload --env-file .env`. `load_dotenv()` 는 코드에 없다 (#59).

---

## 6. 초록불 함정

`continue-on-error`, `if ! cmd; then echo; fi`, 빈 배열 반환, 조용한 `exit 1` — 전부 **"성공했는데
아무 일도 안 한"** 상태를 만든다. 이 리포에서 다섯 번 당했다. 실패는 실패로 보이게 하고,
"아직 안 됨"은 "없음"과 다른 화면으로 낸다 (`/logs` 의 대기 안내가 그 예).

---

## 비밀값

연결 문자열·API 키는 **Vercel 환경변수에만**. 리포·이슈·채팅엔 이름만 (`.env.example`).
D 만 만질 수 있으니 값이 생기면 **D 에게 DM** 으로. (CONTRIBUTING "비밀값")
