# Figure-source map for the current manuscript

| Manuscript figure | Source / status |
|---|---|
| Fig. 1 | Photograph; final raster asset is in `09_current_manuscript_snapshot/fig1.png`. |
| Fig. 2 | Final raster asset is frozen in `09_current_manuscript_snapshot/fig2.png`. The exact source script for this final timing diagram was not located. `current_figure_sources/generate_fig2_fig3.py` is a later candidate schematic and must not be substituted for the frozen asset. |
| Fig. 3 | Final raster asset is frozen in `09_current_manuscript_snapshot/fig3.png`. The exact source script for this final architecture diagram was not located. `09_current_manuscript_snapshot/演示文稿_before_revision.svg`, `演示文稿.svg`, and `current_figure_sources/Fig3_system_workflow.py` are editable working variants and must not be substituted for the frozen final PNG. |
| Fig. 4 | `07_analysis_and_figure_code/current_figure_sources/Fig4_Fig5_vision_split_final.py`, generated from `05_vision_validation_final_48_19ms/vision_validation/results/vision_validation_per_image.csv`. |
| Fig. 5 | Same source as Fig. 4, generated from the same 180-image frozen table. |
| Fig. 6 | `07_analysis_and_figure_code/current_figure_sources/Fig6_completion_time_final.py`; generated from `01_frozen_tables/all_trials_135.csv`. |
| Fig. 7 | `07_analysis_and_figure_code/current_figure_sources/Fig7_workload_success_final.py`; generated from `04_nasa_tlx/nasa_tlx_results/nasa.md` and the observed frozen-mode success counts. |
| Fig. 8 | `07_analysis_and_figure_code/current_figure_sources/Fig8_paired_ce_standardized.py`; generates the paired C--E analysis from `01_frozen_tables/all_trials_135.csv`. |
| Fig. 9 | `07_analysis_and_figure_code/current_figure_sources/Fig9_operator_object_standardized.py`; generates operator/object-stratified C--E summaries from `01_frozen_tables/all_trials_135.csv`. |

Figures 4--9 have bundle-relative generation paths and their regenerated PNGs
were verified byte-for-byte against the frozen manuscript assets. Figure 7
imports `Fig5_combined_final_helper.py`, which is preserved beside its source.
Figures 2--3 are retained as frozen final rasters because their exact source
scripts were not located; the available working diagrams remain provenance
material only and must not replace the frozen assets. The core entry point is
the formal manuscript-aligned check; regenerated figures should be compared
against the frozen manuscript raster before replacing a submission figure.
