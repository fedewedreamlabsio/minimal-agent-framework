#!/usr/bin/env bash
set -euo pipefail

PLAN_ITERS="${1:-2}"
BUILD_ITERS="${2:-30}"
VERIFY_ITERS="${3:-3}"

if ! [[ "$PLAN_ITERS" =~ ^[0-9]+$ && "$BUILD_ITERS" =~ ^[0-9]+$ && "$VERIFY_ITERS" =~ ^[0-9]+$ ]]; then
  echo "Usage: bash .wiggum/run_overnight.sh [plan-iters] [build-iters] [verify-iters]"
  echo "Example: bash .wiggum/run_overnight.sh 2 30 3"
  exit 1
fi

echo "Overnight run starting:"
echo "- plan iterations:   $PLAN_ITERS"
echo "- build iterations:  $BUILD_ITERS"
echo "- verify iterations: $VERIFY_ITERS"

bash .wiggum/loop.sh plan "$PLAN_ITERS"
bash .wiggum/loop.sh build "$BUILD_ITERS"
bash .wiggum/loop.sh verify "$VERIFY_ITERS"
