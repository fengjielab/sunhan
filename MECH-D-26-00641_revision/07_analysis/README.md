# Validation and confirmatory analysis

Validate every acquisition immediately:

```text
python validate_trial.py path/to/I_H_G_<run-uuid>.csv
```

After formal collection, build the trial table and fit the prespecified model:

```text
python analyze_ablation.py ../06_formal_data --output-dir formal_results
```

The analysis requires NumPy, pandas, and statsmodels. With no formal data, it writes an
empty table and status file rather than manufacturing results.

Create a timestamped external backup after each collection day:

```text
python backup_formal_data.py ../06_formal_data X:/MECH_backups
```

The backup destination must be outside the formal-data directory. A same-disk copy is
not a disaster-recovery backup.
