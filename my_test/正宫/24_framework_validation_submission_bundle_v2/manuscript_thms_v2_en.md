# From Nominal Controller Labels to Delivered Interventions: A Fidelity Framework with Prospective Timing–Exposure Criterion Validation

> **Manuscript status.** THMS-oriented English draft v2. The approving or exempting institution, identifier, date, consent procedure, and authorization for secondary use of archived data must be completed from contemporaneous institutional records: `[ETHICS RECORD REQUIRED—DO NOT SUBMIT]`. Authors, affiliations, funding, conflicts of interest, author contributions, acknowledgments, and the final data/code availability statement must likewise be completed before submission and must not be inferred from the experiment files.

## Abstract

Experiments with asynchronous human–machine systems commonly define conditions using nominal labels such as fixed, adaptive, vision-enabled, or combined control. A label, however, does not establish that the coupled human–machine system actually received the corresponding intervention during the outcome window. We propose a realized-intervention fidelity framework that links documented nominal intent, implemented source-code behavior, trial-specific recorded delivery, and outcomes as an evidence chain, (N_m\rightarrow C_m\rightarrow R_i\rightarrow Y_i). Activation-timing error (epsilon_i), outcome-window exposure (Phi_i), clock integrity, and exact acquisition lineage jointly determine which statistical comparisons remain admissible. Evidence was developed in two stages. First, the framework was applied retrospectively to 180 repeated teleoperation trials from five participants. It identified discontinuities among nominal labels, executable guards, and realized timing and narrowed the interpretations supported by the archive. Second, a prospective known-truth criterion study was conducted on the same platform with 20 independent participants. Five conditions systematically manipulated feedback onset and duration to create predefined combinations of (epsilon) and (Phi). Of 300 planned trials, 294 completed and six ended through the 5-N safety abort. An offline reconstruction that did not import online-controller condition constants correctly classified 294/294 evaluable trials. Mean, 95th-percentile, and maximum absolute onset errors were 2.381, 4.957, and 5.408 ms; the corresponding absolute exposure errors were 0.001798, 0.005996, and 0.006760. All frozen criterion-recovery limits were met. Haptic-command clamping occurred in 65/294 completed trials. Clamping did not alter timing or window-exposure reconstruction but constrained interpretation of delivered physical dose and exploratory human outcomes. Human force measures were analyzed descriptively at the participant level and were not used as confirmatory efficacy evidence. Together, the studies show that realized-intervention fidelity can diagnose interpretation boundaries in archived studies and can be prospectively validated against known truth within a system. The results do not constitute external validation or automatically confer causal meaning.

**Index Terms—** Human–machine system evaluation, implementation fidelity, asynchronous teleoperation, outcome-window exposure, runtime timing, criterion validation, data lineage.

# I. Introduction

Closed-loop teleoperation couples human perception, decisions, and adaptation with a haptic interface, supervisory software, a remote robot, and the physical environment. Contact performance is therefore a system outcome produced by continued interaction in the feedback loop rather than an isolated controller output [1]–[4]. Haptic guidance, shared control, impedance modulation, and visual assistance can affect interaction safety and efficiency, yet these components often run in different threads, scheduling cycles, and clock domains [5]–[17].

Experimental conditions are typically organized using labels such as *fixed*, *vision-enabled*, *force-adaptive*, or *combined*. Each label implies parameters, guards, event ordering, and duration: when a mechanism becomes active, when it ends, and how much of an outcome window it covers. Asynchronous execution can cause a nominally post-contact mechanism to activate early, or can allow an executed mechanism to cover only part of the outcome window. Assignment labels, implemented behavior, realized delivery, and statistical outcomes can consequently diverge.

Latency research, robot runtime verification, reproducibility, implementation fidelity, and estimand theory each address part of this problem [18]–[27]. What remains missing for human–machine evaluation is a joint rule for tracing nominal intent to delivered intervention, converting runtime timing into outcome-window exposure, and determining what a comparison still means after an evidence discontinuity.

