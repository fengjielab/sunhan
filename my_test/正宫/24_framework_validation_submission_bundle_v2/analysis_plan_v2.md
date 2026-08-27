# Locked v2 reporting specification (post-acquisition)

This document records the final reproducible analysis and reporting rules for the current v2 reanalysis. It was assembled after acquisition and is **not** a prospective registration; it must not be described as one. Known-truth condition definitions, the acquisition schedule, and the numerical engineering acceptance limits pre-existed this document.

## Cohort

- Authoritative data root: `data/kfb_timing_formal_v1/participants`.
- Included participants: F01–F20, treated as 20 independent human experimental units.
- Expected design: 20 participants × 3 blocks × 5 trials = 300 planned trials.
- Historical `analysis/kfb_timing_formal_v1/first_five` data are unrelated, excluded, and never scanned.
- Six safety-aborted trials remain in disposition and safety summaries; only 294 complete trials enter primary fidelity reconstruction.

## Primary criterion-validation endpoints

- Classification accuracy among fidelity-evaluable complete trials.
- Absolute onset error: MAE, P95, and maximum.
- Absolute outcome-window exposure error: MAE, P95, and maximum.
- Frozen limits: classification ≥95%; timing MAE ≤20 ms; timing P95 ≤20 ms; timing maximum ≤50 ms; exposure MAE ≤0.02.
- Primary success is independent of exploratory human-outcome direction.

## Quality and exploratory endpoints

- Report control-loop P99/maximum, Omega validity, haptic-send failure, 5 N safety abort, and 2 N haptic-command clamping separately.
- Human force source is the Franka-estimated external wrench, not an independent F/T endpoint.
- For exploratory outcomes, aggregate trials within participant-condition first, then compute C1–C4 minus C0 paired differences across participants with 95% t intervals and no confirmatory p-values.
- Repeat exploratory summaries after excluding any trial with haptic clamping; do not select the analysis set by favorability.

## Provenance rules

- CSV files require exact byte hashes.
- Events and summary JSON report both byte hashes and LF-normalized UTF-8 text hashes; raw files are never rewritten.
- The formal analyzer reads the frozen JSON/oracle and does not import online controller condition constants.
- Any missing, duplicate, extra, mislocated, mask-mismatched, or configuration-mismatched trial is a fatal error.
