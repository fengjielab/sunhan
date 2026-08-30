# MECH-D-26-00641 major revision workspace

This directory is physically separated from the submitted manuscript tree.
The frozen baseline is commit `1c1ad02`, tagged `MECH-D-26-00641-submitted`.

## Directory policy

- `00_submitted_snapshot`: immutable submitted source and integrity manifest.
- `01_review_materials`: editor/reviewer files and the response matrix.
- `02_response_letter`: point-by-point response drafts.
- `03_ablation_protocol`: locked protocol, schedules, and case-report forms.
- `04_experiment_code`: baseline archive and working ablation code.
- `05_pilot_data`: pilot-only data. Never pool with formal data.
- `06_formal_data`: append-only formal raw data and daily backups.
- `07_analysis`: validation and statistical analysis code/outputs.
- `08_manuscript`: revision manuscript working copy.
- `09_resubmission_package`: verified final upload package only.

Do not modify the original `elsarticle/elsarticle-v3.5` tree during revision.
Do not manually edit raw CSV/JSON files after acquisition.