We address four research questions:

1. **RQ1—Retrospective diagnosis:** What agreements and deviations occur among nominal conditions, executable logic, and recorded delivery in an archived asynchronous teleoperation study?
2. **RQ2—Interpretation boundary:** How do these deviations constrain the statistical target and scientific wording supported by the archive?
3. **RQ3—Prospective criterion validation:** Can the framework accurately recover (epsilon), (Phi), and condition identity when timing and exposure truth are predefined?
4. **RQ4—Quality constraints:** How should safety aborts, control timing, and haptic saturation be reported alongside criterion recovery without collapsing them into a single pass/fail score?

The work makes three contributions. First, it introduces the (N_m\rightarrow C_m\rightarrow R_i\rightarrow Y_i) evidence chain, integrating event timing, window exposure, clocks, and acquisition identity. Second, it defines an *evidence-admissible estimand*: the narrowest statistical contrast that current intervention evidence permits, without treating post-assignment realized states as automatically causal. Third, it evaluates the framework through complementary retrospective and prospective studies. The first shows diagnostic value in a real archive; the second provides prospective within-system criterion validation. Neither is presented as controller-efficacy validation.

# II. Realized-Intervention Fidelity Framework

## A. Four Evidence Layers

A trial (i) assigned to mode (m) is represented as

\[
N_m\rightarrow C_m\rightarrow R_i\xrightarrow[\mathcal P_i]{}Y_i.
\]

(N_m) is documented nominal intent, including target parameters, activation guards, event order, and expected exposure. (C_m) is the behavior actually implemented in the acquisition software, including initialization and clock domains. (R_i=\{\mathcal E_i,a_i(t),\boldsymbol\theta_i^{log}(t)\}) is the trial-specific recorded intervention defined by events, activation state, and parameter trajectories. (Y_i) is an outcome measured in an explicit window. Exact acquisition lineage (mathcal P_i) establishes that (R_i) and (Y_i) belong to the same acquisition.

Three discontinuities can coexist. (N\neq C) indicates that documented intent was not implemented. (C\neq R) indicates that recorded delivery did not reproduce the behavior expected from implemented logic and recorded inputs. A mismatch between realized delivery and the outcome window indicates exposure error. These discontinuities should not be compressed into a composite score because each changes a different scientific proposition. Lineage integrity is orthogonal: it does not prove correct delivery, but without it the intervention–outcome pair cannot be evaluated reliably.

## B. Timing Error, Window Exposure, and Admissible Contrasts

For nominal and recorded activation times (t^N_{act,i}) and (t^R_{act,i}), respectively,

\[
\epsilon_i=t^R_{act,i}-t^N_{act,i}.
\]

For binary activation (a_i(t)) and outcome window (W=[t_0,t_1]),

\[
\Phi_i=\frac{1}{t_1-t_0}\int_{t_0}^{t_1}a_i(t)\,dt.
\]

(Phi_i=1), (0<\Phi_i<1), and (Phi_i=0) denote full, partial, and zero exposure. These are descriptions of delivered intervention and are not post-outcome trial-exclusion rules.

A nominal contrast can retain its label-based interpretation only when specification, implementation, and delivery support that interpretation. Otherwise, evidence permits a narrower comparison between assigned bundles or realized exposure distributions. We call this the evidence-admissible estimand. It is a statistical target and does not become causal merely because realized exposure has been reconstructed.

## C. Evidence Required Across the Study Lifecycle

Before acquisition, nominal parameters, guards, clocks, outcome windows, and independent experimental units should be frozen. During acquisition, human input, contact events, activation state, parameter trajectories, software identity, control timing, and safety events should be recorded. Before inference, (N\rightarrow C), (C\rightarrow R), and (R\xleftrightarrow{\mathcal P}Y) should be checked in sequence. A metric with no nominal target is *not applicable*; one lacking required records is *not available*. Neither can be converted into a fidelity pass.

