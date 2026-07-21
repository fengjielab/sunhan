# Reproduction verification record

Verification was run locally on 2026-07-21 with the bundle contents frozen at that time.

## Core data checks

`python run_core_reproduction.py` completed successfully.

- 27 matched blocks and 135 frozen trials were found.
- 135 raw trajectory logs and 135 S1 outcome entries were found.
- The C--E completion-time bootstrap 95% interval was `[1.104, 2.508]` s.
- The C--E trajectory-length bootstrap 95% interval was `[-0.0142, 0.0591]` m.
- The closed-set vision-table mean was `48.192906` ms per image.

## Figure checks

The following source scripts regenerated PNG files whose SHA-256 hashes exactly matched the corresponding frozen manuscript assets in `09_current_manuscript_snapshot/`:

| Manuscript asset | Bundle-relative source |
|---|---|
| `fig4.png` | `07_analysis_and_figure_code/current_figure_sources/Fig4_Fig5_vision_split_final.py` |
| `fig5.png` | `07_analysis_and_figure_code/current_figure_sources/Fig4_Fig5_vision_split_final.py` |
| `fig6.png` | `07_analysis_and_figure_code/current_figure_sources/Fig6_completion_time_final.py` |
| `fig7.png` | `07_analysis_and_figure_code/current_figure_sources/Fig7_workload_success_final.py` |
| `fig8.png` | `07_analysis_and_figure_code/current_figure_sources/Fig8_paired_ce_standardized.py` |
| `fig9.png` | `07_analysis_and_figure_code/current_figure_sources/Fig9_operator_object_standardized.py` |

The final Fig. 2 and Fig. 3 PNG assets are preserved, but their exact original generation scripts were not found in the manuscript project. Two editable SVG working files for Fig. 3 variants (`演示文稿_before_revision.svg` and `演示文稿.svg`) are retained in the current manuscript snapshot as provenance only. Candidate scripts and SVG work files are intentionally not claimed as exact reproducers of the frozen final Fig. 2--3 PNG assets.
