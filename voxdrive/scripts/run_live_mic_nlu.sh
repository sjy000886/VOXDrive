#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

python voxdrive/voxdrive_nlu/live_mic_nlu.py "$@"

