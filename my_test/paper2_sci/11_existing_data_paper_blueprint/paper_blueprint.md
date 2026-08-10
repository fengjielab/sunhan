# Existing-data SCI paper blueprint

## Scope lock

- Use only `03_clean_analysis/` as the formal numerical source.
- No new participants, trials, collection, controller modification, or confirmatory experiment.
- Treat the study as an exploratory, log-audited analysis of realized interventions.
- Do not treat A/G/E/F as a strict 2x2 factorial experiment.
- Do not attribute E-A to vision alone, stiffness alone, or a visual-force interaction.

## A. One-sentence story

Reconstructing the interventions actually realized in a human-in-the-loop contact-teleoperation experiment showed that nominal controller labels concealed important timing deviations, while the vision-enabled bundled configuration was associated with lower early contact-force exposure but longer approach and task times in five participants, a pattern consistent with an exploratory safety-efficiency trade-off rather than a confirmed causal controller effect.

## B. Contributions

1. We developed and applied an auditable realized-intervention reconstruction workflow linking immutable trial identities, code logic, event timestamps, activation flags, and stiffness trajectories to test nominal-to-realized fidelity in contact teleoperation.
2. In the cleaned dataset of five participants and 180 repeated trials, the vision-enabled bundled configuration showed a participant-consistent reduction in early excess-force impulse relative to the fixed configuration, accompanied by longer approach and total task times; this pattern is presented as an exploratory safety-efficiency association.
3. Participant-level inference, exact small-sample sensitivity tests, data-lineage repair, and timing audit showed why trial labels and nominal controller definitions alone can overstate the strength or misstate the mechanism of teleoperation results.

## C. Candidate titles

1. **From Nominal Modes to Realized Interventions: A Log-Audited Evaluation of Impedance Strategies in Human-in-the-Loop Contact Teleoperation** — balanced/default.
2. **Auditing Realized Controller Interventions in Human-in-the-Loop Contact Teleoperation** — methodology.
3. **When Controller Labels Do Not Match Execution: A Realized-Intervention Audit of Contact Teleoperation** — methodology, direct.
4. **Code, Logs, and Contact Forces: Reconstructing Realized Interventions in Teleoperation Experiments** — robotics experimentation.
5. **Beyond Nominal Control Modes: Timing Fidelity and Safety-Efficiency Patterns in Contact Teleoperation** — robotics experimentation.
6. **Safety-Efficiency Patterns Under Realized Impedance Configurations in Contact Teleoperation** — teleoperation/results.
7. **Lower Contact-Force Exposure with Longer Task Time: An Exploratory Log-Audited Teleoperation Study** — results-forward.
8. **Human Adaptation and Realized Impedance Interventions in Contact-Rich Teleoperation** — human-in-the-loop/HRI.
9. **Auditing What the Operator Actually Experienced in Contact Teleoperation** — human factors/accessibility.
10. **Nominal-to-Realized Fidelity in Robot Experiments: Evidence from Impedance-Based Contact Teleoperation** — broad methodology.

Recommended working title: Title 1. It contains the methodological contribution, application domain, and study scope without claiming a novel controller or confirmed superiority.

## D. Figure plan

### Fig. 1. System and realized-intervention audit framework

- **Form:** system/audit flow diagram, not a performance plot.
- **Elements:** operator -> teleoperation input -> vision process -> impedance controller -> robot/contact; parallel logging path; nominal mode -> commanded parameter/event -> logged realized intervention -> clean metric -> participant-level inference.
- **Data/source:** `README.md`, `master_trial_manifest.csv`, `timing_audit.csv`, `contact_aligned_trajectories.csv`.
- **Claim:** the paper evaluates nominal-to-realized fidelity and then interprets outcomes using realized interventions.
- **Guardrail:** label the workflow as an audit/reconstruction framework, not a newly validated controller architecture.

### Fig. 2. Nominal versus realized event timing

- **Panel A, G activation:** x-axis `force_activation - task_start` (s); y-axis trial grouped by participant; vertical zero line. Annotate 42/45 before task and median -0.379 s.
- **Panel B, G contact alignment:** x-axis `force_activation - contact` (s); annotate 43/45 before contact and median -1.214 s.
- **Panel C, F activation:** x-axis `force_activation - contact` (s); vertical lines at 0 and intended 0.20 s; annotate median 0.053 s and 42/45 before 0.20 s.
- **Panel D, vision timing:** participant-colored points for E/F `vision_lock - contact`; annotate E 5/45 and F 3/45 post-contact.
- **Source:** `timing_audit.csv`.
- **Claim:** logged timing does not support interpreting G as purely post-contact or F as a faithfully gated 0.20-s refinement.

### Fig. 3. Participant-level E-A safety-efficiency pattern

