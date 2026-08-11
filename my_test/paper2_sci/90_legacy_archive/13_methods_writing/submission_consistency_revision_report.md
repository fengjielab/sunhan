# Submission consistency revision report

## Scope

This revision was applied to the active Methods and Results working set in `13_methods_writing/` and `12_results_writing/`. No numerical value, statistical result, raw-data field, analysis formula, collection code, or Discussion text was changed.

## B. Before-to-after comparison

| Consistency item | Before | After | Reason |
|---|---|---|---|
| Main force metric | “baseline-corrected excess-force impulse” or “early excess-force impulse” | “threshold-referenced excess-force impulse” or, at first use, “excess-force impulse above the trial-specific contact threshold” | The implemented quantity is \(\max[F(t)-T_i,0]\), where \(T_i=\max(1\,\mathrm{N},\mu_0+3\sigma_0)\); no additional sample-wise subtraction of \(\mu_0\) occurs. |
| Internal force-metric field | `baseline_corrected_excess_force_impulse_Ns_0p2_1p0` / `primary_excess_impulse_Ns_0p2_1p0` | Field names retained as immutable lineage identifiers; manuscript wording changed | Renaming clean-data columns would break provenance without changing the calculation. |
| Timing metric | “approach time” | “task-start-to-contact time,” additionally described as the logged “pre-contact interval” | `task_start` marks system readiness, not first human movement. |
| Internal timing field | `approach_time_s` | Field name retained as a legacy internal identifier; source map now states its exact definition | Preserves reproducible joins and statistics while preventing interpretive overreach. |
| Timing interpretation | Could be read as robot approach duration or operator movement speed | Explicitly not interpreted as direct robot approach duration or operator movement speed | The start event does not measure movement onset. |
| Sensitivity-analysis wording | “prespecified sensitivity analyses” | “complementary small-sample sensitivity analyses” | No evidence of prospective preregistration exists. |
| Contrast wording | “predefined contrasts” | “four clean-reanalysis contrasts” / “contrasts evaluated in the clean retrospective reanalysis” | Prevents retrospective choices from being presented as prospectively specified. |
| Success wording | “predefined software-log success criterion” | “archived software-log success definition” | The variable is log-derived and should not imply preregistration or independent adjudication. |
| Intervention wording | “realized configuration/intervention” where potentially ambiguous | “realized logged configuration/intervention” | Separates logged commands/events from independently measured physical impedance. |
| Logged stiffness | Could be read as physical impedance measurement | “logged translational stiffness,” “commanded-stiffness profile,” plus the existing non-equivalence statement | Logged controller parameters are not an independent measurement of physical closed-loop impedance. |
| G implementation | Raw-force detail present | Retained: raw filtered force, fixed 1-N adaptation deadband, no baseline-ready or contact gate | Required implementation-fidelity fact. |
| F implementation | Clock mismatch present | Retained: nominal 0.20-s gate and `time.time()`/`time.perf_counter()` mismatch | Required implementation-fidelity fact. |

## C. Information still requiring confirmation

The complete categorized checklist is maintained in `methods_missing_information.md`.

- Must be resolved before submission: ethics approval/exemption, informed consent, a minimum reproducible human-task description, and all mandatory declarations/checklist fields required by the selected journal.
- If irrecoverable, disclose as limitations: participant demographics and recruitment, training/familiarization, unique object registry and placement, prospective order-allocation procedure, hardware/software versions, camera mounting/calibration, confirmation of any physically mounted but unlogged sensor, detailed technical reasons for the six superseded records, and finer task geometry/rest/practice details.

## D. Residual Methods–Results conflicts

No substantive Methods–Results conflict remains in the active drafts for the following terms and definitions:

- contrasts: E-A, G-A, F-E, and F-G;
- main force metric: threshold-referenced excess-force impulse from 0.20 to 1.00 s after logged contact;
- contact: first trial-specific threshold crossing sustained for 0.050 s, with onset assigned to the first crossing;
- timing metric: task-start-to-contact time, interpreted as a logged pre-contact interval;
- initial peak force: maximum uncorrected estimated-force magnitude from 0 to 0.20 s after contact;
- software-log success: combined completion, grasp-success, and task-end flags;
- intervention language: nominal configuration, commanded configuration, and realized logged intervention/configuration;
- G and F implementation deviations.

Two intentional naming differences remain only inside the clean-analysis data schema: `baseline_corrected_excess_force_impulse_Ns_0p2_1p0` and `approach_time_s`. They are legacy internal column names, not current manuscript definitions, and are explicitly mapped in the source audit. Historical exploratory/confirmatory folders outside the active `12_results_writing/` and `13_methods_writing/` set may retain earlier terminology and must not be copied into the submission manuscript without applying the same consistency rules.
