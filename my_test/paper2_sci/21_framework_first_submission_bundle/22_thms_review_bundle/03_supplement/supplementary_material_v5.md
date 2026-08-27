# Supplementary Material — Version 5

## Human–Machine-Loop-Oriented Realized-Intervention Fidelity Evaluation

This supplement preserves the frozen v4 evidence reconstruction and statistical outputs while supporting the v5 narrative reorganization. It introduces no new acquisition, outcome, statistical test, subgroup, or causal claim. Machine-readable results remain in `v4_data/`; v5 changes their presentation, not their values or schemas.

## Table S1. `ArtifactEvidence` and `EvidenceState` operational contract

`ArtifactEvidence` records the evaluation unit, configuration, trial, frozen outcome window, artifact path and SHA-256, collection commit, rule identifier, extraction mode, observed value, unit, tolerance, missingness, and rationale. Extraction mode is either `automatic` or `structured_author_audit`. Neither `ArtifactEvidence` nor `EvidenceState` accepts an outcome value, effect direction, p value, significance flag, or causal-effect field.

| State | Scientific question | Required evidence | Operational output when incomplete |
|---|---|---|---|
| `nominal_spec` | Is the intended intervention recoverable? | Contemporaneous, versioned and explicit specification/protocol/source documentation | `unavailable`; a label is insufficient |
| `n_to_c` | Did the implementation encode the recoverable intervention? | Available nominal specification plus archived executable source | `not_evaluable` if N is unavailable; otherwise `pass` or cumulative `fail` details |
| `c_to_r` | Was the implementation delivered in the recorded trial? | Source, complete recorded inputs, state/command trajectory | `not_evaluable` if complete replay is unsupported |
| `exposure` | Did the intervention enter the frozen outcome window? | Complete monotonic state trace and window | `unavailable`, never imputed as zero |
| `provenance` | Can the intervention record be linked exactly to the outcome? | Logical ID, acquisition ID, paths, timestamps, collection commit and hashes | `invalid` if any required element is missing or mismatched |

## Table S2. Complete state-to-interpretation rules

| State situation | Cumulative diagnostic consequence | Permitted level | Prohibited claim |
|---|---|---|---|
| `provenance=invalid` | Intervention–outcome linkage blocked | No evaluation of that pair | Any difference linking that intervention and outcome |
| `nominal_spec=unavailable` | Nominal semantics indeterminate | Recoverable realized configuration and exposure | Effect of the unrecovered nominal intervention |
| `n_to_c=fail`, `c_to_r=pass` | Implementation delivered but departed from nominal specification | Disclosed implemented/realized configuration | Correct or nominal intervention effect |
| `c_to_r=fail` | Runtime delivery departed from implementation | Recorded realized delivery | Executable or nominal intervention effect |
| `c_to_r=not_evaluable`, exposure known | Delivery fidelity unknown; realized trajectory/exposure describable | Recorded configuration and exposure | `C=R` or nominal delivery established |
| `c_to_r=not_evaluable`, exposure unavailable | Delivery and exposure unevaluable | Implementation-level description only | Nominal or realized intervention effect |
| `0<exposure<1` | Partial outcome-window exposure | Exposure-distribution-qualified assignment comparison | Uniform complete exposure effect |
| `exposure=0` | No recorded outcome-window exposure | Assignment description with explicit zero exposure | Intervention effect within that window |
| All applicable fields pass | No detected identity break | Nominal identity retained | Causal identification from fidelity alone |

Multiple diagnostics remain cumulative. A more restrictive downstream state does not erase an upstream break. Provenance is an orthogonal linkage prerequisite and is not part of an aggregate fidelity score.

## Table S3. Numerical tolerances and exposure boundaries

Software-command tolerances represent logging or command resolution, not independently measured physical impedance accuracy.

| Quantity | Frozen tolerance |
|---|---:|
| Translational stiffness | 0.5 N/m |
| Rotational stiffness | 0.05 N·m/rad |
| Damping ratio, force-feedback gain, deadband, scale | 0.005 |
| Gripper speed | 0.0005 m/s |
| Gripper force | 0.05 N |

For the left-continuous outcome-window exposure integral, `zero` is \(\Phi\le10^{-12}\), `full` is \(\Phi\ge1-10^{-12}\), and the strict interior is `partial`. The \(10^{-12}\) value is a floating-point boundary rather than a scientific tolerance; approximately 1 ms of an 0.8-s window remains partial exposure.

## Table S4. Real-case structured artifact audit

| Configuration/state | Evidence and extraction | Assigned boundary |
|---|---|---|
| A / N and N→C | Versioned fixed preset and executable initialization; structured author audit | `available`, `pass` |
| G / N | Archived force-only equation but no independent contemporaneous post-contact specification | `unavailable`; label cannot restore the missing semantic claim |
| G / C→R | 12,196 logged command updates replayed automatically | `pass` for archived equation delivery only |
| E / N and N→C | Vision lock, mapping, immediate commands and transition documented and audited | `available`, `pass`; bundled identity |
| F / N→C | `time.time()` enters `system_time()` with a `time.perf_counter()` origin | `fail: clock` |
| F / C→R | Activation/exposure recoverable; complete per-cycle fusion-predicate inputs absent | `not_evaluable`; recorded trajectory remains describable |
| All / exposure | State traces integrated over contact+0.20 to +1.00 s | A 45 full; G 40/5; E 39/2/4; F adaptation 35/7/3 |
| All / provenance | Exact IDs, paths, timestamps, commit and current SHA-256 | 180/180 valid |

