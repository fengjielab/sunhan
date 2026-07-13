Fig. 5 final plotting package
==============================

Files
-----
1. Fig5_a_completion_time_final.py
2. Fig5_b_trajectory_length_final.py
3. Fig5_c_nasa_tlx_final.py
4. Fig5_d_success_rate_final.py
5. Fig5_combined_final.py
6. all_trials_135.csv
7. nasa.md

Recommended command
-------------------
python Fig5_combined_final.py

The combined script writes 600-dpi PNG, vector PDF, and SVG files to ./outputs.

Custom paths
------------
python Fig5_combined_final.py \
  --trial-file /path/to/all_trials_135.csv \
  --nasa-file /path/to/nasa.md \
  --output-dir /path/to/output \
  --dpi 600

Design choices
--------------
- Circles, triangles, and squares identify P01, P02, and P03.
- Panels (a) and (b) display mode-specific task observations from matched blocks.
- Panel (c) shows nine strategy-level questionnaire units per mode and three operator-level means.
- Panel (d) shows descriptive success counts and percentages only.
- Mode C is highlighted consistently; no significance stars or general-population inference are shown.
