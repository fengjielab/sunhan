# Framework validation submission bundle v2

This bundle upgrades the framework paper to a two-study evidence structure:

1. the unchanged retrospective five-participant case demonstrates diagnostic and interpretation-bounding value;
2. the formal F01–F20 study provides prospective within-system criterion validation against known timing and exposure targets.

## Authoritative files

- `manuscript_thms_v2_zh.md`: Chinese approval manuscript.
- `manuscript_thms_v2_en.md`: synchronized English THMS manuscript.
- `analysis_plan_v2.md`: frozen cohort, endpoint, and interpretation rules.
- `analysis/`: generated cohort manifest, trial metrics, summaries, figures, acceptance report, and provenance.

## Reproduction

From the `my_test` repository root:

```text
python analyze_kfb_timing_formal.py --data-dir data/kfb_timing_formal_v1/participants --protocol-config 正宫/23_kfb_timing_pilot/frozen_schedule_formal_v1/protocol_config_v1.json --oracle 正宫/23_kfb_timing_pilot/frozen_schedule_formal_v1/private_oracle/oracle.csv --participants F01-F20 --output-dir 正宫/24_framework_validation_submission_bundle_v2/analysis
```

The command is read-only with respect to acquisition data. It is locked to F01–F20 and does not scan the historical `first_five` directory.

## Submission blockers

The manuscripts intentionally retain explicit placeholders for ethics, consent, authorship, affiliations, funding, conflicts, contributions, acknowledgments, and final data/code availability wording. These must be completed from authentic institutional records before submission.
