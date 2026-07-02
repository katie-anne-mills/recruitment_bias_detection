#!/usr/bin/env bash
# Quick sanity check that OPENAI_API_KEY and ANTHROPIC_API_KEY (from .env or
# the environment) are valid. Makes one cheap, read-only request per key.
set -uo pipefail

if { [ -z "${OPENAI_API_KEY:-}" ] || [ -z "${ANTHROPIC_API_KEY:-}" ]; } && [ -f .env ]; then
  set -a
  source .env
  set +a
fi

check_key() {
  local name="$1" key="$2" status_json="$3"
  shift 3

  if [ -z "$key" ]; then
    echo "$name is not set (checked environment and ./.env)."
    return 1
  fi

  local status
  status=$(curl -s -o "$status_json" -w '%{http_code}' "$@")

  if [ "$status" = "200" ]; then
    echo "$name is valid."
    return 0
  else
    echo "$name check failed (HTTP $status):"
    cat "$status_json"
    echo
    return 1
  fi
}

overall=0

check_key "OPENAI_API_KEY" "${OPENAI_API_KEY:-}" /tmp/openai_key_check.json \
  https://api.openai.com/v1/models \
  -H "Authorization: Bearer ${OPENAI_API_KEY:-}" \
  || overall=1

check_key "ANTHROPIC_API_KEY" "${ANTHROPIC_API_KEY:-}" /tmp/anthropic_key_check.json \
  https://api.anthropic.com/v1/models \
  -H "x-api-key: ${ANTHROPIC_API_KEY:-}" \
  -H "anthropic-version: 2023-06-01" \
  || overall=1

exit $overall
