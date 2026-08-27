# Formal 20-participant criterion-validation results

## Primary result

The fixed cohort contains 20 independent participants and 300 planned trials. 294 trials completed and 6 ended by the prespecified 5 N safety abort. Primary fidelity reconstruction therefore used 294/300 trials.

Condition classification was correct in 294/294 evaluable trials (100.0%). Absolute onset error had MAE 2.381 ms, P95 4.957 ms, and maximum 5.408 ms. Exposure error had MAE 0.001798, P95 0.005996, and maximum 0.006760.

All prespecified criterion-recovery checks passed: true.

## Quality constraints

Haptic command clamping occurred in 65/294 completed trials. This does not alter reconstruction of scheduled onset or outcome-window exposure, but it limits interpretation of delivered physical dose and exploratory human outcomes. Force was the Franka-estimated external wrench, not an independent force/torque sensor endpoint.

## Exploratory participant-level excess-force contrasts

These estimates are descriptive and carry no confirmatory p-values.

| Contrast | n | Mean difference (N·s) | 95% CI | Negative/positive |
|---|---:|---:|---:|---:|
| C1_minus_C0 | 20 | 0.0498 | [-0.0577, 0.1572] | 11/9 |
| C2_minus_C0 | 20 | -0.0423 | [-0.1551, 0.0705] | 9/11 |
| C3_minus_C0 | 20 | -0.0269 | [-0.1763, 0.1225] | 11/9 |
| C4_minus_C0 | 20 | -0.1048 | [-0.2092, -0.0004] | 15/5 |
