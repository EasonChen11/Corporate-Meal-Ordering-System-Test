#!/usr/bin/env bash
# Usage: preview-sanitize-branch.sh <branch-name>
# Emits a docker compose project-name-safe slug (lowercase, [a-z0-9-], <=30 chars).
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "usage: $0 <branch-name>" >&2
  exit 2
fi

echo "$1" \
  | tr '[:upper:]/_.' '[:lower:]---' \
  | sed -E 's/[^a-z0-9-]//g; s/-+/-/g; s/^-+//; s/-+$//' \
  | cut -c1-30 \
  | sed -E 's/-+$//'
