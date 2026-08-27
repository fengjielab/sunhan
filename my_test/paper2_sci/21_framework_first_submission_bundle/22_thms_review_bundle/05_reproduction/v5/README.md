# v5 human–machine-loop-oriented revision

Run from the review-bundle root:

```powershell
python 05_reproduction/v5/validate_v5.py
python 05_reproduction/v5/generate_v5_figures.py
python 05_reproduction/v5/qa_v5.py
```

The v5 package changes narrative order and figure responsibilities without changing the frozen scientific interfaces, evidence states, deterministic rules, analysis data, or statistics.

- `validate_v5.py` reruns the v4 evidence validation and verifies that the captured v4 manuscript/supplement/core-script hashes remain unchanged.
- `generate_v5_figures.py` writes only `02_main_figures/v5/` and the v5 figure report. Figures 3 and 4 read frozen v4/v3 source tables directly.
- `qa_v5.py` checks section/table/figure order, frozen statements, Methods–Results separation, prohibited causal wording, image dimensions, references, supplement links, and the ethics blocker.

Versioned outputs are written to `04_logic_and_qa/v5/`. The current manually edited v4 manuscript is a protected baseline.
