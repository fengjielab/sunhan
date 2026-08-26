# From Nominal Conditions to Realized Interventions: A Fidelity Framework for Asynchronous Human–Machine Experiments

*THMS-oriented English manuscript translated from the fifth-version refined Chinese approval draft*

> **Approval and submission status.** This manuscript uses a frozen, cleaned reanalysis, versioned evidence reconstruction, and rule-level implementation verification. The approving or exempting ethics body, approval number, date, and informed-consent procedures must be completed from contemporaneous institutional records: `[ETHICS RECORD REQUIRED—DO NOT SUBMIT]`. Authors, affiliations, funding, conflicts of interest, author contributions, acknowledgments, and data- and code-availability statements must also be completed before submission. None of these items may be inferred from the currently available data.

## Abstract

Visual, haptic, and control interventions in asynchronous human–machine experiments can change the machine states available to the operator for observation, contact, and control during the outcome window. Condition labels alone therefore do not establish what was actually delivered and exposed in the operator–machine loop. This article proposes a realized-intervention fidelity framework. It organizes the nominal specification, executable implementation, trial-level realized intervention, and outcome as \(N_m\rightarrow C_m\rightarrow R_i\rightarrow Y_i\), and represents the subsequent response pathway in the closed human–machine loop as \(R_i(t)\rightarrow H_i(t+\delta)\rightarrow R_i(t+\delta)\rightarrow Y_i\). The framework reconstructs a five-field evidence state from contemporaneous specifications, archived source code, events, state trajectories, and acquisition provenance. Deterministic rules that do not use outcome direction then constrain the identity of scientifically supportable comparisons. We applied the framework to an archived bilateral teleoperation system comprising an Omega.7 master device, a Franka Panda robot, RGB vision, impedance control, and force feedback, with 180 trials from 5 participants. For G, a post-contact nominal specification was not recoverable, and activation preceded recorded contact in 43/45 trials. For F, the nominal post-contact 0.20-s guard contained a clock-domain mismatch, and only 3/45 trials met that timing. For E, exposure to the visual configuration during the post-contact 0.20–1.00-s window was full in 39 trials, partial in 2, and zero in 4. These findings changed the proposed identities of a purely post-contact G effect, a correctly gated incremental F effect, and a vision-by-force interaction into comparisons among realized configurations with explicit timing, bundled components, and exposure distributions. As an exploratory illustration under the retained comparison, the mean E–A difference in operational excess-force impulse was −0.3489 N·s, with a consistent direction across 5/5 participants. With \(n=5\), this pattern does not provide confirmatory causal evidence for an isolated visual, stiffness, or force component. Realized-intervention fidelity thus translates “what a condition was called” into “what intervention was actually delivered and exposed in the loop, and what can still be scientifically compared,” providing a reproducible evaluation layer for asynchronous human–machine experiments.

**Index Terms—** Asynchronous control, evidence provenance, experimental validity, human–machine systems, implementation fidelity, realized intervention, teleoperation.

# 1. Introduction

Teleoperation, shared control, and other closed-loop human–machine experiments commonly define experimental conditions as fixed, adaptive, vision-enabled, force-feedback, or combined modes [1]–[20]. These labels facilitate assignment and reporting, but they do not establish that the corresponding intervention was delivered in every trial with the intended guards, clocks, parameters, and duration in the operator–machine loop. Asynchronous vision processes, control updates, contact detection, and logging channels can alter intervention onset, duration, and coverage of the outcome window. “Post-contact,” “vision-enabled,” and “vision + force” are therefore experimental commitments that must first be verified, rather than established trial-level facts.

This distinction has direct scientific consequences in human–machine systems. After the realized intervention \(R_i(t)\) changes the visual, haptic, or machine state, the operator may update subsequent input \(H_i(t+\delta)\), which in turn changes the subsequent machine realization and the complete outcome trajectory:

\[
R_i(t)\rightarrow H_i(t+\delta)\rightarrow R_i(t+\delta)\rightarrow Y_i.
\]

An intervention that begins 0.8 s early is therefore not merely a software parameter written ahead of schedule. The operator may receive different feedback during approach, contact, or closed-loop correction, producing a different human–machine trajectory. If outcomes are compared only by nominal condition labels, the resulting statistic may precisely describe a set of data without answering the stated human–machine intervention question.

Prior work has separately established the importance of transparency and latency in teleoperation [1]–[8], variable impedance and teleimpedance [9]–[20], visual–haptic timing [22], reproducibility in human–machine research [23]–[28], runtime verification [29], implementation fidelity [30], and estimand definition [31]. A joint layer is still needed before statistical analysis. It must determine whether a nominal intervention is supported by a specification, whether the implementation encodes that specification, what was actually delivered in each trial, how much exposure occurred within the outcome window, and whether the intervention can be linked exactly to the analyzed record.

