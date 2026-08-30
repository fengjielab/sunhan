import csv
import json
import tempfile
import unittest
from pathlib import Path

from analyze_ablation import read_rows
from validate_trial import REQUIRED_COLUMNS, validate


class AnalysisToolTests(unittest.TestCase):
    def test_schema_v3_trial_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "I_run.csv"
            fields = sorted(REQUIRED_COLUMNS)
            rows = []
            event_by_index = {
                0: "force_baseline_ready",
                1: "vision_lock",
                2: "parameter_transition_end",
                3: "system_ready",
                4: "task_start",
                5: "grasp_start",
                6: "grasp_success",
                7: "release_start",
                9: "task_end",
            }
            for index in range(10):
                row = {key: "" for key in fields}
                row.update({
                    "schema_version": "3", "system_time": str(index * 0.005),
                    "mode": "I", "run_uuid": "run-1", "run_kind": "pilot",
                    "session_id": "P01_S1", "schedule_id": "schedule",
                    "subject_id": "P01", "object_id": "apple", "trial_id": "P01_T01",
                    "trial_order": "1", "repetition": "1",
                    "adaptive_impedance": "1", "adaptive_haptics": "0",
                    "adaptive_gripper": "0", "vision_locked": "1",
                    "vision_class": "apple", "vision_locked_class": "apple",
                    "vision_label": "soft",
                    "capture_perf_time_ns": "100", "inference_start_perf_time_ns": "110",
                    "inference_end_perf_time_ns": "120", "result_receive_perf_time_ns": "130",
                    "parameter_apply_start_perf_time_ns": "140",
                    "u_h_cmd_norm_N": "1.0", "haptic_force_limit_N": "3.0",
                    "K_fb": "0.4", "deadband": "0.4",
                    "gripper_speed": "0.05", "gripper_force": "15.0",
                    "control_target_frequency_hz": "200",
                    "control_target_dt_s": "0.005",
                    "control_dt": "0.005", "control_compute_time_s": "0.004",
                    "control_deadline_miss": "0",
                    "haptic_saturated": "0",
                })
                row["event"] = event_by_index.get(index, "")
                rows.append(row)
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            config = {
                "run_uuid": "run-1", "run_kind": "pilot",
                "session_id": "P01_S1", "schedule_id": "schedule",
                "subject_id": "P01", "object_id": "apple",
                "trial_id": "P01_T01", "trial_order": 1,
                "repetition": 1, "condition": "I",
                "control": {
                    "target_frequency_hz": 200,
                    "target_period_s": 0.005,
                },
                "design": {"fixed_baseline": {
                    "K_fb": 0.4, "deadband": 0.4,
                    "gripper_speed": 0.05, "gripper_force": 15.0,
                }},
            }
            (Path(directory) / "run_config_run-1.json").write_text(
                json.dumps(config), encoding="utf-8"
            )
            self.assertEqual(validate(path)["status"], "pass")

    def test_trial_table_uses_timeout_for_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary = {
                "run_uuid": "run-2", "subject_id": "P01", "object_id": "cup",
                "trial_id": "P01_T02", "trial_order": 2, "repetition": 1,
                "mode": {"condition": "I_G", "adaptive_haptics": False,
                         "adaptive_gripper": True},
                "experiment": {"completed": False, "events": [
                    {"event": "task_start", "system_time": 1.0}
                ]},
            }
            (root / "I_G_run-2_summary.json").write_text(json.dumps(summary), encoding="utf-8")
            rows = read_rows(root, 120.0)
            self.assertEqual(rows[0]["penalized_time_s"], 120.0)
            self.assertEqual(rows[0]["success"], 0)


if __name__ == "__main__":
    unittest.main()
