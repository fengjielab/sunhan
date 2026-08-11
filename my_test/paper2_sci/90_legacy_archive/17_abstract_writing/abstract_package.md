# Abstract package

## A. Version 1 — Recommended conservative submission abstract

Human-in-the-loop contact teleoperation combines haptic feedback, variable-impedance, and vision-informed control, but nominal labels may not characterize the intervention realized when perception, contact detection, and adaptation are asynchronous. We retrospectively audited 180 clean trials from five participants across archived configurations A/G/E/F. Nominal, commanded, and realized logged interventions were reconstructed from code, event timestamps, parameter trajectories, activation states, and provenance; participant was the independent human experimental unit. G first activated before task start in 42/45 trials and before contact in 43/45. F first activated a median 0.053 s after contact rather than reliably enforcing its nominal 0.20-s gate, precluding a clean realized vision × force factorial interpretation. Under the realized bundled configurations, E was associated with lower early threshold-referenced excess-force impulse than A (difference, −0.3489 N·s; 95% CI, −0.6080 to −0.0898), with all five participant differences negative. Exact small-sample and multiplicity-adjusted analyses did not support strong confirmatory inference. This estimate was accompanied by longer task-start-to-contact (+1.7805 s) and total task times (+1.2128 s), forming an observed safety–efficiency trade-off pattern. No stable incremental F-over-E difference was evident, while G-A was small and uncertain. These findings highlight the value of reconstructing realized logged interventions before attributing performance differences to nominal controller mechanisms.

## B. Version 2 — Greater emphasis on robotic application significance

Contact teleoperation must balance interaction with operator responsiveness and task efficiency. Haptic feedback, variable-impedance, and vision-informed control address this balance, but nominal labels may not describe realized controller exposure when perception, contact detection, and adaptive updates are asynchronous. We retrospectively audited 180 clean trials from five participants under archived configurations A/G/E/F, treating participant as the independent human experimental unit. Code, event timestamps, activation states, parameter trajectories, and provenance were linked to reconstruct nominal, commanded, and realized logged interventions. G first activated before task start in 42/45 trials and before contact in 43/45, whereas F first activated a median 0.053 s after contact despite its nominal 0.20-s gate; data therefore did not support a clean realized vision × force factorial interpretation. The realized vision-enabled bundled configuration E was associated with lower early threshold-referenced excess-force impulse than A (difference, −0.3489 N·s; 95% CI, −0.6080 to −0.0898), with all five participant differences negative. Exact small-sample and multiplicity-adjusted analyses did not support strong confirmatory inference. Lower force exposure was accompanied by longer task-start-to-contact (+1.7805 s) and total task times (+1.2128 s), indicating an observed safety–efficiency trade-off pattern. No stable incremental F-over-E difference was evident, and G-A remained small and uncertain. Joint verification of event timing, parameter trajectories, activation states, provenance, and the independent experimental unit can strengthen interpretation before performance differences are assigned to controller mechanisms.

## C. Sentence-level rhetorical decomposition

### Version 1

| Sentence | Function | Role in the abstract |
|---:|---|---|
| V1-S1 | Background + gap | Introduces the controller routes and nominal-versus-realized problem |
| V1-S2 | Methods | Identifies retrospective audit, 180 trials, five participants, and A/G/E/F |
| V1-S3 | Methods | Defines reconstruction sources and participant-level experimental unit |
| V1-S4 | Audit finding | Reports G pre-task/pre-contact activation |
| V1-S5 | Audit finding | Reports F timing and the boundary on factorial interpretation |
| V1-S6 | Performance finding | Reports E-A estimate, CI, and five-participant directional consistency |
| V1-S7 | Performance/inference boundary | States that exact and adjusted analyses do not support strong confirmation |
| V1-S8 | Performance finding | Reports timing differences and the observed trade-off pattern |
| V1-S9 | Performance finding | Summarizes limited incremental evidence for F and G |
| V1-S10 | Interpretation | Gives the methodological significance without proposing a universal standard |

### Version 2

