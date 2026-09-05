# 협업 규칙

계획서 4장을 리포 안으로 옮긴 것이다. 판단이 갈리면 계획서가 기준이다.

> AI 에이전트로 작업한다면 [`AGENTS.md`](../AGENTS.md) 를 먼저 읽는다.
> 파일 소유자 표와 "하지 말 것" 목록이 거기 있다.

## 일상 작업은 push 한 번이 전부다

```
git push
   │
   ├─ autopr    develop 대상 PR을 자동으로 연다
   ├─ ci        ruff · 스모크 · pytest
   └─ automerge CI 통과 시 Merge commit 으로 develop 에 병합
```

**PR을 직접 만들 필요가 없다.** 작업 브랜치에 push 하면 나머지는 자동이다.

자동 PR을 원하지 않을 때:
- 커밋 메시지에 `[wip]` 를 넣는다
- 또는 브랜치 이름을 `wip/...` 로 둔다 (`feature/` `fix/` `docs/` `chore/` 만 자동 대상)
- 이미 PR이 열렸다면 **Draft 로 바꾸거나 `hold` 라벨**을 붙이면 자동 머지가 멈춘다

## 배포 주소 두 개

| 환경 | URL | 언제 갱신되나 |
|---|---|---|
| **스테이징** | https://b7-ai-chatbot-dev.vercel.app | `develop` 에 병합될 때 **자동** |
| **프로덕션** | https://b7-ai-chatbot.vercel.app | `release` 워크플로를 실행할 때 |

push 하고 자동 머지가 끝나면 **스테이징에서 바로 확인**할 수 있다.
평가자에게 제출하는 것은 프로덕션 URL 하나뿐이다.

## 프로덕션 배포는 버튼이다

`develop` → `main` 은 자동이 아니다. **main 에 올리는 순간 Vercel 프로덕션이 갱신**되므로
"지금 나가도 되나"를 판단하는 지점을 남겨뒀다.

```bash
gh workflow run release.yml
```

또는 GitHub **Actions 탭 → release → Run workflow**.
무엇이 나가는지 실행 요약에 커밋 목록으로 표시된다.

## 브랜치

```
feature/{이슈번호}-{설명}  ──자동 PR──▶  develop  ──release 버튼──▶  main  ──▶  Vercel 배포
```

| 브랜치 | 용도 | 규칙 |
|---|---|---|
| `main` | 배포 브랜치 — 항상 동작하는 상태 | 보호됨. develop에서 release PR로만 |
| `develop` | 통합 브랜치 | 보호됨. feature PR의 대상 |
| `feature/{번호}-{설명}` | 기능 단위 | develop에서 분기. 예: `feature/7-chat-api` |
| `fix/{번호}-{설명}` | 버그 수정 | feature와 동일 흐름 |
| `docs/{설명}` | 문서 전용 | |

**`main`·`develop` 둘 다 직접 push가 막혀 있다.** 관리자도 우회할 수 없다.

## 커밋

```
<type>(<범위>): <한 줄 요약> (#이슈번호)

feat(auth): 로그인 API 및 JWT 쿠키 발급 구현 (#12)
fix(chat): AI 타임아웃 시 500 대신 안내 메시지 반환 (#31)
docs(readme): 환경 변수 설정 방법 추가 (#40)
```

- type은 `feat` `fix` `docs` `refactor` `test` `chore` **6개만**
- 커밋은 **"완성 단위"가 아니라 "진행 단위"** 로 쪼갠다.
  `feat: 인증 기능 완성` 1개 대신 → 모델 정의 / 라이브러리 설정 / 회원가입 / 로그인·쿠키 / 의존성 5개
- 단 **"유의미한"** 커밋이어야 한다. `.` 만 찍은 커밋 10개는 감점이다
- **본인 계정으로 커밋한다.** `git config user.name` 을 GitHub 표시명과,
  `user.email` 을 GitHub 계정에 등록된 이메일과 일치시킨다.
  안 맞으면 커밋이 유령 계정으로 집계되고 **나중에 고쳐도 소급되지 않는다**

```bash
git config user.name  "<GitHub 표시명>"
git config user.email "<GitHub 계정 이메일>"
# 확인: 커밋 push 후 GitHub 목록에 아바타가 붙는지 볼 것
```

## PR

- **CI(`ci`)가 통과하면 자동으로 머지된다.** 리뷰 승인은 머지 조건이 아니다
- 자동 머지를 피하려면 **Draft로 바꾸거나 `hold` 라벨**을 붙인다
- PR 본문은 커밋 메시지에서 자동으로 채워진다 → **커밋 메시지를 성의 있게 쓰면 PR이 저절로 좋아진다**
- **Squash 금지** — 리포 설정에서 비활성화해 뒀다.
  Squash는 커밋을 1개로 압축하면서 author를 머지 주체로 바꾸기 때문에
  나머지 팀원의 커밋 수가 0이 된다
- 머지된 브랜치는 **삭제하지 않는다**
- PR은 500라인 이하 권장. 크면 쪼갠다
- 리뷰는 머지를 막지 않는 비동기 코멘트로 남긴다 (페어: A↔B, C↔D)

## CI가 보는 것

| 단계 | 내용 | 머지 차단 |
|---|---|---|
| 린트 | `ruff check .` | ✅ |
| 스모크 | 앱 import + `GET /healthz` 200 | ✅ |
| 테스트 | `pytest` | ✅ |

로컬에서 미리 확인:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt ruff pytest httpx
./.venv/bin/ruff check .
./.venv/bin/uvicorn app.main:app --reload --env-file .env   # http://localhost:8000/healthz
```

## 비밀값

- `.env` 는 **절대 커밋하지 않는다.** 공개 리포라 한 번 올라가면 즉시 유출이고
  커밋 이력에 영구히 남아 **키 재발급 외에 되돌릴 방법이 없다**
- 리포에는 `.env.example` (키 이름만) 만 둔다
- 실제 값은 **Vercel 대시보드 환경변수**에만. Hobby 플랜이라 D만 접근 가능하므로
  변경이 필요하면 D에게 요청한다
- 첫 push 전에 `git status` 에 `.env` 류가 없는지 확인한다
