# Supplementary Material — Version 4

## Artifact-to-State Reconstruction for Fidelity-Constrained Human–Machine Experiments

This supplement documents how raw artifacts are mapped to evidence states, the rule-level implementation verification, the complete exploratory statistics, and the source-level case evidence. It introduces no additional human-subject acquisition, does not change the frozen outcome or analysis unit, and does not claim methodological or external validation.

## Table S1. Artifact-to-state operational rules

| State | Required evidence | Assigner | Operational rule and tolerance | Missing/incomplete output |
|---|---|---|---|---|
| `nominal_spec` | Contemporaneous versioned protocol, specification, or traceable source documentation explicitly defining intervention elements | Structured author audit | `available` only if the artifact is present, contemporaneous, and explicit; a condition label or isolated comment alone is insufficient | `unavailable` |
| `n_to_c` | Available nominal specification and archived executable source | Structured author audit | Compare every required guard, clock, parameter, initialization, and update element. Any demonstrated mismatch yields `fail`; `pass` requires all required checks. Categorical guards/clocks require exact agreement. Logged-command tolerances are listed below | `not_evaluable` |
| `c_to_r` | Archived source, recorded inputs, and logged state/command trajectory | Automatic replay/check | `pass` only if supported complete replay matches categorical states exactly and commands within declared software tolerances; demonstrated discrepancy yields `fail` | `not_evaluable` |
| `exposure` | Complete monotonic state trace and frozen event-aligned window | Automatic integration | Left-continuous integration. `zero` if (\Phi\le10^{-12}); `full` if (\Phi\ge1-10^{-12}); otherwise `partial` | `unavailable`, never imputed as zero |
| `provenance` | Record/trial identity, paths, timestamps, collection commit, and current hashes | Automatic identity/hash check | `valid` only when every required check is complete and exact | `invalid` |

Software-command tolerances represent logging/command resolution, not physical impedance accuracy: `K_trans` 0.5 N/m; `K_rot` 0.05 N·m/rad; `damping_ratio`, `K_fb`, `deadband`, and `scale` 0.005; gripper speed 0.0005 m/s; gripper force 0.05 N. The (10^{-12}) exposure boundary handles floating-point equality only; approximately 1 ms of an 0.8-s window remains `partial`.

The `ArtifactEvidence` schema records the evidence unit, configuration, trial, window, artifact path/hash, collection commit, rule identifier, extraction mode, observed value, unit, tolerance, missing status, and rationale. Neither it nor `EvidenceState` contains an outcome value, effect direction, p value, significance field, or causal-effect flag.

## Table S2. Real-case structured artifact audit

| Configuration/state | Artifact and extraction | Observed evidence | Assigned state and boundary |
|---|---|---|---|
| A / (N) | Archived `interactive_teleop.py`; structured author audit | Versioned A preset and description specify the fixed 200-N/m baseline | `available`; fixed configuration identity only |
| A / (N\rightarrow C) | Same source; structured author audit | Preset and executable initialization use the same fixed command vector with no A update path | `pass` |
| G / (N) | Same source; structured author audit | Force-only label and equation are recoverable, but no independent contemporaneous artifact specifies a post-contact guard | `unavailable`; label cannot supply the missing post-contact specification |
| G / (N\rightarrow C) | Derived rule | (N) unavailable | `not_evaluable`, not a demonstrated mismatch |
| E / (N) | Same source; structured author audit | First valid vision lock followed by bundled profile mapping is explicitly documented | `available`; identifies a bundle, not an isolated visual component |
| E / (N\rightarrow C) | Same source; structured author audit | Vision lock, mapping, immediate commands, and smooth transition represent the declared E elements | `pass` |
| F / (N) | Same source; structured author audit | `FUSION_CONTACT_DELAY_S=0.20` is documented as a contact-onset delay | `available` |
| F / (N\rightarrow C) | Same source; structured author audit plus exact signatures | `time.time()` enters `system_time()` whose origin is `time.perf_counter()` | `fail: clock` |
| A/G/E / (C\rightarrow R) | Source, raw CSV, event JSON, and derived trajectory; automatic | A fixed commands, G equation, and E profile/transition trajectory are replayed/checked | `pass` |
| F / (C\rightarrow R) | Same types of artifacts; automatic availability check | Activation and exposure are recoverable, but all literal fusion-predicate inputs were not preserved for complete per-cycle replay | `not_evaluable`; recorded trajectory/exposure remain describable |
| All / exposure | Raw state traces and frozen contact+0.20-to+1.00-s window; automatic | A 45 full; G 40 full/5 partial; E 39 full/2 partial/4 zero; F 35 full/7 partial/3 zero | Corresponding trial-level exposure state |
| All / provenance | Master manifest, lineage audit, paths, timestamps, commit and SHA-256; automatic | 180/180 exact intervention–outcome record matches | `valid` |

