#!/usr/bin/env bash
# .env.local 의 값을 Vercel production · preview 양쪽에 등록한다.
#
#   ./scripts/vercel-env-push.sh            # .env.local 기본
#   ./scripts/vercel-env-push.sh other.env  # 다른 파일
#
# 값은 이 스크립트 어디에서도 출력하지 않는다. 확인은 `vercel env ls` 로 한다
# (이름과 Encrypted 표시만 보인다).
#
# preview 를 빠뜨리면 스테이징만 조용히 죽는다 — 그래서 두 타깃을 항상 같이 넣는다.
# 비어 있는 키가 하나라도 있으면 종료코드 1 — 반만 된 초록불을 만들지 않는다.

set -euo pipefail

ENV_FILE="${1:-.env.local}"
VERCEL="${VERCEL:-npx vercel}"
KEYS="SECRET_KEY DATABASE_URL AI_API_KEY AI_TIMEOUT_SECONDS"
TARGETS="production preview"

[ -f "$ENV_FILE" ] || { echo "❌ $ENV_FILE 이 없다"; exit 1; }

# KEY=value   # 주석   형태에서 value 만 꺼낸다. 값 안의 '=' 은 보존한다.
read_value() {
  grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2- | sed -E 's/[[:space:]]+#.*$//; s/[[:space:]]+$//'
}

# SECRET_KEY 가 비어 있으면 생성해서 파일에 써넣는다. 화면에는 나오지 않는다.
if [ -z "$(read_value SECRET_KEY)" ]; then
  generated="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  if grep -qE '^SECRET_KEY=' "$ENV_FILE"; then
    sed -i '' -E "s|^SECRET_KEY=.*|SECRET_KEY=$generated|" "$ENV_FILE"
  else
    printf 'SECRET_KEY=%s\n' "$generated" >> "$ENV_FILE"
  fi
  echo "🔑 SECRET_KEY 생성해서 $ENV_FILE 에 기록"
fi

missing=""
for key in $KEYS; do
  value="$(read_value "$key")"
  if [ -z "$value" ]; then
    missing="$missing $key"
    echo "❌ $key  — $ENV_FILE 에 비어 있음, 건너뜀"
    continue
  fi
  for target in $TARGETS; do
    # 이미 있으면 add 가 실패하므로 지우고 다시 넣는다. 없어서 실패하는 건 무시.
    $VERCEL env rm "$key" "$target" --yes >/dev/null 2>&1 || true
    # CLI 가 진행 메시지를 stderr 로 쓴다. 성공하면 삼키고, 실패해야 보여준다.
    if ! out="$(printf '%s' "$value" | $VERCEL env add "$key" "$target" 2>&1)"; then
      echo "❌ $key  → $target 실패:"; echo "$out" | sed 's/^/     /'; exit 1
    fi
    echo "✅ $key  → $target"
  done
done

echo
if [ -n "$missing" ]; then
  echo "⚠️  등록 안 된 키:$missing"
  echo "   $ENV_FILE 에 값을 채우고 다시 실행하면 그것만 추가된다."
  exit 1
fi
echo "모두 등록됨. 확인: $VERCEL env ls production"
