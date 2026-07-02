#!/usr/bin/env python3
"""Shared automatic timing and phase tracking for teleoperation experiments."""

from __future__ import annotations

import json
import math
import time
from collections import deque
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

import numpy as np


PHASE_PREP = "PREP"
PHASE_READY = "READY"
PHASE_APPROACH = "APPROACH"
PHASE_GRASP = "GRASP"
PHASE_TRANSPORT = "TRANSPORT"
PHASE_RELEASE = "RELEASE"
PHASE_COMPLETE = "COMPLETE"
PHASE_INCOMPLETE = "INCOMPLETE"


class ExperimentTimeline:
    """Track experiment events and phases using a monotonic clock.

    Times are based on ``time.perf_counter``.  Wall-clock time is retained only
    as metadata, never for duration calculations.
    """

    BASELINE_DURATION_S = 1.0
    BASELINE_MIN_SAMPLES = 50
    MOVEMENT_WINDOW_S = 0.20
    MOVEMENT_DISTANCE_M = 0.002
    CONTACT_HOLD_S = 0.050
    RELEASE_SETTLE_S = 0.50
    OPEN_WIDTH_M = 0.075

    def __init__(self, mode: str, subject_id: str = "unknown",
                 object_id: str = "unknown", trial_id: str = "unknown"):
        self.mode = mode
        self.subject_id = subject_id
        self.object_id = object_id
        self.trial_id = trial_id
        self.start_perf = time.perf_counter()
        self.start_wall = time.time()
        self.phase = PHASE_PREP
        self.events: List[Dict] = []
        self.event_times: Dict[str, float] = {}
        self._pending_events: List[str] = []
        self._baseline: List[float] = []
        self.force_baseline_mean = math.nan
        self.force_baseline_std = math.nan
        self.force_threshold = math.nan
        self._motion: Deque[Tuple[float, np.ndarray]] = deque()
        self._contact_candidate: Optional[float] = None
        self._release_open_since: Optional[float] = None
        self._last_gripper_state = "IDLE"
        self.completed = False
        self.incomplete = False
        self.mark("system_start", self.start_perf)

    def system_time(self, now: Optional[float] = None) -> float:
        return (time.perf_counter() if now is None else now) - self.start_perf

    def operation_time(self, now: Optional[float] = None) -> float:
        if "task_start" not in self.event_times:
            return math.nan
        t = self.system_time(now)
        end = self.event_times.get("task_end", t)
        return max(0.0, end - self.event_times["task_start"])

    def mark(self, name: str, now: Optional[float] = None, **details) -> bool:
        if name in self.event_times:
            return False
        now = time.perf_counter() if now is None else now
        t = now - self.start_perf
        event = {"event": name, "system_time": t, "phase": self.phase}
        event.update(details)
        self.events.append(event)
        self.event_times[name] = t
        self._pending_events.append(name)
        return True

    def consume_events(self) -> str:
        value = "|".join(self._pending_events)
        self._pending_events.clear()
        return value

    def add_force_baseline(self, force_mag: float, now: float) -> None:
        if self.phase != PHASE_PREP or not np.isfinite(force_mag):
            return
        self._baseline.append(float(force_mag))
        elapsed = now - self.start_perf
        if (elapsed >= self.BASELINE_DURATION_S and
                len(self._baseline) >= self.BASELINE_MIN_SAMPLES and
                not np.isfinite(self.force_threshold)):
            arr = np.asarray(self._baseline, dtype=float)
            self.force_baseline_mean = float(np.mean(arr))
            self.force_baseline_std = float(np.std(arr))
            self.force_threshold = max(
                1.0, self.force_baseline_mean + 3.0 * self.force_baseline_std
            )
            self.mark(
                "force_baseline_ready", now,
                mean_N=self.force_baseline_mean,
                std_N=self.force_baseline_std,
                threshold_N=self.force_threshold,
            )

    @property
    def baseline_ready(self) -> bool:
        return bool(np.isfinite(self.force_threshold))

    def set_ready(self, now: float) -> None:
        if self.phase != PHASE_PREP:
            return
        self.phase = PHASE_READY
        self._motion.clear()
        self.mark("system_ready", now)

    def start_task(self, now: Optional[float] = None,
                   trigger: str = "operator_key") -> bool:
        """Start operation timing explicitly after the system reaches READY."""
        if self.phase != PHASE_READY or self.completed or self.incomplete:
            return False
        now = time.perf_counter() if now is None else now
        self.phase = PHASE_APPROACH
        return self.mark("task_start", now, trigger=trigger)

    def observe_motion(self, pos: np.ndarray, now: float) -> None:
        if self.phase != PHASE_READY or self.completed:
            return
        p = np.asarray(pos, dtype=float).copy()
        self._motion.append((now, p))
        cutoff = now - self.MOVEMENT_WINDOW_S
        while len(self._motion) > 1 and self._motion[0][0] < cutoff:
            self._motion.popleft()
        if len(self._motion) < 2:
            return
        pts = np.stack([item[1] for item in self._motion])
        distance = float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))
        if distance >= self.MOVEMENT_DISTANCE_M:
            self.phase = PHASE_APPROACH
            self.mark("task_start", now, movement_distance_m=distance)

    def observe_contact(self, force_mag: float, now: float) -> None:
        if (self.phase not in (PHASE_APPROACH, PHASE_GRASP, PHASE_TRANSPORT) or
                "contact_onset" in self.event_times or
                not np.isfinite(self.force_threshold)):
            return
        if force_mag > self.force_threshold:
            if self._contact_candidate is None:
                self._contact_candidate = now
            elif now - self._contact_candidate >= self.CONTACT_HOLD_S:
                self.mark("contact_onset", self._contact_candidate,
                          threshold_N=self.force_threshold)
        else:
            self._contact_candidate = None

    def observe_gripper(self, state: str, width_m: float, now: float,
                        grasp_success: Optional[bool] = None) -> None:
        state = str(state)
        if state != self._last_gripper_state:
            if state == "GRASPING":
                if "task_start" not in self.event_times:
                    self.phase = PHASE_APPROACH
                    self.mark("task_start", now, trigger="gripper")
                self.phase = PHASE_GRASP
                self.mark("grasp_start", now)
            elif state == "HOLDING":
                self.phase = PHASE_TRANSPORT
                self.mark("grasp_success", now,
                          grasp_success=True if grasp_success is None else grasp_success)
            elif state == "RELEASING":
                self.phase = PHASE_RELEASE
                self.mark("release_start", now)
                self._release_open_since = None
            self._last_gripper_state = state

        if self.phase == PHASE_RELEASE and state == "IDLE":
            is_open = np.isfinite(width_m) and width_m >= self.OPEN_WIDTH_M
            if is_open:
                if self._release_open_since is None:
                    self._release_open_since = now
                elif now - self._release_open_since >= self.RELEASE_SETTLE_S:
                    self.phase = PHASE_COMPLETE
                    self.completed = True
                    self.mark("task_end", now, success=True)
            else:
                self._release_open_since = None

    def abort(self, reason: str = "interrupted") -> None:
        if self.completed or self.incomplete:
            return
        self.incomplete = True
        self.phase = PHASE_INCOMPLETE
        self.mark("task_incomplete", reason=reason, success=False)

    def snapshot(self, now: Optional[float] = None) -> Dict:
        return {
            "system_time": self.system_time(now),
            "operation_time": self.operation_time(now),
            "phase": self.phase,
            "completed": self.completed,
            "incomplete": self.incomplete,
            "force_baseline_mean": self.force_baseline_mean,
            "force_baseline_std": self.force_baseline_std,
            "force_threshold": self.force_threshold,
        }

    def to_dict(self) -> Dict:
        recognition = math.nan
        if "first_frame" in self.event_times and "vision_lock" in self.event_times:
            recognition = self.event_times["vision_lock"] - self.event_times["first_frame"]
        operation = math.nan
        if "task_start" in self.event_times and "task_end" in self.event_times:
            operation = self.event_times["task_end"] - self.event_times["task_start"]
        return {
            "schema_version": 2,
            "mode": self.mode,
            "subject_id": self.subject_id,
            "object_id": self.object_id,
            "trial_id": self.trial_id,
            "started_at_unix": self.start_wall,
            "phase": self.phase,
            "completed": self.completed,
            "incomplete": self.incomplete,
            "recognition_time_s": recognition,
            "operation_time_s": operation,
            "force_baseline_mean_N": self.force_baseline_mean,
            "force_baseline_std_N": self.force_baseline_std,
            "force_threshold_N": self.force_threshold,
            "events": self.events,
        }

    def save_events(self, path: Path) -> None:
        path = Path(path)
        def clean(value):
            if isinstance(value, dict):
                return {k: clean(v) for k, v in value.items()}
            if isinstance(value, list):
                return [clean(v) for v in value]
            if isinstance(value, (float, np.floating)) and not np.isfinite(value):
                return None
            return value
        with path.open("w", encoding="utf-8") as f:
            json.dump(clean(self.to_dict()), f, ensure_ascii=False, indent=2, allow_nan=False)
