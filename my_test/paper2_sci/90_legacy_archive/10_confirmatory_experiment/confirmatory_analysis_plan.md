# Confirmatory Analysis Plan — A/E Experiment

Status: preregistration-style draft. Freeze a versioned copy before collecting any confirmatory participant outcome.

## Study objective

Independently test whether a vision-enabled pre-contact translational-stiffness configuration reduces baseline-corrected early contact-force exposure compared with a fixed-stiffness baseline under a parameter-matched, within-participant design.

## Primary hypothesis

- Estimand: participant-level mean difference `E - A` in the primary outcome.
- Scientific directional hypothesis: `E - A < 0`.
- Formal test: two-sided alpha 0.05.

## Primary outcome

For each valid trial, trapezoidal integral from 0.20 to 1.00 s after `contact_candidate_start` of:

```text
max(F_raw - baseline_median - T_on, 0)
```

Unit: N·s.

For each participant and mode, average across all valid matched object trials. The primary paired difference is participant mean E minus participant mean A.

## Primary contrast and test

- Contrast: E minus A only.
- Independent experimental unit: participant.
- Primary test: paired t-test on participant-level mean differences.
- Report raw mean difference, participant-level SD of differences, 95% t confidence interval, t statistic, degrees of freedom, and two-sided p-value.
- No trial or block is treated as an independent participant.

## Recruitment and stopping

- Target: 24 analyzable independent participants.
- Recruit up to 28 to allow 10–15% withdrawal/invalid-data loss.
- Fixed-sample design; no outcome-based interim analysis or optional stopping.
- Recruitment completion/exclusion counts are monitored without examining mode-specific outcomes.

## Trial-level validity and exclusions

Trial exclusion is allowed only for a pre-specified technical/protocol failure:

1. missing or hash-invalid CSV/events/summary triplet;
2. non-unique or unresolved trial ID;
3. clock non-monotonicity or an event outside the raw-data time range;
4. emergency stop or hardware/controller crash;
5. object displaced before task start or wrong physical instance/placement;
6. contact-detector engineering failure documented before outcome calculation;
7. intended-versus-realized controller mismatch beyond the frozen tolerance;
8. participant withdrawal or explicit request to delete the trial/session.

Do not exclude trials because of:

- high or low force;
- long or short task time;
- visual misclassification or unknown fallback;
- task failure after a technically valid start;
- an observation being a statistical outlier;
- disagreement with the pilot direction.

No undocumented replacement trial is permitted. A permitted repeat receives a new trial ID, and the original remains immutable with its validity role.

## Participant-level inclusion

- Primary analysis requires at least seven of nine complete matched A/E object pairs.
- If fewer than seven complete pairs remain after blinded technical exclusions, that participant is excluded from the primary paired test but retained in the CONSORT-style flow and applicable sensitivity analyses.
- The decision is made from technical/manifest fields before unblinding mode outcomes.

## Missing data

- No outcome imputation in the primary analysis.
- Within a participant, calculate A and E means from the same set of complete object pairs.
- Report missingness and exclusion by mode, object, material, and reason.
- Sensitivity: trial-level mixed model using all technically valid observations under a missing-at-random assumption.

## Outlier handling

- Primary analysis retains all technically valid outcomes.
- Flag, but do not delete, values beyond 1.5 IQR and robust absolute z-score >3.5.
- Sensitivity analyses:
  1. participant-level median paired difference;
  2. 20% winsorized trial outcomes before participant aggregation;
  3. leave-one-participant-out estimates.
- The untrimmed participant-mean analysis remains primary regardless of sensitivity results.

## Secondary outcomes

Pre-specified secondary family:

1. initial peak estimated force, 0–0.20 s;
2. full early excess-force impulse, 0–1.00 s;
3. approach time;
4. total task time;
5. task success/failure.

Continuous outcomes use participant-level paired differences. Binary success is summarized by paired counts and analyzed with an exact paired binary test if events are sufficient; otherwise it remains descriptive.

Apply Holm correction across the secondary outcome family. The single primary contrast requires no multiplicity correction.

## Secondary material/object analysis

- Estimate E–A separately for soft, medium, and hard strata with 95% CIs.
- Fit a secondary mixed model with fixed effects for mode, material, mode×material, pair order, and session progression; participant and physical object are grouping factors where identifiable.
- Material interaction is exploratory unless separately powered and preregistered.
- Object-level estimates are descriptive and do not substitute trial counts for participants.

## Sensitivity analyses

1. Exhaustive two-sided participant-level sign-flip test.
2. Exact Wilcoxon signed-rank test.
3. Leave-one-participant-out estimates.
4. Alignment sensitivity using `contact_confirmed` rather than candidate-start.
5. Window sensitivity using 0–1.00 s and 0.20–0.80 s.
6. Intention-to-treat system estimate including visual misclassification/fallback.
7. Per-correct-classification estimate, clearly labeled non-primary and potentially selected.
8. Trial-level mixed model with participant clustering and order covariates.

Sensitivity analyses cannot replace the primary analysis because they produce a smaller p-value.

## Randomization audit

Before outcome analysis, verify:

- AB/BA counts by participant and material;
- six material-order permutations;
- object-order balance;
- mode position within matched pair;
- no duplicate trial IDs;
- no mode-dependent technical exclusion imbalance.

## Blinding and analysis freeze

- Freeze code, environment, outcome definitions, and this plan before first confirmatory participant.
- Use masked mode codes during data-integrity and exclusion review where practical.
- Generate the master manifest and technical exclusion report before computing the primary contrast.
- Preserve code commit, environment lock file, raw-file hashes, randomization seed, and analysis run metadata.

## Reporting rule

Report the estimate and uncertainty regardless of statistical significance or agreement with the pilot. Do not change the primary window, participant threshold, contrast, tail, test, or exclusion rule after inspecting confirmatory outcomes.