# III. Study 1: Retrospective Diagnostic Case

## A. Platform and Archived Design

The archived platform combined a Force Dimension Omega.7 master device, an Intel RealSense D435i visual channel, supervisory control, a Franka Emika Panda robot, and a gripper. Five participants completed 180 cleaned trials in a repeated-measures structure comprising three material categories, three repeat blocks, and four configurations (A/G/E/F). The independent human unit was the participant ((n=5)), not the 180 trials. Force was the Panda internal external-wrench estimate (`O_F_ext_hat_K`), not an independent force/torque sensor. Recorded stiffness was a software command rather than an independently verified physical closed-loop impedance.

A was the fixed reference. G contained a raw-force rule. E jointly changed vision and several commanded parameters. F bundled visual and adaptive paths. The retrospective outcome window was 0.20–1.00 s after contact, and the principal descriptive outcome was threshold-referenced excess-force impulse. Because that outcome window was not prospectively registered, human-outcome analyses were exploratory.

## B. Reconstruction

Reconstruction used nominal descriptions, acquisition code, event JSON, sample-level CSV, and summaries. The analysis examined the executable G rule, the nominal F requirement of activation 0.20 s after contact, and visual/adaptive exposure in E and F. A frozen acquisition-identity rule selected 180 analytical acquisitions from 186 archived records. Same-acquisition CSV, event, and summary identities and SHA-256 values established the intervention–outcome lineage.

# IV. Study 2: Prospective Known-Truth Criterion Study

## A. Design and Participants

The criterion study used an isolated `kfb_timing` mode on the same Omega.7–Panda platform. Vision, gripper action, and other adaptation paths were disabled; only the onset and offset of (K_{fb}=0.5\rightarrow0.7) were manipulated. F01–F20 represented 20 independent participants. Each participant had three blocks of five trials, yielding 15 planned trials per participant and a fixed analytical cohort of 300 planned trials. The frozen schedule reserved positions F01–F24, but the present analysis is restricted to completed participants F01–F20. Uncollected positions are not treated as missing human outcomes, and no confirmatory human-effect inference is made.

The task used a fixed contact pad. The nominal control rate was 200 Hz. Contact required baseline-corrected force above threshold for 0.050 s. The outcome window was 0.20–1.00 s after confirmed contact, and a trial ended 1.50 s after contact. A Panda-estimated force above 5 N caused a safety abort, and haptic-command norm was limited to 2 N.

## B. Known-Truth Conditions

The five conditions covered correct, early, late, shortened, and outcome-window-absent exposure. (epsilon) was referenced to nominal activation at 0.20 s after contact.

| Condition | Meaning | Active interval after contact (s) | Expected (epsilon) (s) | Expected (Phi) |
|---|---|---:|---:|---:|
| C0 | Correct | 0.20–1.20 | 0.00 | 1.000 |
| C1 | Early | 0.05–1.20 | −0.15 | 1.000 |
| C2 | Late | 0.50–1.20 | +0.30 | 0.625 |
| C3 | Short | 0.20–0.60 | 0.00 | 0.500 |
| C4 | Zero | 1.10–1.30 | +0.90 | 0.000 |

![Known timing and exposure targets.](analysis/figures/fig4_protocol_design.png)

**Fig. 1.** Frozen activation intervals for C0–C4. The shaded region is the 0.20–1.00-s outcome window. The manipulations provide timing and exposure truth independent of human outcomes.

## C. Independent Reconstruction, Acceptance, and Lineage

The formal analyzer did not import condition constants from the online controller. It independently read the frozen protocol JSON and oracle. The input was locked to F01–F20, with exactly 15 trials required per participant. Each of 300 logical trials required a CSV, event JSON, summary JSON, and manifest. Extra participants, missing or duplicate trials, path errors, mask mismatch, or configuration mismatch caused a fatal error. The historical same-named F01–F05 directory was outside the authoritative input root and was neither scanned nor merged.

