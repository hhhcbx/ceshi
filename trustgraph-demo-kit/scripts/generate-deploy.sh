#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/env.sh"

echo "Generating TrustGraph deployment package with the official configurator."
echo
echo "Recommended choices for this ontology/RAG demo:"
echo "  TrustGraph version: latest stable 2.4+"
echo "  Platform: Docker Compose or Podman Compose"
echo "  Graph store: Apache Cassandra or Neo4j if you want a dedicated graph DB"
echo "  Vector store: Qdrant"
echo "  Object store: Apache Cassandra"
echo "  LLM provider: OpenAI"
echo "  OpenAI-compatible base URL: ${OPENAI_BASE_URL}"
echo "  OCR: No for first run"
echo "  Embeddings: default FastEmbed"
echo "  MCP server: Yes"
echo
echo "The wizard will write deploy.zip and INSTALLATION.md."
npx @trustgraph/config