This article addresses three research questions:

- **RQ1 (Reconstructability):** Can realized-intervention fidelity be reconstructed from archived specifications, source code, events, trajectories, and provenance without using outcome values, directions, or significance?
- **RQ2 (Realized discontinuities):** What discontinuities arise among the nominal specification, executable implementation, realized delivery, and window exposure in an operational asynchronous teleoperation system?
- **RQ3 (Comparison identity):** How does realized-intervention reconstruction change the condition comparisons that the available data can scientifically support?

This article makes three contributions. First, it formulates realized-intervention fidelity as a distinct evaluation layer for asynchronous human–machine experiments, making the intervention actually delivered and exposed in the loop an object that must be verified before statistical comparison. Second, it operationalizes this layer through auditable evidence states and deterministic interpretation constraints. Without examining human outcomes, these constraints distinguish identity retention, an unrecoverable nominal specification, implementation or delivery mismatches, and incomplete exposure. Third, the framework is applied to an archived teleoperation system and shows how reconstruction can materially recast nominal factorial claims as narrower comparisons among realized configurations. The case study is not interpreted as external validation of the framework, and passing a fidelity assessment is not treated as a substitute for the conditions required for causal identification.

![Asynchronous human–machine loop and the realized-intervention fidelity framework.](../02_main_figures/v5_1/Fig01_human_machine_fidelity_framework_v5_1.png)

**Fig. 1.** (A) The operator, Omega.7, asynchronous vision/supervisory controller, Panda, and haptic and machine-state feedback form a closed loop; intervention timing can change subsequent human input and the outcome trajectory. (B) The \(N\rightarrow C\rightarrow R\rightarrow Y\) evidence chain supported by contemporaneous artifacts is reconstructed as an evidence state, which then constrains comparison identity and scientifically admissible wording. Provenance is an orthogonal prerequisite for linking realized interventions to outcomes; retention of identity does not imply causal identification.

# 2. Related Work

## 2.1 Timing and Intervention Exposure in Closed-Loop Teleoperation

Research on bilateral teleoperation has long examined stability, transparency, communication latency, and feedback quality [1]–[8]. Variable-impedance, teleimpedance, and vision-assisted approaches further allow controllers to adapt robot responses online according to the task, environment, or operator state [9]–[20]. This literature shows that visual, haptic, and machine dynamics jointly shape human control behavior. Outcome analyses in many human–machine experiments are organized by assigned condition, whereas trial-level intervention delivery and window exposure are not the primary objects of evaluation. Research on visual–haptic timing also indicates that people can detect relatively small cross-modal temporal discrepancies [22]. This finding motivates closer attention to realized onset timing but does not, by itself, reconstruct each intervention in archived trials.

## 2.2 Reproducibility, Runtime Evidence, and Implementation Fidelity

Research in robotics and human–robot interaction has emphasized transparency in artifacts, code, procedures, and experimental units [23]–[28]. Runtime verification can monitor formal software properties [29], whereas implementation-fidelity research distinguishes planned interventions from their implementation [30]. Both provide important foundations for this study, but neither alone determines the comparison identity of a human–machine experiment. Satisfying a software property does not establish that the operator received full exposure during the outcome window. Conversely, an observed state in a log cannot restore a missing scientific specification.

Work on estimands emphasizes alignment among the theoretical question, the comparison, and the statistical quantity [31]. Accordingly, this study does not create a new causal target after observing the realized intervention. Instead, the evidence chain is used to constrain the narrowest supportable descriptive comparison. The methodological gap is not the absence of another fidelity score, but the absence of an operational transformation from “specification–implementation–realized delivery–window exposure–record identity” to “what comparisons are admissible.”

# 3. Realized-Intervention Fidelity Framework

## 3.1 From the Human–Machine Loop to the Evidence Chain

The evidence chain for one comparison in a human–machine experiment, shown in Fig. 1(B), is represented as

\[
N_m\rightarrow C_m\rightarrow R_i\rightarrow Y_i,
\]

where \(N_m\) is the nominal intervention supported by contemporaneous artifacts, \(C_m\) is the executable implementation in the archived acquisition program, \(R_i\) is the realized intervention recorded in trial \(i\), and \(Y_i\) is the outcome defined over a frozen window and experimental unit. Acquisition provenance \(\mathcal P_i\) is an orthogonal prerequisite for linking \(R_i\) to \(Y_i\); it is not part of the intervention itself.

## 3.2 Five Evidence Questions

The framework represents evidence as a five-field state:

