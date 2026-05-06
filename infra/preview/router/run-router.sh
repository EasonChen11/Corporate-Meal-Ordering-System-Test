#!/usr/bin/env bash
# Idempotent bootstrap for the shared preview router container on the NOL host.
# Safe to re-run; recreates the container if Caddyfile changes.
set -euo pipefail

CADDYFILE="${CADDYFILE:-$(cd "$(dirname "$0")" && pwd)/Caddyfile}"
NETWORK="${NETWORK:-preview-net}"
NAME="${NAME:-caddy-preview-router}"
HOST_PORT="${HOST_PORT:-127.0.0.1:18080}"

docker network inspect "$NETWORK" >/dev/null 2>&1 \
  || docker network create "$NETWORK"

docker rm -f "$NAME" >/dev/null 2>&1 || true

docker run -d \
  --name "$NAME" \
  --restart unless-stopped \
  -p "${HOST_PORT}:80" \
  --network "$NETWORK" \
  -v "${CADDYFILE}:/etc/caddy/Caddyfile:ro" \
  caddy:2-alpine

echo "router up on ${HOST_PORT} using ${CADDYFILE}"