CSV files required exact byte-hash agreement with their manifests. Event and summary JSON files reported both raw-byte and canonical-text hashes; canonicalization removed a UTF-8 byte-order mark and normalized CRLF/CR to LF without rewriting source files. All 300 CSVs matched byte-for-byte. Event and summary JSON raw bytes differed because of line-ending conversion, but canonical content matched the acquisition manifests in 300/300 files for each role. We therefore report canonical text-content agreement, not universal raw-byte agreement.

Primary endpoints were classification accuracy, absolute activation-time error, and absolute exposure error. Frozen limits were classification accuracy at least 95%; timing MAE at most 20 ms, timing P95 at most 20 ms, timing maximum at most 50 ms; and exposure MAE at most 0.02. Control-cycle timing, Omega validity, send failure, safety abort, and haptic clamping were reported separately rather than combined with primary criterion recovery.

## D. Exploratory Human Measures

Threshold-referenced excess-force impulse in the 0.20–1.00-s window was

\[
I_i=\int_{0.20}^{1.00}\max(F_i(t)-T_i,0)\,dt.
\]

Trials were averaged within participant and condition before C1–C4 minus C0 paired differences were calculated. Participant-level mean differences and 95% (t)-intervals were reported without confirmatory (p)-values. A sensitivity analysis excluded every trial with haptic-command clamping. Safety aborts were counted as safety outcomes rather than normal completed outcomes.

# V. Results

## A. Retrospective Diagnostic Boundaries

All 45 G trials followed the implemented raw-force rule, but 43/45 activated before recorded contact and therefore did not represent a pure post-contact force intervention. F did not activate before contact, but only 3/45 trials implemented the nominal +0.20-s gate. Median contact-to-activation time was +0.0533 s and median nominal timing error was −0.1467 s. E visual exposure comprised 39 full, two partial, and four zero-exposure trials; F joint exposure comprised 35 full, seven partial, and three zero-exposure trials.

A/G/E/F could therefore not be interpreted as a clean 2×2 factorial design. E–A denoted a bundled E assignment with heterogeneous visual exposure relative to A; G–A did not identify an isolated post-contact force effect; F–E did not identify a correctly timed +0.20-s incremental mechanism; and F–G did not identify a vision-by-force interaction. The retrospective contribution was to define the narrowest interpretation supported by the archive, not to restore the original hypothesis by deleting deviating trials.

## B. Prospective Criterion Recovery

Of 300 planned trials, 294 completed and were fidelity-evaluable; six ended through the safety abort. All 294 evaluable trials were assigned to the correct known-truth condition.

| Condition | Evaluable/planned | Accuracy | Target onset (s) | Participant-mean onset [95% CI] (s) | Timing MAE (ms) | Target (Phi) | Participant-mean (Phi) [95% CI] | (Phi) MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| C0 | 60/60 | 100% | 0.200 | 0.20291 [0.20235, 0.20347] | 2.932 | 1.000 | 0.99635 [0.99565, 0.99704] | 0.003653 |
| C1 | 59/60 | 100% | 0.050 | 0.05109 [0.05101, 0.05117] | 1.095 | 1.000 | 1.00000 [1.00000, 1.00000] | 0.000000 |
| C2 | 58/60 | 100% | 0.500 | 0.50251 [0.50211, 0.50291] | 2.528 | 0.625 | 0.62186 [0.62136, 0.62236] | 0.003160 |
| C3 | 60/60 | 100% | 0.200 | 0.20282 [0.20239, 0.20324] | 2.826 | 0.500 | 0.49977 [0.49906, 0.50048] | 0.002100 |
| C4 | 57/60 | 100% | 1.100 | 1.10248 [1.10206, 1.10289] | 2.513 | 0.000 | 0.00000 [0.00000, 0.00000] | 0.000000 |

