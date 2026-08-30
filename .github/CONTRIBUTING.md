# 협업 규칙

계획서 4장을 리포 안으로 옮긴 것이다. 판단이 갈리면 계획서가 기준이다.

## 브랜치

```
feature/{이슈번호}-{설명}  ──PR──▶  develop  ──release PR──▶  main  ──▶  Vercel 배포
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
- 자동 머지를 피하려면 **Draft로 열거나 `hold` 라벨**을 붙인다
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
| 테스트 | `pytest` | ❌ → 9/14부터 차단 |

로컬에서 미리 확인:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt ruff pytest httpx
./.venv/bin/ruff check .
./.venv/bin/uvicorn app.main:app --reload   # http://localhost:8000/healthz
```

## 비밀값

- `.env` 는 **절대 커밋하지 않는다.** 공개 리포라 한 번 올라가면 즉시 유출이고
  커밋 이력에 영구히 남아 **키 재발급 외에 되돌릴 방법이 없다**
- 리포에는 `.env.example` (키 이름만) 만 둔다
- 실제 값은 **Vercel 대시보드 환경변수**에만. Hobby 플랜이라 D만 접근 가능하므로
  변경이 필요하면 D에게 요청한다
- 첫 push 전에 `git status` 에 `.env` 류가 없는지 확인한다
