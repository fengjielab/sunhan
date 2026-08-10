# 5. Discussion

## 5.1 Main findings

<!-- D5.1-P1 -->
This retrospective, log-audited analysis identified three principal findings. First, the realized vision-enabled bundled configuration E was associated with lower threshold-referenced excess-force impulse than the fixed configuration A, and the E-A difference had the same direction in all five participants. This directional consistency should nevertheless be interpreted within the limits of the five-participant sample: the exact sign-flip and Wilcoxon tests each yielded \(p=0.0625\), and Holm-adjusted inference did not support a strong confirmatory conclusion. Second, the lower E-A force-exposure estimate was accompanied by longer task-start-to-contact and total task times, forming an observed safety-efficiency trade-off pattern rather than establishing a general trade-off mechanism. Third, the realized logged timing of G and F differed materially from their nominal definitions. The four configurations should therefore be interpreted as bundled realized logged interventions and not as a strict visual-by-force 2 × 2 factorial manipulation.

## 5.2 Lower early force exposure under the vision-enabled configuration

<!-- D5.2-P1 -->
The logged commanded-stiffness profiles provide one physically plausible context for the E-A difference. A maintained a logged translational-stiffness command of 200 N/m, whereas E had a median logged command of 120 N/m at contact, with values varying across its material-dependent profiles. Lower commanded stiffness around contact could have limited the force developed during early interaction. The concordant E-A direction in initial peak force is compatible with the same overall pattern, but this secondary outcome and its multiplicity-adjusted evidence do not identify a mechanism. More generally, the correspondence does not establish stiffness as the isolated cause: the analysis records controller commands rather than an independent measurement of physical closed-loop impedance, and the experiment did not manipulate translational stiffness as a single factor.

<!-- D5.2-P2 -->
E was a bundled configuration in which the vision-derived profile jointly set translational and rotational stiffness, damping ratio, haptic feedback gain, haptic deadband, and gripper force. The visual pathway determined which bundle became available, but the present comparison cannot distinguish an effect of visual information itself from effects of the selected controller, haptic, or gripper parameters. Vision locking also occurred after contact in a minority of E trials, further showing that the timing and content of the realized intervention were not uniform. The most defensible interpretation is therefore that the observed E-A difference was associated with the realized vision-enabled bundled configuration, not with an isolated visual or stiffness mechanism.

<!-- D5.2-P3 -->
Human adaptation offers another compatible, but unverified, explanation. Participants may have altered when they initiated motion, how they paused, or how they responded to the changing haptic and robot behavior. The longer task-start-to-contact interval under E is consistent with a change in interaction timing, but the archived data did not directly measure attention, caution, intent, decision time, or the onset and speed of voluntary approach motion. Accordingly, more conservative operation is one possible explanation for the joint force and timing pattern, but it cannot be distinguished from delayed initiation, additional pauses, or controller-mediated motion differences in the present dataset.

## 5.3 Lower force exposure was accompanied by a longer pre-contact interval

<!-- D5.3-P1 -->
The E-A comparison combined a lower estimate of early threshold-referenced force exposure with longer task-start-to-contact and total task times. Considering these outcomes jointly is important because a force reduction alone would not show whether it was accompanied by additional temporal cost. In the present dataset, the paired pattern is consistent with an observed safety-efficiency trade-off: E was associated with lower early force exposure, but completion of the pre-contact and overall task sequence took longer. This wording describes co-occurring outcomes and does not imply that one outcome caused the other.

<!-- D5.3-P2 -->
The task-start-to-contact measure requires particular caution. Task start was logged when the force baseline and controller were ready, rather than when the participant first moved. The interval could therefore contain reaction time, initial hesitation, actual approach motion, and pauses. The longer pre-contact interval is consistent with more conservative interaction timing, although the archived data cannot distinguish slower physical approach from delayed initiation or additional pauses. It should not be interpreted as direct evidence that participants deliberately moved more slowly.

<!-- D5.3-P3 -->
This combined pattern suggests a practical evaluation principle for human-in-the-loop teleoperation: safety-related physical-interaction metrics and temporal or operator-related metrics should be examined together. A controller configuration that changes early force exposure may also change when interaction begins, how the operator responds, or how long the task takes. The present study cannot determine which temporal component changed, but it illustrates why reporting force exposure without the accompanying task timing could provide an incomplete account of system performance.

## 5.4 Nominal control modes versus realized interventions

<!-- D5.4-P1 -->
The G audit substantially narrows the interpretation of G-A. G was nominally the force-only configuration, but its adaptation used raw filtered force with a fixed 1-N deadband and did not require baseline readiness or logged contact. It became active before task start in 42 of 45 trials and before contact in 43 of 45 trials. G-A therefore compares A with a predominantly pre-activated, force-driven realized logged configuration; it should not be interpreted as the isolated effect of post-contact force feedback. The small G-A force-impulse estimate and its interval cannot establish whether a correctly contact-gated force policy would be beneficial, neutral, or detrimental.

