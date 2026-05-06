#!/usr/bin/env bash
# Sweep: drop preview stacks whose corresponding PR is CLOSED or MERGED.
# OPEN or unknown -> leave alone. Never touches mealorder-main.
set -euo pipefail

PROJECT_PREFIX="${PROJECT_PREFIX:-mealorder}"

PROJECTS=$(docker compose ls --filter name=${PROJECT_PREFIX}- --format json \
  | jq -r '.[] | select(.Name != "'"${PROJECT_PREFIX}"'-main") | .Name')

for proj in $PROJECTS; do
  # Recover original branch name from container label (set in compose override).
  BRANCH=$(docker ps -a --filter "label=mealorder.branch" \
    --filter "label=com.docker.compose.project=$proj" \
    --format '{{.Label "mealorder.branch"}}' | head -n1)

  if [ -z "$BRANCH" ]; then
    echo "[skip] $proj has no mealorder.branch label, leaving alone"
    continue
  fi

  STATE=$(gh pr list --head "$BRANCH" --state all --json state \
    --jq '.[0].state // "UNKNOWN"' 2>/dev/null || echo "UNKNOWN")

  case "$STATE" in
    CLOSED|MERGED)
      echo "[drop] $proj (branch=$BRANCH state=$STATE)"
      docker compose -p "$proj" down -v --remove-orphans
      ;;
    OPEN)
      echo "[keep] $proj (branch=$BRANCH state=OPEN)"
      ;;
    *)
      echo "[skip] $proj (branch=$BRANCH state=$STATE) — not touching"
      ;;
  esac
done
