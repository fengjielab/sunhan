# V3 record-layer analysis specification

## Frozen cohort and evidence layers

- Input is exactly F01–F20 under `data/kfb_timing_formal_v1/participants`.
- The queue contains exactly 300 planned trial IDs. Historical `first_five`
  data are not scanned, copied, or merged.
- Scheduled truth comes only from the frozen protocol JSON and private oracle.
- `R_i^rec` contains logged intervention state, commanded gain, events, and the
  post-clamp command sent to the haptic API.
- `D_i^phys` is `NOT_INDEPENDENTLY_OBSERVED`; software command and API return
  are never treated as physical output confirmation.

## Primary record-layer endpoints

The primary set is the 294 completed, non-aborted, reconstructable trials. Six
safety aborts remain in the 300-trial flow and safety denominator.

- Condition classification accuracy with two-sided exact Clopper–Pearson 95% CI.
- Absolute onset-error MAE, P95, and maximum.
- Absolute outcome-window exposure-error MAE, P95, and maximum.
- Participant-level and condition-level estimates with 95% intervals.

Acceptance limits are classification at least 95%, timing MAE and P95 no more
than 20 ms, timing maximum no more than 50 ms, and exposure MAE no more than
0.02. At 200 Hz, 20 ms is four cycles and 50 ms is ten cycles; 50 ms also equals
the contact-confirmation hold. An exposure error of 0.02 equals 16 ms in the
0.8 s outcome window. These limits predated the present formal data but were not
preregistered.

## Command and variability analyses

- Clamp duration uses left-hold integration of `haptic_clamped` over contact
  +0.20 to +1.00 s.
- Command dose is the trapezoidal integral of logged post-clamp
  `haptic_cmd_norm` over the same window. It is labelled N·s only as a command
  unit, not independently measured physical impulse.
- Whole-trial and outcome-window clamp occurrence are reported separately.
- Human trajectory variability is described by task-start-to-contact duration,
  robot and Omega path length, robot peak speed, internal force impulse, and
  clamp rate.
- Participant-level criterion results are summarized across descriptive
  quartiles of approach duration, robot path, and clamp rate. No significance
  screening is performed.
- Human force contrasts use participants as independent units, remain
  exploratory, and are placed in the supplement.

## Reproducibility and claim controls

CSV sources require byte-exact SHA-256. Event and summary JSON additionally
permit canonical-text equality for BOM/newline-only differences. Two independent
runs must produce byte-identical analysis files. The manuscript may claim only
within-system record-layer criterion validation; physical delivery, external
validation, preregistration, and confirmatory human effects are out of scope.
