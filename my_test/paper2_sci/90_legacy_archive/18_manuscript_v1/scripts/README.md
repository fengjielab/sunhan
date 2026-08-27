# Reproducing manuscript Figures 1–6

The plotting workflow reads only frozen outputs under `03_clean_analysis/`. It does not modify raw acquisitions, acquisition code, or clean-analysis CSV files.

From `18_manuscript_v1/`, run:

```powershell
python -m pip install -r scripts/requirements-figures.txt
python scripts/generate_manuscript_figures.py
```

Optional explicit paths:

```powershell
python scripts/generate_manuscript_figures.py `
  --clean-dir ..\03_clean_analysis `
  --output-dir .\figures `
  --source-data-dir .\figure_source_data `
  --dpi 300
```

Outputs:

- `figures/figure1_reconstruction_framework.{png,pdf}`
- `figures/figure2_realized_timing_audit.{png,pdf}`
- `figures/figure3_ea_safety_efficiency.{png,pdf}`
- `figures/figure4_contact_aligned_trajectories.{png,pdf}`
- `figures/figure5_participant_lopo_stability.{png,pdf}`
- `figures/figure6_lineage_trace_examples.{png,pdf}`
- `figure_source_data/*.csv`: exact plotted extracts and deterministic Figure 6 trial selection
- `figure_source_data/figure_generation_metadata.json`: package versions and SHA-256 hashes of every clean input

The script checks the frozen record counts, mode balance, participant count, and the four principal impulse contrasts before plotting. Figure 6 selects representative records by the smallest absolute distance to the relevant class median, with `record_id` as the tie-breaker; no visually dramatic trial is hand-selected.
