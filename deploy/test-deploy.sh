#!/usr/bin/env bash
set -euo pipefail

# This script runs on the test VM. Releases are immutable Git archives named by SHA.
ROOT="${HOME}/satisfaction-test"
RELEASES="${ROOT}/releases"
ENV_FILE="${ROOT}/shared/test.env"
PROJECT="satisfaction-test"
SERVICES=(postgres_db mlflow redis model_bootstrap api celery_worker frontend)

valid_sha() { [[ "$1" =~ ^[0-9a-f]{40}$ ]]; }

read_sha() {
  local file="$1" value
  [[ -f "$file" ]] || return 1
  value="$(cat "$file")"
  valid_sha "$value" || return 1
  printf '%s' "$value"
}

require_release() {
  local sha="$1"
  valid_sha "$sha" || { echo 'Invalid SHA' >&2; return 1; }
  [[ -f "${RELEASES}/${sha}/.source_sha" ]] || { echo 'Release missing' >&2; return 1; }
  [[ "$(cat "${RELEASES}/${sha}/.source_sha")" == "$sha" ]] || {
    echo 'Release SHA marker mismatch' >&2; return 1;
  }
}

compose() {
  local sha="$1"
  shift
  # The test stack is only reachable on the VM's loopback interface.
  POSTGRES_HOST_PORT=127.0.0.1:5432 \
  MLFLOW_HOST_PORT=127.0.0.1:5000 \
  REDIS_HOST_PORT=127.0.0.1:6379 \
  API_HOST_PORT=127.0.0.1:8000 \
  FRONTEND_HOST_PORT=127.0.0.1:5173 \
  DASHBOARD_HOST_PORT=127.0.0.1:8501 \
  DB_HOST=postgres_db \
  DB_PORT=5432 \
  MLFLOW_TRACKING_URI=http://mlflow:5000 \
  CELERY_BROKER_URL=redis://redis:6379/0 \
  CELERY_RESULT_BACKEND=redis://redis:6379/1 \
  VITE_API_BASE_URL=http://localhost:8000 \
  FRONTEND_BASE_URL=http://localhost:5173 \
    docker compose --project-directory "${RELEASES}/${sha}" \
      --env-file "$ENV_FILE" -p "$PROJECT" \
      -f "${RELEASES}/${sha}/docker-compose.yml" "$@"
}

healthcheck() {
  local attempt
  for attempt in {1..12}; do
    if curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8000/health >/dev/null &&
       curl --fail --silent --show-error --max-time 5 http://127.0.0.1:5173/ >/dev/null; then
      return 0
    fi
    sleep 5
  done
  echo 'API or frontend healthcheck failed' >&2
  return 1
}

activate() {
  local sha="$1"
  require_release "$sha" || return 1
  compose "$sha" build model_bootstrap api celery_worker frontend || return 1
  compose "$sha" up -d --no-build --wait --wait-timeout 180 "${SERVICES[@]}" || return 1
  healthcheck || return 1
}

write_sha() {
  local file="$1" sha="$2" tmp
  tmp="${file}.tmp.$$"
  printf '%s\n' "$sha" > "$tmp"
  mv -f "$tmp" "$file"
}

main() {
  local mode="${1:-}" target="${2:-}" current='' previous=''
  [[ -f "$ENV_FILE" ]] || { echo 'Test environment file missing' >&2; return 1; }
  [[ "$(stat -c '%a' "$ENV_FILE")" == 600 ]] || {
    echo 'Test environment file must have mode 600' >&2; return 1;
  }
  local key
  for key in DB_USER DB_NAME DB_PASSWORD JWT_SECRET_KEY DEMO_ADMIN_PASSWORD PLATFORM_ADMIN_PASSWORD API_KEY; do
    grep -Eq "^${key}=.+$" "$ENV_FILE" || {
      echo "Required test setting missing: $key" >&2; return 1;
    }
  done
  if [[ -f "${ROOT}/current.sha" ]]; then
    current="$(read_sha "${ROOT}/current.sha")" || {
      echo 'Current SHA marker is invalid' >&2; return 1;
    }
    require_release "$current" || return 1
  fi
  case "$mode" in
    deploy)
      require_release "$target" || return 1
      if [[ "$target" == "$current" ]]; then
        echo "Already deployed: $target"
        healthcheck
        return
      fi
      if ! activate "$target"; then
        echo "Candidate $target failed; restoring previous application revision" >&2
        if [[ -n "$current" ]]; then
          activate "$current" || {
            echo 'Automatic rollback failed; manual intervention required' >&2
            return 1
          }
        fi
        return 1
      fi
      [[ -z "$current" ]] || write_sha "${ROOT}/previous.sha" "$current"
      write_sha "${ROOT}/current.sha" "$target"
      ;;
    rollback)
      previous="$(read_sha "${ROOT}/previous.sha")" || {
        echo 'No known previous SHA' >&2; return 1;
      }
      [[ "$previous" != "$current" ]] || {
        echo 'Previous SHA is already current' >&2; return 1;
      }
      activate "$previous" || return 1
      [[ -z "$current" ]] || write_sha "${ROOT}/previous.sha" "$current"
      write_sha "${ROOT}/current.sha" "$previous"
      target="$previous"
      ;;
    *) echo 'Usage: test-deploy.sh deploy SHA | rollback' >&2; return 2 ;;
  esac
  echo "DEPLOYED_SHA=$target"
  echo 'HEALTHCHECK=passed'
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
