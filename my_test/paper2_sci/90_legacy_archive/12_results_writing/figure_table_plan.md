# Final Figure and Table Structure

All numerical content must be generated from `03_clean_analysis/`. Figures use trial-level observations only for implementation-timing audits; human-outcome inference is displayed at participant level (`n=5`).

## Figure 1. System and realized-logged-intervention reconstruction framework

- **Type:** system diagram plus data-lineage flow.
- **Content:** operator, teleoperation interface, vision path, controller, robot/contact, event logger, time-series logger, manifest, clean reconstruction, participant aggregation.
- **Key distinction:** nominal mode -> commanded intervention -> logged event -> realized logged parameter trajectory -> outcome.
- **Source:** `master_trial_manifest.csv`, `data_lineage_audit.csv`, `README.md`.
- **Purpose:** establish the audit object; not presented as a novel controller architecture.

## Figure 2. Nominal versus realized logged intervention timing

- **Panel A:** G activation relative to task start. x-axis: seconds; y-axis: trial grouped by participant. Mark zero, median -0.379 s, and 42/45 pre-task.
- **Panel B:** G activation relative to contact. Mark zero, median -1.214 s, and 43/45 pre-contact.
- **Panel C:** F activation relative to contact. Mark zero and intended +0.20 s; report realized median +0.053 s and 42/45 before +0.20 s.
- **Panel D:** E/F vision lock relative to contact. Show participant-colored trial points; report 5/45 E and 3/45 F post-contact.
- **Source:** `timing_audit.csv`.
- **Purpose:** demonstrate implementation divergence without treating trials as independent participants.

## Figure 3. Participant-level E-A safety-related and timing contrasts

- **Panel A:** threshold-referenced excess-force impulse, 0.2–1.0 s after contact (N·s).
- **Panel B:** task-start-to-contact time (s), interpreted as the logged pre-contact interval.
- **Panel C:** total task time (s).
- **Display:** paired A/E points for five participants plus a separate mean-difference/95% CI axis.
- **Source:** `participant_level_metrics.csv`, `statistics_summary.csv`.
- **Purpose:** show the joint lower-force/longer-pre-contact-interval pattern without attributing the timing difference to operator speed.
- **Prohibited:** trial-level bars or standard errors based on 45 trials/mode.

## Figure 4. Contact-aligned force and logged commanded-stiffness trajectories

- **Panel A:** x-axis time from logged contact (-0.5 to +1.5 s); y-axis estimated external-force magnitude or threshold-referenced excess force above the trial-specific contact threshold (N). The caption must state which of these two logged quantities is plotted.
- **Panel B:** same x-axis; y-axis logged translational stiffness (N/m).
- **Groups:** A/G/E/F.
- **Aggregation:** average trials within participant first; then show mean and t-based 95% CI across five participant curves.
- **Source:** `contact_aligned_trajectories.csv`, `contact_aligned_summary.csv`.
- **Purpose:** descriptively locate force and stiffness differences; no trial-level functional significance bands.

## Figure 5. Participant consistency and LOPO stability

- **Panel A:** individual E-A threshold-referenced impulse differences for P01-P05 with zero reference.
- **Panel B:** full E-A estimate and five LOPO estimates with 95% CIs.
- **Panel C:** F-E full and LOPO estimates, emphasizing the sign change when P03 is excluded.
- **Source:** `statistics_summary.csv`, `participant_level_metrics.csv`, `leave_one_participant_out.csv`.
- **Purpose:** distinguish stable direction from strong confirmatory inference.
- **Not included:** window/threshold sensitivity because no frozen clean sensitivity table currently exists.

## Figure 6. Data-lineage and implementation-deviation examples

- **Panel A:** six known-error records mapped to their six valid replacements while both identities remain in the manifest.
- **Panel B:** deterministic G example nearest the median pre-contact activation time.
- **Panel C:** deterministic F example nearest the median activation delay.
- **Panel D:** deterministic post-contact vision-lock example, accompanied by total incidence.
- **Selection rule:** choose the eligible trial nearest the class median, not the most dramatic trial.
- **Source:** `master_trial_manifest.csv`, `data_lineage_audit.csv`, `timing_audit.csv`, `contact_aligned_trajectories.csv`.
- **Purpose:** connect population timing counts to trace-level execution and record identity.
- **Redundancy rule:** if Figure 6 repeats Figure 2 without showing trace-level information, merge it into Figure 2 and move the lineage map to supplementary material.

## Table I. Nominal definitions and realized logged intervention characteristics

- Rows: A, G, E, F.
- Columns: nominal label, intended visual role, intended force-adaptation role, intended trigger, observed activation/vision timing, contact-aligned stiffness, permissible interpretation.
- Include logged commanded-stiffness descriptors at contact: A median/range 200/200-200 N/m; G 198.3/178.9-200; E 120/50-200; F 120/50-200. At +0.2 s, F median/range 116.1/41.1-189.2 N/m.
- State explicitly that A/G/E/F do not form a strict realized logged 2x2 design.
- Source: `timing_audit.csv`, `contact_aligned_trajectories.csv`, `README.md`.

## Table II. Dataset composition and data provenance

- 5 participants; 4 modes; 45 trials/mode; 9 trials/participant/mode; 180 main trials.
- 60 recorded trials per material category.
- 174 main unique records; 6 valid replacements; 6 known-error records retained outside analysis; 186/186 triplets verified.
- 180/180 clean trials met the software-log success definition, with its measurement limitation noted.
- Source: `master_trial_manifest.csv`, `data_lineage_audit.csv`, `trial_level_metrics.csv`.

## Table III. Participant-level clean-reanalysis contrasts

- Metrics: threshold-referenced excess-force impulse, initial peak force, task-start-to-contact time, and total task time.
- Contrasts: E-A, G-A, F-E, F-G.
- Columns: n participants, raw mean difference, 95% CI, paired t statistic/p, exact sign-flip p, Wilcoxon p, and Holm-adjusted p for each family.
- Source: `statistics_summary.csv`.

## Table IV. Realized timing audit

- G activation relative to task/contact and baseline readiness.
- F activation relative to contact and intended +0.20-s gate.
- E/F vision lock relative to task/contact.
- Mode-wise control-loop median, p95, p99, maximum, and long-cycle fractions.
- Source: `timing_audit.csv`.
