-- Neon SQL Editor: 대상 branch가 development인지 production인지 먼저 확인한다.
-- psql: 연결 정보는 PGHOST/PGDATABASE/PGUSER/PGPASSWORD/PGSSLMODE 등에 주입하고
--       psql -X -v ON_ERROR_STOP=1 -f scripts/check_logs.sql
-- SELECT 전용. 콘솔 캡처에는 시연 계정의 가상 질문/답변만 사용한다.

-- 1. 현재 DB/스키마와 테이블 존재 확인. 하나라도 없으면 초기화부터 한다.
SELECT current_database() AS database_name, current_schema() AS schema_name,
       to_regclass('users') AS users_table, to_regclass('chat_logs') AS logs_table;

-- 2. chat_logs 11개 컬럼 및 NULL 허용 여부.
SELECT ordinal_position, column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = current_schema() AND table_name = 'chat_logs'
ORDER BY ordinal_position;

-- 3. 최근 20건. password_hash나 연결 문자열은 조회하지 않는다.
SELECT id AS chat_id, user_id, request_id, created_at, question, answer,
       status, error_code, provider, model, latency_ms
FROM chat_logs
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- 4. 사용자별 성공/실패 건수 (실패 대화도 DB에 남아야 한다).
SELECT user_id, status, count(*) AS log_count
FROM chat_logs
GROUP BY user_id, status
ORDER BY user_id, status;

-- 5. 아래 숫자 0을 시연 계정의 실제 user_id로 바꾼다.
-- 최근 성공 5개 -> 과거부터 현재: recent_turns와 같은 조회.
SELECT *
FROM (
    SELECT id AS chat_id, user_id, created_at, question, answer
    FROM chat_logs
    WHERE user_id = 0 AND status = 'success'
    ORDER BY created_at DESC, id DESC
    LIMIT 5
) AS recent
ORDER BY created_at ASC, chat_id ASC;

-- 6. 재배포 전 기록한 chat_id로 0을 바꿔 재배포 후 다시 조회한다.
-- 같은 DB/branch에서 id, request_id, 질문/답변, 시각이 유지되어야 한다.
SELECT id AS chat_id, request_id, created_at, question, answer, status
FROM chat_logs
WHERE id = 0;
