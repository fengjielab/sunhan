# v3 method-strengthening reproduction

Run from this directory with:

```powershell
python validate_v3.py
```

The script performs four read-only analyses of frozen source inputs and writes versioned outputs under
`04_logic_and_qa/v3/` and `03_supplement/v3_data/`:

1. exact oracle checking for 11 deterministic evidence-state perturbations;
2. exhaustive enumeration of all 64 initial/replacement record selections;
3. E non-full exposure mechanism reconstruction and F mixed-clock source-signature checking;
4. SHA-256 verification that v1, v2, and their shared main figures remain unchanged.

The controlled cases are an internal discrimination check of the implemented decision rules. They are not
external validation of the framework, and the classifier does not ingest outcome values, effect directions,
or p values.

Generate the two wording-bearing v3 figures without touching the v2 outputs with:

```powershell
python generate_v3_figures.py
```

The figure generator writes only to `02_main_figures/v3/` and stores v3 source data beside these scripts.
