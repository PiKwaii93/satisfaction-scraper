#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_HOME="$(mktemp -d)"
cleanup() {
  local temp_root target
  temp_root="$(cd "${TMPDIR:-/tmp}" && pwd -P)"
  target="$(cd "$TEST_HOME" && pwd -P)"
  [[ "$target" == "$temp_root"/tmp.* ]] || {
    echo 'Refusing to remove an unexpected test directory' >&2
    return 1
  }
  rm -rf -- "$target"
}
trap cleanup EXIT
export HOME="$TEST_HOME"
export FAKE_STATE="$TEST_HOME/state"
mkdir -p "$HOME/satisfaction-test/releases" "$HOME/satisfaction-test/shared" "$HOME/bin" "$FAKE_STATE"
export PATH="$HOME/bin:$PATH"

cat > "$HOME/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
sha=''
action=''
for arg in "$@"; do
  [[ "$arg" =~ /releases/([0-9a-f]{40})/docker-compose.yml ]] && sha="${BASH_REMATCH[1]}"
  [[ "$arg" == up ]] && action=up
done
if [[ "$action" == up ]]; then
  printf '%s\n' "$sha" > "$FAKE_STATE/active.sha"
fi
EOF
cat > "$HOME/bin/curl" <<'EOF'
#!/usr/bin/env bash
active="$(cat "$FAKE_STATE/active.sha" 2>/dev/null || true)"
[[ "$active" != "$(cat "$FAKE_STATE/fail.sha" 2>/dev/null || true)" ]]
EOF
cat > "$HOME/bin/sleep" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$HOME/bin/docker" "$HOME/bin/curl" "$HOME/bin/sleep"

old="$(printf 'a%.0s' {1..40})"
candidate="$(printf 'b%.0s' {1..40})"
for sha in "$old" "$candidate"; do
  mkdir -p "$HOME/satisfaction-test/releases/$sha"
  printf '%s\n' "$sha" > "$HOME/satisfaction-test/releases/$sha/.source_sha"
done
printf '%s\n' "$old" > "$HOME/satisfaction-test/current.sha"
cat > "$HOME/satisfaction-test/shared/test.env" <<'EOF'
DB_USER=test
DB_NAME=test
DB_PASSWORD=test-password
JWT_SECRET_KEY=test-secret
DEMO_ADMIN_PASSWORD=test-demo-password
PLATFORM_ADMIN_PASSWORD=test-platform-password
API_KEY=test-api-key
EOF
chmod 600 "$HOME/satisfaction-test/shared/test.env"

printf '%s\n' "$candidate" > "$FAKE_STATE/fail.sha"
if bash "$SCRIPT_DIR/test-deploy.sh" deploy "$candidate" > "$FAKE_STATE/failed.log" 2>&1; then
  echo 'Failed healthcheck was accepted' >&2
  exit 1
fi
[[ "$(cat "$HOME/satisfaction-test/current.sha")" == "$old" ]]
[[ "$(cat "$FAKE_STATE/active.sha")" == "$old" ]]

rm "$FAKE_STATE/fail.sha"
bash "$SCRIPT_DIR/test-deploy.sh" deploy "$candidate" > "$FAKE_STATE/success.log"
[[ "$(cat "$HOME/satisfaction-test/current.sha")" == "$candidate" ]]
[[ "$(cat "$HOME/satisfaction-test/previous.sha")" == "$old" ]]

bash "$SCRIPT_DIR/test-deploy.sh" rollback > "$FAKE_STATE/rollback.log"
[[ "$(cat "$HOME/satisfaction-test/current.sha")" == "$old" ]]
[[ "$(cat "$HOME/satisfaction-test/previous.sha")" == "$candidate" ]]
[[ "$(cat "$FAKE_STATE/active.sha")" == "$old" ]]
echo 'PASS failed healthcheck, automatic restoration, previous SHA selection and rollback'
