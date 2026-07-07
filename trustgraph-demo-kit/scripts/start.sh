#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/env.sh"

COMPOSE_FILE="${1:-docker-compose.yaml}"

if [ ! -f "${COMPOSE_FILE}" ]; then
  echo "Compose file not found: ${COMPOSE_FILE}" >&2
  echo "Run this from the directory where deploy.zip was unpacked, or pass the compose file path." >&2
  exit 1
fi

if command -v docker >/dev/null 2>&1; then
  docker compose -f "${COMPOSE_FILE}" up -d
elif command -v podman-compose >/dev/null 2>&1; then
  podman-compose -f "${COMPOSE_FILE}" up -d
else
  echo "Neither docker compose nor podman-compose is available." >&2
  exit 1
fi

echo
echo "TrustGraph is starting. Wait for services to stabilize, then run:"
echo "  trustgraph-demo-kit/scripts/verify.sh"
echo
echo "Workbench UI: http://localhost:8888"
echo "Grafana:      http://localhost:3000"
echo "API Gateway:  ${TRUSTGRAPH_URL}"

