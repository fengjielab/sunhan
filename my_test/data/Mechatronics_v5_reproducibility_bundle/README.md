# Reproducibility bundle: Object-Conditioned Strategy-Level Joint Parameter-Bundle Configuration for Haptic Teleoperation

This bundle preserves the de-identified data, analysis material, figure sources, and manuscript snapshot supporting the associated haptic-teleoperation study.  It is organised so that a reviewer can reproduce the manuscript-aligned core checks without relying on historical scripts whose assumptions no longer match the revised paper.

## Quick start

From the bundle root, use Python 3.10 or newer:

```powershell
python -m pip install -r requirements.txt
python run_core_reproduction.py
```

The entry point runs `verify_bundle.py` and the manuscript-aligned paired C--E bootstrap analysis.  Expected core outputs are a C--E completion-time difference of 1.795 s and a 95% percentile-bootstrap interval of [1.104, 2.508] s, displayed in the manuscript as 1.79 s and [1.10, 2.51] s.

## Contents

- `01_frozen_tables/`: the 135 de-identified trial records. `all_trials_135.csv` includes matched-block identifiers, completion time, trajectory length, success/failure outcome, and outcome provenance. `all_trials_135_objective_only_original.csv` is retained as the pre-merge objective-metric table.
- `02_objective_trial_sources/`: the 135 source JSON summaries referenced by the frozen table.
- `02_raw_trajectory_csv/`: one master-trajectory CSV for each frozen trial.
- `03_outcome_registry/`: Supplementary Table S1 (outcomes) and Tables S2--S3 (mode sequences and evidence boundaries).
- `04_nasa_tlx/`: raw NASA-TLX records and summaries. `nasa.md` is comma-separated data despite its historical extension.
- `05_vision_validation_final_48_19ms/`: frozen 180-image closed-set vision-validation inputs, results, and images. The mean per-image inference time in `vision_validation/results/vision_validation_per_image.csv` is 48.192906 ms.
- `06_cycle_timing/`: retained cycle-timing traces and their original notes. They are not used to support the revised manuscript's online-latency or hard-real-time claims.
- `07_analysis_and_figure_code/`: core analysis entry points, preserved figure-source scripts, and explicit notes distinguishing current from legacy scripts.
- `08_manuscript_snapshot/`: historical manuscript snapshot retained for provenance only.
- `09_current_manuscript_snapshot/`: current submission snapshot, including LaTeX source, bibliography/style files, figures, and compiled PDF.

`DATA_DICTIONARY.md` defines the data fields and `FIGURE_SOURCE_MAP.md` maps manuscript figures to the available source material.

## Verified data relationships

- The frozen table has 135 trials: 27 matched blocks, each containing modes A--E.
- S1 has 135 entries and matches the frozen records at the displayed precision for completion time and trajectory length.
- Observed success counts are A=22, B=21, C=26, D=24, and E=24.
- The primary C--E analysis resamples the 27 matched blocks, not 135 trials independently.

## Scope and evidence boundaries

This package supports the paper's system-level, within-sample evidence for the tested closed object set. It does **not** establish independent haptic/gripper effects, their interaction, unknown-object generalisation, verified pre-contact configuration, end-to-end triggering latency, or hard-real-time performance. The formal trials did not retain synchronized per-trial visual class/confidence, trigger timestamp, strategy-assignment timestamp, or contact timestamp. Video and a detailed failure taxonomy were likewise not retained. These items cannot be reconstructed from the archived files.

The cycle-time notes contain an internal discrepancy (the stated cycle total does not equal the CSV row total); therefore those traces are provided as provenance rather than a current performance claim. The archived trajectory inputs are available, but the historical pause-count smoothing/threshold rule cannot yet reproduce the reported pause values exactly; pause results should remain exploratory until that implementation is recovered.

## Current versus legacy code

Use only `run_core_reproduction.py`, `verify_bundle.py`, and `07_analysis_and_figure_code/bootstrap_ci_ce.py` to check the manuscript-aligned core result. `07_analysis_and_figure_code/LEGACY_SCRIPTS.md` documents scripts retained for provenance that must not be used as the reproduction authority, because they contain historical paths or analyses/conclusions no longer used in the revised manuscript.

## Release actions required before public deposition

1. Choose and add a repository `LICENSE` (the authors/depositor must make this legal choice).
2. Deposit this exact directory to a public repository such as Zenodo or Figshare and add its DOI to the manuscript data-availability statement and `CITATION.cff`.
3. Confirm that all required consent/ethics and de-identification conditions permit the chosen license and public release.

No DOI or license is claimed in this local working copy.
