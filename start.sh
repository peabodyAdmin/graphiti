#!/usr/bin/env bash

# Start Graphiti MCP and Neo4j using the MCP docker-compose file and the root .env.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ROOT_DIR}/canonical.env"
COMPOSE_FILE="${ROOT_DIR}/mcp_server/docker/docker-compose-neo4j.yml"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing canonical.env in repo root. Copy from canonical.env.example and configure." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or not on PATH." >&2
  exit 1
fi

CMD=(docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d)
echo "Starting Graphiti services with: ${CMD[*]}"
"${CMD[@]}"

echo "Services are starting. Check status with:"
echo "  docker compose --env-file \"${ENV_FILE}\" -f \"${COMPOSE_FILE}\" ps"