This is a structured author audit, not an automatic source-code semantics classifier and not a dual-review agreement study. Exact rows, SHA-256 values, rules, tolerances, and rationales are in `v4_data/real_case_artifact_audit.csv`.

## Table S3. Configuration-level evidence reconstruction

| Configuration | (s_N) | (s_{NC}) | (s_{CR}) | Exposure distribution | Provenance |
|---|---|---|---|---|---|
| A | available | pass | pass | 45 full | 45/45 valid |
| G | unavailable | not evaluable | pass | 40 full, 5 partial | 45/45 valid |
| E | available | pass | pass | 39 full, 2 partial, 4 zero | 45/45 valid |
| F | available | fail: clock | not evaluable | 35 full, 7 partial, 3 zero | 45/45 valid |

G replay covered 12,196 logged command-update rows across 45 trials. Maximum absolute errors were (3.33\times10^{-16}) for force ratio, (5.68\times10^{-14}) N/m for target stiffness, and (8.53\times10^{-14}) N/m for the smoothed stiffness update, all below the frozen (10^{-10}) numerical check tolerance. This establishes replay consistency of the archived G software equation; it does not restore an unavailable post-contact nominal specification.

## Table S4. Rule-level implementation verification cases

| Case | Raw-artifact perturbation | Expected/observed key state | Expected/observed comparison level | Exact match |
|---|---|---|---|---:|
| S00 | Complete evidence chain | all pass/full/valid | nominal identity retained | 1 |
| S01 | Label present, nominal artifact absent | (s_N=unavailable) | realized configuration | 1 |
| S02 | Guard mismatch | (s_{NC}=fail: guard) | implemented/realized configuration | 1 |
| S03 | Clock mismatch | (s_{NC}=fail: clock) | implemented/realized configuration | 1 |
| S04 | Replayed runtime delivery mismatch | (s_{CR}=fail) | realized delivery | 1 |
| S05 | 0.00125 window exposure | partial | assignment with exposure distribution | 1 |
| S06 | Zero window exposure | zero | assignment with zero exposure | 1 |
| S07 | Replay and exposure trace unavailable | `not_evaluable`/`unavailable` | implementation only | 1 |
| S08 | Invalid provenance | invalid | none | 1 |
| S09 | Guard mismatch plus partial exposure | both diagnostics retained | implemented/realized configuration | 1 |
| S10 | Runtime mismatch plus invalid provenance | both diagnostics; pair blocked | none | 1 |
| S11 | Guard+clock mismatch, unreplayed (C\rightarrow R), known partial exposure | all diagnostics retained | recorded realized configuration | 1 |

All 12 cases matched the separately stored oracle. This verifies that the implementation follows the declared Stage A and Stage B rules and remains falsifiable within that state space. It does not establish state-space completeness, real-world diagnostic sensitivity, methodological validity, or cross-system generalizability.

## Table S5. Participant-level exploratory contrasts

Participant is the independent human unit in every row ((n=5)). Differences use the first-listed configuration minus the second-listed configuration.

| Contrast | Difference, N·s | 95% t CI, N·s | Paired-t p | Exact sign-flip p | Exact Wilcoxon p | Holm paired-t p |
|---|---:|---:|---:|---:|---:|---:|
| E–A | −0.3489 | [−0.6080, −0.0898] | 0.0201 | 0.0625 | 0.0625 | 0.0633 |
| G–A | −0.0742 | [−0.1978, 0.0494] | 0.1708 | 0.0625 | 0.0625 | 0.3416 |
| F–E | −0.0212 | [−0.1433, 0.1010] | 0.6556 | 0.6875 | 0.8125 | 0.6556 |
| F–G | −0.2958 | [−0.5000, −0.0917] | 0.0158 | 0.0625 | 0.0625 | 0.0633 |

