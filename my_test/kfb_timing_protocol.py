#!/usr/bin/env python3
"""Pure protocol logic for the prospective K_fb timing pilot.

This module deliberately has no robot or haptic-device dependency.  The live
controller, schedule generator, offline reconstruction, and unit tests all use
the same frozen condition definitions from here.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple


NS_PER_S = 1_000_000_000


@dataclass(frozen=True)
class ConditionSpec:
    code: str
    label: str
    onset_s: float
    offset_s: float
    expected_epsilon_s: float
    expected_phi: float


CONDITIONS: Dict[str, ConditionSpec] = {
    "C0": ConditionSpec("C0", "Correct", 0.20, 1.20, 0.00, 1.000),
    "C1": ConditionSpec("C1", "Early", 0.05, 1.20, -0.15, 1.000),
    "C2": ConditionSpec("C2", "Late", 0.50, 1.20, 0.30, 0.625),
    "C3": ConditionSpec("C3", "Short", 0.20, 0.60, 0.00, 0.500),
    "C4": ConditionSpec("C4", "Zero", 1.10, 1.30, 0.90, 0.000),
}


@dataclass(frozen=True)
class KfbTimingConfig:
    protocol_version: str = "kfb-timing-pilot-v1"
    control_frequency_hz: float = 200.0
    baseline_duration_s: float = 2.0
    baseline_min_samples: int = 300
    baseline_sigma_multiplier: float = 1.4826
    contact_on_sigma: float = 5.0
    contact_off_sigma: float = 3.0
    contact_min_delta_N: float = 0.75
    contact_off_fraction: float = 0.60
    contact_hold_s: float = 0.050
    outcome_window_start_s: float = 0.20
    outcome_window_end_s: float = 1.00
    trial_end_after_contact_s: float = 1.50
    K_trans_N_per_m: float = 200.0
    K_rot_Nm_per_rad: float = 13.0
    damping_ratio: float = 1.2
    position_scale: float = 3.0
    deadband_N: float = 0.3
    K_fb_baseline: float = 0.5
    K_fb_intervention: float = 0.7
    force_abort_N: float = 5.0
    haptic_command_limit_N: float = 2.0
    target_speed_limit_m_s: float = 0.03
    max_metric_gap_s: float = 0.020
    movement_speed_threshold_m_s: float = 0.005
    movement_sustain_s: float = 0.020
    contact_normal_axis: str = "z"

    def validate(self) -> None:
        if self.baseline_duration_s <= 0 or self.baseline_min_samples < 2:
            raise ValueError("baseline requirements must be positive")
        if not 0 < self.contact_hold_s < self.trial_end_after_contact_s:
            raise ValueError("invalid contact hold or trial duration")
        if not 0 <= self.outcome_window_start_s < self.outcome_window_end_s:
            raise ValueError("invalid outcome window")
        if self.K_fb_intervention <= self.K_fb_baseline:
            raise ValueError("intervention K_fb must exceed baseline K_fb")
        if self.contact_normal_axis not in ("x", "y", "z"):
            raise ValueError("contact_normal_axis must be x, y, or z")
        for spec in CONDITIONS.values():
            if not 0 <= spec.onset_s < spec.offset_s <= self.trial_end_after_contact_s:
                raise ValueError(f"invalid condition interval: {spec.code}")


DEFAULT_CONFIG = KfbTimingConfig()


def _canonical_payload(config: KfbTimingConfig) -> dict:
    config.validate()
    return {
        "config": asdict(config),
        "conditions": {key: asdict(CONDITIONS[key]) for key in sorted(CONDITIONS)},
    }


def config_hash(config: KfbTimingConfig = DEFAULT_CONFIG) -> str:
    payload = json.dumps(
        _canonical_payload(config), sort_keys=True, ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_config(path: Path, config: KfbTimingConfig = DEFAULT_CONFIG) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _canonical_payload(config)
    payload["config_sha256"] = config_hash(config)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    """Hash exact bytes; use for acquired artifacts that must not change."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text_file(path: Path) -> str:
    """Hash UTF-8 text canonically across Windows/Linux checkouts."""
    text = Path(path).read_text(encoding="utf-8-sig")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def software_hash(paths: Iterable[Path]) -> str:
    """Hash source text after BOM/newline normalization."""
    digest = hashlib.sha256()
    for path in sorted((Path(item) for item in paths), key=lambda item: item.name):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        text = path.read_text(encoding="utf-8-sig")
        canonical = text.replace("\r\n", "\n").replace("\r", "\n")
        digest.update(canonical.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


@dataclass(frozen=True)
class RuntimeSnapshot:
    baseline_ready: bool
    contact_candidate: bool
    contact_confirmed: bool
    contact_confirmed_ns: Optional[int]
    intervention_active: bool
    intervention_state: str
    K_fb_commanded: float
    transition_reason: str
    force_baseline_median_N: float
    force_baseline_sigma_N: float
    force_threshold_on_N: float
    force_threshold_off_N: float
    force_corrected_N: float
    completed: bool
    aborted: bool
    abort_reason: str
    events: Tuple[str, ...]


class KfbTimingRuntime:
    """Deterministic baseline/contact/intervention state machine."""

    def __init__(
        self,
        condition: ConditionSpec,
        start_mono_ns: int,
        config: KfbTimingConfig = DEFAULT_CONFIG,
    ) -> None:
        if condition.code not in CONDITIONS:
            raise ValueError(f"unknown condition: {condition.code}")
        config.validate()
        self.condition = condition
        self.config = config
        self.start_mono_ns = int(start_mono_ns)
        self._baseline_values = []
        self.baseline_ready = False
        self.baseline_median_N = math.nan
        self.baseline_sigma_N = math.nan
        self.threshold_on_N = math.nan
        self.threshold_off_N = math.nan
        self.contact_candidate_ns: Optional[int] = None
        self.contact_confirmed_ns: Optional[int] = None
        self.intervention_active = False
        self.intervention_ever_activated = False
        self.intervention_ever_deactivated = False
        self.completed = False
        self.aborted = False
        self.abort_reason = ""

    def _finalize_baseline(self) -> None:
        median = float(statistics.median(self._baseline_values))
        mad = float(statistics.median(abs(value - median) for value in self._baseline_values))
        sigma = self.config.baseline_sigma_multiplier * mad
        delta_on = max(self.config.contact_min_delta_N, self.config.contact_on_sigma * sigma)
        delta_off = max(
            self.config.contact_off_sigma * sigma,
            self.config.contact_off_fraction * delta_on,
        )
        self.baseline_median_N = median
        self.baseline_sigma_N = sigma
        self.threshold_on_N = median + delta_on
        self.threshold_off_N = median + delta_off
        self.baseline_ready = True

    def abort(self, reason: str) -> None:
        if self.completed or self.aborted:
            return
        self.aborted = True
        self.abort_reason = str(reason)
        self.intervention_active = False

    def step(self, force_mag_N: float, now_mono_ns: int) -> RuntimeSnapshot:
        now_mono_ns = int(now_mono_ns)
        if now_mono_ns < self.start_mono_ns:
            raise ValueError("monotonic time moved backwards")
        events = []
        transition_reason = ""
        force_value = float(force_mag_N)

        # The 5 N stop is an absolute Panda-estimated force-magnitude limit,
        # active from the first sample. Baseline correction is only for contact
        # detection and the operational excess-force endpoint.
        if (
            not self.aborted
            and not self.completed
            and math.isfinite(force_value)
            and force_value > self.config.force_abort_N
        ):
            self.abort("force_limit_exceeded")
            transition_reason = "safety_abort"
            events.append("safety_abort")

        if not self.baseline_ready and not self.aborted:
            if math.isfinite(force_value):
                self._baseline_values.append(force_value)
            elapsed_s = (now_mono_ns - self.start_mono_ns) / NS_PER_S
            if (
                elapsed_s >= self.config.baseline_duration_s
                and len(self._baseline_values) >= self.config.baseline_min_samples
            ):
                self._finalize_baseline()
                events.append("force_baseline_ready")

        corrected = (
            max(force_value - self.baseline_median_N, 0.0)
            if self.baseline_ready and math.isfinite(force_value)
            else math.nan
        )

        if self.baseline_ready and not self.aborted and not self.completed:
            if self.contact_confirmed_ns is None:
                if force_value >= self.threshold_on_N:
                    if self.contact_candidate_ns is None:
                        self.contact_candidate_ns = now_mono_ns
                        events.append("contact_candidate")
                    held_s = (now_mono_ns - self.contact_candidate_ns) / NS_PER_S
                    if held_s >= self.config.contact_hold_s:
                        self.contact_confirmed_ns = now_mono_ns
                        events.append("contact_confirmed")
                elif force_value < self.threshold_off_N:
                    self.contact_candidate_ns = None

        if self.contact_confirmed_ns is not None and not self.aborted and not self.completed:
            contact_elapsed_s = (now_mono_ns - self.contact_confirmed_ns) / NS_PER_S
            desired_active = self.condition.onset_s <= contact_elapsed_s < self.condition.offset_s
            if desired_active != self.intervention_active:
                self.intervention_active = desired_active
                if desired_active:
                    self.intervention_ever_activated = True
                    transition_reason = "scheduled_onset"
                    events.append("kfb_intervention_on")
                else:
                    self.intervention_ever_deactivated = True
                    transition_reason = "scheduled_offset"
                    events.append("kfb_intervention_off")
            if contact_elapsed_s >= self.config.trial_end_after_contact_s:
                self.intervention_active = False
                self.completed = True
                transition_reason = transition_reason or "scheduled_trial_end"
                events.append("trial_complete")

        if self.aborted:
            state = "aborted"
        elif self.completed:
            state = "complete"
        elif not self.baseline_ready:
            state = "baseline"
        elif self.contact_confirmed_ns is None:
            state = "approach"
        elif self.intervention_active:
            state = "intervention"
        else:
            state = "hold_baseline"

        return RuntimeSnapshot(
            baseline_ready=self.baseline_ready,
            contact_candidate=self.contact_candidate_ns is not None,
            contact_confirmed=self.contact_confirmed_ns is not None,
            contact_confirmed_ns=self.contact_confirmed_ns,
            intervention_active=self.intervention_active,
            intervention_state=state,
            K_fb_commanded=(
                self.config.K_fb_intervention
                if self.intervention_active
                else self.config.K_fb_baseline
            ),
            transition_reason=transition_reason,
            force_baseline_median_N=self.baseline_median_N,
            force_baseline_sigma_N=self.baseline_sigma_N,
            force_threshold_on_N=self.threshold_on_N,
            force_threshold_off_N=self.threshold_off_N,
            force_corrected_N=corrected,
            completed=self.completed,
            aborted=self.aborted,
            abort_reason=self.abort_reason,
            events=tuple(events),
        )


def classify_delivery(onset_s: float, offset_s: float, phi: float) -> str:
    """Classify a reconstructed delivery without consulting outcome columns."""
    if not all(math.isfinite(value) for value in (onset_s, offset_s, phi)):
        return "NOT_EVALUABLE"
    best_code = "NOT_EVALUABLE"
    best_distance = math.inf
    for code, spec in CONDITIONS.items():
        distance = (
            abs(onset_s - spec.onset_s) / 0.05
            + abs(offset_s - spec.offset_s) / 0.05
            + abs(phi - spec.expected_phi) / 0.05
        )
        if distance < best_distance:
            best_distance = distance
            best_code = code
    return best_code if best_distance <= 3.0 else "NOT_EVALUABLE"
