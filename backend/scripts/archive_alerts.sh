#!/usr/bin/env bash
# Archives the current alert log and starts a fresh empty one for the demo.
# Run this from the project root (where logs/alerts.jsonl lives).
set -euo pipefail

LOG_PATH="logs/alerts.jsonl"
ARCHIVE_DIR="logs/archive"

if [ ! -f "$LOG_PATH" ]; then
  echo "No alert log found at $LOG_PATH — nothing to archive."
  exit 0
fi

mkdir -p "$ARCHIVE_DIR"
STAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE_PATH="$ARCHIVE_DIR/alerts_${STAMP}.jsonl"

cp "$LOG_PATH" "$ARCHIVE_PATH"
echo "Archived $(wc -l < "$LOG_PATH") alerts to $ARCHIVE_PATH"

: > "$LOG_PATH"
echo "Cleared $LOG_PATH — ready for a clean demo."