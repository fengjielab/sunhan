# Methods structure, placement, and reviewer-risk audit

## C. Recommended final Methods structure

1. **2.1 Experimental System**  
   Hardware, teleoperation mapping, internal force estimate, haptic rendering, vision process, nominal versus logged timing.

2. **2.2 Human-in-the-Loop Task and Dataset**  
   Participants, task-state sequence, repeated-measures structure, material/block labels, unavailable demographics/object details, independent unit.

3. **2.3 Nominal Control Configurations**  
   A/G/E/F acquisition-time definitions and parameter bundles; Table I; explicit non-factorial statement.

4. **2.4 Realized-Intervention Logging and Reconstruction**  
   Nominal/commanded/realized definitions, exact record identity, event and activation reconstruction, monotonic time axis, F clock-domain defect, G raw-force activation.

5. **2.5 Contact and Outcome Definitions**  
   Per-trial baseline and threshold, sustained contact rule, impulse/peak/time/success definitions, activation timing, descriptive trajectory construction.

6. **2.6 Data Provenance and Clean Analysis Cohort**  
   186 records, six excluded errors, six valid replacements, final 180 keys, immutable lineage, SHA-256 verification.

7. **2.7 Statistical Analysis**  
   Participant aggregation, four paired contrasts, t/CI, exact tests, Holm, LOPO, descriptive trajectories.

This ordering preserves the required logic: system -> task -> nominal modes -> realized intervention -> outcomes -> provenance -> inference.

## F. Content suitable for the main manuscript

- Core platform: Omega.7, Franka Panda/Hand, RealSense color stream, Cartesian impedance architecture.
- Explicit internal-force-estimate wording and absence of an independent external-force measurement in the archived path.
- Five-participant repeated-measures structure and participant as the inferential unit.
- Concise A/G/E/F Table I with bundled parameters and permissible interpretation.
- Definitions of nominal, commanded, and logged realized intervention.
- Monotonic event time axis and short disclosure of the G/F implementation deviations.
- Contact threshold, contact-hold rule, main retrospective threshold-referenced impulse, initial peak, timing outcomes, and software-log success.
- 186 -> 180 lineage and replacement decision.
- Participant-level statistical procedure and exact-test/Holm/LOPO sensitivity framework.

## G. Content suitable for Supplementary Methods

- Full soft/medium/hard visual preset table.
- Full F posterior-policy parameters, including class-specific force deadbands, saturation values, gains, stiffness bounds, and smoothing coefficients.
- Exact G update equation and parameter values.
- Complete event-state machine and gripper transition logic.
- Complete CSV/event/summary schemas.
- Force-estimator implementation, built-in wrench field, and alpha=0.3 exponential filter.
- SHA-256 implementation and six-record replacement mapping.
- All timestamp formulas and event/CSV consistency checks.
- Timestamp-derived mode-order sequences; clearly labeled as realized order, not a documented randomization plan.
- Mode-wise realized control-cycle distributions.
- Contact-aligned interpolation grid and trajectory aggregation details.

## H. Five likely Reviewer 2 attacks

1. **“Participant demographics and ethics are missing.”**  
   Current defense: none from the archive. This must remain `[NEEDS VERIFICATION]`; it is the most serious reporting gap.

2. **“The force outcome is not a calibrated external-sensor measurement.”**  
   Defense from existing materials: describe the Franka internal wrench estimate, built-in field, local alpha=0.3 filter, per-trial baseline/threshold, and limitation. Do not claim metrological force accuracy.

3. **“Task-start-to-contact time begins at system readiness rather than first voluntary movement.”**  
   Defense: define it exactly as `contact_onset-task_start`, describe it as the logged pre-contact interval, and do not interpret it as directly measured robot approach duration or operator movement speed.

4. **“The modes are confounded and implementation fidelity is poor.”**  
   Defense: Table I exposes parameter bundling; Section 2.4 makes the audit a core method; G/F are analyzed as realized logged configurations, not clean factors.

5. **“Order, object identity, and physical task standardization are insufficiently recorded.”**  
   Defense from existing data: report the matched participant-material-block structure and actual timestamp order, while treating object identity, placement, and intended randomization as limitations rather than inventing them.

## I. Sentences at risk of converting nominal design into realized fact

| Risky sentence | Why unsafe | Required correction |
|---|---|---|
| “F refinement started 0.20 s after contact.” | This was design intent, not logged execution. | “F was configured with an intended 0.20-s delay; realized activation was reconstructed from `fusion_active` and did not consistently follow that gate.” |
| “G provided post-contact force feedback.” | G usually activated before task/contact. | “G was the nominal force-only configuration, whose logged stiffness adaptation was driven by raw estimated force without a contact gate.” |
| “E applied vision-based parameters before contact.” | Vision lock followed contact in some trials. | “E applied the first locked vision-based preset when detection became available; timing relative to contact was reconstructed per trial.” |
| “A was software-locked at fixed parameters.” | The data mode was `default`, which was not included in the code’s keyboard-lock list. | “A was nominally fixed, and its logged parameter trajectories remained at the fixed preset.” |
| “The experiment used a 2 x 2 visual-by-force design.” | Parameters and timing were bundled. | “The study recorded four configurations that were analyzed as bundled realized logged interventions.” |
| “Contact force was measured by an F/T sensor.” | No external sensor acquisition path existed. | “Force magnitude was derived from the Franka internal estimated external wrench.” |
| “The controller operated at 200 Hz.” | 200 Hz was nominal; logged cycle timing had variability. | “The supervisory loop targeted 200 Hz, and realized cycle duration was recorded per sample.” |
| “Task time began when the participant moved.” | The executed code marked task start at system readiness. | “Task start was automatically marked after force-baseline and controller readiness.” |
| “The primary outcome was prespecified.” | No preregistration evidence exists. | “The 0.2-1.0-s threshold-referenced excess-force impulse was the main outcome of the clean retrospective reanalysis.” |
| “Success represented independently verified physical completion.” | Success was derived from software events. | “Success was defined by the software-log completion, grasp-success, and task-end flags.” |
| “Soft, medium, and hard represented three known physical objects.” | Object identity was not archived. | “Soft, medium, and hard were archived material-category labels; physical-object identity was unavailable.” |
| “Trial order was randomized.” | No randomization record was found. | “Mode order varied in the timestamped record; the intended randomization procedure was not archived.” |