- **Panels:** early excess-force impulse, approach time, total task time.
- **Left of each panel:** paired A/E participant dots connected within participant.
- **Right of each panel:** E-A mean difference with t-based 95% CI and a zero line.
- **Y axes:** N*s, s, and s respectively; never combine normalized values on one axis.
- **Source:** `participant_level_metrics.csv`, `statistics_summary.csv`.
- **Annotations:** n=5; paired t, exact sign-flip, and Holm-adjusted results shown compactly or deferred to Table III.
- **Claim:** E-A force and time estimates move in opposite desirability directions, consistent with a safety-efficiency trade-off.

### Fig. 4. Participant-aggregated contact-aligned realized trajectories

- **Panel A:** x-axis -0.5 to 1.5 s from contact; y-axis baseline-corrected excess force (N).
- **Panel B:** same x-axis; y-axis realized translational stiffness (N/m).
- **Grouping:** A/G/E/F curves; first average trials within participant, then mean and 95% t-CI across five participant curves.
- **Source:** `contact_aligned_trajectories.csv`, `contact_aligned_summary.csv`.
- **Claim:** descriptively locate when force and stiffness trajectories diverge.
- **Guardrail:** no trial-level functional significance bands and no claim that curve separation identifies a causal mechanism.

### Fig. 5. Participant consistency and analysis stability

- **Panel A:** five participant E-A impulse differences with zero line.
- **Panel B:** full estimate and five LOPO estimates with 95% CIs.
- **Panel C only if a new clean-derived sensitivity table is frozen before manuscript plotting:** prespecified window or threshold sensitivity. No such table currently exists in `03_clean_analysis`, so this panel is not yet evidence-backed and must otherwise be omitted.
- **Source:** `participant_level_metrics.csv`, `leave_one_participant_out.csv`.
- **Claim:** E-A direction persists under removal of any one participant, although interval precision remains weak.
- **Guardrail:** do not state that every LOPO analysis is statistically significant.

### Fig. 6. Deterministically selected implementation-deviation traces

- **Panels:** one G pre-activation trace, one early F activation trace, one post-contact vision-lock trace, and the six-record lineage replacement map.
- **Selection rule:** choose the eligible trace nearest the median timing within each prespecified deviation class, not the most dramatic trace; state total class incidence beside the example.
- **Axes:** time relative to task/contact on x-axis; force, activation flag, or stiffness on separate aligned y-axes.
- **Source:** `timing_audit.csv`, `contact_aligned_trajectories.csv`, `master_trial_manifest.csv`, `data_lineage_audit.csv`.
- **Claim:** show how audit findings appear within trials and how record identity affects analytical inclusion.
- **Guardrail:** `03_clean_analysis` contains no prediction-label field supporting an “unknown prediction” rate; do not include such a panel without a clean-derived source.

### Redundancy decision

- Fig. 2 reports population-level timing distributions and incidence.
- Fig. 6 reports trace-level manifestation plus record-lineage reconstruction.
- If the journal limits figures, merge Fig. 6 trace insets into Fig. 2 and move the lineage map to the supplement; do not retain two figures that merely repeat the same counts.

## E. Table plan

### Table I. Nominal definitions versus realized intervention characteristics

- Rows: A, G, E, F.
- Columns: nominal description; vision use; force-adaptation rule; intended trigger; observed activation/lock timing; stiffness at contact and +0.2 s; interpretive status.
- State explicitly that the modes are bundled configurations and not a strict realized 2x2 design.
- Source: `timing_audit.csv`, `contact_aligned_trajectories.csv`, `README.md`.

### Table II. Dataset and lineage

- 5 participants; 4 modes; 45 trials/mode; 9 trials/participant/mode; 180 main trials.
- 174 main unique records + 6 valid replacements; 6 known-error records retained outside the analysis; 186/186 file triplets verified.
- 60 trials per recorded material category.
- 180/180 clean trials satisfy the software-log success definition, with the measurement limitation stated.
- Source: `master_trial_manifest.csv`, `data_lineage_audit.csv`, `trial_level_metrics.csv`.

### Table III. Participant-level outcomes and predefined contrasts

- Rows grouped by metric: primary impulse, initial peak, approach time, total task time.
- Contrasts: E-A, G-A, F-E, F-G.
- Columns: n participants, raw mean difference, 95% CI, paired t p, exact sign-flip p, Wilcoxon p, and three Holm-adjusted p values.
- Keep E-A primary in the main visual hierarchy; treat F-G as descriptive because it is not a clean interaction contrast.
- Source: `statistics_summary.csv`.

### Table IV. Realized timing audit

