# Framework-first manuscript package

This directory contains the current integrated English manuscript. The scientific narrative is organized as an operational realized-intervention fidelity framework followed by a retrospective teleoperation case study. Original acquisitions, acquisition code, and frozen clean-analysis results are not modified by this package.

## Current manuscript

- `manuscript_v1_en.md`: current framework-first English manuscript.
- `manuscript_v1_zh.md`: an earlier section-matched Chinese review copy; it has **not** yet been synchronized to the framework-first English structure and must not be treated as the submission source.

## Journal-facing figures and supplement

- THMS main Figures 1–4: `../19_publication_figures/figures/`.
- Supplementary Figures S1–S3: the same package's `Fig05`, `Fig06`, and `Fig07`, mapped in `../20_submission_package/supplementary_material.md`.
- Figure source extracts, hashes, scripts, and a machine-readable manifest: `../19_publication_figures/`.
- Supplementary Tables S1–S4 and submission blockers: `../20_submission_package/`.

The manuscript-local `figures/` and `scripts/` directories are retained as a legacy version-1 figure package. The journal-facing source of truth is `../19_publication_figures/`; do not mix the two figure sets in a submission.

## Reproduce the current figures

From `paper2_sci`:

```powershell
python -m pip install -r 20_submission_package/requirements-analysis.txt
python 19_publication_figures/scripts/generate_all_figures.py --root .
```

The figure QA gate checks the frozen 180-trial dataset, the configuration-level fidelity counts, exposure classes, and participant-level inputs before plotting. See `../19_publication_figures/FIGURE_REPRODUCTION_README.md` for individual commands and output details.

## Current submission blockers

Authorship, ethics/consent, declarations, repository identifiers, and journal-specific formatting remain unresolved. The authoritative checklist is `../20_submission_package/SUBMISSION_REQUIRED_INFORMATION.md`. Values marked `[NEEDS VERIFICATION]` must be recovered from contemporaneous records or disclosed as limitations; they must not be inferred.
