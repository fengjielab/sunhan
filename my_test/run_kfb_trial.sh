#!/usr/bin/env bash
set -euo pipefail

# One-command launcher for the prospective K_fb timing pilot.
# Run from any directory with: bash ~/sunhan/my_test/run_kfb_trial.sh

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

TRIAL_ID="${1:-ENG_E01_01}"
SUBJECT_ID="${2:-ENGINEER}"
PILOT_DIR="$SCRIPT_DIR/paper2_sci/23_kfb_timing_pilot"
SCHEDULE_DIR="$PILOT_DIR/frozen_schedule_v6"
ORACLE_PATH="$SCHEDULE_DIR/private_oracle/oracle.csv"
START_POSE_PATH="$PILOT_DIR/start_pose_v1.json"
DATA_DIR="$SCRIPT_DIR/data/kfb_timing_pilot"

for required_file in \
  "$SCRIPT_DIR/interactive_teleop.py" \
  "$SCRIPT_DIR/capture_kfb_start_pose.py" \
  "$SCRIPT_DIR/verify_kfb_timing_setup.py" \
  "$ORACLE_PATH"; do
  if [[ ! -f "$required_file" ]]; then
    echo "错误：缺少文件 $required_file" >&2
    exit 1
  fi
done

if [[ ! -f "$START_POSE_PATH" ]]; then
  echo
  echo "首次运行需要冻结起始位姿。"
  echo "请先确认："
  echo "  1) 弹性垫至少 60 x 60 x 10 mm，并已刚性固定；"
  echo "  2) 5 N 内不触底、不移动；"
  echo "  3) Panda末端已由安全流程放在垫面法向外 30 +/- 2 mm；"
  echo "  4) 急停可立即触及。"
  read -r -p "四项均确认后输入 YES：" CONFIRMATION
  if [[ "$CONFIRMATION" != "YES" ]]; then
    echo "未确认安全条件，已停止。"
    exit 1
  fi

  python3 "$SCRIPT_DIR/capture_kfb_start_pose.py" \
    --output "$START_POSE_PATH" \
    --pad-width-mm 60 \
    --pad-height-mm 60 \
    --pad-thickness-mm 10 \
    --pad-distance-mm 30 \
    --fixed-target-checked
fi

echo
echo "正在校验冻结日程、软件哈希与起始位姿……"
python3 "$SCRIPT_DIR/verify_kfb_timing_setup.py" \
  --schedule-dir "$SCHEDULE_DIR" \
  --start-pose-file "$START_POSE_PATH"

mkdir -p "$DATA_DIR"

echo
echo "即将启动：subject=$SUBJECT_ID, trial=$TRIAL_ID, mode=kfb_timing"
echo "启动后先保持静止2秒；看到提示后缓慢接近；出现 HOLD 后保持1.5秒。"
if [[ "${KFB_SKIP_LAUNCH_CONFIRM:-0}" != "1" ]]; then
  read -r -p "按 Enter 启动试次，或按 Ctrl+C 取消："
fi

exec python3 "$SCRIPT_DIR/interactive_teleop.py" \
  --mode kfb_timing \
  --subject-id "$SUBJECT_ID" \
  --trial-id "$TRIAL_ID" \
  --object-id FIXED_PAD \
  --kfb-oracle "$ORACLE_PATH" \
  --kfb-start-pose-file "$START_POSE_PATH" \
  --trajectory-dir "$DATA_DIR"