Overall absolute onset error had MAE 2.381 ms, P95 4.957 ms, and maximum 5.408 ms. Absolute exposure error had MAE 0.001798, P95 0.005996, and maximum 0.006760. Classification and all five error checks met the frozen limits.

![Recovery against known truth.](analysis/figures/fig5_fidelity_recovery.png)

**Fig. 2.** Recovered activation time and outcome-window exposure in 294 completed trials. Blue points represent trials, red points are means, and black lines are frozen truths. The figure evaluates criterion recovery, not human effects.

## C. Quality, Safety, and Saturation

Safety aborts were distributed as C0: 0, C1: 1, C2: 2, C3: 0, and C4: 3. Completed counts were 60, 59, 58, 60, and 57. Every completed trial had outcome-window Omega validity of at least 99%. No completed trial had control-cycle P99 above 20 ms or maximum above 50 ms, and no haptic-send failure occurred.

At least one haptic-command clamp occurred in 71/300 planned trials and in 65/294 completed trials. Completed clamped counts for C0–C4 were 15, 15, 15, 9, and 11. Clamping did not change activation-state-derived (epsilon) or (Phi), but it showed that a commanded (K_{fb}) change did not guarantee proportional physical haptic dose. It therefore constrains human-outcome interpretation rather than invalidating timing–exposure criterion recovery.

![Trial disposition and haptic clamping.](analysis/figures/fig6_flow_and_quality.png)

**Fig. 3.** Left: completed trials and safety aborts among 60 planned trials per condition. Right: completed trials containing at least one 2-N haptic-command clamp.

## D. Exploratory Human Outcomes

Participant-level mean excess-force impulses for C0–C4 were 0.6124, 0.6621, 0.5701, 0.5855, and 0.5076 N·s. Paired differences relative to C0 were:

| Contrast | Participants | Mean difference (N·s) | 95% CI | Negative/positive participants |
|---|---:|---:|---:|---:|
| C1−C0 | 20 | +0.0498 | [−0.0577, +0.1572] | 11/9 |
| C2−C0 | 20 | −0.0423 | [−0.1551, +0.0705] | 9/11 |
| C3−C0 | 20 | −0.0269 | [−0.1763, +0.1225] | 11/9 |
| C4−C0 | 20 | −0.1048 | [−0.2092, −0.0004] | 15/5 |

C1, C2, and C3 intervals crossed zero and participant directions were inconsistent. The descriptive C4 interval ended slightly below zero, but C4 was not a confirmatory human-effect hypothesis, and the analysis involved multiple contrasts, condition-imbalanced safety aborts, haptic saturation, and an internally estimated force source. It is therefore not presented as confirmatory efficacy evidence. The unclamped-trial analysis is provided as a supplementary sensitivity analysis and is not selected according to favorability.

# VI. Discussion

## A. Distinct Roles of the Two Studies

The retrospective and prospective studies provide different evidence. The retrospective case demonstrates that the framework is not merely an abstract checklist: it detects specification, implementation, and delivery discontinuities in a real asynchronous system and changes what A/G/E/F comparisons can mean. The prospective study demonstrates that (epsilon), (Phi), and condition identity can be recovered accurately when truth is known. Its success does not depend on favorable human outcomes from the five-participant archive and directly addresses the concern that the framework is only a post hoc narrative applied to a failed experiment.

The prospective study does not rehabilitate the original controller effects. Interpretation of the archived A/G/E/F effects remains constrained by their delivery deviations. The new study validates the measurement and reasoning framework, not the efficacy of the original controllers. Maintaining this boundary is the principal value of the two-stage design.

## B. Implications for Human–Machine Evaluation

An experimental condition in an asynchronous human–machine system should be treated as a dynamic object requiring trial-specific verification rather than as a static label. A minimum record should include a shared monotonic timebase, task and contact events, activation state, commanded parameter trajectories, human-input validity, control-cycle timing, and exact acquisition identity. Reports should separate primary intervention criteria, system-quality constraints, and human outcomes so that a global pass rate does not conceal failure at one evidence layer.