\[
S=(s_N,s_{NC},s_{CR},s_{\Phi},s_{\mathcal P}).
\]

The five fields address the following scientific questions:

1. \(s_N\): Is the intervention originally intended for delivery in the operator–machine loop known?
2. \(s_{NC}\): Does the archived implementation encode an intervention supported by contemporaneous artifacts?
3. \(s_{CR}\): Do the recorded inputs and trajectories support that the implementation was actually delivered?
4. \(s_{\Phi}\): Did the intervention occur within the frozen outcome window, and how much of the window did it cover?
5. \(s_{\mathcal P}\): Can the intervention trajectory be linked exactly to the outcome record being analyzed?

States are derived either by automated computation or by a structured author audit. Automated computation is used for event differences, trajectories, exposure, identity, and hashes. The structured audit evaluates whether contemporaneous artifacts constitute an adequate specification and whether the specification corresponds semantically to the source code. No independent dual-review semantic audit was performed; inter-rater agreement is therefore not reported. Complete field definitions, rules, tolerances, missing-data handling, and source audits are provided in Supplementary Tables S1–S4.

For a binary activation state \(a_i(t)\) and a window \(W=[t_0,t_1]\), exposure is defined as

\[
\Phi_i(W)=\frac{1}{|W|}\int_{t_0}^{t_1}\mathbb I[a_i(t)=1]dt.
\]

Full, partial, and zero exposure are encoded using frozen numerical boundaries. If the trajectory or window is incomplete, exposure is recorded as unavailable rather than replaced with zero.

## 3.3 From Evidence State to Admissible Interpretation

Evidence states are not aggregated into a single score. Instead, they determine the diagnosis, intervention identity, admissible comparison level, and prohibited wording. The main text uses four interpretation boundaries: an intact identity chain, a nominal specification that is not recoverable, an implementation/delivery mismatch, and incomplete exposure. An operational summary is provided in Table II, with the complete deterministic rules in Supplementary Table S2.

When the nominal identity cannot be retained, a descriptive comparison between realized configurations can be reported:

\[
D^R_{m_1,m_0}=\mathbb E[Y\mid R\in\mathcal R_{m_1}]-\mathbb E[Y\mid R\in\mathcal R_{m_0}].
\]

\(D^R\) is not a causal target redefined after observing \(R\). Any causal interpretation still requires additional support for the assignment mechanism, exchangeability, consistency, measurement validity, and independent units of inference.

# 4. Archived Human–Machine Experiment and Reconstruction Methods

## 4.1 Human Teleoperation System and Experimental Structure

The archived system comprised an Omega.7 human input device, a Franka Panda robot with a Franka Hand, an Intel RealSense D435i RGB vision process, a supervisory controller, impedance/force-feedback updates, and asynchronous logs. The operator commanded master-device motion through the Omega.7. The supervisory controller combined visual locking, contact estimation, and configuration logic to generate machine commands. External force estimated internally by the Panda contributed both to contact-related states and, through the force-feedback channel, to operator input. This architecture formed a closed loop in which visual, haptic, and machine states acted jointly.

The 5 participants completed 180 analyzed trials across 3 materials, 3 repeated blocks, and 4 configurations, with 45 trials per configuration. Repeated trials were used to describe trial-level fidelity, but the participant remained the independent human experimental unit for outcome analysis (\(n=5\)). Participant demographics, training, object geometry, and prospective randomization or counterbalancing were not recovered from the current record lineage.

![Experimental apparatus, closed-loop signal paths, and archived experimental procedure.](../02_main_figures/v5_1/Fig02_system_experiment_v5_1.png)

**Fig. 2.** (A) Physical experimental apparatus, including the Omega.7, Panda, Franka Hand, RealSense, and task workspace. (B) Closed-loop signals and asynchronous event channels. (C) Archived experimental structure and outcome window. The figure describes only the system and measurement procedure; it does not report reconstruction results.

## 4.2 Archived Conditions and Intended Operator-Side Exposure

The four archived configurations were labeled A, G, E, and F. Table I reports only the experimental structure recoverable from condition definitions and program documentation. “Intended operator-side exposure” is not inferred from a label; final identity is determined by framework-based reconstruction.

**TABLE I. ARCHIVED EXPERIMENTAL CONDITIONS AND OPERATOR-SIDE EXPOSURES TO BE VERIFIED.**

