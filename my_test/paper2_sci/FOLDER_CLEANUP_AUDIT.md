# Folder cleanup audit

## Direct answer

The complete current paper is in:

`F:\sun\sunhan\my_test\paper2_sci\21_framework_first_submission_bundle`

No other top-level manuscript or figure directory should be treated as the current submission version.

## Safe cleanup boundary

### Keep at the top level

- `21_framework_first_submission_bundle/`: current paper and submission package.
- `02_audit/`, `03_processed_data/`, and `03_clean_analysis/`: inputs/outputs required by the current hard-coded clean rebuild path.
- `README.md` and this audit.

### Keep outside this folder

- `F:\sun\sunhan\my_test\data\ral_date`: original read-only acquisitions.

### Moved to the reversible legacy archive

- Directories `04_statistics/` through `17_abstract_writing/` listed individually in the root README.
- Original working copies `18_manuscript_v1/`, `19_publication_figures/`, and `20_submission_package/`, because snapshots are already present in the bundle.
- `analysis_summary.json`, which belongs to an earlier analysis narrative.

All 18 items were moved to `90_legacy_archive/`. Nothing was deleted.

### Do not automatically delete

- `01_primary_first_attempt_data/` and `01_selected_data/` together occupy approximately 480.82 MB. They appear to be data copies rather than the current raw-data read path, but deletion requires an exact file/hash comparison against `data/ral_date` and confirmation that no external workflow depends on them.

## Remaining optional cleanup

Perform the two large data-copy decisions separately after a hash audit. Until then, keep both `01_*` directories unchanged.
