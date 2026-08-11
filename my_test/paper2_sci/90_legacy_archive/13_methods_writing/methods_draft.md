# 2. Methods

> Drafting note: statements marked `[NEEDS VERIFICATION]` are not supported by the archived code, logs, or clean-analysis lineage currently available. They must be verified from contemporaneous records before submission or removed. This draft describes the experiment that was actually recorded and does not treat the four configurations as a factorial 2 × 2 design.

## 2.1 Teleoperation system and data acquisition

**M2.1-P1 — Robotic and haptic system.** The experimental platform comprised a Franka Emika Panda robot controlled through the `panda_py`/`libfranka` interface, a Franka Hand gripper, and a Force Dimension Omega.7 haptic device used as the master interface. Incremental translational motion of the Omega.7 was scaled by a factor of 3 and sign-mapped to the Cartesian position target of the Panda; the robot end-effector orientation was held at its initialized value during each trial. Cartesian impedance commands specified translational stiffness, rotational stiffness, and damping ratio. Gripper commands were updated at a nominal rate of 30 Hz, with a commanded speed of 0.05 m/s in all analyzed configurations. The control computer, operating-system version, processor, graphics hardware, and exact library versions were not preserved in the experimental metadata `[NEEDS VERIFICATION]`.

**M2.1-P2 — Force estimation and haptic feedback.** The force signal used for feedback, event detection, and outcome calculation was obtained from the Panda state variable `O_F_ext_hat_K`, i.e., the robot's internal estimate of the external Cartesian wrench, rather than from a separately logged external force/torque sensor. Each wrench component was exponentially filtered according to \(\hat{w}_k=0.3w_k+0.7\hat{w}_{k-1}\). Analyses used the magnitude of the filtered translational components, \(F_k=\sqrt{F_{x,k}^2+F_{y,k}^2+F_{z,k}^2}\). Component-wise haptic force feedback to the Omega.7 applied the configuration-specific feedback gain after a configuration-specific haptic deadband. The absence of an independently acquired external force/torque channel is established for the archived acquisition path; whether any unlogged external sensor was physically mounted during data collection remains `[NEEDS VERIFICATION]`.

**M2.1-P3 — Vision and control processes.** Vision-enabled configurations used an Intel RealSense D435i. The audited acquisition code enabled a 424 × 240 BGR color stream at a nominal 15 frames/s; depth acquisition was not enabled. A `yolo11n.pt` model was executed in a separate process with a confidence threshold of 0.25. The detected class was mapped through the archived physics-mapping module to one of four semantic profiles: soft, medium, hard, or unknown. The first valid mapped detection locked the profile for the remainder of the trial. The supervisory loop requested a nominal frequency of 200 Hz and logged one time-series row per loop iteration. Because the measured `control_dt` was irregular, all time-domain analyses used recorded timestamps rather than assuming a constant 200-Hz sampling rate.

**M2.1-P4 — Recorded channels.** Each archived acquisition produced a raw CSV time series, an event JSON file, and a summary JSON file. The CSV included monotonic relative time, experimental phase and event state, master-device position and gripper input, commanded and measured robot position, filtered force and torque components, force magnitude, commanded impedance and feedback parameters, gripper commands and measured state, vision outputs and lock state, adaptation flags and targets, baseline statistics, contact threshold, and realized control-cycle duration. The event JSON recorded system, task, baseline, contact, grasp, release, completion, and incomplete-trial events when available.

## 2.2 Participants, task, and repeated-measures structure

**M2.2-P1 — Participants.** Five participants, labeled P01–P05 in the clean data, completed the archived experiment. Participant age, sex or gender, handedness, prior teleoperation experience, recruitment procedure, compensation, and training protocol were not recoverable from the supplied data lineage `[NEEDS VERIFICATION]`. The approving ethics body, approval identifier, and informed-consent procedure also require verification from the original study records `[NEEDS VERIFICATION]`. The participant, rather than the trial or participant-by-material block, was treated as the independent human experimental unit.