| Configuration | Primary Channels and Machine Changes | Trigger or Timing Indicated by Labels/Artifacts | Operator-Side Exposure to Be Verified | Evaluation Prerequisite |
|---|---|---|---|---|
| A | Fixed impedance and fixed command configuration | Remains fixed after initialization | Fixed machine response and force-feedback baseline | Verify initialization and trial trajectory |
| G | Original online force rule without vision | Label suggests a contact-related adjustment | Force-related change in machine response; the specific “post-contact” meaning cannot be established from the label alone | Recover an independent specification and replay the rule |
| E | Visual lock triggers a bundled multiparameter configuration | Transition after the first valid visual lock | Bundled machine and haptic changes delivered after visual recognition | Verify mapping, transition, and window exposure |
| F | Force refinement added to E | Artifacts indicate gating at 0.20 s after contact | Exposure first to the bundled visual change and then to delayed force refinement | Verify guard, clock, delivery, and exposure |

## 4.3 Evaluation Rules and Realized-Intervention Reconstruction

**TABLE II. EVIDENCE SCENARIOS AND ADMISSIBLE SCIENTIFIC INTERPRETATIONS.**

| Evidence Scenario | Supportable Interpretation | Unsupported Claim |
|---|---|---|
| Identity chain intact and provenance valid | Retain the nominal intervention identity supported by the specification | Claim a causal effect from fidelity alone |
| Nominal specification not recoverable | Describe the recoverable realized configuration and exposure | Interpret a condition label as the unrecovered nominal intervention |
| Implementation or delivery mismatch / not fully evaluable | Describe the recorded implementation, trajectory, or delivery state | Claim that the intended strategy or \(C=R\) has been established |
| Window exposure partial, zero, or unavailable | Provide an assignment-based description qualified by the exposure distribution, or stop the corresponding evaluation | Claim a uniformly complete intervention effect within the window |

All trials point to acquisition commit `09c13e0b679905f14f770d820af00841546cb4cc`. Configuration-level semantic audits used the source-code snapshot from that commit. Trial-level automated computations used the master manifest, raw CSV files, event JSON files, summary JSON files, logged states, and current SHA-256 hashes.

For each configuration, reconstruction sequentially examined the contemporaneous specification; the guards, clocks, parameters, initialization, and update logic in the source code; state or command trajectories under recorded inputs; left-continuous exposure within the frozen window; and the links among logical trial, acquisition record, and file hash. When complete replay was possible, recorded inputs were supplied to archived formulas and the results were compared with logged trajectories. When cycle-level predicate inputs were missing, delivery fidelity was conservatively recorded as not evaluable, while directly reconstructable activation and exposure descriptions were retained. Any missing specification, implementation mismatch, unavailable replay, or incomplete exposure was encoded before outcomes were examined.

When both target activation \(t^N_{act}\) and a common clock mapping were supported, timing error was defined as \(\epsilon_{act}=t^R_{act}-t^N_{act}\). The clock-domain check compared the sources and origins of time values on the two sides of the guard; trial timing was described using aligned recorded events. The method did not infer an unknown nominal specification from recorded activation times, nor did it attribute an outcome jointly produced by scheduling, other guards, and log sampling to a single software expression.

## 4.4 Outcome and Statistical Analysis

The primary outcome was operational above-threshold force impulse during the post-contact 0.20–1.00-s window. This window corresponds to the stage in which the operator enters post-contact closed-loop correction and subsequent input can be affected by visual, haptic, and machine-impedance states. Both contact alignment and impulse calculation used the Panda internal `O_F_ext_hat_K` estimate. The outcome was therefore an operational contact outcome measured within the human–machine loop, rather than a physical safety endpoint measured by an independent external force sensor.

Data were first aggregated within material and repeated block for each participant, after which paired configuration differences were calculated. We report the participant mean, t-based 95% confidence interval, paired t-test, exact sign-flip test, exact Wilcoxon test, and Holm correction across 4 comparisons. With only 5 participants, the outcome analysis remained an exploratory illustration. Record-selection robustness enumerated all \(2^6=64\) choices across 6 initial/alternative record pairs. Fixed adjacent windows, leave-one-participant-out analyses, and secondary timing metrics are retained in the Supplementary Material.

## 4.5 Rule-Level Internal Verification

The two-stage interface was implemented as `ArtifactEvidence→EvidenceState` and `EvidenceState→Decision`. Inputs, expected states, and expected decisions were stored in a frozen oracle table separate from the executable code. The 12 controlled artifact cases covered an intact chain, a missing specification, guard/clock mismatches, runtime deviations, partial/zero/unavailable exposure, invalid provenance, and multiple co-occurring discontinuities. This check tested only whether the implementation faithfully executed the stated rules and could be challenged by counterexamples. It did not estimate sensitivity to unknown faults, completeness of the state space, or cross-system validity.

# 5. Results

## 5.1 RQ1–RQ2: Realized Timing and Exposure in Operational Trials

