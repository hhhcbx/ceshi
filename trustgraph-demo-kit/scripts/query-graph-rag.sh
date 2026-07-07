#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/env.sh"

QUESTION="${*:-Using the knowledge graph, explain relationships between places, organizations, products, and historical processes in the sample documents. Highlight which relationships look ontology-worthy.}"

tg-invoke-graph-rag \
  --url "${TRUSTGRAPH_URL}" \
  --token "${TRUSTGRAPH_TOKEN}" \
  --workspace "${TRUSTGRAPH_WORKSPACE}" \
  --flow-id "${TRUSTGRAPH_FLOW_ID}" \
  --collection "${TRUSTGRAPH_COLLECTION}" \
  --explainable \
  --question "${QUESTION}"

