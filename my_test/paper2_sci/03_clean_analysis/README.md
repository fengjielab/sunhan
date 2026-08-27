# 03_clean_analysis

This directory is the rebuilt, non-destructive analysis lineage for the 180 valid teleoperation trials. It does not overwrite any raw file, collection code, historical manifest, processed table, statistic, or figure.

## 1. Frozen source state

- Raw data root: `F:/sun/sunhan/my_test/data/ral_date`
- Historical 186-record manifest: `F:/sun/sunhan/my_test/正宫/02_audit/trial_manifest_186.csv`
- Collection code commit: `09c13e0b679905f14f770d820af00841546cb4cc`
- Collection code files audited at that commit:
  - `my_test/interactive_teleop.py`
  - `my_test/experiment_protocol.py`
- Historical outputs were backed up before this reconstruction at:
  - `F:/sun/sunhan/my_test/paper2_sci_backups/analysis_snapshot_20260809_095836`

All 186 CSV/events/summary triplets are checked against the SHA-256 hashes in the historical manifest before any metric is calculated.

## 2. User-confirmed record-validity decision

On 2026-08-09, the user confirmed that the six extracted `20260729` records were erroneous and that their corresponding `20260730` records were valid replacements.

The clean main analysis therefore contains:

- 174 normal unique records;
- 6 valid `20260730` replacement records;
- total: 180 valid trial keys.

The six erroneous `20260729` records remain in `master_trial_manifest.csv` with `analysis_role=excluded_known_error`. They are never deleted and never enter the clean metrics. The six replacements are marked `analysis_role=main_valid_replacement`.

## 3. Reproducible lineage

```text
raw CSV + events JSON + summary JSON
  -> historical trial_manifest_186.csv
  -> SHA-256 and companion-file verification
  -> master_trial_manifest.csv
  -> validity selection (174 unique + 6 valid replacements)
  -> raw/event preprocessing on the same record_id
  -> trial_level_metrics.csv + timing_audit.csv
  -> participant_level_metrics.csv
  -> statistics_summary.csv + leave_one_participant_out.csv
  -> tables/ and figures/
```

The `record_id` is `trial_key|timestamp`. Raw time-series, event times, force threshold, success status, and summary metadata must share this exact `record_id`. Joining only by `trial_key` is prohibited.

## 4. Time-axis reconstruction

- `ExperimentTimeline.start_perf` uses `time.perf_counter()`.
- Event `system_time` and CSV `system_time` are seconds relative to that monotonic origin.
- `started_at_unix` uses `time.time()` and is retained only as wall-clock metadata.
- No ROS timestamp field is present in the supplied CSV or event schema; `ros_timestamp_available=0` is recorded rather than inferred.
- `task_start`, `contact_onset`, `vision_lock`, and CSV activation flags are represented on the monotonic relative timeline.

For every valid trial, `timing_audit.csv` reports:

- `vision_lock - task_start`;
- `vision_lock - contact`;
- `force_activation - task_start`;
- `force_activation - contact`;
- event/CSV vision-lock sampling difference;
- control-cycle median, p95, p99, maximum, and long-cycle fractions.

## 5. Metric definitions

- Contact threshold: logged `max(1 N, baseline mean + 3 baseline SD)`.
- Primary outcome: trapezoidal integral of `max(F_ext_mag - threshold, 0)` from 0.2 to 1.0 s after logged contact onset.
- Initial peak force: maximum estimated force magnitude from 0 to 0.2 s after contact.
- Approach time: `contact_onset - task_start`.
- Total task time: `task_end - task_start`.
- Success: experiment completed AND logged grasp success AND logged task-end success.
- Contact-aligned trajectories: interpolation on -0.50 to 1.50 s at 0.01 s resolution.
- Force adaptation activation:
  - G: first CSV row with `force_adapt_active > 0`;
  - F: first CSV row with `fusion_active > 0`.

Force is the Franka internal estimated external wrench magnitude, not an independently calibrated external force-sensor measurement.

## 6. Statistical unit and inference

The independent human experimental unit is `participant` (`n=5`). Neither 180 trials nor 45 blocks are treated as independent human samples.

Workflow:

1. Average the nine trials within each participant and mode.
2. Form predefined participant-level paired differences: `E-A`, `G-A`, `F-E`, and `F-G`.
3. Report raw mean difference and t-based 95% CI.
4. Report paired t-test, exhaustive two-sided sign-flip sensitivity, and exact Wilcoxon sensitivity.
5. Apply Holm correction across the four predefined contrasts separately for each metric and each p-value family.
6. Perform leave-one-participant-out analysis without changing the analysis method to pursue significance.

With only five participants, the smallest possible two-sided exhaustive sign-flip p-value is 0.0625 before multiplicity correction.

## 7. F-mode timing validation

Design intent: fusion starts no earlier than 0.20 s after `contact_onset`.

Collection-code behavior: the main loop passes `time.time()` into `_update_vision_force_fusion`, which calls `ExperimentTimeline.system_time(now)` and subtracts a `time.perf_counter()` origin. The mixed clock domains make the 0.20 s gate immediately pass once contact exists.

Log behavior in the clean 45 F trials:

- median first activation relative to contact: approximately 0.053 s;
- 42/45 activated before 0.20 s;
- the three later activations correspond to vision locking after contact, not evidence that the intended gate worked.

Design, code, and logs are therefore inconsistent.

## 8. G-mode activation validation

G uses raw estimated force magnitude, a fixed 1 N deadband, and no contact gate or baseline subtraction. Its last-update timestamp is initialized to zero, so the update law runs during PREP.

Clean-log counts:

- 42/45 activated before task start;
- 43/45 activated before contact;
- 2/45 activated at or after contact;
- 45/45 first activations occurred with raw estimated force above 1 N;
- 42/45 activated before the force baseline was declared ready.

The evidence supports raw-force baseline, fixed deadband, and initialization as causes. Contact detection is not used by the G update law. No mixed-clock comparison is needed to explain G activation.

## 9. Output files

- `master_trial_manifest.csv`: all 186 records and their clean analysis roles.
- `data_lineage_audit.csv`: file existence and SHA-256 verification for all triplets.
- `trial_level_metrics.csv`: recomputed metrics for 180 valid trials.
- `timing_audit.csv`: unified timing and control-cycle audit for 180 valid trials.
- `participant_level_metrics.csv`: 5 participants × 4 modes.
- `statistics_summary.csv`: predefined participant-level inference.
- `leave_one_participant_out.csv`: LOPO sensitivity for every core metric and contrast.
- `contact_aligned_trajectories.csv`: clean trial-level force/stiffness trajectories.
- `contact_aligned_summary.csv`: participant-aggregated trajectory summaries.
- `old_new_trial_metric_comparison.csv`: historical-versus-clean trial values.
- `old_new_statistics_comparison.csv`: historical-versus-clean participant inference.
- `tables/`: compact result, timing, and validity tables.
- `figures/`: rebuilt diagnostic figures; these are analysis QA figures, not manuscript figures.
- `scripts/clean_analysis.py`: complete reconstruction script.

## 10. Reproduction command

```powershell
python F:\sun\sunhan\my_test\正宫\03_clean_analysis\scripts\clean_analysis.py
```

The script stops if the source manifest no longer contains 186 records/180 keys, if the selected main set is not exactly 180 unique keys, if the six user-confirmed validity decisions are not found, or if any raw companion file fails its recorded SHA-256 hash.
