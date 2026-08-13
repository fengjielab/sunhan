#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ $# -ne 2 ]]; then
  echo "用法: bash run_kfb_formal_trial.sh TRIAL_ID PARTICIPANT_ID" >&2
  echo "示例: bash run_kfb_formal_trial.sh F01_M01_01 F01" >&2
  exit 2
fi

TRIAL_ID="$1"
PARTICIPANT_ID="$2"
PILOT_DIR="$SCRIPT_DIR/paper2_sci/23_kfb_timing_pilot"
SCHEDULE_DIR="$PILOT_DIR/frozen_schedule_formal_v1"
ORACLE_PATH="$SCHEDULE_DIR/private_oracle/oracle.csv"
START_POSE_PATH="$PILOT_DIR/start_pose_v1.json"
DATA_DIR="$SCRIPT_DIR/data/kfb_timing_formal_v1"

python3 "$SCRIPT_DIR/verify_kfb_timing_formal_setup.py" \
  --schedule-dir "$SCHEDULE_DIR" \
  --start-pose-file "$START_POSE_PATH"

mkdir -p "$DATA_DIR"

echo
echo "即将启动正式试次：participant=$PARTICIPANT_ID, trial=$TRIAL_ID"
echo "启动后先保持静止2秒；看到提示后缓慢接近；出现HOLD后保持轻触1.5秒。"
read -r -p "按 Enter 启动，或按 Ctrl+C 取消："

exec python3 "$SCRIPT_DIR/interactive_teleop.py" \
  --mode kfb_timing \
  --subject-id "$PARTICIPANT_ID" \
  --trial-id "$TRIAL_ID" \
  --object-id FIXED_PAD \
  --kfb-oracle "$ORACLE_PATH" \
  --kfb-start-pose-file "$START_POSE_PATH" \
  --trajectory-dir "$DATA_DIR"
