# Confirmatory Experiment Design

Status: design draft for approval. No collection or analysis code is changed by this document.

## 1. Scientific questions

### Primary Research Question

For matched physical objects and participants, does a vision-enabled, pre-contact translational-stiffness configuration reduce baseline-corrected early contact-force exposure compared with a fixed-stiffness configuration, when all non-stiffness controller, gripper, timing, contact-detection, and software-pipeline settings are held constant?

### Secondary Research Question 1

Is any reduction in early force exposure accompanied by increased approach time or total task time?

### Secondary Research Question 2

Is the A–E effect direction reasonably consistent across pre-specified material strata and physical objects?

The incremental benefit of contact-triggered force refinement is not a confirmatory question in this experiment. It may be studied later after a clean, shared refinement law passes engineering acceptance.

## 2. Experimental-mode decision

### Recommended minimal confirmatory experiment

- A: fixed translational stiffness.
- E: vision-selected pre-contact translational stiffness.
- Both modes run the same vision pipeline in the background. In A, the result is logged but cannot change the controller. This controls camera, inference, CPU, USB, and waiting-time effects.
- Task motion cannot begin until vision has locked, the intended stiffness command has been applied, and the realized value has settled.
- No post-contact online stiffness change is allowed in either mode.

### Optional clean 2 × 2 mechanism experiment

Factors:

- Vision mapping: OFF/ON.
- Contact-triggered force refinement: OFF/ON.

Cells:

- A00: fixed base stiffness; refinement OFF.
- G01*: fixed base stiffness; refinement ON after confirmed contact.
- E10: vision-selected base stiffness; refinement OFF.
- F11*: vision-selected base stiffness; the identical refinement law ON after confirmed contact.

The asterisks distinguish the proposed G/F cells from the historical implementations. Historical G and F cannot be reused because they have different update laws, gates, parameters, and timing behavior.

### Comparison

| Criterion | Minimal A/E | Clean 2 × 2 |
|---|---|---|
| Scientific value | Direct independent confirmation of the strongest pilot finding | Can estimate vision, refinement, and interaction mechanisms |
| Workload | 18 measured trials/participant with the proposed 9-object design | 36 measured trials/participant for the same objects |
| Statistical efficiency | High for the primary E–A contrast | Lower; interaction requires separate power planning |
| Interpretability | Very high | High only after a full controller refactor |
| Publication value | High if independently pre-registered and replicated | Potentially high, but only if implementation fidelity is demonstrated |
| Implementation risk | Low to moderate | High |

Recommendation: run the minimal A/E experiment as the next confirmatory study. Treat force refinement as a later mechanism study rather than expanding this experiment to rescue F–E.

## 3. Common frozen controller settings

Candidate values to be frozen before recruitment, subject only to the engineering acceptance test:

- Initial and fixed translational stiffness, `K_fixed`: 200 N/m.
- Vision map: soft 50 N/m; medium 120 N/m; hard 200 N/m; unknown fallback 200 N/m.
- Rotational stiffness: 10 Nm/rad in every mode and material.
- Damping rule: constant damping ratio `zeta=1.0`, using the same matrix-construction formula in every mode. If the implementation derives physical damping from stiffness, that formula is identical across cells.
- Haptic feedback gain: 0.5 in every mode.
- Haptic feedback deadband: 0.3 N in every mode; this is not the contact-detector threshold.
- Position scale: 3.0 in every mode.
- Gripper speed: 0.05 m/s in every mode.
- Gripper force: common candidate 10 N in every mode; the selected object set must be graspable and safe at this common value.
- Same controller initialization, transition duration, contact detector, task state machine, logger, manifest builder, and file schema.

These numerical values are not to be tuned using participant outcome data. If an engineering value fails acceptance, change it before recruitment, document the reason, rerun the complete acceptance suite, and freeze the new value.

## 4. Exact realized-intervention definition

### A — fixed baseline

