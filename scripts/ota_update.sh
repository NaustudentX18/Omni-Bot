#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BRANCH="${1:-$(git rev-parse --abbrev-ref HEAD)}"
REMOTE="${2:-origin}"

echo "Checking for updates on ${REMOTE}/${BRANCH}..."
git fetch "$REMOTE" "$BRANCH"

PENDING="$(git rev-list --count "HEAD..${REMOTE}/${BRANCH}" || echo 0)"
if [[ "$PENDING" == "0" ]]; then
  echo "Already up to date."
  exit 0
fi

echo "Applying ${PENDING} update(s)..."
git pull "$REMOTE" "$BRANCH"
echo "OTA update complete."
