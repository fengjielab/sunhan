# Manuscript version 1 (Markdown package)

This directory contains an integrated English manuscript and a section-matched Chinese review translation. The integrated Markdown copies now contain the complete Figure 1–6 package. The frozen source chapters, original acquisitions, collection code, and `03_clean_analysis` directory were not modified.

## Deliverables

- `manuscript_v1_en.md`: integrated English manuscript version 1.
- `manuscript_v1_zh.md`: section-matched Chinese review translation.
- `figures/figure1_...` through `figure6_...`: 300-dpi PNG files embedded in both Markdown manuscripts and vector PDF equivalents.
- `scripts/generate_manuscript_figures.py`: one-command reproduction of all six figures from frozen clean-analysis CSV files.
- `figure_source_data/`: exact plotted extracts, the deterministic representative-trial selection, package versions, and SHA-256 hashes of all inputs.

## Source map

- Abstract: `17_abstract_writing/abstract_package.md`, recommended conservative Version 1.
- Introduction and Related Work: `15_introduction_related_work/`.
- Methods: `13_methods_writing/methods_draft.md`, mechanically renumbered from Section 2 to Section 3 in the integrated copy.
- Results: `12_results_writing/results_draft.md`.
- Discussion: `14_discussion_writing/discussion_draft.md`.
- Conclusion: `16_conclusion_writing/conclusion_package.md`, conclusion paragraph only.
- References: the 28 verified core entries in `15_introduction_related_work/verified_references.md`.
- Figures: regenerated from `03_clean_analysis/` using the manuscript-local plotting script. No raw acquisition is read directly by the figure script.

## Reproduce Figures 1–6

From this directory:

```powershell
python -m pip install -r scripts/requirements-figures.txt
python scripts/generate_manuscript_figures.py
```

The script checks 186 archived records, 180 selected trials, 45 trials per mode, five independent participants, and the four frozen primary impulse contrasts before plotting. Figure 6 uses a deterministic nearest-to-class-median selection rule rather than hand-picking visually extreme examples. See `scripts/README.md` for explicit path options and the complete output list.

## Submission blockers retained in version 1

- Authors and affiliations have not been inserted.
- Ethics approval/exemption and informed-consent information require verification.
- Participant demographics, training details, hardware/software metadata, and contemporaneous documentation for the six replacement acquisitions remain marked where relevant.
- Figure 1–6 are complete and reproducible. Table I is embedded; Tables II–IV remain to be formatted if required by the selected journal.
