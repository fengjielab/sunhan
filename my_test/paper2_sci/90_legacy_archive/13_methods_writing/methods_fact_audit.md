# Methods Fact Audit

## Audit scope and evidence hierarchy

This audit distinguishes acquisition-time design from logged execution. Evidence was prioritized as follows:

1. collection code at commit `09c13e0b679905f14f770d820af00841546cb4cc`;
2. raw CSV/events/summary triplets referenced by `03_clean_analysis/master_trial_manifest.csv`;
3. clean manifests, metrics, timing audits, and the reconstruction script in `03_clean_analysis/`;
4. narrative drafts only as discovery aids, never as confirmation.

Status meanings:

- **confirmed:** directly supported by code, clean data, or archived logs;
- **partially confirmed:** part of the statement is supported, but a material detail is missing or only indirectly recoverable;
- **not confirmed:** no reliable archival evidence was found.

## A. Participants

| Item | Status | Audited fact | Evidence |
|---|---|---|---|
| Participant count | confirmed | Five independent participants contributed clean data. | `participant_level_metrics.csv`; `trial_level_metrics.csv` |
| Participant identifiers | confirmed | P01, P02, P03, P04, and P05. | `participant_level_metrics.csv` |
| Sex/gender | not confirmed | No reliable demographic record was found. | Absent from clean tables, manifests, and event schema |
| Age | not confirmed | No reliable age record was found. | Absent from clean tables, manifests, and event schema |
| Dominant hand | not confirmed | No reliable record was found. | Absent from clean tables and archived event schema |
| Robotics/teleoperation experience | not confirmed | No reliable experience record was found. | Absent from clean tables and archived event schema |
| Training or familiarization | not confirmed | Existing narrative drafts mention training in other study versions, but no record tied to this five-participant dataset was found. | No training field or training log in the clean lineage |
| Ethics approval/exemption | not confirmed | No approval number, exemption letter, or archived ethics statement was found. | No source in clean lineage or acquisition logs |
| Informed consent | not confirmed | No consent form or trial-linked consent field was found. | No source in clean lineage or acquisition logs |

## B. Experimental platform

| Item | Status | Audited fact | Evidence |
|---|---|---|---|
| Robot platform | confirmed | A Franka Panda robot was controlled through `panda_py`/`libfranka` using a Cartesian impedance controller. | collection commit: `my_test/interactive_teleop.py`, initialization and controller construction |
| End effector/gripper | confirmed | A Franka Hand gripper was accessed through `libfranka.Gripper`; homing, move, grasp, stop, and release states were implemented. | collection commit: `my_test/interactive_teleop.py`, gripper initialization/state machine |
| Master device | confirmed | A Force Dimension Omega.7 supplied translational and gripper inputs and received force feedback through the DHD/DRD APIs. | collection commit: `my_test/interactive_teleop.py` |
| Vision sensor | confirmed | An Intel RealSense D435i was used; the acquisition code enabled a 424 x 240 BGR color stream at a nominal 15 frames/s. Depth was not enabled by the audited acquisition code. | collection commit: `_vision_loop()` |
| Vision model | confirmed | The acquisition code loaded a `yolo11n.pt` weights file with a confidence threshold of 0.25 in a separate process and mapped detections to soft/medium/hard/unknown profiles. | collection commit: `interactive_teleop.py`; `biaoding/vision_physics_mapper.py` |
| Control architecture | confirmed | Omega.7 increments were scaled and sign-mapped to Panda Cartesian position targets; the end-effector orientation was held at its initialized value during a trial. | collection commit: main loop, position mapping, `set_control()` |
| Nominal main-loop rate | confirmed | The code requested a 200-Hz loop and recorded one sample per loop (`TRAJECTORY_DECIMATION=1`). | collection commit: `CTRL_FREQ`, run loop, trajectory recording |
| Realized loop timing | confirmed | Per-cycle `control_dt` was logged and summarized; the clean analysis did not assume a constant realized rate. | `timing_audit.csv`; `clean_analysis.py` |
| Force/wrench source | confirmed | The recorded signal was the Franka internal estimated external wrench (`O_F_ext_hat_K`) passed through the local `ForceEstimator`, not an independent external force/torque sensor. | collection commit: `plans/force_estimator.py`; summary field `source` |
| Force filtering | confirmed | The default estimator used the built-in wrench and a first-order exponential update with alpha=0.3. | collection commit: `plans/force_estimator.py`, default constructor and `update()` |
| External six-axis force sensor | not confirmed | No external force/torque sensor acquisition path was present in the audited code or log schema. | collection code and CSV header |
| Operating system | not confirmed | Linux-like paths and APIs appear in code, but the operating system/version was not archived as experimental metadata. | No OS field in logs/summary |
| Control-computer CPU/GPU | not confirmed | Hardware specifications were not found. | No hardware inventory in clean lineage |
| Software/library versions | partially confirmed | Python packages and APIs are identifiable, and the YOLO directory name suggests a local installation, but exact runtime versions were not logged. | imports and model path; no environment lock file tied to trials |
| Communication architecture | partially confirmed | Panda communication through `panda_py/libfranka`, Omega.7 through DHD/DRD, and RealSense through `pyrealsense2` are confirmed; network/USB topology and latency instrumentation were not fully archived. | collection code |