**M2.2-P2 — Task and event sequence.** The logged protocol represented a teleoperated manipulation sequence comprising approach, threshold-defined initial contact, grasp, transport, release, and task completion. Baseline acquisition occurred during a preparation phase. `task_start` was issued automatically after the force baseline was ready and no controller transition was active; it therefore denoted system readiness rather than the first detected human movement. Contact, grasp, release, and completion were subsequently reconstructed from the event log. The task ended after release, a return to the IDLE gripper state, a measured or last-commanded gripper width of at least 0.075 m, and a 0.50-s settling period. The precise object geometry, start and destination locations, placement tolerances, participant instructions, practice procedure, and rest schedule were not encoded in the archived lineage `[NEEDS VERIFICATION]`.

**M2.2-P3 — Experimental structure.** The clean dataset contained 180 analyzed trials in a within-participant repeated-measures structure: 5 participants × 3 material categories (soft, medium, and hard) × 3 repeated blocks × 4 recorded configurations (A, G, E, and F). Thus, each participant contributed 36 trials, including nine trials per configuration, and each configuration contained 45 trials in total. A matched block was defined by participant, material category, and repeated-block index and contained one trial from each configuration, yielding 45 matched blocks. The clean manifest preserved material category but not a unique object or physical-instance identifier. Consequently, material-category comparisons cannot be interpreted as controlled comparisons of documented physical specimens. Acquisition timestamps showed that configuration order varied, but no prospective randomization or counterbalancing schedule was recovered `[NEEDS VERIFICATION]`.

## 2.3 Nominal experimental configurations

**M2.3-P1 — Configuration definitions.** The four configurations are denoted by their archived labels but are described as bundled supervisory configurations rather than as isolated experimental factors. Their nominal initialization and update rules are summarized in Table I. Configuration A was a fixed high-impedance baseline. Configuration G used no vision and applied force-dependent impedance adaptation. Configuration E used vision to select a bundled material-specific parameter preset. Configuration F used the same vision-dependent preset mechanism as E and additionally contained a nominal force-dependent stiffness-refinement rule. These labels describe the acquisition code's intended roles; realized activation times and logged parameter trajectories were audited separately as described in Section 2.4.

**Table I. Nominal definitions of the four archived configurations.**

| Configuration | Before vision lock or adaptation | Vision-dependent preset | Nominal force-dependent rule | Other common settings |
|---|---|---|---|---|
| A | \(K_t=200\) N/m; \(K_r=13\) N·m/rad; \(\zeta=1.2\); haptic gain \(K_{fb}=0.5\); haptic deadband = 0.3 N | None | None | Scale = 3; gripper speed = 0.05 m/s; gripper force = 20 N |
| G | Base \(K_t=200\) N/m; \(K_r/K_t=0.065\); \(\zeta=1.2\); \(K_{fb}=0.5\); haptic deadband = 0.3 N | None | Raw-force adaptation with 1-N adaptation deadband, 5-N saturation, reduction coefficient 0.5, smoothing factor 0.3, and nominal 0.05-s update interval; no contact gate | Scale = 3; gripper speed = 0.05 m/s; gripper force = 20 N |
| E | Standard preset before lock: \(K_t=150\) N/m; \(K_r=10\) N·m/rad; \(\zeta=1.0\); \(K_{fb}=0.5\); haptic deadband = 0.3 N; gripper force = 20 N | Soft: 50, 5, 0.8, 0.2, 0.3, 8; medium: 120, 8, 1.0, 0.5, 0.4, 15; hard: 200, 13, 1.2, 0.7, 0.5, 20 | None | Preset tuple order: \(K_t\), \(K_r\), \(\zeta\), \(K_{fb}\), haptic deadband, gripper force; scale = 3; speed = 0.05 m/s |
| F | Same standard preset as E before lock | Same soft, medium, hard, and unknown-fallback mapping as E | Class-specific raw-force stiffness refinement, nominally permitted 0.20 s after contact and updated at nominal 0.05-s intervals | Scale = 3; gripper speed = 0.05 m/s; vision preset also set damping, haptic, and gripper parameters |

