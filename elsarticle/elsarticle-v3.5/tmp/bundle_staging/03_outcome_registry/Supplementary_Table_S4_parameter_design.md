# Supplementary Table S4. Parameter design space, engineering constraints, and selected levels

| Parameter | Low-to-high operational effect | Engineering constraint | Selected levels |
|---|---|---|---|
| Slave impedance: $K_t$ | Greater translational compliance and lower impact -> greater positional stability. | No sustained oscillation during qualitative screening. | 50 / 150 / 200 N/m |
| Slave impedance: $K_r$ | Greater rotational compliance about the fixed desired orientation -> greater resistance to rotational disturbance. | No sustained oscillation during qualitative screening. | 5 / 10 / 13 N m/rad |
| Slave impedance: $\zeta$ | Increasing $\zeta$ -> increasing normalized controller damping action for fixed $\mathbf{K}$. | Avoid sustained oscillation and excessive sluggishness. | 0.8 / 1.0 / 1.2 |
| Haptic interface: $K_f$ | Weaker -> stronger rendered external-force cue. | Acceptable Omega.7 response. | 0.2 / 0.5 / 0.7 |
| Haptic interface: $d$ | Greater suppression of small signals. | Haptic-interface jitter and noise. | 0.3 / 0.4 / 0.5 N |
| Gripper: $v_g$ | Lower-impact motion -> faster grasp establishment. | Franka Hand execution range. | 0.02 / 0.05 / 0.10 m/s |
| Gripper: $F_g$ | Lower -> higher requested grasp force. | Franka Hand force setting. | 8 / 15 / 20 N |

The three engineering-selected operating points were qualitatively screened before formal data collection, then fixed before the 135 trials. They are not optimized values or material-specific damage limits.