## C. Human-in-the-loop task and experimental structure

| Item | Status | Audited fact | Evidence |
|---|---|---|---|
| Participant action | partially confirmed | Participants used Omega.7 motion and gripper inputs to command approach, contact, grasp, transport, and release phases. The exact instructed destination, placement geometry, and verbal instructions were not archived. | collection state machine and main loop; event names |
| Task start | confirmed | In the executed main loop, `task_start` was automatically marked immediately after the per-trial force baseline was ready and the initial parameter transition was no longer active. It was not defined by the first participant movement in the analyzed trials. | collection commit: run loop lines calling `set_ready()` and `start_task(..., trigger="system_ready")` |
| Approach interval | confirmed | Defined analytically as `contact_onset - task_start`. | `clean_analysis.py`; `trial_level_metrics.csv` |
| Logged contact | confirmed | Translational estimated-force magnitude had to exceed a trial-specific threshold continuously for 0.050 s; the event time was assigned to the first threshold crossing in that sustained interval. | collection commit: `experiment_protocol.py` |
| Grasp start/success | confirmed | `grasp_start` was marked on transition to GRASPING; `grasp_success` was marked on transition to HOLDING using the gripper-state success flag. | collection commit: `experiment_protocol.py`; gripper state machine |
| Task completion | confirmed | `task_end` was marked after release, return to IDLE, an open width of at least 0.075 m, and a 0.50-s settling interval. | collection commit: `experiment_protocol.py` |
| Material conditions | confirmed | The clean manifest contains soft, medium, and hard categories, with 60 clean trials per category. | `master_trial_manifest.csv`; `trial_level_metrics.csv` |
| Object identity/physical instance | not confirmed | Event JSON files did not preserve `object_id`, and the clean manifest contains material category but not a unique physical-object identifier. | archived event schema; `master_trial_manifest.csv` |
| Spatial arrangement/orientation | not confirmed | Object pose, camera pose, initial placement, and destination were not recorded in the clean lineage. | Absent from clean tables and events |
| Repeated-measures structure | confirmed | 5 participants x 3 materials x 3 repeated blocks x 4 modes = 180 clean trials. | `master_trial_manifest.csv` |
| Trials per participant | confirmed | 36 trials per participant. | `trial_level_metrics.csv` |
| Trials per mode | confirmed | 45 trials per mode. | `trial_level_metrics.csv` |
| Trials per participant x mode | confirmed | 9 trials per participant and mode. | `participant_level_metrics.csv`; manifest aggregation |
| Trials per material x mode | confirmed | 15 trials per material and mode. | `master_trial_manifest.csv` |
| Block definition | confirmed | A matched block was participant x material x repeated-block label and contained one trial from each of A/G/E/F; there were 45 such blocks. | `master_trial_manifest.csv` |
| Trial/mode randomization | not confirmed | Timestamp-derived mode order varied across blocks, but no archived randomization or counterbalancing protocol was found. | `master_trial_manifest.csv`; no randomization record |

## D. Nominal and realized mode definitions