**M2.3-P2 — Vision-dependent preset transition.** In E and F, the controller began with the standard preset and, after the first valid semantic lock, transitioned over 30 nominal 0.01-s steps (approximately 0.30 s) to the selected profile. The soft, medium, and hard tuples in Table I jointly changed translational stiffness, rotational stiffness, damping ratio, haptic feedback gain, haptic deadband, and commanded gripper force. The unknown label used the medium preset as the fallback for the vision-selected parameters. E and F therefore cannot be interpreted as interventions on translational stiffness alone.

**M2.3-P3 — G adaptation rule.** For G, the raw filtered force magnitude—not a threshold-referenced signal—was converted to the normalized adaptation ratio

\[
r_G(F)=\operatorname{clip}\left(\frac{F-1}{5-1},0,1\right),
\]

and the target translational stiffness was

\[
K_{t,G}^{*}=200\,[1-0.5r_G(F)].
\]

The commanded translational stiffness moved 0.3 of the remaining distance toward this target at each nominal 0.05-s update, and rotational stiffness was maintained at \(0.065K_{t,G}\). The update function did not require baseline completion or logged contact. Consequently, the archived label “force-only” denotes the code path and must not be read as evidence that adaptation occurred only after contact.

**M2.3-P4 — F refinement rule.** For F, force refinement was evaluated only after a vision profile had locked, its transition had completed, and a contact event existed. Within semantic class \(c\), raw filtered force was converted to

\[
r_F(F,c)=\operatorname{clip}\left(\frac{F-F_{db,c}}{F_{sat,c}-F_{db,c}},0,1\right),
\]

with stiffness target

\[
K_{t,F}^{*}=\operatorname{clip}\{K_{t,vision,c}[1+g_c r_F(F,c)],K_{min,c},K_{max,c}\}.
\]

The parameter sets \((g_c,F_{db,c},F_{sat,c},s_c,K_{min,c},K_{max,c})\) were soft: (−0.25, 0.3 N, 2.5 N, 0.40, 30 N/m, 90 N/m); medium: (−0.35, 0.8 N, 6.0 N, 0.25, 85 N/m, 130 N/m); hard: (−0.15, 1.2 N, 8.0 N, 0.20, 140 N/m, 170 N/m); and unknown: (−0.10, 1.0 N, 8.0 N, 0.25, 60 N/m, 135 N/m). Here, \(s_c\) was the smoothing factor applied to translational and proportionally scaled rotational stiffness. Although the source code specified a 0.20-s post-contact gate, the realized timing did not implement that delay reliably because two clock domains were mixed (Section 2.4). F is therefore analyzed as an audited realized logged configuration, not as a correctly gated 0.20-s post-contact intervention.

## 2.4 Realized-intervention and timing reconstruction

**M2.4-P1 — Nominal, commanded, and realized intervention.** Three levels of intervention description were retained. The *nominal configuration* was the intended mode definition in the acquisition source code. The *commanded configuration* was represented by the parameter and activation fields written on each control-loop row. The *realized logged intervention* was reconstructed from those time-varying fields and event timestamps for each selected raw record. Analyses and wording concerning intervention timing were based on the realized logged intervention, not solely on mode names or source-code comments. This reconstruction does not constitute an independent measurement of the robot's physical closed-loop impedance; it establishes what the archived software commanded and logged.

**M2.4-P1a — A configuration implementation.** The archived A trials were stored under the internal mode name `default`, and the run initialization applied the `experiment_fixed_a` parameter set. Unlike the explicitly locked experimental mode names, `default` was not protected by the code's keyboard-parameter lock. However, the recorded A parameter channels at task start, contact, and across the contact-aligned stiffness trajectories showed the nominal A values without observed stiffness changes. A is therefore described as a realized fixed logged configuration while retaining the distinction between logged constancy and software-enforced locking.

**M2.4-P2 — Trial identity and joins.** Every analyzed time series was selected through the master trial manifest. The exact record identifier combined the logical trial key with its acquisition timestamp. CSV, event JSON, and summary JSON paths and SHA-256 hashes were checked as a triplet. Tables were not joined by logical trial key alone when both an initial record and a replacement record existed. This rule ensured that scalar metrics, event timing, thresholds, and raw trajectories for an analyzed trial originated from the same archived acquisition.

