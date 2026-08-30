# Implementation status

Updated: 2026-08-30

## Completed

- Submitted commit `1c1ad02` tagged `MECH-D-26-00641-submitted`.
- Submitted source archived, expanded, hashed and marked read-only.
- Reviewer PDFs copied, visually checked and hashed.
- Revision manuscript is physically separated from the submitted tree.
- Review-response matrix covers Reviewer A and all 25 Reviewer B points.
- Four-condition hardware-independent design implemented and unit tested.
- Neutral baseline is consistent across disabled channels.
- Formal C/D/E names removed from the launch interface.
- Schema-v3 acquisition adds perception/queue/update timestamps, phase events,
  haptic base/aperture/final commands, force limiting/saturation, controller timing,
  factor flags, schedule metadata and code/model provenance.
- Task start waits for visual lock and parameter-transition completion; a 10-s lock
  timeout aborts pilot/formal runs instead of silently using a fallback.
- Deterministic balanced 384-trial schedule generated and validated.
- Separate 24-trial pilot schedule and dry-run/execute launcher generated; the launcher
  automatically validates each newly saved pilot trial.
- Pilot/formal directory guards, UUID filenames and exclusive file creation prevent
  accidental pooling or raw-file overwrites.
- Trial validator, verified backup tool, trial-table builder, mixed models,
  phase-wise models and participant/phase plotting scripts are implemented.

## Passed software checks

- 5 ablation mapping unit tests.
- 2 validation/analysis unit tests.
- Python syntax compilation for acquisition, protocol, launcher and analysis tools.
- Hardware-free soft/medium/hard x four-condition mapping simulation.
- Empty-data analysis smoke test confirms that no results are fabricated.

## Not completed because real-world input/data are required

- Ethics institution, exemption/approval reference and determination date.
- Authoritative Omega.7 device force/servo specifications and final safety review.
- Locked visual model file and SHA-256 on the experiment computer.
- One-to-two-operator hardware pilot and its validation reports.
- Formal protocol lock and 384 human trials.
- Confirmatory estimates, figures and numerical reviewer responses.
- Data-dependent manuscript revision and public repository DOI.

The next permissible step is the hardware pilot. Formal data collection is blocked
while `03_ablation_protocol/FORMAL_LOCK.md` remains `NOT LOCKED`.
