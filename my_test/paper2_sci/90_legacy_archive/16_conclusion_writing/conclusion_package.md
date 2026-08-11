# 6. Conclusion

This study examined whether nominal controller modes in human-in-the-loop contact teleoperation accurately represented the realized logged interventions recorded in individual trials. The participant-level reanalysis showed that the realized vision-enabled bundled configuration E was associated with lower early threshold-referenced excess-force exposure than the fixed configuration A, with the same direction observed across all five participants; given the small sample and retrospective analysis, this pattern remains exploratory rather than a confirmed safety improvement. The lower force-exposure estimate was accompanied by longer task-start-to-contact and total task times, constituting an observed safety–efficiency trade-off pattern without establishing a causal trade-off mechanism. Timing reconstruction further showed that G did not realize a purely post-contact force-only intervention and that F did not reliably enforce its nominal 0.20-s post-contact gate. Accordingly, in this dataset, a nominal mode label did not by itself establish the intervention represented by the acquired trial data. For human-in-the-loop robot experiments involving asynchronous perception, contact detection, and adaptation, controller evaluation can be strengthened by preserving and jointly verifying event timing, commanded parameter trajectories, activation states, acquisition provenance, and the independent experimental unit used for inference. Together, these findings highlight the value of reconstructing what a human–robot system actually executed before assigning observed performance differences to the intended controller mechanism.

## Sentence-to-evidence map

| Sentence | Main statement | Evidence in the frozen paper |
|---:|---|---|
| 1 | The research question concerns whether nominal modes represent realized logged interventions | Methods 2.4.1–2.4.5; Results 4.1–4.2; Discussion 5.4–5.5 |
| 2 | E showed directionally lower early threshold-referenced force exposure than A in all five participants, with an exploratory boundary | Results 4.4.1–4.4.2; Discussion 5.1.1 and 5.2.1–5.2.2; Methods 2.7.1–2.7.3 |
| 3 | Lower E-A force exposure co-occurred with longer task-start-to-contact and total task times | Results 4.5.1–4.5.2; Discussion 5.3.1–5.3.2 |
| 4 | G was not purely post-contact and F did not reliably implement the nominal 0.20-s gate | Results 4.2.1–4.2.2; Methods 2.3.3–2.3.4 and 2.4.4; Discussion 5.4.1–5.4.2 |
| 5 | Nominal labels alone did not establish the realized intervention | Results 4.2.3; Discussion 5.4.3 |
| 6 | Event timing, commanded parameter trajectories, activation state, provenance, and the independent unit strengthen evaluation | Methods 2.4, 2.6, and 2.7; Discussion 5.5.1–5.5.3 |
| 7 | Mechanistic attribution should follow reconstruction of actual execution | Synthesis of Results 4.1–4.6 and Discussion 5.4–5.5 |

## Evidence-boundary audit

No sentence exceeds the evidence reported in the frozen Methods, Results, or Discussion.

- Sentence 2 reports an association and directional consistency, not a confirmed significant safety improvement; it explicitly retains the five-participant, small-sample, retrospective boundary.
- Sentence 3 reports co-occurrence and explicitly rejects a causal trade-off mechanism.
- Sentence 4 does not claim that force feedback in general was ineffective; it is limited to the realized logged G and F implementations.
- Sentence 5 is limited to this dataset's documented implementation deviations and does not claim that nominal labels are always invalid.
- Sentence 6 is framed as a reporting and evaluation consideration (`can be strengthened`), not as a universal standard.
- Logged commanded parameters are not described as independently measured physical impedance.
- No new experiment, method, mechanism, literature claim, p-value, or causal attribution has been introduced.