| Item | Status | Audited fact | Evidence |
|---|---|---|---|
| A nominal definition | confirmed | Fixed-baseline configuration using the `experiment_fixed_a` preset: Kt=200 N/m, Kr=13 N*m/rad, damping ratio=1.2, haptic gain=0.5, haptic deadband=0.3 N, scale=3, gripper speed=0.05 m/s, and gripper force=20 N. | collection commit: presets and run initialization |
| A realized parameters | confirmed | Logged A values at task start and contact matched the nominal values; Kt remained 200 N/m in the contact-aligned trajectory. | raw CSVs referenced by master manifest; `contact_aligned_trajectories.csv` |
| A parameter lock | partially confirmed | A was nominally fixed and logged as fixed, but the data used controller mode `default`, for which keyboard locking was not enforced by the audited code. No logged parameter changes were observed. | collection commit; raw A parameter trajectories |
| G nominal definition | confirmed | Force-only label with Kt base=200 N/m, Kr/Kt ratio=0.065, damping ratio=1.2, adaptation deadband=1 N, saturation=5 N, alpha=0.5, smoothing=0.3, and nominal update interval=0.05 s. | collection commit: G constants and update law |
| G gating logic | confirmed | G used raw estimated-force magnitude and did not consult logged contact or baseline readiness. | collection commit: `_update_force_only_adaptive_impedance()` |
| G realized timing | confirmed | Logged activation frequently occurred during PREP and before task/contact; occurrence counts are reported in Results rather than Methods. | `timing_audit.csv`; `README.md` |
| E nominal definition | confirmed | Vision-enabled multi-parameter configuration. Before first valid vision lock it used the standard preset; the first locked semantic label selected soft/medium/hard presets that jointly changed stiffness, damping ratio, haptic gain/deadband, and gripper force. | collection commit: presets and vision-lock application |
| E realized timing | confirmed | Vision lock timing and parameter trajectories were logged; vision lock was not universally pre-contact. | `timing_audit.csv`; raw CSVs |
| F nominal definition | confirmed | Vision-enabled parameters plus a class-specific force-dependent stiffness refinement intended to begin 0.20 s after logged contact and update at nominal 0.05-s intervals. | collection commit: F constants/policy |
| F actual code timing | confirmed | The main loop passed `time.time()` to a gate that subtracted a `time.perf_counter()` origin, mixing clock domains and bypassing the intended delay after contact existed. | collection commit: main loop, fusion update, timeline code |
| F realized timing | confirmed | Activation was reconstructed from the first positive `fusion_active` row; it is not interpreted as a correctly gated 0.20-s condition. | `timing_audit.csv`; `clean_analysis.py` |
| Strict 2 x 2 interpretation | not confirmed | The four realized logged configurations do not support a clean 2 x 2 factorial interpretation because parameters were bundled and G/F timing diverged from nominal labels. | code/log/timing audit |

## E. Data acquisition and time base

| Item | Status | Audited fact | Evidence |
|---|---|---|---|
| Force/wrench channels | confirmed | Fx, Fy, Fz, Tx, Ty, Tz and translational magnitude were recorded from the filtered internal estimate. | CSV header and trajectory recorder |
| Master/robot position | confirmed | Omega.7 position, Cartesian target, and Panda end-effector position were logged. | CSV header and trajectory recorder |
| Control parameters | confirmed | Kt, Kr, damping ratio, haptic gain, haptic deadband, scale, and gripper parameters were logged per sample. | CSV header and trajectory recorder |
| Event log | confirmed | Separate JSON recorded system start/ready, task start, vision events, baseline ready, contact, grasp, release, completion, and incomplete events when present. | archived events JSON; `experiment_protocol.py` |
| Monotonic time axis | confirmed | Event and CSV `system_time` were relative to `ExperimentTimeline.start_perf` using `time.perf_counter()`. | collection commit; `timing_audit.csv` |
| Wall-clock time | confirmed | `time.time()` was retained as `started_at_unix` metadata and also used by some scheduling logic; it was not used for clean duration subtraction. | collection commit; `timing_audit.csv` |
| ROS timestamps | confirmed absent | No ROS timestamp field existed in the supplied CSV or event schema; clean audit recorded `ros_timestamp_available=0`. | `timing_audit.csv`; CSV schema |
| Vision results | confirmed | Class, semantic label, confidence, lock flag, first frame, first detection, and vision-lock events were recorded in raw logs. | CSV header and events JSON |
| Activation flags | confirmed | `force_adapt_active` identified G activation; `fusion_active` identified F activation. | raw CSV schema; `clean_analysis.py` |
| Realized sampling | confirmed | `control_dt` was recorded every logged loop; clean analysis summarized median, p95, p99, maximum, and long-cycle fractions. | `timing_audit.csv` |
| File structure | confirmed | Each archived record comprised a CSV time series, events JSON, and summary JSON. | `master_trial_manifest.csv`; `data_lineage_audit.csv` |

## F. Data cleaning and provenance

