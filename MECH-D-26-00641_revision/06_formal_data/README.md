# Append-only formal raw data

Formal collection is prohibited while `03_ablation_protocol/FORMAL_LOCK.md` says
`NOT LOCKED`. Each run must include the software-generated configuration, CSV,
events JSON, summary JSON, manual outcome row, and validation report. Never modify or
rename a raw acquisition file after validation; corrections belong in an audit log.

New acquisitions are grouped automatically as:

`P01/P01_S1/G01_apple_R1/`

Each `G##_object_R#` directory contains the four scheduled conditions for one object
and repetition. Technical repeat attempts remain in the same group with a new run
UUID. Existing flat pilot data are not moved or renamed.
