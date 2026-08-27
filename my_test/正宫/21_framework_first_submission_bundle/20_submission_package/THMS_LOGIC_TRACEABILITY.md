# THMS logic and evidence traceability

This file is the review map for `18_manuscript_v1/manuscript_thms_v1_zh.md`. It does not redefine frozen data or outcomes.

| Manuscript claim or decision | Framework location | Evidence source | Main-paper location | Visual/table support | Required wording boundary |
|---|---|---|---|---|---|
| A is a fixed logged-command configuration | (C\rightarrow R) command-state check | `trial_level_fidelity_metrics.csv` | 4.1 RQ1 | Fig. 3 context; Supplementary Fig. S1 | Logged command constancy is not independently measured physical impedance |
| G follows the executable raw-force rule | (C\rightarrow R) | source-code guard audit; `trial_level_fidelity_metrics.csv` | 3.2, 3.3, 4.1 | Fig. 3A; Table III | 45/45 executable compliance does not create a post-contact nominal specification |
| G cannot support a post-contact effect claim | nominal specification unavailable plus realized event order | archive/specification audit; activation/contact timestamps | Abstract, 3.2, 4.1–4.2, Discussion | Fig. 3A; Table III | Do not classify G as verified (N\neq C) unless an independent contemporaneous post-contact specification is recovered |
| F nominal +0.20-s timing was not reliably implemented | (N\neq C) with realized timing consequence | literal mixed-clock implementation; `trial_level_fidelity_metrics.csv` | Abstract, 3.2–3.3, 4.1–4.2, Discussion | Fig. 2B, Fig. 3B, Table III | Do not claim (C\neq R) without replay showing that the logged state violated the literal mixed-clock predicate |
| E/F have heterogeneous outcome-window exposure | (R\rightarrow Y) exposure | `outcome_window_exposure.csv` | 2.2–2.3, 4.1–4.2 | Fig. 3C; Table III | Exposure categories describe assigned-mode distributions and are not outcome-selected exclusion rules |
| Intervention and outcome records share exact acquisition identity | orthogonal provenance prerequisite | `data_lineage_audit.csv`, verified hashes, master manifest | 3.2–3.3, 4.1 | Fig. 2C; Supplementary Fig. S3 | Provenance consistency does not prove intervention-delivery fidelity |
| E-A is an admissible descriptive comparison | all layers plus inference unit | participant aggregation and Table III fidelity mapping | 4.2–4.3 | Table III; Fig. 4 | Describe E as a bundled assignment with heterogeneous realized visual exposure; do not isolate vision or stiffness |
| Participant is the human inference unit | (Y_i) definition | `participant_level_metrics.csv`; repeated-measures structure | Abstract, 3.1, 3.4, Results | Fig. 2C, Fig. 3 footnote, Fig. 4 | 180 trials are fidelity observations/repeats, not 180 independent human samples |
| E-A outcome patterns are exploratory | admissible interpretation | retrospective endpoint definition; `statistics_summary.csv` | Abstract, 3.3–3.4, 4.3, Discussion | Fig. 4; Supplementary Table S5; Supplementary Fig. S2 | Report estimates, participant directions, exact tests, and multiplicity; no confirmatory or causal claim |
| Contact-aligned stiffness is contextual | bounded mechanistic context | `contact_aligned_summary.csv` | Discussion 5.3 | Supplementary Fig. S1 | Logged commanded stiffness is not physical closed-loop impedance or a causal mechanism test |

## RQ closure

| Research question | Evidence output | Manuscript endpoint |
|---|---|---|
| RQ1: implementation and realization patterns | trial-level guards, timing, exposure, and provenance | Section 4.1 and Fig. 3 |
| RQ2: consequences for scientific interpretation | nominal claim → fidelity evidence → permitted/prohibited wording | Section 4.2 and Table III |
| RQ3: bounded outcome pattern after reconstruction | five participant-level E-A paired differences and sensitivity analyses | Section 4.3, Fig. 4, and Supplementary Table S5 |
