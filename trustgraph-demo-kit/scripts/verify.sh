#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/env.sh"

if ! command -v tg-verify-system-status >/dev/null 2>&1; then
  echo "TrustGraph CLI is not installed in this shell." >&2
  echo "Install it with a version matching your deployment, for example:" >&2
  echo "  python3 -m venv env" >&2
  echo "  . env/bin/activate" >&2
  echo "  pip install trustgraph-cli" >&2
  exit 1
fi

tg-verify-system-status