Contact alignment and impulse computation both use the Panda internal `O_F_ext_hat_K` estimate. The outcome is operational and is not an independently sensed physical-safety endpoint.

## Table S6. Fixed adjacent-window sensitivity for E–A

| Post-contact window | E–A difference, N·s | 95% t CI | Participant direction | Exact sign-flip p |
|---|---:|---:|---:|---:|
| 0.10–1.00 s | −0.3718 | [−0.6618, −0.0819] | 5/5 negative | 0.0625 |
| 0.30–1.00 s | −0.3238 | [−0.5474, −0.1002] | 5/5 negative | 0.0625 |
| 0.20–0.80 s | −0.2438 | [−0.4635, −0.0241] | 5/5 negative | 0.0625 |
| **0.20–1.00 s** | **−0.3489** | **[−0.6080, −0.0898]** | **5/5 negative** | **0.0625** |
| 0.20–1.20 s | −0.4307 | [−0.6960, −0.1653] | 5/5 negative | 0.0625 |

These windows do not create additional independent observations or primary outcomes.

## Table S7. Exhaustive record-selection robustness

| Contrast | Minimum mean difference, N·s | Maximum mean difference, N·s | Negative means | All 5 participants negative | Negative-participant range |
|---|---:|---:|---:|---:|---:|
| E–A | −0.353791 | −0.336697 | 64/64 | 64/64 | 5–5 |
| G–A | −0.074218 | −0.074218 | 64/64 | 64/64 | 5–5 |
| F–E | −0.067805 | −0.000304 | 64/64 | 0/64 | 2–3 |
| F–G | −0.330284 | −0.279877 | 64/64 | 64/64 | 5–5 |

Every logical trial remains represented once in all (2^6=64) combinations. The initial records were marked erroneous, so these are counterfactual/adversarial record-selection checks rather than 64 provenance-valid datasets. F–E does not support stable participant direction.

## Table S8. F clock chain and E non-full exposure

Literal-equivalent F pseudocode:

```text
timeline.start_perf = time.perf_counter()
now = time.time()
update_vision_force_fusion(now)

elapsed = timeline.system_time(now) - contact_t
        = (now - timeline.start_perf) - contact_t
if elapsed < 0.20 s:
    return
activate_if_remaining_guards_pass()
```

The mixed clock predicate destroys the nominal contact-relative delay semantics. The observed median contact-to-activation time of +0.0532736 s is downstream realized timing after contact, other guards, scheduling, and logging; it is not a 53-ms delay generated numerically by the mixed clocks. Only 3/45 F trials reached the nominal +0.20-s timing and none activated before recorded contact.

For E, the four zero-exposure trials locked vision 1.0716–1.4338 s after contact and completed transitions 1.5014–1.8069 s after contact, after the +1.00-s endpoint. The two partial fractions were 0.966863 and 0.00115488; the latter contributes approximately 1 ms at the window end and is deliberately not rounded to zero.

## Existing supporting figures

- **Figure S1:** `supplementary_figures/FigS01_contact_aligned_force_and_stiffness.png`
- **Figure S2:** `supplementary_figures/FigS02_participant_and_lopo_stability.png`
- **Figure S3:** `supplementary_figures/FigS03_lineage_and_trace_examples.png`

## Machine-readable v4 files

- `v4_data/controlled_artifact_case_results.csv`
- `v4_data/trial_evidence_states.csv`
- `v4_data/real_case_artifact_audit.csv`
- `v4_data/record_selection_64_combinations.csv`
- `v4_data/record_selection_summary.csv`
- `v4_data/e_nonfull_exposure_mechanisms.csv`
- `v4_data/f_clock_evidence.json`
- `../04_logic_and_qa/v4/v4_validation_report.json`
- `../04_logic_and_qa/v4/baseline_integrity.csv`
- `../05_reproduction/v4/artifact_to_state_rules.csv`
- `../05_reproduction/v4/structured_semantic_audit.csv`
- `../05_reproduction/v4/controlled_artifact_cases.csv`
