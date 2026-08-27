# v4 artifact-to-state reproduction

Run from the review-bundle root:

```powershell
python 05_reproduction/v4/validate_v4.py
python 05_reproduction/v4/generate_v4_figures.py
python 05_reproduction/v4/qa_v4.py
```

The v4 pipeline implements two explicitly separated stages:

1. `ArtifactEvidence -> EvidenceState`: specification/source audit, trajectory replay, exposure integration, and exact provenance checks;
2. `EvidenceState -> Decision`: cumulative diagnostics, nominal identity, comparison level, and wording constraints.

Key boundaries:

- automatic computation is separated from structured author audit;
- no independent dual-review claim is made;
- neither interface accepts outcomes, effect directions, p values, or significance;
- `c_to_r=not_evaluable` can coexist with recoverable exposure;
- controlled cases are rule-level implementation verification/internal discrimination, not methodological or external validation;
- the scripts write only versioned v4 outputs and verify frozen v1–v3 hashes.

Inputs and oracles are stored separately from executable logic:

- `artifact_to_state_rules.csv`
- `structured_semantic_audit.csv`
- `controlled_artifact_cases.csv`
- `baseline_hashes.json`

Generated tables are written to `03_supplement/v4_data/`; validation and QA reports are written to `04_logic_and_qa/v4/`; figures are written to `02_main_figures/v4/`.