- G: 42/45 before task, 43/45 before contact, median offsets -0.379 and -1.214 s.
- F: median +0.053 s from contact; 42/45 earlier than 0.20 s.
- E/F vision: median lock relative to contact -0.755/-0.941 s; post-contact lock 5/45 and 3/45.
- Control loop: mode-wise median, p95, p99, maximum; report as execution context rather than performance evidence.
- Source: `timing_audit.csv`.

## F. Results structure and required numbers

### 4.1 Dataset integrity and realized-intervention reconstruction

- Begin with 186 audited records and verified triplets.
- Explain the six known-error 20260729 records and their six valid 20260730 replacements without deleting either lineage.
- Final main set: 180 unique trial keys, 5 participants, 45 trials per mode, 9 trials per participant per mode.
- Figures/Tables: Fig. 1, Fig. 6, Table II.

### 4.2 Nominal modes differed from realized interventions

- G: 42/45 pre-task, 43/45 pre-contact; medians -0.379 and -1.214 s.
- G activation context: 45/45 raw estimated force >1 N and 42/45 before baseline ready.
- F: intended 0.20 s; realized median 0.053 s; 42/45 before 0.20 s.
- E: vision lock median 0.755 s before contact, but 5/45 after contact.
- F: vision lock median 0.941 s before contact, but 3/45 after contact.
- Figures/Tables: Fig. 2, Fig. 6, Table I, Table IV.

### 4.3 The vision-enabled configuration showed lower early force exposure

- Primary E-A impulse: -0.3489 N*s, 95% CI [-0.6080, -0.0898].
- Paired t p=0.0201; exact sign-flip p=0.0625; Wilcoxon p=0.0625.
- Holm-adjusted p: t=0.0633; sign-flip=0.2500; Wilcoxon=0.2500.
- All 5/5 participant means were directionally lower under E.
- Secondary initial peak: -0.4140 N, 95% CI [-0.7483, -0.0798]; paired t p=0.0263; exact p=0.0625; Holm t p=0.0789.
- Required interpretation: consistent exploratory association, not a confirmed visual or stiffness causal effect.
- Figures/Tables: Fig. 3, Fig. 4, Table III.

### 4.4 Lower force exposure was accompanied by temporal cost

- Approach E-A: +1.7805 s, 95% CI [1.5084, 2.0527]; paired t p=5.40e-05; exact p=0.0625; Holm t p=0.000162 and exact p=0.2500.
- Total task E-A: +1.2128 s, 95% CI [0.5741, 1.8514]; paired t p=0.00620; exact p=0.0625; Holm t p=0.0186 and exact p=0.2500.
- Both directions were consistent in 5/5 participant means.
- Use “consistent with a safety-efficiency trade-off,” not a mediation or causal mechanism claim.
- Figures/Tables: Fig. 3, Table III.

### 4.5 Force-only and additional force refinement showed limited interpretable evidence

- G-A impulse: -0.0742 N*s, 95% CI [-0.1978, 0.0494], paired t p=0.1708; G is not interpretable as pure post-contact feedback.
- F-E impulse: -0.0212 N*s, 95% CI [-0.1433, 0.1010], paired t p=0.6556, exact p=0.6875, Wilcoxon p=0.8125.
- F-E LOPO changed sign when P03 was omitted.
- F-G remains tabled as descriptive: -0.2958 N*s, 95% CI [-0.5000, -0.0917], paired t p=0.0158 but exact p=0.0625 and Holm t p=0.0633.
- Conclusion: no discernible incremental F-over-E benefit under the realized implementation; not “force refinement is ineffective.”
- Figures/Tables: Table III; Fig. 5 or supplement.

### 4.6 Robustness and participant-level consistency

- E-A impulse LOPO estimates: -0.4028 to -0.2860 N*s; all retain the same direction.
- One LOPO interval crosses zero; the diagnostic supports directional stability, not universal significance.
- Approach LOPO estimates: +1.7340 to +1.8497 s; total-task LOPO: +0.9871 to +1.3056 s.
- Exact two-sided sign-flip p cannot be below 0.0625 at n=5.
- No clean window/threshold sensitivity table currently exists; do not report such a result until it is generated reproducibly from clean sources.
- Figures/Tables: Fig. 5, Table III or supplement.

## G. Discussion logic

### 5.1 Nominal-to-realized fidelity is an experimental variable

Connect the G/F timing deviations and E/F late-lock trials to the general requirement that controller intent, command, execution, and logged exposure must be distinguished. Do not frame this as a software-error anecdote; frame it as a reproducibility and intervention-fidelity problem.

### 5.2 Multiple mechanisms remain compatible with the E-A pattern

Discuss pre-contact stiffness configuration, visual information, slower approach, operator adaptation, and bundled parameter differences as competing explanations. State that current data cannot isolate their individual contributions.

### 5.3 Safety and efficiency moved together

