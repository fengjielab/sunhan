# Ablation experiment code

`baseline_code_1c1ad02.zip` is the untouched code archive. All revision changes are
under `working/`.

For the first hardware pilot, follow
`../../03_ablation_protocol/PILOT_OPERATIONS.md` and use the separate
`pilot_schedule.csv`; do not use the 384-trial formal schedule.

## Hardware-free checks

From `working/my_test`:

```text
python -m unittest test_ablation_design.py
python -m py_compile interactive_teleop.py experiment_protocol.py ablation_design.py
python simulate_ablation.py --output ../../../07_analysis/ablation_mapping_check.json
```

## Pilot launch example

Use the exact next row in `03_ablation_protocol/randomization_schedule.csv` and replace
the example IDs accordingly:

Prefer the schedule launcher, which fills all metadata from the locked row. Omit
`--execute` for a dry run:

```text
python run_scheduled_trial.py \
  --schedule ../../../03_ablation_protocol/randomization_schedule.csv \
  --subject-id P01 --trial-order 1 --run-kind formal \
  --data-root ../../../06_formal_data \
  --yolo-model /absolute/path/to/locked_model.pt --execute
```

For an unscheduled pilot-only check, the lower-level command is:

```text
python interactive_teleop.py --mode I_H_G --run-kind pilot \
  --trajectory-dir ../../../05_pilot_data/PILOT01 \
  --subject-id PILOT01 --object-id apple --trial-id PILOT01_T01 \
  --session-id PILOT01_S1 \
  --schedule-id MECH-D-26-00641-PILOT-v1 \
  --trial-order 1 --repetition 1 \
  --haptic-force-limit 3.0 --yolo-model /absolute/path/to/locked_model.pt
```

## Formal launch rule

Formal launch uses `--run-kind formal` and a directory under `06_formal_data`. The
program rejects missing subject, object, trial, schedule, session, order, or repetition
metadata and writes an immutable UUID-named run configuration before hardware starts.

Do not use the historical C/D/E labels. They are intentionally absent from formal
choices. Do not change the force limit, visual model, confidence threshold, parameters,
or code after `FORMAL_LOCK.md` is signed.

## Runtime dependencies

Hardware execution requires the existing Omega.7 Force Dimension Python bindings,
`panda_py`, Franka/libfranka access, RealSense/`pyrealsense2`, OpenCV, Ultralytics, and
the exact locked model file. Analysis-only tests do not import hardware packages.
