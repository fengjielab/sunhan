#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from trust_correction import (
    TrustCorrectionConfig,
    TrustCorrectionState,
    correction_window_open,
    config_hash,
    update_trust_correction,
)


class TrustCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.cfg = TrustCorrectionConfig()

    def step(self, state, force, current, prior=200.0, threshold=1.0):
        return update_trust_correction(
            state,
            force_mag_N=force,
            force_threshold_N=threshold,
            current_K=current,
            prior_K=prior,
            config=self.cfg,
        )

    def test_no_risk_preserves_prior(self):
        result = self.step(TrustCorrectionState(), 1.0, 200.0)
        self.assertEqual(result.state.trust, 1.0)
        self.assertEqual(result.command_K, 200.0)
        self.assertFalse(result.active)

    def test_risk_monotonically_reduces_trust_and_stiffness(self):
        state = TrustCorrectionState()
        current = 200.0
        trusts = []
        stiffness = []
        for _ in range(30):
            result = self.step(state, 4.0, current)
            state = result.state
            current = result.command_K
            trusts.append(state.trust)
            stiffness.append(current)
        self.assertTrue(all(a >= b for a, b in zip(trusts, trusts[1:])))
        self.assertTrue(all(a >= b for a, b in zip(stiffness, stiffness[1:])))
        self.assertGreaterEqual(current, self.cfg.K_min)
        self.assertLess(current, 200.0)

    def test_correct_soft_prior_cannot_fall_below_safe_anchor(self):
        state = TrustCorrectionState()
        current = 50.0
        for _ in range(50):
            result = self.step(state, 10.0, current, prior=50.0)
            state = result.state
            current = result.command_K
        self.assertEqual(current, 50.0)
        self.assertEqual(result.target_K, 50.0)

    def test_update_respects_step_and_global_bounds(self):
        result = self.step(TrustCorrectionState(), 10.0, 200.0)
        self.assertLessEqual(abs(result.command_K - 200.0), 20.0)
        self.assertGreaterEqual(result.command_K, 50.0)
        self.assertLessEqual(result.command_K, 200.0)

    def test_config_hash_is_repeatable(self):
        self.assertEqual(config_hash(self.cfg), config_hash(self.cfg))
        self.assertEqual(len(config_hash(self.cfg)), 16)

    def test_correction_window_is_strictly_bounded(self):
        self.assertFalse(correction_window_open(0.049, self.cfg))
        self.assertTrue(correction_window_open(0.05, self.cfg))
        self.assertTrue(correction_window_open(0.80, self.cfg))
        self.assertFalse(correction_window_open(0.801, self.cfg))


if __name__ == "__main__":
    unittest.main()