All 180/180 intervention trajectories were linked to outcomes through checks of exact record identity, path, timestamp, acquisition commit, and current hash. The executable original force rule for G was replayable at 12,196 logged command updates across 45 trials. The maximum numerical errors for force ratio, target translational stiffness, and the 0.3 smoothing update were all below \(10^{-10}\). However, an independent contemporaneous artifact could not recover the nominal “post-contact G” specification, and G activated before recorded contact in 43/45 trials. Delivery consistency with the source-code equation therefore cannot restore the missing scientific intent.

The F source code passed `time.time()` into a system-time calculation whose origin was `time.perf_counter()`, thereby violating the clock semantics of the nominal 0.20-s post-contact guard. F never activated before contact, but only 3/45 trials activated at least 0.20 s after contact; the observed median contact-to-activation interval was 0.05327 s. This recorded interval of approximately 53 ms resulted from the complete downstream path, including other guards, scheduling, state conditions, and log sampling. It was not a 53-ms delay numerically “caused” by the mixed-clock expression. Activation and exposure for F could be reconstructed, but complete cycle-level predicate inputs were unavailable. Accordingly, \(s_{CR}\) was recorded as `not_evaluable`, rather than `pass` or `fail`.

Exposure to the visual configuration for E within the outcome window was full in 39 trials, partial in 2, and zero in 4. In the 4 zero-exposure trials, both visual lock and completion of the transition occurred after the end of the window. The two partial-exposure values were 0.966863 and 0.00115488; the latter covered only approximately 1 ms at the end of the window. For F, exposure to the visual configuration was full in 42 trials and zero in 3. Exposure to the force adaptation and joint visual–adaptation configuration was full in 35 trials, partial in 7, and zero in 3.

![Realized activation timing for G/F and outcome-window exposure for E/F.](../02_main_figures/v5_1/Fig03_realized_intervention_fidelity_v5_1.png)

**Fig. 3.** (A) Timing of the first G activation relative to contact and replay results for the executable rule. (B) Realized F activation relative to the nominal +0.20-s gate; the mixed clocks and unavailability of complete \(C\rightarrow R\) predicate replay are explicitly marked. (C) Trial-level full, partial, and zero exposure for E/F during the post-contact 0.20–1.00-s window. Human-outcome inference remains at the level of 5 participants.

## 5.2 RQ3: Comparison Identity After Reconstruction

The evidence states and admissible interpretations are summarized in Table III. Reconstruction neither excluded trials nor regrouped them according to outcomes; it changed the scientific names assigned to the original condition comparisons.

**TABLE III. REALIZED-INTERVENTION FIDELITY AND SUPPORTABLE COMPARISON IDENTITIES FOR THE ARCHIVED CONDITIONS.**

| Configuration | \(s_N\) | \(s_{NC}\) | \(s_{CR}\) | Window Exposure | Supportable Identity and Comparison Boundary |
|---|---|---|---|---|---|
| A | available | pass | pass | 45 full | Fixed A identity can be retained; causal interpretation is not automatically authorized |
| G | unavailable | not_evaluable | pass | 40 full/5 partial | Replay-consistent realized original-force G versus fixed A; cannot be described as a purely post-contact effect |
| E | available | pass | pass | 39 full/2 partial/4 zero | Assigned bundled E configuration with heterogeneous visual exposure versus A; cannot be decomposed into isolated visual, stiffness, or force effects |
| F | available | fail: clock | not_evaluable | 35 full/7 partial/3 zero | Recorded early/heterogeneous F versus E; cannot be described as the correctly implemented +0.20-s strategy or as establishing \(C=R\) |

Consequently, G–A can describe only the realized original-force G rule, predominantly activated before contact, relative to fixed A. E–A describes assignment to the bundled E configuration and its heterogeneous visual exposure relative to A. F–E describes the recorded early/heterogeneous F configuration relative to E, with disclosure that complete delivery replay was not evaluable. F–G likewise cannot be interpreted as factorial main effects of vision, force, or their interaction.

## 5.3 Exploratory Outcome Pattern Under the Retained Comparison

For the E–A realized-configuration comparison that remained descriptively supportable after reconstruction, the mean difference in operational excess-force impulse was −0.3489 N·s (95% CI, −0.6080 to −0.0898; paired t-test, \(p=0.0201\)); the difference was negative for all 5 participants. The exact sign-flip and Wilcoxon tests both yielded \(p=0.0625\). After Holm correction across 4 contrasts, the paired t-test yielded 0.0633 and both exact tests yielded 0.2500. This result is therefore an exploratory, directionally consistent pattern for the bundled E configuration, rather than a confirmatory causal effect or an isolated mechanism.