**M2.4-P3 — Time bases.** The protocol initialized a monotonic origin using `time.perf_counter()`. Event times and the CSV `system_time` field were stored as seconds relative to this origin and formed the analysis time base. A Unix wall-clock value from `time.time()` was retained as acquisition metadata and was also used by parts of the runtime scheduler. No ROS timestamp was present in the supplied raw schema. Clean durations were calculated only from events reconstructed on the monotonic relative timeline.

**M2.4-P4 — Timing deviations in G and F.** The G updater used raw filtered force and did not inspect baseline readiness or contact status; its activation was therefore reconstructed as the first row with `force_adapt_active>0`. For F, the main loop supplied a `time.time()` value to a delay check that converted its argument by subtracting the `time.perf_counter()` origin. This wall-clock/monotonic-clock mismatch could satisfy the nominal 0.20-s gate immediately after a contact event existed. F activation was therefore reconstructed as the first row with `fusion_active>0`, without assuming correct enforcement of the nominal delay. Counts and distributions of realized activation timing are reported in Results.

**M2.4-P5 — Realized parameters and cycle timing.** Translational and rotational stiffness, damping ratio, haptic feedback gain, haptic deadband, motion scale, gripper speed and force, vision status, adaptation status, and update targets were extracted from the selected raw CSV at task start, contact, and throughout each trial. Per-loop `control_dt` was summarized by its median, upper quantiles, maximum, and long-cycle fractions. Interpolation of contact-aligned trajectories used logged time and did not replace these realized intervals with the nominal controller period.

## 2.5 Event detection and outcome definitions

**M2.5-P1 — Baseline and contact detection.** During PREP, force baseline acquisition continued for at least 1.0 s and at least 50 samples. For trial \(i\), the software computed the mean \(\mu_{0,i}\) and population standard deviation \(\sigma_{0,i}\) of force magnitude and set the contact threshold to

\[
T_i=\max(1.0\ \mathrm{N},\mu_{0,i}+3\sigma_{0,i}).
\]

A contact candidate began when force magnitude exceeded \(T_i\). Contact was confirmed only if the threshold remained exceeded for 0.050 s, and the recorded contact onset was assigned to the first threshold-crossing time of that confirmed interval. All 180 selected trials contained a finite logged threshold; the analysis script's fallback threshold reconstruction was therefore not used for the clean dataset.

**M2.5-P2 — Main safety-related outcome.** The main retrospectively defined safety-related outcome was the threshold-referenced excess-force impulse from 0.20 to 1.00 s after contact. For trial \(i\), threshold-referenced excess force was

\[
F_{excess,i}(t)=\max[F_i(t)-T_i,0],
\]

and the outcome was computed by trapezoidal integration,

\[
I_{excess,i}^{0.2:1.0}=\int_{0.20}^{1.00}F_{excess,i}(t_c+\tau)\,d\tau,
\]

reported in N·s. The 0.20–1.00-s window was applied consistently by the clean-analysis script but was not prospectively preregistered; it is therefore described as a retrospective analysis choice rather than a confirmatory primary endpoint.

**M2.5-P3 — Secondary scalar outcomes.** Initial peak force was the maximum uncorrected force magnitude from contact through 0.20 s after contact. Task-start-to-contact time was `contact − task_start`, and total task time was `task_end − task_start`. Because `task_start` represented system readiness rather than first human movement, task-start-to-contact time was interpreted as a pre-contact interval and not as a direct measurement of robot approach duration or operator movement speed. A trial-level software-log success flag required a completed event, a grasp-success flag, and a successful task-end flag. This variable represents completion according to the archived control and event logic, not an independently adjudicated clinical or physical success criterion.

