#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

export VOXDRIVE_VOICE_ENABLED="${VOXDRIVE_VOICE_ENABLED:-1}"
# Voice demo mode must always start with the ego vehicle held at full brake.
export VOXDRIVE_START_HOLD=1
export VOXDRIVE_VOICE_COMMAND_PATH="${VOXDRIVE_VOICE_COMMAND_PATH:-$PROJECT_ROOT/voxdrive/runtime/voice_command.json}"

exec "$PROJECT_ROOT/voxdrive/scripts/run_minddrive_route.sh" "$@"
