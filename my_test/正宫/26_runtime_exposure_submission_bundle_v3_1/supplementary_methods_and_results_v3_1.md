# THMS v3.1 Supplementary Methods and Results

This supplement reports details intentionally removed from the five-figure, three-table main manuscript. Machine-readable values in `analysis/` are authoritative.

## S1. Analysis unit and deterministic bootstrap

The human-variability analysis has exactly 20 independent units (F01–F20). Trial metrics were first calculated for each of 294 evaluable trials and then aggregated within participant. No trial was treated as an independent person. For each of six stressors and each of timing MAE and exposure MAE, Spearman correlation was calculated across the 20 participant summaries. A percentile interval used 10,000 participant resamples with replacement and fixed NumPy seed 20260827. The 12 relationships were reported without (p)-values or significance selection. Classification was not analyzed because all 20 participant values equaled 100%.

## S2. Participant-level human-variability ranges

| Stressor | Evidence category | Participant-mean minimum | Q1 | Median | Q3 | Maximum | IQR |
|---|---|---:|---:|---:|---:|---:|---:|
| Approach duration (s) | Coupled task timing | 1.30334 | 1.74723 | 1.86518 | 2.10886 | 2.83597 | 0.36164 |
| Omega path (m) | Human-input-related trajectory | 0.023674 | 0.029196 | 0.031289 | 0.034816 | 0.046430 | 0.005620 |
| Panda path (m) | Coupled human–machine trajectory | 0.009544 | 0.014915 | 0.017706 | 0.021877 | 0.024442 | 0.006962 |
| Panda peak speed (m/s) | Coupled human–machine trajectory | 0.026774 | 0.028528 | 0.030188 | 0.032230 | 0.034210 | 0.003701 |
| Internal-force impulse (N·s) | Coupled interaction estimate | 0.24920 | 0.42995 | 0.56917 | 0.71544 | 1.18810 | 0.28549 |
| Whole-trial clamp rate | Condition–operator background | 0.0667 | 0.0667 | 0.1667 | 0.3141 | 0.7857 | 0.2474 |
| Outcome-window clamp-trial rate | Condition–operator background | 0.0000 | 0.0667 | 0.1333 | 0.2667 | 0.4286 | 0.2000 |

The all-trial approach-duration envelope was 0.61447–5.30009 s; it is a trial-level envelope and not an independent-participant range.

## S3. Participant-level recovery

