#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: bash .wiggum/loop.sh [plan|build|verify] [max-iterations]"
  echo "Examples:"
  echo "  bash .wiggum/loop.sh plan 1"
  echo "  bash .wiggum/loop.sh build"
  echo "  bash .wiggum/loop.sh verify 2"
}

PHASE="build"
MAX_ITERATIONS=0

if [ $# -gt 0 ]; then
  case "$1" in
    plan|build|verify)
      PHASE="$1"
      if [ $# -gt 1 ]; then
        MAX_ITERATIONS="$2"
      fi
      ;;
    *)
      usage
      exit 1
      ;;
  esac
fi

if ! [[ "$MAX_ITERATIONS" =~ ^[0-9]+$ ]]; then
  echo "Invalid max-iterations: $MAX_ITERATIONS"
  usage
  exit 1
fi

PROMPT_FILE=".wiggum/PROMPT_${PHASE}.md"
CONFIG_FILE=".wiggum/config.json"

if [ ! -f "$PROMPT_FILE" ]; then
  echo "Missing prompt: $PROMPT_FILE"
  exit 1
fi
if [ ! -f "$CONFIG_FILE" ]; then
  echo "Missing config: $CONFIG_FILE"
  exit 1
fi

ENGINE_NAME=$(python3 - <<'PY'
import json
with open(".wiggum/config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)
print(cfg.get("engine", {}).get("name", ""))
PY
)

readarray -d '' ENGINE_CMD < <(python3 - <<'PY'
import json
import sys
with open(".wiggum/config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)
cmd = cfg.get("engine", {}).get("command") or []
if not cmd:
    sys.exit("engine.command missing in .wiggum/config.json")
sys.stdout.buffer.write(b"\0".join(s.encode("utf-8") for s in cmd) + b"\0")
PY
)

COMPLETION_PROMISE=$(python3 - <<'PY'
import json
with open(".wiggum/config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)
print(cfg.get("completion_promise", ""))
PY
)

if [ -z "$COMPLETION_PROMISE" ]; then
  echo "completion_promise missing in .wiggum/config.json"
  exit 1
fi

if [ "${WIGGUM_DANGEROUS:-}" = "1" ] && [ "$ENGINE_NAME" = "claude" ]; then
  ENGINE_CMD+=("--dangerously-skip-permissions")
fi

RUN_ROOT=".wiggum/runs/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RUN_ROOT"

ITERATION=1
while true; do
  if [ "$MAX_ITERATIONS" -gt 0 ] && [ "$ITERATION" -gt "$MAX_ITERATIONS" ]; then
    echo "Reached max iterations: $MAX_ITERATIONS"
    break
  fi

  ITER_DIR="$RUN_ROOT/iter-$(printf '%03d' "$ITERATION")"
  mkdir -p "$ITER_DIR"
  LOG_FILE="$ITER_DIR/${PHASE}.log"

  echo "Running $PHASE iteration $ITERATION..."
  if ! cat "$PROMPT_FILE" | "${ENGINE_CMD[@]}" >"$LOG_FILE" 2>&1; then
    echo "Engine command failed. See $LOG_FILE"
    exit 1
  fi

  if grep -Fq "$COMPLETION_PROMISE" "$LOG_FILE"; then
    echo "Completion promise detected. Stopping."
    break
  fi

  ITERATION=$((ITERATION + 1))
done
