# Phase 2 data-lineage audit — pending confirmation

This directory contains read-only audit outputs. No original manifest, raw file, processed metric, analysis script, or collection code has been modified.

## Mapping result

- `trial_manifest_186.csv`: 186 records, 180 unique `trial_key` values.
- 174 trial keys contain one record.
- 6 trial keys contain two records: one first attempt and one retest.
- `included_main_first_attempt=1`: 180 records, comprising 174 unique records plus the first attempt for each of the 6 duplicated keys.
- `record_role=retest_sensitivity_only`: 6 records.
- `included_sensitivity_latest=1`: 180 records, comprising 174 unique records plus the retest for each duplicated key.
- `trial_manifest_180.csv`: 180 unique keys and matches the latest-record selection for all 180 keys. It matches the first-attempt selection for only 174 keys.
- `trial_metrics_main_180.csv`: 180 unique keys and its `timestamp` matches the first-attempt record for all 180 keys.

## Current mismatch mechanism

`09_latency_aware_paper/analyze_latency_aware.py` loads scalar metrics from `03_processed_data/trial_metrics_main_180.csv`, but loads raw time-series paths from `02_audit/trial_manifest_180.csv`. The script joins them by `trial_key` without checking timestamp or file hash. For the 6 duplicated keys, scalar metrics therefore come from the first attempt while raw time-series come from the retest.

All paths in `data_lineage_audit.csv` are relative to:

`F:/sun/sunhan/my_test/data/ral_date`

## Confirmation gate

No repair has been applied. After user confirmation, the next phase will create a unique master manifest with first attempts as the main analysis and retests retained only as sensitivity records.