**M2.5-P4 — Contact-aligned trajectories and activation times.** Force and commanded translational stiffness were aligned to contact. Stiffness was interpolated on a common grid from −0.50 to +1.50 s in 0.01-s increments. Trial-level vision timing was reconstructed from the `vision_lock` event and the first row with `vision_locked>0`. G force-adaptation timing was the first row with `force_adapt_active>0`, and F force-refinement timing was the first row with `fusion_active>0`. Where relevant, event times were expressed relative to both `task_start` and contact.

## 2.6 Data provenance and cleaning

**M2.6-P1 — Archived and selected records.** The archive contained 186 acquisition records representing 180 logical trial keys. Of these, 174 were unique main records. Six logical trials had an initial record dated 20260729 and a corresponding replacement record dated 20260730. The six 20260729 records were retained read-only in the archive and classified as known-error records; the six 20260730 records were selected as the main valid replacements. The replacement decision was supplied as part of the data audit, but the contemporaneous technical failure documentation for the affected acquisitions was not found `[NEEDS VERIFICATION]`.

**M2.6-P2 — Lineage checks.** All 186 archived records had a corresponding CSV/events/summary triplet, and the files selected in the master manifest were hash-checked. The clean analysis selected one record for each of the 180 logical trial keys. It then generated the master manifest, lineage audit, trial-level metrics, participant-level metrics, timing audit, statistical summary, leave-one-participant-out summary, and contact-aligned trajectory tables. Original acquisition files and source code were treated as read-only inputs; clean outputs were written to a separate analysis directory.

**M2.6-P3 — Inclusion and missingness.** The main analysis included the 180 manifest-selected records. The six superseded 20260729 records were excluded from the main analysis and retained for lineage and sensitivity purposes. No threshold fallback was required in the selected set. Apart from the manifest-based record replacement, no additional trial-level exclusion or outlier deletion was applied by the clean-analysis script. Every participant-by-configuration cell contained all nine planned trials, and no values were missing for the main threshold-referenced impulse outcome, initial peak force, task-start-to-contact time, total task time, or software-log success in the trial-level table.

## 2.7 Statistical analysis

**M2.7-P1 — Participant-level aggregation and contrasts.** Statistical inference treated the five participants as the independent units. For each scalar outcome, the nine selected trials within each participant and configuration were averaged to obtain participant-level configuration means. The clean retrospective reanalysis evaluated four contrasts: E-A, G-A, F-E, and F-G. Trial counts and the 45 participant-by-material-by-block matched sets were used to describe the repeated observations and data coverage, not as independent human sample sizes.

**M2.7-P2 — Estimates and paired tests.** For each contrast, the raw paired mean difference across participants and a two-sided 95% confidence interval were calculated. The interval used the Student-\(t\) distribution with four degrees of freedom. A two-sided paired \(t\)-test was implemented as a one-sample test of the five participant-level paired differences against zero. Because the sample was small, two complementary small-sample sensitivity analyses were also reported: an exhaustive two-sided sign-flip test over all \(2^5\) sign assignments using the absolute mean difference as the statistic, and a two-sided exact Wilcoxon signed-rank test. The analysis did not select among these tests according to which produced the smallest p-value.

**M2.7-P3 — Multiplicity and robustness.** Holm adjustment was applied across the four contrasts separately for each outcome and separately within each family of p-values. Unadjusted estimates, confidence intervals, and p-values were retained alongside adjusted inference. Leave-one-participant-out analysis repeated the paired mean and \(t\)-based confidence interval after omitting each participant in turn to assess whether a contrast was driven by a single participant. Given the five-participant sample and retrospective endpoint definition, the analyses were interpreted as exploratory rather than as a definitive confirmatory test.

**M2.7-P4 — Trajectory summaries and software.** For contact-aligned trajectories, trials were first averaged within participant at each time point and configuration. The plotted group trajectory was then the mean of the five participant trajectories, with pointwise \(t\)-based 95% confidence intervals. These bands were descriptive and were not treated as simultaneous confidence bands or as a time-resolved significance test. Data reconstruction and analysis were performed in Python using the archived clean-analysis script; the exact Python and package versions used for the reported run were not captured in the supplied provenance `[NEEDS VERIFICATION]`.
