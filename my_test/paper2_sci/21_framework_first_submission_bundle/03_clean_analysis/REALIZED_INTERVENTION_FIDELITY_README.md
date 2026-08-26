# Realized-Intervention Fidelity Framework

This analysis extends the frozen clean reconstruction without altering the existing trial metrics, participant statistics, or manuscript. It uses all 180 selected clean records and retains noncompliant trials as experimental facts.

## Four layers

1. **Nominal intervention:** stated mode semantics, initial commands, intended event order, and timing target.
2. **Executable/commanded logic:** guards, clock calls, update laws, and software commands implemented by the archived acquisition code.
3. **Realized logged intervention:** event-aligned command trajectories, activation states, and exact record provenance.
4. **Outcome interpretation:** whether the relevant intervention was present during the frozen early-force outcome window and what the archived contrast can estimate.

`realized logged` refers to logged software command/event traces. The dataset does not contain an independent measurement of physical endpoint impedance.

## Source inputs

- `master_trial_manifest.csv`
- `data_lineage_audit.csv`
- `trial_level_metrics.csv`
- `timing_audit.csv`
- Raw CSV/events/summary triplets under `F:/sun/sunhan/my_test/data/ral_date`
- Archived acquisition logic in `interactive_teleop.py` and `experiment_protocol.py`

## Generated outputs

- `intervention_specification.csv`: one machine-readable specification for each of A/G/E/F.
- `trial_level_fidelity_metrics.csv`: per-record event order, activation timing, parameter landmarks, exposure, provenance, clock, and control-cycle metrics.
- `configuration_fidelity_summary.csv`: long-form mode-level counts, compliance rates, medians, IQRs, and ranges.
- `outcome_window_exposure.csv`: per-record linkage between the frozen early-force outcome and realized intervention exposure in contact+0.20 to +1.00 s.
- `tables/nominal_vs_realized_interpretation.csv`: nominal-versus-realized scientific interpretation table.
- `figures/realized_intervention_fidelity_framework.{png,pdf,svg}`: four-layer framework and A/G/E/F examples.
- `figures/trial_level_intervention_timing_raster.{png,pdf,svg}`: all-trial event-aligned timing raster.
- `REALIZED_INTERVENTION_FIDELITY_REPORT.md`: bounded framework conclusion.
- `fidelity_qa_report.json` and `tables/fidelity_qa_checks.csv`: reproducibility checks.

## Metric conventions

- F activation timing error is
  `t_first_fusion_active - (t_contact + 0.20 s)`.
- G contact-aligned activation is descriptive. No G timing-error value is created because executable G has no contact gate.
- `event_order_compliance` compares the realized trace with the nominal scientific event order.
- `executable_logic_compliance` checks the archived code-level guards separately. This distinction prevents G's semantic mismatch from being mislabeled as a runtime implementation failure.
- Vision transition completion is the first logged sample at the selected Kt/Kr/damping target within resolution tolerances. The observation method is retained per trial.
- Exposure duration is integrated on the logged time axis in the frozen 0.80-s outcome window.
- `control_cycle_adherence` is the fraction of logged cycles no longer than twice the nominal 5-ms period. It is a transparent scheduler diagnostic, not a composite fidelity score or an acceptance threshold selected from outcomes.
- Acquisition lineage is valid only when raw CSV, event JSON, summary JSON, and scalar outcome share the selected `record_id`, timestamped paths, and currently verified SHA-256 hashes.

## Reproduction

```powershell
python F:\sun\sunhan\my_test\正宫\03_clean_analysis\scripts\fidelity_analysis.py
python F:\sun\sunhan\my_test\正宫\03_clean_analysis\scripts\qa_fidelity_analysis.py
```

The QA script stops on duplicate/missing records, source-hash failure, outcome mismatch, unbounded exposure fractions, unexpected A/G/F checks, missing figures, or the appearance of inferential fishing columns.

## Explicit exclusions

- No compliant-only subgroup hypothesis test.
- No removal of early G activation or failed F gates.
- No optimization of fidelity thresholds against outcomes.
- No new participant-level inference.
- No composite fidelity score.
- No claim that commanded stiffness is independently measured physical impedance.