Interpret the lower force exposure and longer times as a trade-off pattern. Human caution/adaptation is an inference, not a directly measured mediator. Avoid implying that longer time necessarily caused the force reduction.

### 5.4 Implications for robot-experiment reporting

Argue for a reporting chain of code version -> nominal rule -> commanded parameters -> event timing -> realized trajectory -> analysis record. Explain why trial-level significance and controller labels alone are insufficient when human participants are the independent unit.

### 5.5 Limitations

State proactively: five independent participants; repeated trials are not independent humans; exploratory/non-preregistered analysis; bundled parameters; imperfect mode-order balance; Franka internal external-wrench estimate; incomplete physical object identity; software-log-based success; G/F implementation deviations; occasional post-contact vision locking; no strong population generalization; no isolated visual, stiffness, or force-refinement causal effect.

## H. Introduction argument chain

1. **Existing research context:** contact teleoperation seeks to limit contact force while preserving task efficiency; impedance, visual perception, and force-responsive adaptation are common design ingredients.
2. **Problem:** experimental papers often evaluate nominal controller modes, although the operator and robot respond to interventions realized in time, not labels in a protocol.
3. **Gap:** code logic, event clocks, activation flags, parameter trajectories, and trial data lineage are rarely integrated into the inferential unit used to evaluate human-in-the-loop controller performance.
4. **Paper question:** what interventions were actually realized in this experiment, and what participant-level safety-efficiency pattern remains after reconstructing them?
5. **Contributions:** auditable reconstruction workflow; exploratory E-A safety-efficiency pattern; demonstration of how lineage, timing, and participant-level inference constrain interpretation.

All literature claims require later verification with real sources; this blueprint supplies no fabricated citations.

## I. Results that can be stated directly

- Audited dataset counts, replacement mapping, and file verification.
- G/F activation incidence and timing medians.
- E/F post-contact vision-lock counts.
- Participant-level raw differences, CIs, all p-value families, and Holm corrections.
- Five observed E-A participant differences share the same direction.
- E-A LOPO estimates all retain the full-sample direction.
- All 180 trials met the software-log success definition, accompanied immediately by its measurement limitation.

“Directly” means factual/descriptive confidence, not strong population-level causal confidence.

## J. Results requiring cautious language

- E “was associated with” lower early force exposure.
- The E-A pattern “is consistent with” a safety-efficiency trade-off.
- Initial peak force provides concordant but secondary support.
- G-A shows a small negative average under the realized, pre-activated G implementation.
- F-E shows no discernible incremental benefit in this dataset.
- Operator caution, stiffness configuration, visual information, and adaptation are plausible explanations only.

## K. Statements that are prohibited

- Vision caused the force reduction.
- Reduced stiffness alone caused the force reduction.
- Visual and force feedback had a significant synergy.
- F significantly outperformed E.
- Force refinement is ineffective.
- G was a pure post-contact force-feedback mode.
- The four modes formed a strict 2x2 experiment.
- The study had 180 independent human samples.
- The E-A effect is confirmed or generalizes to the population.
- The Franka force estimate is an independently calibrated ground-truth contact force.
- Every E/F trial received its visual intervention before contact.

## L. Reviewer 2 attack test

1. **“With only five participants, is the study statistically credible?”**  
   **Answerability:** only partially. Existing data can show participant-level estimates, exact sign-flip/Wilcoxon sensitivity, Holm correction, and LOPO stability. They cannot support strong population generalization. Treat this as a central limitation.

2. **“Is this merely post-hoc debugging rather than a scientific contribution?”**  
   **Answerability:** partially. Defend with a reproducible, general audit chain and show that realized timing changes the permissible scientific interpretation. Avoid claiming that one audited dataset validates the workflow universally.

3. **“What component of E caused the lower impulse?”**  
   **Answerability:** no. The present modes bundle visual information, stiffness configuration, operator timing, and other differences. State explicitly that the data estimate a bundled-configuration association, not a component mechanism.

4. **“Do implementation deviations invalidate all mode comparisons?”**  
   **Answerability:** partially. They invalidate clean factorial and pure post-contact interpretations of G/F. They do not erase descriptive contrasts among realized configurations, nor the auditable E-A participant-level association, provided timing heterogeneity is disclosed.

5. **“Are force, success, order, and object factors measured well enough?”**  
   **Answerability:** partially to no. Force is an internal robot estimate, success is software-log based, order is incompletely balanced, and physical object identity is incomplete. Existing data can document these limitations and avoid unsupported adjustment or generalization, but cannot remove them.

## Stop condition

This deliverable freezes the existing-data paper story and evidence boundaries. It does not contain a full Introduction, Abstract, Discussion, or manuscript, and it proposes no additional data collection.
