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

if [[ ! "$TRIAL_ID" =~ ^(F[0-9]{2})_M(0[1-3])_(0[1-5])$ ]]; then
  echo "错误：Trial ID格式不正确：$TRIAL_ID" >&2
  echo "正确示例：F01_M01_01（参与者F01，第1区组，第1次）" >&2
  exit 2
fi

TRIAL_PARTICIPANT_ID="${BASH_REMATCH[1]}"
BLOCK_ID="${BASH_REMATCH[2]}"
if [[ "$PARTICIPANT_ID" != "$TRIAL_PARTICIPANT_ID" ]]; then
  echo "错误：Trial ID属于$TRIAL_PARTICIPANT_ID，但输入的参与者是$PARTICIPANT_ID。" >&2
  exit 2
fi

PILOT_DIR="$SCRIPT_DIR/paper2_sci/23_kfb_timing_pilot"
SCHEDULE_DIR="$PILOT_DIR/frozen_schedule_formal_v1"
ORACLE_PATH="$SCHEDULE_DIR/private_oracle/oracle.csv"
START_POSE_PATH="$PILOT_DIR/start_pose_v1.json"
DATA_DIR="$SCRIPT_DIR/data/kfb_timing_formal_v1/participants/$PARTICIPANT_ID/block_$BLOCK_ID"

python3 "$SCRIPT_DIR/verify_kfb_timing_formal_setup.py" \
  --schedule-dir "$SCHEDULE_DIR" \
  --start-pose-file "$START_POSE_PATH"

mkdir -p "$DATA_DIR"

echo
echo "即将启动正式试次：participant=$PARTICIPANT_ID, trial=$TRIAL_ID"
echo "本次数据将自动保存到：$DATA_DIR"
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
