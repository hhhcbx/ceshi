#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$(cd "${ROOT_DIR}/.." && pwd)"

if [ -f "${REPO_DIR}/.env" ]; then
  # shellcheck disable=SC1091
  set -a
  . "${REPO_DIR}/.env"
  set +a
elif [ -f "${ROOT_DIR}/.env" ]; then
  # shellcheck disable=SC1091
  set -a
  . "${ROOT_DIR}/.env"
  set +a
fi

export IAM_BOOTSTRAP_TOKEN="${IAM_BOOTSTRAP_TOKEN:-tg_replace_with_your_local_admin_token}"
export TRUSTGRAPH_TOKEN="${TRUSTGRAPH_TOKEN:-${IAM_BOOTSTRAP_TOKEN}}"
export GF_SECURITY_ADMIN_PASSWORD="${GF_SECURITY_ADMIN_PASSWORD:-admin}"
export TRUSTGRAPH_URL="${TRUSTGRAPH_URL:-http://localhost:8088/}"
export TRUSTGRAPH_WORKSPACE="${TRUSTGRAPH_WORKSPACE:-default}"
export TRUSTGRAPH_COLLECTION="${TRUSTGRAPH_COLLECTION:-default}"
export TRUSTGRAPH_FLOW_ID="${TRUSTGRAPH_FLOW_ID:-default}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.deepseek.com/v1}"

if [ "${OPENAI_TOKEN:-}" = "" ]; then
  echo "OPENAI_TOKEN is empty. Fill it with your DeepSeek API key before testing LLM/RAG." >&2
fi

