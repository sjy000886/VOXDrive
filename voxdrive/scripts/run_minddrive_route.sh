#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

CARLA_ROOT="${CARLA_ROOT:-$PROJECT_ROOT/0.9.15}"
if [[ ! -x "$CARLA_ROOT/CarlaUE4.sh" ]]; then
  echo "CARLA_ROOT is invalid: $CARLA_ROOT" >&2
  echo "Set it before running, for example: export CARLA_ROOT=/home/ys/MindDrive/0.9.15" >&2
  exit 1
fi

export CARLA_ROOT
export IS_BENCH2DRIVE="${IS_BENCH2DRIVE:-1}"
export SCENARIO_RUNNER_ROOT="${SCENARIO_RUNNER_ROOT:-$PROJECT_ROOT/rl_projects/scenario_runner}"
export VOXDRIVE_VOICE_ENABLED="${VOXDRIVE_VOICE_ENABLED:-1}"
export VOXDRIVE_START_HOLD="${VOXDRIVE_START_HOLD:-0}"
export VOXDRIVE_VOICE_COMMAND_PATH="${VOXDRIVE_VOICE_COMMAND_PATH:-$PROJECT_ROOT/voxdrive/runtime/voice_command.json}"
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/rl_projects:$PROJECT_ROOT/rl_projects/scenario_runner:$CARLA_ROOT/PythonAPI/carla/dist/carla-0.9.15-py3.7-linux-x86_64.egg:$CARLA_ROOT/PythonAPI/carla:${PYTHONPATH:-}"

ROUTES="${ROUTES:-data/routes/rollout_routes.xml}"
ROUTES_SUBSET="${ROUTES_SUBSET:-1773}"
REPETITIONS="${REPETITIONS:-1}"
CONFIG="${CONFIG:-adzoo/minddrive/configs/minddrive_qwen2_05B_infer.py}"
CKPT="${CKPT:-ckpts/minddrive/minddrive_rltrain.pth}"
PORT="${PORT:-2000}"
TM_PORT="${TM_PORT:-8000}"
TIMEOUT="${TIMEOUT:-120}"
GPU_RANK="${GPU_RANK:-0}"
TRACK="${TRACK:-SENSORS}"
LOAD_ONCE="${LOAD_ONCE:-0}"
CARLA_RENDER_MODE="${CARLA_RENDER_MODE:-windowed}"
CARLA_QUALITY_LEVEL="${CARLA_QUALITY_LEVEL:-Low}"
CARLA_EXTRA_ARGS="${CARLA_EXTRA_ARGS:-}"

mkdir -p outputs
CHECKPOINT="${CHECKPOINT:-outputs/minddrive_route_${ROUTES_SUBSET}.json}"
DEBUG_CHECKPOINT="${DEBUG_CHECKPOINT:-outputs/minddrive_route_${ROUTES_SUBSET}_debug.json}"

python rl_projects/leaderboard/leaderboard_evaluator.py \
  --host localhost \
  --port "$PORT" \
  --traffic-manager-port "$TM_PORT" \
  --timeout "$TIMEOUT" \
  --routes "$ROUTES" \
  --routes-subset "$ROUTES_SUBSET" \
  --repetitions "$REPETITIONS" \
  --agent team_code/minddrive_b2d_agent.py \
  --agent-config "${CONFIG}+${CKPT}" \
  --track "$TRACK" \
  --checkpoint "$CHECKPOINT" \
  --debug-checkpoint "$DEBUG_CHECKPOINT" \
  --gpu-rank "$GPU_RANK" \
  --load-once "$LOAD_ONCE" \
  --carla-render-mode "$CARLA_RENDER_MODE" \
  --carla-quality-level "$CARLA_QUALITY_LEVEL" \
  --carla-extra-args "$CARLA_EXTRA_ARGS"