1. At controller initialization: `K_trans=200`, `K_rot=10`, `zeta=1.0`.
2. Before vision lock: parameters remain at the common initialization values.
3. After vision lock: visual label/confidence are logged in shadow mode; no controller parameter changes.
4. Before contact: `K_trans=200`; no online update permitted.
5. After contact: `K_trans=200`; no online update permitted.
6. Force-refinement trigger: not applicable and hard-disabled.
7. Earliest force-refinement time: not applicable.
8. Stiffness update rule: fixed.
9. Damping update rule: common `zeta=1.0` rule; no mode-specific branch.
10. Gripper: common force/speed/width settings.

### E — vision-enabled pre-contact configuration

1. At controller initialization: the same `K_trans=200`, `K_rot=10`, `zeta=1.0`.
2. Before vision lock: parameters remain identical to A.
3. After the first valid vision lock: set only `K_trans` to the frozen mapping; all other parameters remain common. Unknown uses the pre-registered 200 N/m fallback and is not excluded.
4. Before contact: mapped `K_trans` must have settled for at least 0.20 s and be within the acceptance tolerance before task start.
5. After contact: hold the mapped value; no online update permitted.
6. Force-refinement trigger: not applicable and hard-disabled.
7. Earliest force-refinement time: not applicable.
8. Stiffness update rule: one pre-task transition from 200 N/m to the mapped target, then fixed.
9. Damping update rule: the same `zeta=1.0` construction used in A.
10. Gripper: identical to A.

### Optional G01* and F11* definitions

- Their task-start and pre-contact base stiffness must equal their corresponding OFF cell: G01*=A00 and F11*=E10.
- Refinement is prohibited during PREP, READY, and APPROACH.
- Only a `contact_confirmed` event can arm refinement.
- No arbitrary 0.20 s delay is added. First update occurs on the next eligible control cycle after confirmation.
- G01* and F11* use the exact same relative update law and parameter set.
- Rotational stiffness, damping rule, gripper, feedback gain, haptic deadband, logging, and timing remain common.

Every trial logs intended, commanded, and measured/realized parameters. A trial cannot be called A/E/G*/F* solely from a command-line label; its realized-intervention record must satisfy the corresponding rules.

## 5. Unified clock design

Use one monotonic experiment clock for all durations and ordering:

- Acquire `t0_mono_ns = time.perf_counter_ns()` once when the trial object is constructed.
- Store every event and every parameter update as integer `t_mono_ns - t0_mono_ns`.
- `time.time_ns()` may be stored once as wall-clock metadata only. It is never used in a gate, duration, timeout, or cross-event comparison.
- If ROS is later used, retain the ROS timestamp in a separate field and estimate an explicit clock transform to the monotonic experiment clock. Never subtract ROS time directly from Python monotonic time.
- Control-loop scheduling, contact confirmation, transition settling, and optional refinement all use the same monotonic source.

Required events:

- `trial_initialized`
- `vision_start`
- `vision_lock`
- `vision_target_commanded`
- `vision_target_settled`
- `task_start`
- `approach_start`
- `contact_candidate_start`
- `contact_confirmed`
- `force_refinement_enabled`
- `force_refinement_first_update`
- `grasp_start`
- `task_end`

Every parameter-update row includes `trial_id`, monotonic timestamp, old value, target value, commanded value, realized value, update source, and enabling event ID.

## 6. Contact detector

### Baseline acquisition

- Acquire immediately before each measured trial with the robot stationary, gripper in the common start state, and no environmental contact.
- Duration: 2.0 s after discarding an initial 0.5 s settling segment.
- Require at least 300 valid samples and no force-estimator saturation or controller transition.
- Baseline location: median raw force magnitude.
- Noise estimate: `sigma_robust = 1.4826 × MAD`.
- Freeze baseline at task start; do not let online drift correction absorb a true contact.

### Baseline correction and threshold

- `F_corrected = max(F_raw - baseline_median, 0)`.
- `T_on = max(T_min, 5 × sigma_robust)`.
- `T_off = max(3 × sigma_robust, 0.60 × T_on)`.
- `T_min` is an engineering noise-floor parameter. Candidate: 0.75 N. Its final value must be selected only from no-contact/load-cell acceptance data and frozen before recruitment.

Physical meaning:

- Subtracting the per-trial baseline removes the static estimator bias that caused historical G pre-activation.
- The robust median/MAD reduce sensitivity to isolated baseline spikes.
- Five noise scales make false threshold crossings rare.
- A lower release threshold provides hysteresis and prevents chatter.

