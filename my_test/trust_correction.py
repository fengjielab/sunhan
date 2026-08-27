#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""接触风险驱动的视觉先验可信度修正（纯计算模块）。

该模块不依赖机器人或视觉硬件，便于在正式实验前离线验证更新律。
它只修正“已施加先验的可信度”，不把接触力解释为新的材料类别。
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import math


@dataclass(frozen=True)
class TrustCorrectionConfig:
    """固定实验参数；任何字段变化都会改变配置哈希。"""

    version: str = "trust-v1.1"
    update_interval_s: float = 0.05
    contact_delay_s: float = 0.05
    posterior_window_s: float = 0.80
    safe_anchor_K: float = 50.0
    K_min: float = 50.0
    K_max: float = 200.0
    force_guard_min_N: float = 1.5
    force_saturation_N: float = 4.0
    risk_ema_alpha: float = 0.30
    trust_decay_per_update: float = 0.10
    stiffness_smooth_factor: float = 0.30
    max_stiffness_step_N_per_m: float = 20.0
    K_rot_ratio: float = 0.065
    damping_ratio: float = 1.0
    K_fb: float = 0.5
    deadband_N: float = 0.3
    position_scale: float = 3.0
    emergency_force_N: float = 12.0
    emergency_hold_s: float = 0.10


@dataclass(frozen=True)
class TrustCorrectionState:
    trust: float = 1.0
    risk_ema: float = 0.0


@dataclass(frozen=True)
class TrustCorrectionResult:
    state: TrustCorrectionState
    risk_raw: float
    force_guard_N: float
    target_K: float
    command_K: float
    delta_K: float
    active: bool


def _clip(value: float, lower: float, upper: float) -> float:
    return min(max(float(value), float(lower)), float(upper))


def config_hash(config: TrustCorrectionConfig) -> str:
    """返回可写入每条日志的短 SHA-256 配置指纹。"""

    payload = json.dumps(
        asdict(config), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def correction_window_open(
    contact_elapsed_s: float, config: TrustCorrectionConfig
) -> bool:
    """Only allow posterior updates inside the prespecified contact window."""

    return (
        math.isfinite(contact_elapsed_s)
        and config.contact_delay_s <= contact_elapsed_s <= config.posterior_window_s
    )


def update_trust_correction(
    state: TrustCorrectionState,
    *,
    force_mag_N: float,
    force_threshold_N: float,
    current_K: float,
    prior_K: float,
    config: TrustCorrectionConfig,
) -> TrustCorrectionResult:
    """执行一次 20 Hz 后验修正。

    风险由基线校正后的接触阈值归一化得到；可信度仅可下降，因此在一次
    试次内不会因短时卸载重新相信已经受到挑战的先验。目标刚度是视觉先验
    与安全锚点的凸组合，随后通过平滑和单步限幅生成控制命令。
    """

    if not all(math.isfinite(v) for v in (
        force_mag_N, force_threshold_N, current_K, prior_K,
        state.trust, state.risk_ema,
    )):
        raise ValueError("trust correction inputs must be finite")

    guard = max(float(force_threshold_N), config.force_guard_min_N)
    saturation = max(config.force_saturation_N, guard + 1e-6)
    risk_raw = _clip(
        (float(force_mag_N) - guard) / (saturation - guard), 0.0, 1.0
    )
    risk_ema = _clip(
        config.risk_ema_alpha * risk_raw
        + (1.0 - config.risk_ema_alpha) * state.risk_ema,
        0.0,
        1.0,
    )
    trust = _clip(
        state.trust - config.trust_decay_per_update * risk_ema, 0.0, 1.0
    )

    prior_K = _clip(prior_K, config.K_min, config.K_max)
    anchor_K = _clip(config.safe_anchor_K, config.K_min, config.K_max)
    target_K = _clip(
        trust * prior_K + (1.0 - trust) * anchor_K,
        config.K_min,
        config.K_max,
    )
    requested_step = config.stiffness_smooth_factor * (target_K - current_K)
    limited_step = _clip(
        requested_step,
        -config.max_stiffness_step_N_per_m,
        config.max_stiffness_step_N_per_m,
    )
    command_K = _clip(current_K + limited_step, config.K_min, config.K_max)

    return TrustCorrectionResult(
        state=TrustCorrectionState(trust=trust, risk_ema=risk_ema),
        risk_raw=risk_raw,
        force_guard_N=guard,
        target_K=target_K,
        command_K=command_K,
        delta_K=command_K - prior_K,
        active=(risk_ema > 0.0 and trust < state.trust),
    )
