# THMS LaTeX manuscript

This project contains the IEEE Transactions on Human-Machine Systems (THMS)
LaTeX manuscript for:

> From Nominal Conditions to Realized Interventions: A Fidelity Framework for
> Asynchronous Human--Machine Experiments

## Files
- `main.tex` — complete main manuscript
- `references.bib` — 36-entry BibTeX database
- `figures/` — four main figures in PDF format
- `main.pdf` — locally compiled review PDF

## Compile
Recommended:
1. pdflatex main
2. bibtex main
3. pdflatex main
4. pdflatex main

Equivalent one-command local build:

    latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

On Overleaf, upload the project and set `main.tex` as the main file.

## Core format
The journal currently asks authors to use the standard **IEEE Transactions
two-column format**. The LaTeX document therefore uses:

    \documentclass[journal]{IEEEtran}

For a regular paper, keep the submission at or below the journal's stated
maximum of 10 Transactions pages unless prior approval applies.

The current abstract is 250 words. The compiled manuscript is 9 Transactions
pages with the current anonymous-author placeholders.

## Notes
- Do not use the IEEE conference template (`conference` option).
- Avoid manually changing margins, font sizes, column spacing, or line spacing
  to force the paper under the page limit.
- Do not load the ordinary `caption` package with IEEEtran.
- Use vector PDF/EPS for plots whenever possible.
- THMS no longer normally publishes author photos/biographies for regular papers.

## Submission blockers

The author names, affiliations, and Hua Zhang's correspondence email have been
entered. Before submission, complete the remaining funding, conflict-of-interest,
author-contribution, acknowledgment, and data- and code-availability metadata.
Ethics approval or exemption and informed-consent procedures must be resolved
from contemporaneous institutional records; do not infer them from the archived
data.