### Confirmation and debounce

- Detector disabled before `approach_start`.
- Candidate begins when `F_corrected >= T_on`.
- Contact is confirmed only if the signal remains above `T_off` continuously for 50 ms.
- A drop below `T_off` before confirmation resets the candidate.
- After confirmation, the contact event is latched for the trial; repeated triggers cannot re-arm a controller.
- Record both candidate-start and confirmation timestamps.
- Outcome alignment uses candidate-start as the estimated onset; refinement may use only the later confirmation event.

Acceptance must demonstrate zero false triggers in the specified no-contact dry-runs and quantify timing error against an external load cell or equivalent independent reference.

## 7. Force-refinement design for a later 2 × 2 study

Recommended enabling sequence:

```text
contact candidate
  -> 50 ms confirmation
  -> force_refinement_enabled
  -> first eligible control cycle
  -> force_refinement_first_update
```

Additional delay: 0 s after confirmation.

Reason: the scientific factor is contact-contingent refinement. The detector already provides persistence and debounce. An additional 0.10 or 0.20 s delay would introduce another unpowered design factor. The historical 0.20 s value has no demonstrated theoretical basis and should not be retained for continuity.

Proposed common law for G01*/F11*:

```text
r = clip((F_corrected - T_on) / (F_sat - T_on), 0, 1)
K_target = clip(K_base × (1 - alpha × r), K_min, K_base)
K_next = K_current + beta × (K_target - K_current)
```

- Same `alpha`, `beta`, `F_sat`, update rate, and lower-bound rule in G01* and F11*.
- Parameters fixed by bench safety/stability tests, not participant outcomes.
- Damping ratio remains at the common value and uses the common construction rule.
- Log `K_base`, `r`, `K_target`, `K_commanded`, `K_realized`, and activation source each cycle.

## 8. Outcomes

### Primary outcome

Baseline-corrected excess-force impulse from 0.20 to 1.00 s after estimated contact onset:

```text
integral max(F_raw - baseline_median - T_on, 0) dt
```

Rationale:

- The pilot's 0.20–1.00 s window was exploratory/post hoc and cannot be called historically pre-specified.
- In the new independent experiment it will be prospectively fixed before collection.
- The 0–0.20 s initial-impact phase is kept separate because it is most sensitive to contact-alignment jitter and detector confirmation.
- The engineering test must verify that onset alignment error is small relative to 0.20 s. If it fails, the window must be changed before preregistration and the sample-size calculation repeated.

### Secondary outcomes

1. Initial peak estimated force, 0–0.20 s.
2. Full early impulse, 0–1.00 s, as window sensitivity.
3. Approach time: `contact_candidate_start - approach_start`.
4. Total task time: `task_end - task_start`.
5. Logged task success/failure and predefined failure category.
6. Vision classification correctness and fallback rate as implementation outcomes, not exclusion criteria.

Only the 0.20–1.00 s impulse is confirmatory primary.

## 9. Participant sample size

Pilot participant-level E–A differences:

- Mean: -0.3489 N·s.
- SD of five participant differences: 0.2086 N·s.
- Observed paired `d_z`: 1.672; this is likely inflated by a five-person pilot.

Two-sided paired t-test, alpha 0.05:

| Scenario | Assumed difference | Assumed d_z | Complete participants, 80% | Complete participants, 90% |
|---|---:|---:|---:|---:|
| A. Current pilot estimate | 0.3489 N·s | 1.672 | 6 | 6 |
| B. 75% of pilot estimate | 0.2617 N·s | 1.254 | 8 | 9 |
| C. 50% of pilot estimate | 0.1745 N·s | 0.836 | 14 | 18 |
| D. Provisional SESOI | 0.2000 N·s | 0.959 | 11 | 14 |

Provisional SESOI 0.20 N·s is about 25% of the pilot A mean (0.807 N·s). It must be confirmed as materially meaningful using object-safety/engineering judgment before preregistration; it is not chosen because of its p-value.

Minimum recommendation: 18 analyzable participants for 90% power under the 50%-effect scenario. Preferred recommendation: 24 analyzable participants to reduce reliance on the uncertain five-person variance estimate and support material/object sensitivity analyses. Recruit 28 independent participants, expecting approximately 24 analyzable after a 10–15% withdrawal/invalid-data allowance.

