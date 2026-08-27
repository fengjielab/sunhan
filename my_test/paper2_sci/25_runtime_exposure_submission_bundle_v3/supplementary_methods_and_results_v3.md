# Supplementary methods and results v3

## S1. Layer-specific interpretation

| Layer | Evidence in this study | Status | Permitted interpretation |
|---|---|---|---|
| Nominal specification, `N_m` | Frozen protocol and private oracle | Supported | Scheduled condition truth |
| Code implementation, `C_m` | Versioned acquisition software and offline parser | Supported with common-source limitation | Implementation trace within one software ecosystem |
| Recorded state, `R_i^rec` | Events, `intervention_state`, `K_fb_commanded` | Within-system criterion validated | Activation timing and outcome-window exposure recovery |
| Sent command, within `R_i^rec` | Post-clamp command, clamp flag, API return | Observed software record | Command-layer saturation and command integral |
| Physical delivery, `D_i^phys` | No independent output sensor | Not independently observed | No physical-dose or end-to-end delivery claim |
| Human outcome, `Y_i` | Franka internal external-wrench estimate | Exploratory | Participant-level descriptive comparison only |
| Provenance, `P_i` | Trial identity and SHA-256 | Supported | Source linkage, not proof of delivery |

## S2. Record-command layer

Among 294 evaluable trials, 65 contained at least one command clamp anywhere in
the trial and 47 contained a clamp in the 0.20–1.00 s outcome window.

| Condition | Evaluable | Any-time clamp | Window clamp | Mean window clamp fraction | P95 | Maximum | Participant-mean sent-command integral, N·s (95% CI) |
|---|---:|---:|---:|---:|---:|---:|---:|
| C0 | 60 | 15 | 14 | 0.1103 | 0.6638 | 0.9943 | 0.9773 [0.8865, 1.0682] |
| C1 | 59 | 15 | 13 | 0.1021 | 0.6238 | 0.7485 | 1.0224 [0.9383, 1.1064] |
| C2 | 58 | 15 | 11 | 0.0610 | 0.4289 | 0.6250 | 0.8394 [0.7726, 0.9063] |
| C3 | 60 | 9 | 9 | 0.0230 | 0.1697 | 0.3827 | 0.7891 [0.7014, 0.8767] |
| C4 | 57 | 11 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.5917 [0.5215, 0.6619] |

C4 is the decisive window-binding example: 11 evaluable C4 trials clamped at
some point, but none clamped inside the outcome window because its scheduled
intervention began after that window. The integral is the logged post-clamp
software command; it is not measured physical impulse.

## S3. Human-generated trajectory variability

Participant mean task-start-to-contact duration ranged 1.3033–2.8360 s; the
trial-level range was 0.6145–5.3001 s. Participant mean approach robot path
ranged 0.00954–0.02444 m, internal-force impulse ranged 0.2492–1.1881 N·s, and
the fraction of evaluable trials with any clamp ranged 6.67%–78.57%.

Despite this variation, every participant had 100% record-layer condition
classification. Participant timing MAE ranged 1.386–3.052 ms and exposure MAE
ranged 0.000771–0.002521. In all quartiles of approach duration, robot path, and
clamp rate, mean classification remained 100%; quartile timing MAE remained
2.23–2.62 ms and exposure MAE remained 0.00143–0.00203. These are descriptive
robustness summaries, not hypothesis tests and not hardware validation.

## S4. Exploratory human outcomes

The participant-level paired differences in threshold-referenced excess-force
impulse are retained exactly as descriptive analyses:

| Contrast | Participants | Mean difference, N·s | 95% CI | Negative/positive |
|---|---:|---:|---:|---:|
| C1−C0 | 20 | +0.0498 | [−0.0577, +0.1572] | 11/9 |
| C2−C0 | 20 | −0.0423 | [−0.1551, +0.0705] | 9/11 |
| C3−C0 | 20 | −0.0269 | [−0.1763, +0.1225] | 11/9 |
| C4−C0 | 20 | −0.1048 | [−0.2092, −0.0004] | 15/5 |

No confirmatory p-values are calculated. C4 is not promoted to a confirmed
effect because the study was not designed for confirmatory human inference,
four contrasts were examined, aborts were condition-imbalanced, command
saturation occurred, and force came from an internal robot estimate.

Machine-readable participant, sensitivity, and audit tables are in `analysis/`.
