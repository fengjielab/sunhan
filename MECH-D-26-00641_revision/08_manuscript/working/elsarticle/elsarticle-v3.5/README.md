# Mechatronics LaTeX manuscript

Open `main.tex` in VS Code; it is the only compilation entry point. Edit the numbered chapter files, `declarations.tex`, `references.bib`, or the figure PNG files as needed. In LaTeX Workshop, run the recipe `pdflatex -> bibtex -> pdflatex x2`.

Project files are intentionally flat for Editorial Manager submission. `supplementary.tex` is a separate editable supplementary document and `highlights.txt` is uploaded as a separate Highlights file. `main.pdf` and `supplementary.pdf` are local verification outputs, not source files.

The reproducibility bundle is archived on Zenodo at https://doi.org/10.5281/zenodo.21486014. It contains de-identified data, final Fig. 1--Fig. 8 and Supplementary Fig. S1 image assets, the core analysis script, and accompanying checksums, citation information, licence, and metadata.

`analysis.py` is the core-results reproduction script. It reads `trials.csv`, `vision_test.csv`, and `nasa_tlx.csv`. This script reproduces the main descriptive statistics and the primary paired C--E bootstrap comparison: the 135 trials and 27 matched blocks, the C--E completion-time difference, completion-time and trajectory-length bootstrap confidence intervals, A--E mean completion times, visual classification accuracy and inference time, and Raw NASA-TLX means.
