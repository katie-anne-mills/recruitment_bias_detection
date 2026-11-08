#!/usr/bin/env bash
# Quick sanity check of the credentials in .env (or the environment):
#   - OPENAI_API_KEY against OPENAI_BASE_URL (the Azure OpenAI v1 endpoint;
#     one read-only request that lists models — no tokens are generated)
#   - AWS_BEARER_TOKEN_BEDROCK for the GovAI proxy (presence only)
set -uo pipefail

if { [ -z "${OPENAI_API_KEY:-}" ] || [ -z "${AWS_BEARER_TOKEN_BEDROCK:-}" ]; } && [ -f .env ]; then
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

if [ -z "${OPENAI_BASE_URL:-}" ]; then
  echo "OPENAI_BASE_URL is not set (checked environment and ./.env) — without it requests go to public OpenAI, not Azure."
  overall=1
else
  check_key "OPENAI_API_KEY" "${OPENAI_API_KEY:-}" /tmp/azure_openai_key_check.json \
    "${OPENAI_BASE_URL%/}/models" \
    -H "Authorization: Bearer ${OPENAI_API_KEY:-}" \
    || overall=1
fi

if [ -z "${AWS_BEARER_TOKEN_BEDROCK:-}" ]; then
  echo "AWS_BEARER_TOKEN_BEDROCK is not set (checked environment and ./.env)."
  overall=1
else
  echo "AWS_BEARER_TOKEN_BEDROCK is set (not validated — the GovAI proxy has no free read-only endpoint)."
fi

exit $overall