The study also separates implementation consistency from physical dose. Activation timing and window exposure were reconstructed accurately in all 294 completed trials, while 65 contained haptic-command clamping. The former supports the timing–exposure criteria; the latter limits interpretation of feedback amplitude. A study targeting physical dose or human effect should add independent force/torque measurement and end-to-end haptic-output calibration. A study targeting implementation fidelity must state explicitly that it validates commands and records.

## C. Validity Boundaries

The prospective experiment is a single-platform, single-software-ecosystem, within-team criterion study. The offline analyzer did not import online condition constants, but the controller, logging architecture, and apparatus can still share common-mode errors. We therefore do not claim external validation. Further validation should reproduce known-truth recovery on a second teleoperation system, a distinct task, or through an independent team.

The fixed pad and 1.5-s hold minimized object and task variability to create a controlled validation environment. They validate the framework's measurement chain rather than effects in complex grasping, transport, perception, or long-latency tasks. The 20-participant cohort provides repeated participant-level implementation evidence, but the schedule reserved 24 positions while 20 were analyzed. Because no confirmatory human-effect inference is made, this difference is reported transparently rather than justified through a post hoc power calculation.

Ethics, demographics, training, and consent information must be completed from contemporaneous institutional records. Acquisition files cannot substitute for research-governance evidence, and the manuscript must not be submitted without those records.

# VII. Conclusion

We proposed and evaluated realized-intervention fidelity using two evidence stages. The five-participant retrospective case showed how discontinuities among nominal semantics, executable logic, and delivered intervention narrow scientific interpretation. The 20-participant prospective known-truth study achieved 100% classification in 294 completed trials, timing-error P95 below 5 ms, and exposure-error P95 below 0.006, supporting within-system criterion validity of (epsilon) and (Phi). Safety aborts, haptic saturation, and the internally estimated force source remained visible rather than being obscured by primary criterion success. Realized-intervention fidelity is therefore a necessary evidence layer between condition assignment and defensible inference in asynchronous human–machine experiments. Its validation does not by itself establish controller efficacy, causal human effects, or cross-system generalizability.

# References

[1] B. Hannaford, “A design framework for teleoperators with kinesthetic feedback,” *IEEE Trans. Robot. Autom.*, vol. 5, no. 4, pp. 426–434, 1989.

[2] D. A. Lawrence, “Stability and transparency in bilateral teleoperation,” *IEEE Trans. Robot. Autom.*, vol. 9, no. 5, pp. 624–637, 1993.

[3] P. F. Hokayem and M. W. Spong, “Bilateral teleoperation: An historical survey,” *Automatica*, vol. 42, no. 12, pp. 2035–2057, 2006.

[4] C. Passenberg, A. Peer, and M. Buss, “A survey of environment-, operator-, and task-adapted controllers for teleoperation systems,” *Mechatronics*, vol. 20, no. 7, pp. 787–801, 2010.

[5] K. Huang, D. Chitrakar, F. Rydén, and H. J. Chizeck, “Evaluation of haptic guidance virtual fixtures and 3D visualization methods in telemanipulation—A user study,” *Intell. Service Robot.*, vol. 12, pp. 289–301, 2019.

[6] D. Rakita, B. Mutlu, and M. Gleicher, “Effects of onset latency and robot speed delays on mimicry-control teleoperation,” in *Proc. ACM/IEEE HRI*, 2020.

[7] J. Louca, K. Eder, J. Vrublevskis, and A. Tzemanaki, “Impact of haptic feedback in high latency teleoperation for space applications,” *ACM Trans. Human-Robot Interact.*, vol. 13, no. 2, Art. 16, 2024.

[8] N. Hogan, “Impedance control: An approach to manipulation: Part I—Theory,” *J. Dyn. Syst., Meas., Control*, vol. 107, no. 1, pp. 1–7, 1985.

