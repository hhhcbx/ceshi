#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${1:-docker-compose.yaml}"

if [ ! -f "${COMPOSE_FILE}" ]; then
  echo "Compose file not found: ${COMPOSE_FILE}" >&2
  exit 1
fi

if command -v docker >/dev/null 2>&1; then
  docker compose -f "${COMPOSE_FILE}" down -v -t 0
elif command -v podman-compose >/dev/null 2>&1; then
  podman-compose -f "${COMPOSE_FILE}" down -v -t 0
else
  echo "Neither docker compose nor podman-compose is available." >&2
  exit 1
fi

