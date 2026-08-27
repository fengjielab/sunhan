# Final SCI figure reproduction

This directory contains the final, script-generated publication figures for the manuscript. The workflow is read-only with respect to `03_clean_analysis`; it does not alter frozen data, selected records, fidelity classes, statistics, or conclusions.

## Requirements

```powershell
python -m pip install -r 19_publication_figures/requirements-figures.txt
```

Only Python, pandas, NumPy, Matplotlib, and SciPy are required. SciPy is retained for compatibility with the frozen statistical environment; the figure scripts do not recompute or optimize inferential results.

## Generate all figures

From `正宫`:

```powershell
python 19_publication_figures/scripts/generate_all_figures.py --root .
```

The same command may be run from the repository root:

```powershell
python my_test/正宫/19_publication_figures/scripts/generate_all_figures.py --root .
```

Every individual script also supports the required interface, for example:

```powershell
python 19_publication_figures/scripts/fig03_fidelity_results.py --root .
```

## Frozen QA gate

Every script first inspects and prints the actual clean CSV schema, then runs the same frozen-value QA gate. Generation stops before plotting if any expected value differs. The machine-readable report is `figure_qa_report.json`.

Checks include:

- 180 selected trials and 45 trials for each A/G/E/F configuration;
- G pre-contact activation 43/45 and executable compliance 45/45;
- F nominal +0.20-s compliance 3/45, median activation +0.0533 s, and median timing error -0.1467 s;
- E vision exposure 39 full / 2 partial / 4 zero;
- F vision exposure 42 full / 0 partial / 3 zero;
- F adaptation and joint exposure 35 full / 7 partial / 3 zero.

Current frozen-suite QA result: **PASS (11/11 checks)**. The new setup/process Figure 2 additionally passes **5/5 process-specific checks**, recorded in `figure02_process_qa.txt`.

## Figure map

| Figure | Script | Output stem (`.pdf`, `.svg`, `.png`) | Clean inputs | Panel meaning |
|---|---|---|---|---|
| Fig01 | `fig01_framework.py` | `Fig01_realized_intervention_framework` | conceptual definition and generated `figure01_source_data.csv` | Generic four-layer framework, three evidence interfaces, asynchronous event channels, and admissible interpretation; provenance is intentionally excluded |
| Fig02 | `fig02_process_evidence.py` | `Fig02_experimental_setup_and_process` | packaged `assets/experimental_setup.jpg`, `trial_level_fidelity_metrics.csv`, `contact_aligned_summary.csv` | (A) unmodified annotated setup photograph; (B) all 45 F event sequences summarized by trial points, IQRs, and medians; (C) contact-aligned excess force; (D) logged commanded stiffness |
| Fig03 | `fig03_fidelity_results.py` | `Fig03_realized_intervention_fidelity` | `trial_level_fidelity_metrics.csv`, `outcome_window_exposure.csv` | (A) all G trials ranked by activation latency with task/baseline/contact events; (B) all F trials relative to contact and the nominal +0.20-s gate; (C) full/partial/zero outcome-window exposure |
| Fig04 | `fig04_participant_outcomes.py` | `Fig04_participant_EA_outcomes` | `participant_level_metrics.csv`, `statistics_summary.csv`; `trial_level_fidelity_metrics.csv` for the 9-trial pre-aggregation QA only | Fidelity-bounded interpretation map plus the primary participant-level E-A excess-force-impulse result, including raw, multiplicity-adjusted, and exact inference |
| Fig05 / S1 | `fig05_contact_trajectories.py` | `Fig05_contact_aligned_trajectories` | `contact_aligned_summary.csv`; `contact_aligned_trajectories.csv` and `trial_level_fidelity_metrics.csv` for hierarchical-aggregation and commanded-`K_t` QA | Supplementary descriptive context: participant-aggregated contact-aligned excess force and logged commanded translational stiffness |
| Fig06 | `fig06_participant_lopo.py` | `Fig06_participant_lopo_stability` | `participant_level_metrics.csv`, `statistics_summary.csv`, `leave_one_participant_out.csv` | (A) individual E-A differences; (B) E-A LOPO; (C) F-E LOPO |
| Fig07 | `fig07_lineage_examples.py` | `Fig07_lineage_trace_examples` | `master_trial_manifest.csv`, `timing_audit.csv`, `contact_aligned_trajectories.csv` | (A) lineage replacements; (B) G timing; (C) F timing/trace; (D) post-contact vision lock |

## Outputs

Each figure produces:

- an editable vector PDF with TrueType text (`pdf.fonttype = 42`);
- an editable SVG with live text (`svg.fonttype = none`);
- a white-background PNG at 600 dpi or higher.

All files are saved with `bbox_inches="tight"` and `pad_inches=0.02` under `figures/`.

Each figure has one complete source-data extract under `figure_source_data/`:

- `figure01_source_data.csv` through `figure07_source_data.csv`.

Trial-level extracts retain `record_id`, trial identity fields, and a `source_row` where applicable. Sorting is stable and never removes record identity.

## Provenance manifest

`figure_manifest.json` records, per figure:

- figure name and script path;
- every clean input path and SHA-256 digest;
- source-data path and digest;
- PDF/SVG/PNG output paths;
- Python, NumPy, pandas, and Matplotlib versions;
- UTC generation timestamp.

## Visual conventions

- A: dark gray, circle, solid;
- G: blue, square, dashed;
- E: bluish green, triangle, solid;
- F: vermillion, diamond, dash-dot.

All human-outcome panels display the five participant-level observations. Trial-level fidelity panels explicitly state that trials are fidelity observations, not independent human samples for outcome inference. The THMS main manuscript uses Figures 1–4; Fig05, Fig06, and Fig07 are mapped to Supplementary Figures S1–S3. No smoothing, compliant-only filtering, manual point entry, or outcome-dependent trial selection is used.