| Sentence | Function | Role in the abstract |
|---:|---|---|
| V2-S1 | Background | Frames physical interaction, responsiveness, and efficiency as an application-level balance |
| V2-S2 | Background + gap | Introduces controller routes and the nominal-versus-realized problem |
| V2-S3 | Methods | Identifies retrospective audit, data volume, configurations, and experimental unit |
| V2-S4 | Methods | Lists reconstruction evidence and the three intervention levels |
| V2-S5 | Audit finding | Reports G/F timing and the factorial-interpretation boundary |
| V2-S6 | Performance finding | Reports E-A estimate, CI, realized bundle, and all-five consistency |
| V2-S7 | Performance/inference boundary | Retains exact-test and multiplicity-adjusted exploratory limits |
| V2-S8 | Performance finding | Reports the observed force-exposure/task-timing pattern |
| V2-S9 | Performance finding | Summarizes F-E instability and G-A uncertainty |
| V2-S10 | Interpretation | Emphasizes practical verification before mechanistic attribution |

## D. Numerical consistency audit against frozen Results

| Abstract value | Frozen source | Verification |
|---|---|---|
| 5 participants | Results 4.1.2; Methods 2.2.1 | Exact match |
| 180 clean trials | Results 4.1.1–4.1.2; Methods 2.2.3 and 2.6 | Exact match |
| Four configurations A/G/E/F | Results 4.1.2; Methods 2.2.3 and 2.3 | Exact match |
| G: 42/45 before task start | Results 4.2.1 | Exact match |
| G: 43/45 before contact | Results 4.2.1 | Exact match |
| F: median 0.053 s after contact | Results 4.2.2 | Exact match; described as median first activation |
| F nominal gate: 0.20 s | Methods 2.3.4 and 2.4.4; Results 4.2.2 | Exact match; not described as reliably realized |
| E-A impulse difference: −0.3489 N·s | Results 4.4.1 | Exact match |
| E-A 95% CI: −0.6080 to −0.0898 N·s | Results 4.4.1 | Exact match |
| Five E-A participant differences in the same/negative direction | Results 4.4.2 | Exact match |
| E-A task-start-to-contact difference: +1.7805 s | Results 4.5.1 | Exact match |
| E-A total-task-time difference: +1.2128 s | Results 4.5.2 | Exact match; Results reports 1.2128 s after rounding |
| No stable incremental F-over-E difference | Results 4.6.2 | Exact qualitative summary of small, mixed-direction, LOPO-unstable estimate |
| G-A estimate small and uncertain | Results 4.6.1 | Exact qualitative summary of −0.0742 N·s with CI crossing zero |

No p-value was added to either abstract. The CI and small-sample/multiplicity statement preserve the frozen inferential boundary without selectively emphasizing the unadjusted paired t-test.

## E. Overstatement and conflict audit

### Sentences requiring the most caution

| Sentence | Potential risk | Why the current wording remains within evidence |
|---|---|---|
| V1-S1 | Broad background claim | It summarizes controller routes already covered in the frozen Introduction and does not claim novelty |
| V1-S5 / V2-S5 | Could sound like the nominal design never existed | Both versions say the *realized* data do not support a clean factorial interpretation; they do not deny the nominal code design |
| V1-S6 / V2-S6 | Could be read as isolated vision effect | Both retain “realized bundled configuration”; neither attributes E-A to vision alone |
| V1-S7 / V2-S7 | Significance understatement/overstatement balance | Explicitly states that exact small-sample and multiplicity-adjusted analyses do not support strong confirmation |
| V1-S8 / V2-S8 | “Safety–efficiency” could imply a causal mechanism | Both use “accompanied by” and “observed ... pattern”; neither says the force difference caused the timing difference |
| V1-S9 / V2-S9 | Could be overread as force feedback being ineffective | Limited to realized F-E and G-A evidence; no general force-feedback conclusion |
| V2-S10 | Could sound like a reporting standard | Uses “can strengthen,” not “must,” “standard,” or “universally applicable” |

### Conflict checks

- No causal claim exceeds the frozen Discussion.
- No novelty or priority claim is present.
- No strong confirmatory significance claim is present.
- Nominal F timing is explicitly distinguished from realized F timing.
- G is not described as a pure post-contact force-only intervention.
- The metric is consistently named `threshold-referenced excess-force impulse`.
- `task-start-to-contact` is not called approach duration or operator speed.
- Logged parameters are not described as independently measured physical impedance.
- The participant, not trial or block, is the independent human experimental unit.
- No new literature, experiment, mechanism, endpoint, exclusion rule, or statistical analysis is introduced.

## F. Recommendation

**Recommend Version 1 for submission.** It places the nominal-versus-realized intervention problem first, gives G/F timing and E-A evidence comparable weight, and ends on the paper's central methodological interpretation. Version 2 is also evidence-consistent, but its application-oriented opening and verification checklist make it slightly more suitable for a systems-oriented journal or cover-letter summary than for the most conservative manuscript abstract.
