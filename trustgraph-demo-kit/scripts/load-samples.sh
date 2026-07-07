#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/env.sh"

if ! command -v tg-load-sample-documents >/dev/null 2>&1; then
  echo "TrustGraph CLI is not installed in this shell." >&2
  exit 1
fi

tg-load-sample-documents \
  --url "${TRUSTGRAPH_URL}" \
  --token "${TRUSTGRAPH_TOKEN}" \
  --workspace "${TRUSTGRAPH_WORKSPACE}"

echo
echo "Next in the Workbench UI:"
echo "  1. Open Document Ingestion."
echo "  2. Submit sample documents for processing."
echo "  3. Use the default flow and default collection."
echo "  4. After processing, inspect Ontology Workbench and Graph Explorer."

