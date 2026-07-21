# Data dictionary

## `01_frozen_tables/all_trials_135.csv`

One row is one physical trial.  The file has 135 rows, arranged as 27 matched
blocks with one trial in each mode A--E.

| Field | Meaning |
|---|---|
| `operator` | De-identified operator ID: P01--P03. |
| `group_num` | Preassigned operator-by-strategy schedule group (1--9). |
| `object_attr` | Strategy category in the source data: soft, medium, or hard. |
| `specific_object` | Object instance, recorded bilingually in the frozen source. |
| `mode` | Experimental mode A--E; see the manuscript Table 3. |
| `b_subtype` | Manual strategy-selection subtype used only in mode B. |
| `duration_s` | Completion time in seconds. |
| `traj_length_m` | Master-side trajectory length in metres. |
| `matched_block_id` | Matched block identifier MB01--MB27. |
| `outcome` | S = success; F = failure.  This was merged from the manual outcome registry. |
| `outcome_source` | Provenance of the outcome field. |
| `source_file` | Relative path to the archived objective trial summary. |

## `04_nasa_tlx/nasa_tlx_results/nasa.md`

Despite its `.md` extension, this is a UTF-8 CSV-formatted file.  It contains
45 questionnaire records: 3 operators x 3 strategy-level units x 5 modes.
The six demand columns range from 0 to 100.  Raw NASA-TLX is their unweighted
arithmetic mean.

## Scope limitations

The archive contains no event-level visual class, confidence, strategy-trigger,
contact-time, or synchronized trigger--contact logs from the formal trials.
It also contains no video-based independent re-rating of success/failure.
