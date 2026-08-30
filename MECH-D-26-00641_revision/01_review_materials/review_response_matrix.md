# Review-response matrix

Legend: `implemented` means revision infrastructure/code is present; `requires data`
means the response cannot be finalized before pilot/formal collection; `author input`
means factual information must come from the authors.

## Reviewer A (`comments.pdf`)

| ID | Core concern | Planned evidence/change | Status |
|---|---|---|---|
| A1 | Full multi-channel adaptation is not isolated; gripper-only missing | New `I`, `I_H`, `I_G`, `I_H_G` 2x2 experiment and H/G interaction model | implemented; requires data |
| A2 | Why master haptics matter; not fingertip grasp-force feedback | Define it as estimated arm/environment kinesthetic feedback; log `u_h_base`, aperture cue and final command; narrow claims | implemented; requires manuscript edit |
| A3 | Effects of `Kt`, `Kr`, `Kf` unclear | Phase-wise force/command plots plus separate standardized parameter-range characterization | logging implemented; requires data |
| A4 | Gripper speed directly affects total time | Report approach/grasp/transport/release durations; fixed gripper in `G=0` cells | implemented; requires data |
| A5 | C-E intervention differs by strategy | Replace pooled C-E causal interpretation with balanced factorial contrasts and strategy/object strata | implemented; requires data |
| A6 | Meaning of 200 Hz unclear | Report application-loop distribution, jitter, misses and relation to device/robot inner loops | logging implemented; requires device facts |
| A7 | Stability/passivity not established | Smooth impedance and haptic gain transitions; software force limit and saturation log; add bounded-range experimental stability assessment and limitation | partially implemented; requires assessment |

## Reviewer B (`reviewer_report.pdf`)

| ID | Core concern | Planned evidence/change | Status |
|---|---|---|---|
| B1 | Three participants and block-level pseudoreplication | Eight-participant confirmatory study; participant random-intercept model; old 135 trials descriptive only | protocol implemented; requires data |
| B2 | Order, learning and fatigue confounding | Seeded balanced schedule, two sessions, trial-order/repetition covariates, publish full schedule | implemented |
| B3 | No online perception records | Capture/inference/result/update timestamps, class, confidence, queue age, lock/fallback and update-to-contact | implemented; requires pilot validation |
| B4 | No channel-level ablation | Four-cell 2x2 H/G experiment | implemented; requires data |
| B5 | Mode-E baseline mismatched | Neutral baseline fixed at `[150,10,1.0,0.5,0.4,0.05,15]`; no old C/E causal claim | implemented |
| B6 | Engineering screening undocumented | Freeze candidate ranges, screening sample, acceptance criteria and independence; run nearby-value sensitivity | requires author records/data |
| B7 | Manual object categories lack mechanical criteria | Measure/document dimensions and at least operational compliance/slip criteria; describe mapping as predefined lookup | requires measurements/manuscript edit |
| B8 | No direct force/deformation/slip/video evidence | Label Franka force as estimated and gripper force as requested; record aperture and blinded slip/drop outcomes; narrow safety/deformation claims unless sensors/video added | forms/logging implemented; requires data |
| B9 | 200-Hz jitter and queue age | Log start-to-start period, compute time, overrun, miss rate, max/percentiles and visual queue age | implemented; requires data |
| B10 | Force saturation and stability | 3-N configurable software norm limit, saturation field and smoothed `Kf/d`; document device limits | implemented; device-limit facts required |
| B11 | One-shot 0.25 lock lacks robustness | Preserve every detection event; add threshold/occlusion/distractor/unknown tests and compare multi-frame policy offline before deciding whether to change lock rule | logging implemented; robustness study required |
| B12 | Generalization and novelty overstated | Limit title/abstract/conclusion to predefined objects, strategies and task; contrast with object-conditioned/shared-control work | requires manuscript edit |
| B13 | Left-hand use and phase definitions | Use dominant hand; define and log task/phase endpoints and initial-pose tolerance | implemented |
| B14 | Broad performance claim and post-hoc success analysis | Primary capped time-to-success at 120 s; success model and successful-only sensitivity; use “completion time” language | protocol implemented; requires data |
| B15 | Literature incomplete | Verify and cite the six suggested papers and related primary literature | requires literature work |
| B16 | `D_API=2ζ√K` units unclear | Describe it as the API parameterization/damping-ratio setting, not a complete dimensionally explicit Cartesian dynamics equation; document API | requires manuscript edit/device docs |
| B17 | Impedance error sign undefined | Define desired-minus-actual or actual-minus-desired consistently with implementation | requires manuscript edit |
| B18 | Aperture cue is self-generated, not remote feedback | Rename to master-aperture cue; log separately as `u_g_aperture_N`; do not call it grasp-force feedback | implemented; manuscript edit required |
| B19 | `Kf` and `d` jointly change `d/Kf` | Log/report effective threshold for every sample and profile | implemented |
| B20 | Fixed width 0 m and 0.080-m tolerance | Explain Franka `grasp` semantics, actual aperture measurement and object-size implications; tighten success endpoint if hardware permits | logging implemented; author/device check required |
| B21 | Raw NASA-TLX dimensions absent | Use six-dimension raw template and report dimensions separately | implemented; requires data |
| B22 | Participant plots and CIs absent | Produce participant-level plots and CIs; avoid object-level inference from blocks | analysis requirement; requires data |
| B23 | Ethics issuer/reference absent | Formal lock requires institution, reference/determination and date | author input required; formal collection blocked |
| B24 | Public repository required | Prepare anonymized trial data, schedule, code, detector/configuration and parameter files; deposit after checks | workspace prepared; external deposit pending |
| B25 | Figure readability | Render at journal final column width and inspect fonts/annotation density | final QA pending |

## Critical-path order

1. Complete ethics facts and pilot gate.
2. Pilot and validate schema-v3 acquisition.
3. Lock protocol/code/model hashes.
4. Collect 384 formal trials and manual outcomes.
5. Run confirmatory and sensitivity analyses.
6. Revise manuscript and replace every `requires data` item with exact results/locations.
