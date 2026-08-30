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
                    "capture_perf_time_ns": "100", "inference_start_perf_time_ns": "110",
                    "inference_end_perf_time_ns": "120", "result_receive_perf_time_ns": "130",
                    "parameter_apply_start_perf_time_ns": "140",
                    "u_h_cmd_norm_N": "1.0", "haptic_force_limit_N": "3.0",
                    "control_dt": "0.005", "control_deadline_miss": "0",
                    "haptic_saturated": "0",
                })
                if index == 0:
                    row["event"] = "task_start|vision_lock"
                if index == 9:
                    row["event"] = "task_end"
                rows.append(row)
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
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