The structured semantic audit was performed by the authors. It is not an automatic source-semantics classifier or a dual-review agreement study.

## Table S5. Frozen controlled artifact cases

| Case | Artifact perturbation | Expected key state | Expected comparison level |
|---|---|---|---|
| S00 | Complete chain | all pass/full/valid | nominal identity retained |
| S01 | Label present, nominal artifact absent | `nominal_spec=unavailable` | realized configuration |
| S02 | Guard mismatch | `n_to_c=fail: guard` | implemented/realized configuration |
| S03 | Clock mismatch | `n_to_c=fail: clock` | implemented/realized configuration |
| S04 | Replayed runtime delivery mismatch | `c_to_r=fail` | realized delivery |
| S05 | 0.00125 exposure | partial | exposure-distribution-qualified assignment |
| S06 | Zero exposure | zero | assignment with zero exposure |
| S07 | Replay and exposure trace absent | `not_evaluable`/`unavailable` | implementation only |
| S08 | Invalid provenance | invalid | none |
| S09 | Guard mismatch plus partial exposure | both diagnostics retained | implemented/realized configuration |
| S10 | Runtime mismatch plus invalid provenance | both retained; pair blocked | none |
| S11 | Guard+clock mismatch, incomplete C→R replay, known partial exposure | all diagnostics retained | recorded realized configuration |

All 12 frozen cases matched their separately stored oracle. This is rule-level implementation verification/internal discrimination, not state-space completeness, diagnostic sensitivity, methodological validity, or external validation.

## Table S6. Participant-level exploratory contrasts

Participant is the independent human unit in every row (\(n=5\)). Differences use the first-listed configuration minus the second-listed configuration.

| Contrast | Difference, N·s | 95% t CI, N·s | Paired-t p | Exact sign-flip p | Exact Wilcoxon p | Holm paired-t p |
|---|---:|---:|---:|---:|---:|---:|
| E–A | −0.3489 | [−0.6080, −0.0898] | 0.0201 | 0.0625 | 0.0625 | 0.0633 |
| G–A | −0.0742 | [−0.1978, 0.0494] | 0.1708 | 0.0625 | 0.0625 | 0.3416 |
| F–E | −0.0212 | [−0.1433, 0.1010] | 0.6556 | 0.6875 | 0.8125 | 0.6556 |
| F–G | −0.2958 | [−0.5000, −0.0917] | 0.0158 | 0.0625 | 0.0625 | 0.0633 |

Contact alignment and impulse computation both use the Panda internal `O_F_ext_hat_K` estimate. The outcome is operational and not an independently sensed physical-safety endpoint.

## Table S7. Fixed adjacent-window sensitivity for E–A

| Post-contact window | E–A difference, N·s | 95% t CI | Participant direction | Exact sign-flip p |
|---|---:|---:|---:|---:|
| 0.10–1.00 s | −0.3718 | [−0.6618, −0.0819] | 5/5 negative | 0.0625 |
| 0.30–1.00 s | −0.3238 | [−0.5474, −0.1002] | 5/5 negative | 0.0625 |
| 0.20–0.80 s | −0.2438 | [−0.4635, −0.0241] | 5/5 negative | 0.0625 |
| **0.20–1.00 s** | **−0.3489** | **[−0.6080, −0.0898]** | **5/5 negative** | **0.0625** |
| 0.20–1.20 s | −0.4307 | [−0.6960, −0.1653] | 5/5 negative | 0.0625 |

These windows do not create additional independent observations or primary outcomes.

## Table S8. Exhaustive record-selection robustness

| Contrast | Minimum mean, N·s | Maximum mean, N·s | Negative means | All five participants negative |
|---|---:|---:|---:|---:|
| E–A | −0.353791 | −0.336697 | 64/64 | 64/64 |
| G–A | −0.074218 | −0.074218 | 64/64 | 64/64 |
| F–E | −0.067805 | −0.000304 | 64/64 | 0/64 |
| F–G | −0.330284 | −0.279877 | 64/64 | 64/64 |

Every logical trial remains represented once. The initial records were marked erroneous, so these combinations are counterfactual/adversarial selection checks rather than 64 provenance-valid datasets.

## Supporting figures and machine-readable files

- Figure S1: `Fig05_contact_aligned_trajectories.{png,pdf,svg}`
- Figure S2: `Fig06_participant_lopo_stability.{png,pdf,svg}`
- Figure S3: `Fig07_lineage_trace_examples.{png,pdf,svg}`
- Frozen data: `v4_data/controlled_artifact_case_results.csv`, `trial_evidence_states.csv`, `real_case_artifact_audit.csv`, `record_selection_64_combinations.csv`, `record_selection_summary.csv`, `e_nonfull_exposure_mechanisms.csv`, and `f_clock_evidence.json`
- Frozen logic: `../05_reproduction/v4/artifact_to_state_rules.csv`, `structured_semantic_audit.csv`, and `controlled_artifact_cases.csv`