Across all 64/64 record selections, the E–A mean remained negative, ranging from −0.353791 to −0.336697 N·s, and every selection retained negative differences for all 5 participants. This robustness check neither changed the provenance status of the erroneous initial records nor increased the independent sample size.

![Participant-paired E–A outcomes and record-selection robustness.](../02_main_figures/v5_1/Fig04_EA_outcome_robustness_v5_1.png)

**Fig. 4.** (A) Paired E–A differences in operational excess-force impulse during the post-contact 0.20–1.00-s window for 5 participants, with the 95% confidence interval for the mean. (B) Range of the E–A mean across 64 record selections. The comparison shown is between the bundled E configuration with heterogeneous visual exposure and fixed A; it does not represent a causal effect of an isolated visual, stiffness, or force strategy.

## 5.4 Rule-Level Internal Verification

All 12/12 frozen cases returned the expected evidence states, cumulative diagnoses, identities, and comparison levels. The checks confirmed that a label cannot make a missing specification available, guard and clock mismatches can coexist, and approximately 1 ms of exposure remains partial exposure. They also confirmed that a missing trajectory produces unavailable rather than zero exposure, invalid provenance prevents evaluation of the intervention–outcome link, and incomplete replay can coexist with known exposure. These results constitute rule-level implementation verification, not diagnostic accuracy, a methodological validity rate, or external validation.

# 6. Discussion

## 6.1 Implications for the Interpretation of Human–Machine Experiments

The main finding is not a software defect itself. Rather, intervention delivery timing and window exposure can change the closed loop entered by the operator. G predominantly activated before contact, most F activations occurred earlier than the nominal gate, and some E trials lacked full exposure to the visual configuration during the outcome window. Each discrepancy could change the machine state and feedback available to the operator during approach, contact, and correction, thereby changing subsequent input and the outcome trajectory. A condition label is therefore not a sufficient experimental unit for a human–machine intervention.

Realized-intervention reconstruction also changed the scientific identity of the results. The available data cannot answer questions about a purely post-contact G intervention, a correctly gated F intervention, or a factorial vision-by-force effect. They can still address a narrower question: what descriptive differences are observed between a particular archived implementation, with its recorded exposure distribution, and a fixed or other realized configuration? This narrowing does not exclude unfavorable trials. It aligns the comparison name with verifiable evidence.

## 6.2 Requirements for Prospective Experimental Design

Prospective asynchronous human–machine experiments should freeze the intervention specification, common clock, event definitions, outcome window, and independent experimental unit before acquisition. During acquisition, they should preserve every guard input, the reason for each state transition, the complete activation trajectory, and exact record identity. Evidence reconstruction should be conducted independently before inference. Reports should present the nominal assignment, realized delivery timing, exposure distribution, and any element that was not evaluable.

These requirements do not replace evaluations of control performance, usability, workload, or subjective experience. Instead, they establish a credible treatment identity for those measures. Particularly in systems that update visual, haptic, and control parameters asynchronously, delivery and exposure should be recorded as experimental variables rather than embedded as implementation assumptions within condition labels.

## 6.3 Methodological Implications

The framework connects several previously separate lines of work. Latency research shows that timing may affect human–machine performance; runtime verification checks software properties; reproducibility research preserves artifacts and procedures; implementation fidelity distinguishes a planned intervention from its implementation; and estimand research links theory to statistics. The contribution of this study is to transform this evidence into comparison identities and wording boundaries, while preserving the distinctions between automated computation and semantic audit, trial-level fidelity and participant-level inference, and identity verification and causal identification.

The 12 controlled cases make the rule implementation executable and challengeable by counterexamples, but they do not establish that the rule space is complete. The archived case shows that multiple discontinuities can coexist within one acquisition; it does not constitute cross-system external validation. Future methodological validation should prospectively freeze specifications and oracles across multiple platforms, inject known and unknown faults through an independent process, and evaluate diagnostic accuracy, rates of not-evaluable determinations, and semantic-audit agreement.

## 6.4 Limitations

The independent human sample comprised only 5 participants, and the framework was operationalized in only one archived teleoperation system. Information about prospective randomization or counterbalancing was not recovered. E and F were bundled multiparameter configurations; E–A and F–E cannot be attributed to isolated visual, stiffness, force-feedback, or gripper parameters. Contact alignment and the outcome shared the Panda internal force estimate, and logged stiffness was not an independently measured physical impedance.

Participant demographics, training, object geometry, and several experimental-procedure details were not recovered from the current record lineage. The structured semantic audit was author-conducted and did not use independent dual coding. Complete cycle-level predicate inputs for F were unavailable, so the complete \(C\rightarrow R\) relation could only be recorded as not evaluable. Contemporaneous evidence for the failure of 6 replaced record groups remained incomplete; the 64 combinations cannot make erroneous records provenance-valid. Ethics approval or exemption and informed consent must be resolved affirmatively from contemporaneous institutional records before submission.

