# DB 구조 — C / #36

정의의 기준은 `app/models.py`다. `users`는 A, `chat_logs`는 C가 관리한다.
한 사용자는 대화 기록을 0개 이상 갖고, 대화 기록은 반드시 사용자 1명에 속한다.
외래키는 `chat_logs.user_id → users.id`이며 사용자 삭제 시 연쇄 삭제는 설정하지 않았다.

## users (A의 모델을 문서화)

| 컬럼 | PostgreSQL 타입 | 제약·의미 |
|---|---|---|
| id | BIGINT / BIGSERIAL | PK, 자동 증가 |
| username | TEXT | NOT NULL, 고유 인덱스 `ix_users_username` |
| password_hash | TEXT | NOT NULL, 해시만 보관; 조회 API·확인 SQL에 노출하지 않음 |
| created_at | TIMESTAMPTZ | NOT NULL, DB의 `now()` |

## chat_logs (11개 컬럼)

| 컬럼 | PostgreSQL 타입 | 제약·저장 이유 |
|---|---|---|
| id | BIGINT / BIGSERIAL | PK, 대화 한 건을 식별 |
| user_id | BIGINT | NOT NULL, `users.id` 참조; 사용자별 조회·격리 |
| request_id | TEXT | NOT NULL, 요청·AI·DB 서버 로그와 연결 |
| question | TEXT | NOT NULL, 사용자가 보낸 질문 원문 |
| answer | TEXT | NOT NULL, AI 답변 원문; AI 실패 시 빈 문자열 |
| status | TEXT | NOT NULL, CHECK: `success` 또는 `error` |
| error_code | TEXT | 유일한 nullable 컬럼; 성공 시 NULL, 실패 원인 분류 |
| provider | TEXT | NOT NULL, 호출 제공자 추적 |
| model | TEXT | NOT NULL, 답변을 만든 모델 추적 |
| latency_ms | INTEGER | NOT NULL, CHECK: 0 이상; AI 지연 시간 |
| created_at | TIMESTAMPTZ | NOT NULL, DB의 `now()`; 발생 순서 확인 |

질문·답변은 공백이나 줄바꿈을 제거하지 않는다. 질문 길이 상한을 DB에 두지 않는다.
`request_id`에는 조회용 인덱스 `ix_chat_logs_request_id`가 있지만 고유 제약은 없다.
`ix_chat_logs_user_created_id(user_id, created_at, id)`는 사용자별 시간순 조회에 사용한다.
같은 시각의 행은 `id`로 정렬 순서를 고정한다.

`ChatLog.chat_id`는 `id`를 읽는 Python 속성이다. DB의 12번째 컬럼이 아니다.
B의 `log.id`와 D의 응답 스키마 `ChatLogItem.chat_id`를 같은 값에 연결한다.

## DB 접근 계약

서비스 요청의 SQL은 `app/crud.py`에 모은다. 수동 초기화·검증 스크립트와 테스트는 별도다.

| 함수 | 반환값 | 동작 |
|---|---|---|
| `create_chat_log(...)` | `ChatLog` | 성공·실패 저장 후 commit; DB 오류는 rollback 후 전파 |
| `recent_turns(db, user_id, n=AI_CONTEXT_TURNS)` | `list[ChatLog]` | 자신의 성공 기록만 필터 → 최근 n개 선택 → 과거부터 현재 |
| `list_chat_logs(db, user_id, limit=20, offset=0)` | `list[ChatLog]` | 자신의 성공·실패 기록을 최신순으로 페이지 조회 |

모두 동기 `Session`을 사용하며 `await` 없이 호출한다. ORM 객체를 반환하고,
JSON 변환은 API 경계에서 `ChatLogItem.model_validate()`로 한다.
`recent_turns`의 기본 개수는 `app/config.py`의 `AI_CONTEXT_TURNS`(현재 5)다.
조회 개수가 0이면 빈 목록, 음수 인자는 `ValueError`다. DB 조회 실패를 빈 목록으로 숨기지 않는다.

## 조회 API 계약

`GET /api/me/chats?limit=20&offset=0` → `list[ChatLogItem]`.
`limit`, `offset`은 0 이상 정수다. `limit=0`은 빈 목록이다.
소유자 ID는 클라이언트가 지정하지 않고 `CurrentUser`에서 가져온다.
인증·Session은 `app/deps.py`의 `CurrentUser`, `DbSession`을 재사용한다.

반환 필드: `chat_id`, `request_id`, `question`, `answer`, `status`, `error_code`,
`latency_ms`, `created_at`. 사용자 ID·비밀번호 해시·provider·model은 API에 포함하지 않는다.
비로그인 401, 잘못된 페이지 인자 422, DB 조회 실패 500은 공통 오류 스키마를 따른다.

## 적용 경계

- `scripts/create_tables.py`는 없는 테이블만 만든다. 기존 컬럼·인덱스를 변경하는 마이그레이션이 아니다.
- 실제 Neon 적용은 D가 development·production 각각 실행한다. 브랜치 간 DDL은 자동 반영되지 않는다.
- `app/main.py`의 라우터 등록과 `/logs` 화면 연결은 D 담당이다.
- 실제 배포 확인 및 증빙 절차는 [README 8절](../README.md#8-db-확인-방법)을 따른다.