No interim outcome-based stopping or sample-size reduction is allowed.

## 10. Randomization and balance

### Recommended two-mode study

- Nine registered physical objects: three per material stratum.
- Each participant completes one matched A/E pair for each object: 18 measured trials.
- Same physical instance and placement jig within each pair.
- Pair order is AB or BA and balanced within participant and material.
- With 24 analyzable participants, allocate 12 to global AB-first and 12 to BA-first schedules.
- Balance the six material-order permutations across participants; with 24 participants, use each permutation four times.
- Randomize object order within material using a reproducible seed generated before the session.
- Training uses separate objects and is not analyzed.
- Short reset/check period between paired trials; no undocumented redo.

### If a four-mode study is later approved

Use the four Williams sequences:

- A–G*–F*–E
- G*–E–A–F*
- E–F*–G*–A
- F*–A–E–G*

These cover each ordered first-order carryover once. With 24 participants, allocate six participants per sequence. Object and material order must still be independently constrained and balanced.

## 11. Object and material registry

Required trial-level fields:

- `trial_id`
- `participant_id`
- `session_id`
- `mode_assignment`
- `mode_order_position`
- `block_id`
- `object_id`
- `object_name`
- `material_truth`
- `physical_instance_id`
- `orientation_code`
- `placement_jig_id`
- `placement_coordinates`
- `initial_robot_pose_id`
- `initial_gripper_width`
- `vision_predicted_class`
- `vision_confidence`
- `vision_fallback_used`

Material truth and object identity are separate variables. Generalization across material classes is not inferred merely from multiple trials of one physical object. Each matched A/E pair uses the same physical instance, orientation, jig, and robot start pose.

## 12. Engineering acceptance test

Complete at least 100 dry-runs before participant recruitment. Recommended suite: 40 no-contact runs, 40 controlled-contact runs with an independent load reference, and 20 interruption/recovery and file-integrity runs, distributed across all modes and material targets.

| Test | Pass criterion |
|---|---|
| Pre-contact strategy activation | 0 activations before `contact_confirmed` in every force-enabled dry-run |
| No-contact false trigger | 0/40 no-contact runs |
| Controlled-contact detection | 40/40 detected; timing error median <=10 ms and maximum <=25 ms versus independent reference |
| Vision traceability | 100% have start, lock, label, confidence, command, and settled timestamps |
| Pre-contact vision readiness | 100% of measured-style runs lock and settle before task start or abort cleanly before task start |
| Intended versus realized stiffness | Absolute error <=1 N/m or <=1%, whichever is larger, before task start and throughout fixed phases |
| Force-refinement timing, if used | Never earlier than confirmation; first update within two control cycles and <=20 ms |
| Clock integrity | All event/parameter timestamps monotonic; no mixed-clock subtraction paths |
| Control-cycle tail | Median <=6 ms; p95 <=10 ms; p99 <=20 ms; no cycle >50 ms within the contact-analysis window |
| File completeness | 100% CSV/events/summary/manifest entries present and hash verified |
| Trial IDs | 100% unique; no ID reuse after abort/crash |
| Manifest generation | Main/incomplete/aborted roles generated automatically and match the files |
| Crash recovery | 10/10 injected interruptions create an immutable incomplete record and restart with a new trial ID |
| Parameter branch equality | Automated configuration diff finds no non-factor differences between paired modes |

Failure of any hard criterion blocks participant recruitment. A change requires a new version tag and rerunning the complete acceptance suite.

## 13. Relationship between exploratory and confirmatory experiments

- Historical clean experiment: explicitly exploratory/pilot evidence and implementation audit; not pooled into the new primary hypothesis test.
- New experiment: independent, preregistered A/E confirmation with corrected timing, parameter isolation, object registry, and participant-level inference.
- Historical G/F data: evidence about implementation fidelity and limitations, not confirmatory evidence for force refinement.
- Report cohort-specific effect estimates whether or not the new result agrees with the pilot.
- A pooled participant-level estimate may be shown only as a secondary cohort-stratified synthesis, never as a replacement for the new confirmatory test.