<!-- D5.4-P2 -->
The F audit imposes a corresponding boundary on F-E. Although the nominal source-code logic specified a 0.20-s post-contact delay, the audited wall-clock/monotonic-clock mismatch did not reliably enforce that gate, and the median first logged activation occurred 0.053 s after contact. Consequently, the observed F-E comparison does not estimate the effect of a correctly gated 0.20-s force-refinement policy. The small and leave-one-participant-out-unstable F-E estimate should be read as evidence about the realized logged F configuration only; it does not demonstrate that force refinement in general is ineffective.

<!-- D5.4-P3 -->
Together, these observations illustrate the importance of separating nominal, commanded, and realized logged interventions. A mode name and its intended source-code logic describe the experimental plan, while time-varying command fields and activation events describe what the software exposed during a particular acquisition. Neither is equivalent to an independent measurement of physical impedance. For asynchronous human-in-the-loop systems, interpretation is therefore strengthened when the timing of perception, contact, parameter application, and adaptation is reconstructed for each trial rather than inferred from the controller label alone.

## 5.5 Implications for human-in-the-loop teleoperation experiments

<!-- D5.5-P1 -->
The present audit suggests several practical reporting considerations rather than a new universal standard. Event timestamps should accompany mode labels, and logs should preserve the trajectories of commanded stiffness, adaptation state, vision lock, contact, and other parameters that define exposure to an intervention. Reporting nominal controller parameters without their application times may be insufficient when perception, human action, and controller updates proceed asynchronously.

<!-- D5.5-P2 -->
Data identity is equally important. In this study, the raw trajectory, event JSON, summary record, threshold, and scalar metrics were required to originate from the same timestamped acquisition, and initial and replacement records were distinguished by an exact record identifier. This provenance rule prevented a scalar outcome from being combined with event timing or parameter trajectories from a different attempt. Similar analyses benefit from a manifest that retains excluded or superseded records while explicitly identifying the single record used for the main analysis.

<!-- D5.5-P3 -->
The inferential structure should also match the experimental unit. Repeated trials can improve estimation within a participant, but they do not increase the number of independent human participants. Here, inference was therefore based on five participant-level paired means. In addition, software-log completion should be labeled as such: the absence of variation in the archived success flag does not replace independent physical or video adjudication. These distinctions help align the reported precision and outcome meaning with what was actually observed.

## 5.6 Limitations

<!-- D5.6-P1 -->
The principal limitation is the sample of only five independent participants. The 180 clean trials provided repeated observations within those participants, not 180 independent human samples, and exact small-sample inference was correspondingly coarse. The 0.20–1.00-s threshold-referenced impulse window was also selected for the clean retrospective reanalysis and was not prospectively preregistered as a primary endpoint. The results should therefore be regarded as exploratory evidence rather than as an independently powered confirmatory test.

<!-- D5.6-P2 -->
Causal interpretation is further constrained by configuration bundling and incomplete prospective order documentation. E and F jointly changed multiple controller, haptic, and gripper parameters, preventing attribution to any single component. The archived timestamps showed realized order, but a complete prospective randomization or counterbalancing plan was not recovered; learning, fatigue, or order effects therefore cannot be excluded. The present contrasts characterize the observed configurations under this experimental sequence rather than isolated parameter effects.

<!-- D5.6-P3 -->
Measurement and metadata limitations also restrict generalization. Force was derived from the Franka internal estimated external wrench rather than from an independently logged external force/torque sensor. Material-category labels were retained, but unique physical-object identity, pose, and placement were incomplete, precluding a strict claim of object-level generalization. All 180 trials met the software-log success definition, but success was not independently adjudicated from video or manual review. Participant demographics, prior experience, and training details were not recoverable from the current archive; if they cannot be verified from contemporaneous records, their absence should be disclosed because it limits assessment of sample representativeness and operator-related variability.

<!-- D5.6-P4 -->
Finally, the G and F implementation deviations limit conclusions about the nominal force-related mechanisms. G did not realize a contact-gated post-contact policy, and F did not reliably realize its intended 0.20-s delay. These deviations do not invalidate the descriptive comparisons among the realized logged configurations, but they prevent those comparisons from answering whether correctly gated force adaptation would add benefit to the vision-enabled configuration. `[NEEDS VERIFICATION before submission: ethics approval or exemption and informed-consent information must be confirmed from institutional records and reported in the appropriate Methods or declaration section; they must not be inferred in the Discussion.]`