[9] D. S. Walker, R. P. Wilson, and G. Niemeyer, “User-controlled variable impedance teleoperation,” in *Proc. IEEE ICRA*, 2010.

[10] J. Buchli, F. Stulp, E. Theodorou, and S. Schaal, “Learning variable impedance control,” *Int. J. Robot. Res.*, vol. 30, no. 7, pp. 820–833, 2011.

[11] A. Ajoudani, N. G. Tsagarakis, and A. Bicchi, “Tele-impedance: Teleoperation with impedance regulation using a body–machine interface,” *Int. J. Robot. Res.*, vol. 31, no. 13, pp. 1642–1656, 2012.

[12] L. Peternel, T. Petrič, and J. Babič, “Robotic assembly solution by human-in-the-loop teaching method based on real-time stiffness modulation,” *Auton. Robots*, vol. 42, pp. 1–17, 2018.

[13] F. J. Abu-Dakka, L. Rozo, and D. G. Caldwell, “Force-based variable impedance learning for robotic manipulation,” *Robot. Auton. Syst.*, vol. 109, pp. 156–167, 2018.

[14] F. J. Abu-Dakka and M. Saveriano, “Variable impedance control and learning—A review,” *Front. Robot. AI*, vol. 7, 590681, 2020.

[15] Y. Michel, R. Rahal, C. Pacchierotti, P. Robuffo Giordano, and D. Lee, “Bilateral teleoperation with adaptive impedance control for contact tasks,” *IEEE Robot. Autom. Lett.*, vol. 6, no. 3, pp. 5429–5436, 2021.

[16] L. Peternel and A. Ajoudani, “After a decade of teleimpedance: A survey,” *IEEE Trans. Human-Mach. Syst.*, vol. 53, no. 2, pp. 401–416, 2023.

[17] Y. Michel, Z. Li, and D. Lee, “A learning-based shared control approach for contact tasks,” *IEEE Robot. Autom. Lett.*, vol. 8, no. 12, pp. 8002–8009, 2023.

[18] I. M. L. C. Vogels, “Detection of temporal delays in visual-haptic interfaces,” *Human Factors*, vol. 46, no. 1, pp. 118–134, 2004.

[19] F. Bonsignorio and A. P. del Pobil, “Toward replicable and measurable robotics research,” *IEEE Robot. Autom. Mag.*, vol. 22, no. 3, pp. 32–35, 2015.

[20] F. Bonsignorio, “A new kind of article for reproducible research in intelligent robotics,” *IEEE Robot. Autom. Mag.*, vol. 24, no. 3, pp. 178–182, 2017.

[21] H. Gunes *et al.*, “Reproducibility in human-robot interaction: Furthering the science of HRI,” *Current Robot. Rep.*, vol. 3, no. 4, pp. 281–292, 2022.

[22] R. Aldana-López, R. Aragüés, and C. Sagüés, “Latency vs precision: Stability preserving perception scheduling,” *Automatica*, vol. 155, 111123, 2023.

[23] S. Bagchi *et al.*, “Towards improved replicability of human studies in human-robot interaction,” in *Companion Proc. ACM/IEEE HRI*, 2023.

[24] S. Marchesi *et al.*, “Tools and methods to study and replicate experiments addressing human social cognition in interactive scenarios,” *Behav. Res. Methods*, vol. 56, no. 7, pp. 7543–7560, 2024.

[25] J. Huang *et al.*, “ROSRV: Runtime verification for robots,” in *Runtime Verification*, pp. 247–254, 2014.

[26] C. Carroll, M. Patterson, S. Wood, A. Booth, J. Rick, and S. Balain, “A conceptual framework for implementation fidelity,” *Implementation Sci.*, vol. 2, 40, 2007.

[27] I. Lundberg, R. Johnson, and B. M. Stewart, “What is your estimand? Defining the target quantity connects statistical evidence to theory,” *Am. Sociol. Rev.*, vol. 86, no. 3, pp. 532–565, 2021.
