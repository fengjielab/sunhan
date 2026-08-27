# Frozen analysis plan: THMS runtime-exposure v3.1

## Scope

- Formal source: `data/kfb_timing_formal_v1/participants` only.
- Permitted participants: exactly F01–F20, treated as 20 independent people.
- Planned queue: 20 × 15 = 300 logical trials.
- Primary evaluable set: 294 complete trials; six safety aborts remain in flow/safety summaries.
- Historical `first_five` data and earlier same-name F01–F05 files are outside the source root and are never scanned.
- Physical delivery is not independently observed.

## Primary schedule-to-record endpoints

Condition accuracy with exact Clopper–Pearson 95% CI; absolute activation-time error MAE/P95/maximum; and absolute outcome-window exposure error MAE/P95/maximum. Limits are accuracy ≥0.95, timing MAE/P95 ≤0.020 s, timing maximum ≤0.050 s, and exposure MAE ≤0.02.

## Participant-level stress test

Trial values are aggregated before relation analysis, giving exactly 20 units. Six stressors are approach duration, Omega approach path, Panda approach path, Panda peak approach speed, Panda internal-force impulse, and whole-trial clamp rate. Outcome-window clamp rate is summarized separately. Omega path is human-input-related; Panda and force quantities are coupled metrics; clamping is a condition–operator background.

For each stressor, Spearman correlation is reported against participant timing MAE and exposure MAE with a fixed-seed (20260827), 10,000-resample participant bootstrap percentile interval. No (p)-values or significance filtering are used. Accuracy is excluded because it is constant. Quartile summaries are secondary. Human-force outcomes remain exploratory.

## Main-manuscript allocation

The main manuscript is fixed at five figures and three tables: framework; retrospective discontinuities; primary recovery; window binding; human variability; plus retrospective diagnosis, reference conditions, and primary validation tables. Detailed participant, association, outcome, sensitivity, and provenance results remain supplementary.

## Reproducibility and guards

The analyzer reads frozen protocol and oracle files independently of online-controller constants. Missing, duplicated, mismatched, or illegal records fail immediately. CSV byte identity and JSON byte/canonical-text identity are reported separately. Figures are emitted in PNG/SVG/PDF. Two independent reruns must be byte-identical. Earlier bundles and raw sources are read-only comparison targets. Ethics details are a submission blocker until replaced by authentic records.
