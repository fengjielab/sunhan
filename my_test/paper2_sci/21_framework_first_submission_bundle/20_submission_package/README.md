# Submission package

This directory assembles the journal-facing materials for the framework-first manuscript without changing original acquisitions or frozen clean outcomes.

## Contents

- `supplementary_material.md`: metric dictionary, fidelity summary, exploratory statistics, historical-versus-clean sensitivity, and Supplementary Figures S1–S2.
- `SUBMISSION_REQUIRED_INFORMATION.md`: unresolved information that must be verified rather than inferred.
- `MANUSCRIPT_READINESS_AUDIT.md`: completed work, evidence boundaries, submission blockers, and the final release gate.
- `requirements-analysis.txt`: pinned versions from the verified local analysis/figure environment (Python 3.13.5).
- `scripts/qa_manuscript.py`: checks the manuscript narrative and main/supplement figure wiring against frozen clean outputs.
- `manuscript_qa_report.json`: machine-readable result of the manuscript QA gate.

## Reproducible evidence chain

1. Archived source manifest and read-only acquisitions.
2. `03_clean_analysis/scripts/clean_analysis.py`.
3. `03_clean_analysis/scripts/fidelity_analysis.py`.
4. Clean QA (`38/38`) and fidelity QA (`30/30`).
5. Participant-level aggregation and frozen statistics.
6. `19_publication_figures/scripts/generate_all_figures.py`.
7. Main manuscript and this supplement.

Run from `paper2_sci` after installing the pinned packages:

```powershell
python -m pip install -r 20_submission_package/requirements-analysis.txt
python 03_clean_analysis/scripts/clean_analysis.py
python 03_clean_analysis/scripts/qa_clean_analysis.py
python 03_clean_analysis/scripts/fidelity_analysis.py
python 03_clean_analysis/scripts/qa_fidelity_analysis.py
python 19_publication_figures/scripts/generate_all_figures.py --root .
python 20_submission_package/scripts/qa_manuscript.py --root .
```

The repository location/DOI, license, ethics statement, and author declarations remain submission blockers listed in `SUBMISSION_REQUIRED_INFORMATION.md`.
