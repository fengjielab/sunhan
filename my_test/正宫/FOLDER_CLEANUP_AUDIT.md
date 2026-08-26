# Folder cleanup audit

## Direct answer

The complete current paper is in:

`F:\sun\sunhan\my_test\正宫\21_framework_first_submission_bundle`

The old `paper2_sci` path is a compatibility junction to `正宫` and should not be treated as a second copy.

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

### Duplicate data cleanup completed

- `01_primary_first_attempt_data/` and `01_selected_data/` were verified file-by-file against `data` using SHA-256 and removed.
- 1,080 duplicate files were removed; the audit record is `02_audit/cleanup_audit_20260826.json`.

## Remaining optional cleanup

Other historical and derived files remain because they were not part of this confirmed raw-data duplicate set.