# 7. Conclusion

Nominal condition labels alone do not establish that an asynchronous human–machine system delivered the corresponding intervention in the operator–machine loop. By linking the specification, implementation, trial-level delivery, window exposure, and record identity, realized-intervention fidelity reconstruction determines when a nominal comparison can be retained, when it must be recast, and when it is not evaluable. In this archived teleoperation case, the process materially changed the scientific identities of comparisons involving G, E, and F and constrained E–A to an exploratory bundled-configuration comparison. Future human–machine experiments should record intervention delivery timing and window exposure as explicit experimental variables so that “what was actually compared” can be verified before statistical inference.

# References

1. Hannaford, B. (1989). A design framework for teleoperators with kinesthetic feedback. *IEEE Transactions on Robotics and Automation, 5*(4), 426–434. https://doi.org/10.1109/70.88057
2. Lawrence, D. A. (1993). Stability and transparency in bilateral teleoperation. *IEEE Transactions on Robotics and Automation, 9*(5), 624–637. https://doi.org/10.1109/70.258054
3. Hokayem, P. F., & Spong, M. W. (2006). Bilateral teleoperation: An historical survey. *Automatica, 42*(12), 2035–2057. https://doi.org/10.1016/j.automatica.2006.06.027
4. Passenberg, C., Peer, A., & Buss, M. (2010). A survey of environment-, operator-, and task-adapted controllers for teleoperation systems. *Mechatronics, 20*(7), 787–801. https://doi.org/10.1016/j.mechatronics.2010.04.005
5. Huang, K., Chitrakar, D., Rydén, F., & Chizeck, H. J. (2019). Evaluation of haptic guidance virtual fixtures and 3D visualization methods in telemanipulation—A user study. *Intelligent Service Robotics, 12*, 289–301. https://doi.org/10.1007/s11370-019-00283-w
6. Rakita, D., Mutlu, B., & Gleicher, M. (2020). Effects of onset latency and robot speed delays on mimicry-control teleoperation. In *Proceedings of the 2020 ACM/IEEE International Conference on Human-Robot Interaction*. https://doi.org/10.1145/3319502.3374838
7. Louca, J., Eder, K., Vrublevskis, J., & Tzemanaki, A. (2024). Impact of haptic feedback in high latency teleoperation for space applications. *ACM Transactions on Human-Robot Interaction, 13*(2), Article 16, 1–21. https://doi.org/10.1145/3651993
8. Gong, Y., Mat Husin, H., Erol, E., Ortenzi, V., & Kuchenbecher, K. J. (2024). AiroTouch: Enhancing telerobotic assembly through naturalistic haptic feedback of tool vibrations. *Frontiers in Robotics and AI, 11*, 1355205. https://doi.org/10.3389/frobt.2024.1355205
9. Hogan, N. (1985). Impedance control: An approach to manipulation: Part I—Theory. *Journal of Dynamic Systems, Measurement, and Control, 107*(1), 1–7. https://doi.org/10.1115/1.3140702
10. Walker, D. S., Wilson, R. P., & Niemeyer, G. (2010). User-controlled variable impedance teleoperation. In *2010 IEEE International Conference on Robotics and Automation*. https://doi.org/10.1109/ROBOT.2010.5509811
11. Buchli, J., Stulp, F., Theodorou, E., & Schaal, S. (2011). Learning variable impedance control. *The International Journal of Robotics Research, 30*(7), 820–833. https://doi.org/10.1177/0278364911402527
12. Ajoudani, A., Tsagarakis, N. G., & Bicchi, A. (2012). Tele-impedance: Teleoperation with impedance regulation using a body–machine interface. *The International Journal of Robotics Research, 31*(13), 1642–1656. https://doi.org/10.1177/0278364912464668
13. Peternel, L., Petrič, T., & Babič, J. (2018). Robotic assembly solution by human-in-the-loop teaching method based on real-time stiffness modulation. *Autonomous Robots, 42*, 1–17. https://doi.org/10.1007/s10514-017-9635-z
14. Abu-Dakka, F. J., Rozo, L., & Caldwell, D. G. (2018). Force-based variable impedance learning for robotic manipulation. *Robotics and Autonomous Systems, 109*, 156–167. https://doi.org/10.1016/j.robot.2018.07.008
15. Abu-Dakka, F. J., & Saveriano, M. (2020). Variable impedance control and learning—A review. *Frontiers in Robotics and AI, 7*, 590681. https://doi.org/10.3389/frobt.2020.590681
16. Michel, Y., Rahal, R., Pacchierotti, C., Robuffo Giordano, P., & Lee, D. (2021). Bilateral teleoperation with adaptive impedance control for contact tasks. *IEEE Robotics and Automation Letters, 6*(3), 5429–5436. https://doi.org/10.1109/LRA.2021.3066974
17. Peternel, L., & Ajoudani, A. (2023). After a decade of teleimpedance: A survey. *IEEE Transactions on Human-Machine Systems, 53*(2), 401–416. https://doi.org/10.1109/THMS.2022.3231703
18. Michel, Y., Li, Z., & Lee, D. (2023). A learning-based shared control approach for contact tasks. *IEEE Robotics and Automation Letters, 8*(12), 8002–8009. https://doi.org/10.1109/LRA.2023.3322332
19. Huang, Y.-C., Abbink, D. A., & Peternel, L. (2021). A semi-autonomous tele-impedance method based on vision and voice interfaces. In *2021 20th International Conference on Advanced Robotics*, 180–186. https://doi.org/10.1109/ICAR53236.2021.9659427
20. Siegemund, G., Díaz Rosales, A., Glodde, A., Dietrich, F., & Peternel, L. (2024). Semi-autonomous teleimpedance based on visual detection of object geometry and material and its relation to environment. In *2024 IEEE-RAS 23rd International Conference on Humanoid Robots*, 779–786. https://doi.org/10.1109/Humanoids58906.2024.10769858
21. Jekel, H. H. A., Díaz Rosales, A., & Peternel, L. (2026). Visio-verbal teleimpedance interface: Enabling semi-autonomous control of physical interaction via eye tracking and speech. *Frontiers in Robotics and AI, 13*, 1749105. https://doi.org/10.3389/frobt.2026.1749105
22. Vogels, I. M. L. C. (2004). Detection of temporal delays in visual-haptic interfaces. *Human Factors, 46*(1), 118–134. https://doi.org/10.1518/hfes.46.1.118.30394
23. Bonsignorio, F., & del Pobil, A. P. (2015). Toward replicable and measurable robotics research [From the Guest Editors]. *IEEE Robotics & Automation Magazine, 22*(3), 32–35. https://doi.org/10.1109/MRA.2015.2452073
24. Bonsignorio, F. (2017). A new kind of article for reproducible research in intelligent robotics [From the Field]. *IEEE Robotics & Automation Magazine, 24*(3), 178–182. https://doi.org/10.1109/MRA.2017.2722918
25. Gunes, H., Broz, F., Crawford, C. S., Rosenthal-von der Pütten, A., Strait, M., & Riek, L. (2022). Reproducibility in human-robot interaction: Furthering the science of HRI. *Current Robotics Reports, 3*(4), 281–292. https://doi.org/10.1007/s43154-022-00094-5
26. Aldana-López, R., Aragüés, R., & Sagüés, C. (2023). Latency vs precision: Stability preserving perception scheduling. *Automatica, 155*, 111123. https://doi.org/10.1016/j.automatica.2023.111123
27. Bagchi, S., Holthaus, P., Beraldo, G., Senft, E., Hernandez, D., Han, Z., Jayaraman, S. K., Rossi, A., Esterwood, C., Andriella, A., & Pridham, P. S. (2023). Towards improved replicability of human studies in human-robot interaction. In *Companion of the 2023 ACM/IEEE International Conference on Human-Robot Interaction*. https://doi.org/10.1145/3568294.3580162
28. Marchesi, S., De Tommaso, D., Kompatsiari, K., Wu, Y., & Wykowska, A. (2024). Tools and methods to study and replicate experiments addressing human social cognition in interactive scenarios. *Behavior Research Methods, 56*(7), 7543–7560. https://doi.org/10.3758/s13428-024-02434-z
29. Huang, J., Erdogan, C., Zhang, Y., Moore, B., Luo, Q., Sundaresan, A., & Roşu, G. (2014). ROSRV: Runtime verification for robots. In *Runtime Verification* (Lecture Notes in Computer Science, Vol. 8734, pp. 247–254). Springer. https://fsl.cs.illinois.edu/publications/huang-erdogan-zhang-moore-luo-sundaresan-rosu-2014-rvtool.html
30. Carroll, C., Patterson, M., Wood, S., Booth, A., Rick, J., & Balain, S. (2007). A conceptual framework for implementation fidelity. *Implementation Science, 2*, 40. https://doi.org/10.1186/1748-5908-2-40
31. Lundberg, I., Johnson, R., & Stewart, B. M. (2021). What is your estimand? Defining the target quantity connects statistical evidence to theory. *American Sociological Review, 86*(3), 532–565. https://doi.org/10.1177/00031224211004187
