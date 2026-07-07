#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/env.sh"

QUESTION="${*:-In the sample documents, what are the most important entities and themes that should become ontology classes or properties?}"

tg-invoke-document-rag \
  --url "${TRUSTGRAPH_URL}" \
  --token "${TRUSTGRAPH_TOKEN}" \
  --workspace "${TRUSTGRAPH_WORKSPACE}" \
  --flow-id "${TRUSTGRAPH_FLOW_ID}" \
  --collection "${TRUSTGRAPH_COLLECTION}" \
  --explainable \
  --question "${QUESTION}"