| ID | Evaluable | Accuracy | Timing MAE (ms) | Timing/limit (%) | Exposure MAE | Exposure/limit (%) | Approach (s) | Omega path (m) | Panda path (m) | Force impulse (N·s) | Clamp rate (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F01 | 15 | 100% | 1.446 | 7.23 | 0.001142 | 5.71 | 1.787 | 0.02367 | 0.01497 | 0.533 | 13.33 |
| F02 | 14 | 100% | 2.304 | 11.52 | 0.001244 | 6.22 | 2.089 | 0.02446 | 0.01948 | 1.188 | 78.57 |
| F03 | 13 | 100% | 2.724 | 13.62 | 0.002349 | 11.75 | 2.103 | 0.02917 | 0.02101 | 0.743 | 46.15 |
| F04 | 15 | 100% | 2.241 | 11.21 | 0.002343 | 11.71 | 1.703 | 0.03062 | 0.01217 | 0.317 | 6.67 |
| F05 | 15 | 100% | 2.271 | 11.36 | 0.001663 | 8.31 | 1.893 | 0.02920 | 0.01494 | 0.427 | 6.67 |
| F06 | 14 | 100% | 1.987 | 9.94 | 0.002192 | 10.96 | 1.762 | 0.03108 | 0.01380 | 0.606 | 42.86 |
| F07 | 15 | 100% | 2.520 | 12.60 | 0.002266 | 11.33 | 1.303 | 0.02608 | 0.00954 | 0.249 | 6.67 |
| F08 | 15 | 100% | 2.502 | 12.51 | 0.002186 | 10.93 | 1.837 | 0.03266 | 0.01753 | 0.634 | 20.00 |
| F09 | 15 | 100% | 2.648 | 13.24 | 0.001839 | 9.20 | 1.802 | 0.03541 | 0.01659 | 0.458 | 13.33 |
| F10 | 15 | 100% | 2.228 | 11.14 | 0.001616 | 8.08 | 1.547 | 0.03110 | 0.01408 | 0.398 | 6.67 |
| F11 | 15 | 100% | 2.396 | 11.98 | 0.001456 | 7.28 | 1.611 | 0.02505 | 0.01485 | 0.431 | 20.00 |
| F12 | 15 | 100% | 3.029 | 15.15 | 0.002349 | 11.74 | 1.976 | 0.03324 | 0.01793 | 0.498 | 13.33 |
| F13 | 15 | 100% | 2.549 | 12.74 | 0.001893 | 9.46 | 1.829 | 0.03080 | 0.01788 | 0.491 | 6.67 |
| F14 | 15 | 100% | 2.057 | 10.29 | 0.001193 | 5.96 | 2.129 | 0.03806 | 0.02226 | 0.690 | 6.67 |
| F15 | 15 | 100% | 3.052 | 15.26 | 0.001611 | 8.05 | 2.126 | 0.04643 | 0.02337 | 0.751 | 33.33 |
| F16 | 15 | 100% | 2.671 | 13.36 | 0.001995 | 9.98 | 2.223 | 0.03369 | 0.02286 | 0.701 | 26.67 |
| F17 | 15 | 100% | 2.271 | 11.35 | 0.001655 | 8.27 | 1.575 | 0.03148 | 0.01577 | 0.332 | 6.67 |
| F18 | 15 | 100% | 2.430 | 12.15 | 0.001594 | 7.97 | 2.492 | 0.03578 | 0.02444 | 0.807 | 20.00 |
| F19 | 15 | 100% | 2.787 | 13.93 | 0.002521 | 12.61 | 2.023 | 0.03462 | 0.02193 | 0.777 | 46.67 |
| F20 | 13 | 100% | 1.386 | 6.93 | 0.000771 | 3.85 | 2.836 | 0.03609 | 0.02186 | 0.706 | 30.77 |

## S4. Continuous participant-level relations

| Stressor | Timing \(\rho\) [bootstrap 95% interval] | Exposure \(\rho\) [bootstrap 95% interval] |
|---|---:|---:|
| Approach duration | 0.215 [−0.293, 0.674] | −0.215 [−0.629, 0.291] |
| Omega path | 0.217 [−0.314, 0.681] | −0.083 [−0.615, 0.494] |
| Panda path | 0.403 [−0.054, 0.773] | −0.194 [−0.599, 0.296] |
| Panda peak speed | 0.208 [−0.343, 0.683] | −0.395 [−0.801, 0.121] |
| Internal-force impulse | 0.244 [−0.201, 0.617] | −0.173 [−0.605, 0.338] |
| Whole-trial clamp rate | 0.279 [−0.189, 0.683] | 0.062 [−0.442, 0.550] |

All intervals include zero. This does not prove absence of association; it documents uncertainty and the absence of a criterion failure within the sampled range.

## S5. Quartile robustness

The earlier quartile analysis was retained as secondary. Across 12 groups defined by approach duration, Panda path, and whole-trial clamp rate, each group contained five participants and mean classification remained 100%. Group timing MAE ranged from 2.2275 to 2.6230 ms and exposure MAE from 0.0014327 to 0.0020251. Exact membership and bounds are in `analysis/supplementary_quartile_robustness.csv`.

## S6. Exploratory human outcomes

Panda `O_F_ext_hat_K` is an internal force estimate, not an independent sensor measurement. Contrasts used participant-level C1–C4 minus C0 paired means. No human contrast defined framework success.

| Contrast | Participants | Excess-force impulse difference (N·s), mean [95% CI] | Negative/positive direction |
|---|---:|---:|---:|
| C1−C0 | 20 | +0.0498 [−0.0577, 0.1572] | 11/9 |
| C2−C0 | 20 | −0.0423 [−0.1551, 0.0705] | 9/11 |
| C3−C0 | 20 | −0.0269 [−0.1763, 0.1225] | 11/9 |
| C4−C0 | 20 | −0.1048 [−0.2092, −0.0004] | 15/5 |

After restricting to complete, unclamped trials, paired participant counts varied from 18 to 20 and all four impulse intervals included zero. This sensitivity result illustrates why command saturation constrains human-outcome interpretation. Full impulse and peak-force contrasts are in `analysis/supplementary_exploratory_contrast_summary.csv`.

## S7. Safety, provenance, and evidence boundaries

Six planned trials were safety aborts: C1, one; C2, two; C4, three. Abort trials stayed in the 300-trial flow but not in the 294-trial record-recovery denominator. The formal queue contains exactly F01–F20 and never scans the earlier same-name archive.

CSV required byte-exact SHA-256 identity. For event and summary JSON, newline differences caused byte inequality while canonical UTF-8 text agreed in 300/300 files for each class. This is reported as two distinct statements. Original files were not rewritten.

The physical-delivery layer is marked `NOT_INDEPENDENTLY_OBSERVED` in every generated status table. `haptic_send_ok` is only an API return. The post-clamp sent-command integral is software-command evidence. Panda force is an internal estimate. These three quantities must not be merged in wording or analysis.

## S8. Reproducible artifacts

Primary machine-readable artifacts are:

- `participant_human_variability.csv`
- `human_variability_range.csv`
- `human_variability_associations.csv`
- `bootstrap_provenance.json`
- `condition_record_fidelity.csv`
- `record_command_summary.csv`
- `quality_and_safety_summary.csv`
- `supplementary_quartile_robustness.csv`
- `supplementary_exploratory_contrast_summary.csv`
- `analysis_provenance.json`

The five figures are emitted as PNG, SVG, and PDF from the same deterministic script. The bundle verifier independently reruns the analysis twice and compares every generated byte.
