# Confirmatory 2x2 ablation protocol

Protocol ID: `MECH-D-26-00641-ABLATION-v1`  
Status: **repair candidate; pilot_v1 hardware smoke test required**
Formal lock requires the pilot gate and ethics fields below to be completed.

## Research question and hypotheses

All conditions use object-conditioned adaptive translational/rotational impedance (`I`).
The two randomized factors are object-conditioned master haptics (`H`) and
object-conditioned gripper execution (`G`).

- `I`: adaptive impedance; fixed haptics and fixed gripper.
- `I_H`: adaptive impedance and haptics; fixed gripper.
- `I_G`: adaptive impedance and gripper; fixed haptics.
- `I_H_G`: all three channels adaptive.

Primary tests are the main effects of `H` and `G` and the `H x G` interaction.
The full method is supported only if its contrast and/or interaction is estimated with
an uncertainty interval that excludes a practically negligible effect defined before
formal lock.

## Locked control parameters

Disabled channels use one neutral baseline for every object and condition:

| Parameter | Locked value |
|---|---:|
| Translational stiffness initial value | 150 N/m |
| Rotational stiffness initial value | 10 Nm/rad |
| Damping ratio initial value | 1.0 |
| Haptic gain `Kf` | 0.4 |
| Haptic deadband `d` | 0.4 N |
| Effective external-force threshold `d/Kf` | 1.0 N |
| Position scale | 3.0 |
| Gripper speed | 0.05 m/s |
| Requested gripper force | 15 N |
| Application haptic-force norm limit | 3.0 N |

Object profiles change `Kt`, `Kr`, and damping in all four conditions. They change
`Kf` and `d` only when `H=1`, and gripper speed/requested force only when `G=1`.
Position scaling, task geometry, controller frequency, visual model, confidence
threshold, and software force limit are common to all conditions.

## Participants, objects, and trial count

- Eight operators (`P01`-`P08`), with dominant hand used for Omega.7 operation.
- Six predefined objects: apple, banana, bottle, cup, mouse, and scissors.
- Four conditions and two repetitions per object.
- 48 formal trials per participant and 384 formal trials total.
- Two sessions per participant, 24 formal trials per session, preferably on separate days.
- Practice: at least one successful trial per condition before formal collection.
  Practice and pilot files must never enter `06_formal_data`.

The sample supports a participant-level mixed model but remains modest. Report effect
sizes and confidence intervals and limit claims to the tested predefined objects,
strategies, task, equipment, and operating conditions.

## Randomization and masking

Use only `randomization_schedule.csv`, generated with seed `260641`. Object order is
randomized for each participant and divided across two sessions. Condition order uses
a balanced Latin-square sequence and its reverse across repetitions. The schedule is
generated before data collection and must not be edited by hand.

The operator may see the detected object label but must not be told which H/G factors
are enabled. The experimenter follows the next schedule row and records deviations.

## Trial procedure

1. Verify consent/ethics record, dominant-hand setup, device calibration, force limit,
   camera view, object ID, initial pose tolerance, and clear workspace.
2. Launch exactly one scheduled condition with all required IDs. The software writes
   an immutable run configuration before connecting to hardware.
3. Keep the participant still during the one-second external-force baseline.
4. Start automatically only after the controller transition and baseline are ready.
5. The task is approach, grasp, transport to the marked target, and release.
6. Stop at successful open release or at 120 s. Record drops, collisions, slips,
   retries, unexpected strategy locks, and experimenter interventions.
7. Record the six raw NASA-TLX dimensions after each four-condition object block.
8. Run the trial validator immediately. A failed validation is retained as raw data,
   documented, and repeated only under the predefined repeat rule.

Repeat only for hardware/software interruption before the endpoint. Never repeat
because a result is slow or unsuccessful. Keep both attempts and mark the interrupted
one excluded with its predefined reason.

## Outcomes

Primary endpoint: time to successful release, capped at 120 s for an unsuccessful or
timed-out trial. The primary mixed model uses `log(time_s)` with fixed effects `H`,
`G`, `H x G`, object, trial order, and repetition, plus participant random intercept.

Secondary outcomes:

- success, drop, slip, collision, retry, and intervention rates;
- approach, grasp, transport, and release durations for completed trials;
- estimated Franka external-force peak/RMS by phase (not direct contact force);
- requested gripper force, measured aperture where available, and haptic command;
- haptic saturation count, deadline-miss rate, cycle-time percentiles and maximum;
- visual class/confidence, false trigger, no-lock/fallback rate, camera-to-result age,
  result-to-parameter transition latency, and update relative to contact;
- all six raw NASA-TLX dimensions and participant-level plots.

Sensitivity analyses: successful-only time, participant-cluster bootstrap, condition
order/repetition interactions, strategy/object strata, and exclusion of documented
hardware interruptions. No block-level p-values will treat trials as independent
participants.

## Pilot gate and formal lock

Pilot with one or two operators. Formal collection is prohibited until all items pass:

- four-condition software tests and schedule balance pass;
- every CSV contains schema v3 and all required metadata/timestamps;
- camera result age and parameter-transition latency are finite on mapped trials;
- phase events are ordered and the successful endpoint is detected correctly;
- force limiting is active and saturation events are logged;
- no unsafe oscillation, unexpected motion, or unhandled controller overrun occurs;
- one participant can complete 24 trials without excessive fatigue;
- parameter values, model file/hash, task timeout, and practical-effect threshold are
  recorded in `FORMAL_LOCK.md` and not changed thereafter;
- ethics institution, determination/reference number, and date are documented.

The repaired pilot schedule includes a 12-trial PILOT02 supplement covering banana,
scissors, and bottle. Together with cup, mouse, and apple in PILOT02 session 1, this
provides one four-condition hardware block for every formal object and a 24-trial
session-load check before formal lock. New files are grouped by object order and
repetition as `G##_object_R#`; existing raw files are never moved or renamed.

Pilot data are descriptive safety/feasibility data only.

## Pilot_v0 findings and restart rule

`PILOT01` pilot_v0 completed all 12 scheduled rows, but it is engineering evidence
only. The run exposed synchronous gripper-state reads in the control loop, an
incorrect deadline definition, missing strict object-lock checks, and no effective
H/G manipulation for the medium profile. Those issues were repaired before
pilot_v1.

Do not combine pilot_v0 with pilot_v1 or formal data. Before starting `PILOT02`, run
one hardware smoke trial with the repaired code and require: strict validator PASS,
the scheduled object and semantic label match, H/G manipulation checks pass, strict
JSON files parse, and measured control timing is reported without a severe warning.
If the nominal 200 Hz target remains infeasible after removing blocking I/O, lock and
report the measured update rate and weaken the real-time claim rather than repeatedly
retuning the experiment.