| Item | Status | Audited fact | Evidence |
|---|---|---|---|
| Archived record count | confirmed | 186 archived records representing 180 trial keys. | `master_trial_manifest.csv` |
| Unique normal records | confirmed | 174 records were `main_unique`. | `master_trial_manifest.csv` |
| Valid replacement records | confirmed | Six 20260730 records were retained as `main_valid_replacement`. | `master_trial_manifest.csv` |
| Known-error records | confirmed | Six corresponding 20260729 records were retained in the manifest as `excluded_known_error`. | `master_trial_manifest.csv` |
| Reason for replacement | partially confirmed | The record-validity decision was explicitly confirmed by the user, but a detailed failure mechanism for each erroneous acquisition was not archived in the clean tables. | `README.md`; manifest selection reason |
| Clean cohort | confirmed | 180 unique main-analysis trial keys. | `master_trial_manifest.csv`; `trial_level_metrics.csv` |
| Join rule | confirmed | Raw time series, events, and summary were joined only by exact `record_id = trial_key|timestamp`; joining duplicated records by trial key alone was prohibited. | `README.md`; `clean_analysis.py` |
| File integrity | confirmed | Existence and SHA-256 hash checks passed for all 186 file triplets. | `data_lineage_audit.csv` |

## G. Contact and outcome definitions

| Item | Status | Audited fact | Evidence |
|---|---|---|---|
| Baseline | confirmed | During PREP, estimated-force magnitude was accumulated for at least 1.0 s and at least 50 samples; mean and population SD were logged. | collection commit: `experiment_protocol.py` |
| Contact threshold | confirmed | Trial-specific threshold T=max(1 N, baseline mean + 3 baseline SD). All 180 clean trials contained a finite logged threshold. | `experiment_protocol.py`; `trial_level_metrics.csv` |
| Contact onset | confirmed | First threshold crossing that remained above threshold for at least 0.050 s; t=0 for contact-aligned analysis. | `experiment_protocol.py`; `clean_analysis.py` |
| Threshold-referenced excess-force impulse | confirmed | Integral from 0.2 to 1.0 s after logged contact of max(Fext magnitude - T, 0), using trapezoidal integration; unit N*s. No additional sample-wise subtraction of the baseline mean was present. | `clean_analysis.py` |
| Endpoint status | partially confirmed | The 0.2-1.0-s window was the main outcome of the clean retrospective reanalysis; no evidence showed that it was preregistered before data collection. | `README.md`; analysis history |
| Initial peak force | confirmed | Maximum estimated translational-force magnitude from 0 to 0.2 s after logged contact; not threshold-referenced in the reported field. | `clean_analysis.py` |
| Task-start-to-contact time | confirmed | `contact_onset - task_start`; this is a logged pre-contact interval because `task_start` marks system readiness, not first human movement. The internal clean-data field retains the legacy name `approach_time_s`. | `clean_analysis.py`; `experiment_protocol.py` |
| Total task time | confirmed | `task_end - task_start`. | `clean_analysis.py` |
| Software-log success | confirmed | Completed event AND grasp-success flag AND task-end success flag. | `clean_analysis.py` |
| Stiffness trajectory | confirmed | Logged translational stiffness interpolated from -0.50 to +1.50 s around contact at 0.01-s spacing. | `clean_analysis.py`; contact-aligned files |
| Vision timing | confirmed | Event `vision_lock` and first logged `vision_locked>0` row were reconstructed on the monotonic timeline. | `timing_audit.csv`; `clean_analysis.py` |
| Force-adaptation timing | confirmed | First `force_adapt_active>0` for G and first `fusion_active>0` for F. | `clean_analysis.py` |

## H. Statistical analysis

| Item | Status | Audited fact | Evidence |
|---|---|---|---|
| Participant aggregation | confirmed | Nine trials were averaged within participant and mode before inference. | `clean_analysis.py`; `participant_level_metrics.csv` |
| Paired contrasts | confirmed | E-A, G-A, F-E, and F-G. | `clean_analysis.py`; `statistics_summary.csv` |
| Paired t-test | confirmed | Implemented as a two-sided one-sample t-test of participant paired differences against zero, with t-based 95% CI. | `clean_analysis.py` |
| Exact sign-flip | confirmed | Exhaustive two-sided enumeration of all sign assignments to the participant differences, using absolute mean difference. | `clean_analysis.py` |
| Exact Wilcoxon | confirmed | Two-sided exact Wilcoxon signed-rank test. | `clean_analysis.py` |
| Holm correction | confirmed | Applied across the four contrasts separately within each metric and separately for each p-value family. | `clean_analysis.py` |
| LOPO | confirmed | Each participant was omitted in turn and the mean difference and t-based CI were recomputed. | `clean_analysis.py`; `leave_one_participant_out.csv` |
| Contact-aligned trajectories | confirmed | Trials were averaged within participant first, then summarized across participants with t-based CIs. | `clean_analysis.py`; `contact_aligned_summary.csv` |
| Trial-level trajectory inference | confirmed absent | Functional trajectories were descriptive and were not subjected to trial-level significance testing in the clean analysis. | `README.md`; `clean_analysis.py` |
