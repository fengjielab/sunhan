# Minimum reproducibility package

This is the reviewer-facing minimum package for the haptic-teleoperation manuscript. It contains the data and code needed to reproduce the main descriptive results and the primary paired C--E bootstrap comparison.

## Contents

```text
data/
  trials.csv              135 de-identified trials in 27 matched blocks
  nasa_tlx.csv            45 Raw NASA-TLX questionnaire records
  vision_test.csv         180 closed-set visual-validation records
  parameter_mapping.csv   object-to-strategy and parameter mapping
scripts/
  analysis.py             core summary and bootstrap analysis
figures/
  fig1.jpg, fig2.png--fig9.png   final manuscript raster assets
README.md
```

Run the core check from this directory with Python 3.10 or newer:

```powershell
python scripts/analysis.py
```

The script reports the 27 matched blocks, the mean C--E completion-time difference, the matched-block bootstrap interval, trajectory-length interval, visual-test summary, and Raw NASA-TLX means. NumPy is the only external Python dependency.

The trial file uses anonymous operator IDs (`P01`--`P03`) and contains completion time, trajectory length, outcome, object, mode, and matched-block identifiers. Failure labels are coded `S` or `F`. The vision file contains true/predicted classes, confidence, inference time, and class/mapping correctness. Parameter values are engineering-selected operating points and are not material-strength limits.

The full archival bundle remains in the numbered directories (`01_frozen_tables`--`09_current_manuscript_snapshot`), including raw trajectory CSVs, source JSON summaries, supplementary tables, and provenance material. Video, synchronized per-trial visual/contact event logs, and detailed failure-type records were not retained and are not claimed as available.
