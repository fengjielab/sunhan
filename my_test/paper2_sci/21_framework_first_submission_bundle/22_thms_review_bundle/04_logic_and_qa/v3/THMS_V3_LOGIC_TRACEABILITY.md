# THMS v3 logic and evidence traceability

This file maps every strengthened v3 claim to its rule, evidence, manuscript location, and wording boundary.

| Claim or decision | Rule/evidence state | Frozen source | v3 location | Wording boundary |
|---|---|---|---|---|
| The classifier discriminates the declared state space | 11 deterministic cases; exact oracle match | `controlled_cases.csv`; `controlled_perturbation_results.csv` | Abstract; 3.1; 4.1; Supplement S7 | Internal implementation/discrimination check, not external validation |
| Missing nominal specification is not (N\neq C) | `nominal_spec=unavailable`, `n_to_c=not_evaluable` | G specification audit and classifier S01 | 2.2–2.3; 4.2 | Do not infer a missing G specification from the label |
| Executable compliance does not establish nominal fidelity | `n_to_c=fail`, `c_to_r=pass` | G/F source and logs; S02/S03 | Table II; 4.2 | Describe implemented/realized configuration, not nominal policy effect |
| F has a source-established clock mismatch | `n_to_c=fail`, detail=`clock` | collection commit `09c13e...`; `f_clock_evidence.json` | 3.3; 4.2; Supplement S8 | 53 ms is downstream realized timing, not a numerical mixed-clock delay |
| E has 39/2/4 full/partial/zero exposure | exposure integration in the frozen outcome window | `trial_level_fidelity_metrics.csv`; `e_nonfull_exposure_mechanisms.csv` | Abstract; 4.2; Supplement S8 | Exposure classes do not select or exclude trials |
| Current intervention–outcome provenance is valid | `provenance=valid` for 180 selected records | master manifest, data-lineage audit, current SHA-256 checks | 3.4; 4.2 | Provenance does not prove delivery fidelity |
| E-A remains negative under all record choices | exhaustive (2^6=64) masks | `old_new_trial_metric_comparison.csv`; v3 enumeration | Abstract; 4.3; Supplement S6 | Initial records remain superseded/erroneous; do not call all combinations valid datasets |
| Force outcome is operational and shares a channel with contact | contact and outcome both use `O_F_ext_hat_K` | acquisition schema and clean analysis | 3.2–3.3; 5.3 | Not independently sensed physical safety or independent alignment evidence |
| E-A is descriptive and exploratory | fidelity-constrained comparison plus participant (n=5) | participant/statistics summaries | 4.3; Fig. 4 | No isolated vision/stiffness or confirmatory causal claim |
| Causal identification is outside the fidelity classifier | fixed classifier output boundary | `evidence_state.py`; all 11 cases | 2.2–2.3; 4.1; Discussion | Nominal identity retained does not authorize causal wording |

## Version preservation

The v3 reproduction check verifies SHA-256 hashes for both earlier manuscripts and all 12 shared v2 main-figure assets. New wording-bearing figures are written only under `02_main_figures/v3/`.
