#!/usr/bin/env python3

from __future__ import annotations

import tempfile
import unittest
from collections import Counter
from pathlib import Path

from generate_kfb_timing_schedule import PARTICIPANTS, build_schedules
from kfb_timing_protocol import (
    CONDITIONS,
    DEFAULT_CONFIG,
    KfbTimingRuntime,
    NS_PER_S,
    classify_delivery,
    config_hash,
    write_config,
)


class KfbTimingRuntimeTests(unittest.TestCase):
    def simulate(self, condition_code: str):
        dt_ns = int(0.005 * NS_PER_S)
        runtime = KfbTimingRuntime(CONDITIONS[condition_code], 0)
        snapshots = []
        for now_ns in range(0, int(4.0 * NS_PER_S), dt_ns):
            now_s = now_ns / NS_PER_S
            force = 1.0 if now_s < 2.10 else 2.0
            snapshot = runtime.step(force, now_ns)
            snapshots.append((now_ns, snapshot))
            if snapshot.completed:
                break
        return runtime, snapshots

    def test_all_conditions_reach_expected_timing_and_completion(self):
        for code, spec in CONDITIONS.items():
            with self.subTest(code=code):
                runtime, snapshots = self.simulate(code)
                self.assertTrue(runtime.completed)
                contact_ns = runtime.contact_confirmed_ns
                self.assertIsNotNone(contact_ns)
                on_times = [
                    now_ns for now_ns, snap in snapshots
                    if "kfb_intervention_on" in snap.events
                ]
                off_times = [
                    now_ns for now_ns, snap in snapshots
                    if "kfb_intervention_off" in snap.events
                ]
                self.assertEqual(len(on_times), 1)
                self.assertEqual(len(off_times), 1)
                onset = (on_times[0] - contact_ns) / NS_PER_S
                offset = (off_times[0] - contact_ns) / NS_PER_S
                self.assertAlmostEqual(onset, spec.onset_s, delta=0.0051)
                self.assertAlmostEqual(offset, spec.offset_s, delta=0.0051)

    def test_absolute_force_safety_abort_after_baseline(self):
        runtime = KfbTimingRuntime(CONDITIONS["C0"], 0)
        for index in range(401):
            runtime.step(1.0, index * 5_000_000)
        snapshot = runtime.step(5.01, 2_010_000_000)
        self.assertTrue(snapshot.aborted)
        self.assertEqual(snapshot.abort_reason, "force_limit_exceeded")
        self.assertEqual(snapshot.K_fb_commanded, DEFAULT_CONFIG.K_fb_baseline)

    def test_absolute_force_safety_abort_during_baseline(self):
        runtime = KfbTimingRuntime(CONDITIONS["C0"], 0)
        snapshot = runtime.step(5.01, 5_000_000)
        self.assertTrue(snapshot.aborted)
        self.assertFalse(snapshot.baseline_ready)
        self.assertIn("safety_abort", snapshot.events)

    def test_delivery_classification(self):
        for code, spec in CONDITIONS.items():
            self.assertEqual(
                classify_delivery(spec.onset_s, spec.offset_s, spec.expected_phi),
                code,
            )

    def test_config_hash_and_serialization_are_stable(self):
        self.assertEqual(config_hash(), config_hash())
        self.assertEqual(len(config_hash()), 64)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            write_config(path)
            self.assertIn(config_hash(), path.read_text(encoding="utf-8"))


class ScheduleTests(unittest.TestCase):
    def test_schedule_counts_and_blinding(self):
        run_rows, oracle_rows = build_schedules()
        self.assertEqual(len(run_rows), 105)
        self.assertEqual(len(oracle_rows), 105)
        self.assertEqual(len({row["trial_id"] for row in run_rows}), 105)
        self.assertEqual(len({row["masked_condition"] for row in run_rows}), 105)
        self.assertFalse(any("true_condition" in row for row in run_rows))
        self.assertEqual(sum(row["phase"] == "engineering" for row in run_rows), 25)
        self.assertEqual(sum(row["phase"] == "training" for row in run_rows), 20)
        self.assertEqual(sum(row["phase"] == "measured" for row in run_rows), 60)
        for participant in PARTICIPANTS:
            measured = [
                row for row in oracle_rows
                if row["participant_id"] == participant and row["phase"] == "measured"
            ]
            self.assertEqual(len(measured), 15)
            counts = {code: 0 for code in CONDITIONS}
            for row in measured:
                counts[row["true_condition"]] += 1
            self.assertEqual(set(counts.values()), {3})
        run_by_id = {row["trial_id"]: row for row in run_rows}
        measured = [row for row in oracle_rows if row["phase"] == "measured"]
        position_counts = Counter(
            (row["true_condition"], int(run_by_id[row["trial_id"]]["position"]))
            for row in measured
        )
        self.assertTrue(all(
            position_counts[(code, position)] in (2, 3)
            for code in CONDITIONS for position in range(1, 6)
        ))


if __name__ == "__main__":
    unittest.main()
