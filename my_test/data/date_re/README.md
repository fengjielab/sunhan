# Mechatronics v5 reproducibility archive

Version: 1.0.0  
Release date: 2026-07-22

This is the minimal reproducibility package for the associated haptic-teleoperation manuscript. It is prepared for deposit in Zenodo or another DOI-issuing repository.

## Contents

```text
data/
  trials.csv
  nasa_tlx.csv
  vision_test.csv
  parameter_mapping.csv
scripts/
  analysis.py
figures/
  fig1.jpg ... fig9.png
CITATION.cff
METADATA.txt
LICENSE.txt
README.md
```

Run the core analysis from this directory:

```powershell
python scripts/analysis.py
```

The script requires Python 3.10 or newer and NumPy. It checks the 135 trials in 27 matched blocks, reports the paired C--E bootstrap comparison, and summarizes the visual-validation and Raw NASA-TLX records.

The archive contains de-identified trial-level data. The parameter values are engineering-selected operating points, not material-strength limits. Video, synchronized per-trial visual/contact event logs, and detailed failure-type records are not included.

When depositing this archive, select the appropriate license, add the final manuscript DOI if one becomes available, and publish a versioned release. The repository will then mint the DOI.
