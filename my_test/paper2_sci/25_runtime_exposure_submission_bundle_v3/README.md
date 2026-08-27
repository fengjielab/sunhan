# THMS runtime-exposure submission bundle v3

This bundle is a new, non-destructive revision.  V1, V2, the formal raw data,
and the historical `first_five` archive are outside this bundle and are not
modified or merged.

## Evidence claim

The formal study supports within-system criterion validation from frozen
scheduled conditions to recorded runtime-state timing and outcome-window
exposure.  Logged haptic vectors are post-clamp software commands and
`haptic_send_ok` is an API return.  No independent sensor measured physical
delivery; therefore this bundle makes no physical-delivery, external-validation,
or confirmatory human-effect claim.

## Reproduction

Run from the `my_test` directory:

```text
python analyze_kfb_runtime_exposure_v3.py --data-dir data/kfb_timing_formal_v1/participants --protocol-config 正宫/23_kfb_timing_pilot/frozen_schedule_formal_v1/protocol_config_v1.json --oracle 正宫/23_kfb_timing_pilot/frozen_schedule_formal_v1/private_oracle/oracle.csv --participants F01-F20 --output-dir 正宫/25_runtime_exposure_submission_bundle_v3/analysis
python -m unittest test_analyze_kfb_timing.py test_analyze_kfb_timing_formal.py test_analyze_kfb_runtime_exposure_v3.py test_kfb_timing_protocol.py
python verify_v3_bundle.py
```

## Bundle contents

- `manuscript_thms_v3_zh.md`: Chinese approval manuscript.
- `manuscript_thms_v3_en.md`: English THMS manuscript.
- `supplementary_methods_and_results_v3.md`: detailed exploratory and audit tables.
- `analysis_plan_v3.md`: locked analysis definitions and claim boundaries.
- `analysis/`: deterministic tables, JSON audit records, summary, and figures.

## Submission blockers

`[ETHICS RECORD REQUIRED—DO NOT SUBMIT]` and the author/institution/funding/
conflict-of-interest placeholders must be replaced only from authentic records.
Their presence is intentionally checked by the bundle verifier.
