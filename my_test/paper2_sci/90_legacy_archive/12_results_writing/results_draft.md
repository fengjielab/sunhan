# 4. Results

## 4.1 Data provenance and realized-intervention reconstruction

<!-- R4.1-P1 -->
The reconstructed lineage contained 186 timestamped records. Of these, 174 were retained as unique main records and six 20260730 records were retained as valid replacements for six known-error 20260729 records. The six known-error records remained in the master manifest with an excluded analysis role rather than being deleted. This procedure yielded 180 unique trial keys for the clean main analysis. The CSV time series, event log, and summary file associated with every one of the 186 records were present and matched their recorded SHA-256 hashes.

<!-- R4.1-P2 -->
The clean dataset comprised five participants and four recorded modes (A, G, E, and F), with 45 trials per mode and nine trials per participant per mode. The recorded material categories were balanced at 60 trials each for soft, medium, and hard materials. All 180 clean trials met the archived software-log success definition. Because the independent human experimental unit was the participant, the nine trials within each participant and mode were averaged before inferential comparisons; consequently, all outcome contrasts reported below were based on five paired participant means rather than on 180 trials or 45 blocks.

## 4.2 Nominal and realized logged interventions diverged

<!-- R4.2-P1 -->
The logged activation timing showed that the nominal force-only mode G was not realized as a purely post-contact intervention. The first G activation occurred before task start in 42 of 45 trials and before logged contact in 43 of 45 trials. The median activation offsets were -0.379 s relative to task start and -1.214 s relative to contact. All 45 first activations occurred when the raw estimated external force exceeded the fixed 1-N deadband, and 42 occurred before the force baseline was declared ready.

<!-- R4.2-P2 -->
The nominal 0.20-s post-contact gate in mode F was also not reproduced in the recorded execution. Across the 45 F trials, the median first activation was 0.053 s after logged contact, and 42 activations occurred earlier than 0.20 s. The three later activations coincided with trials in which vision locking occurred after contact. Thus, the recorded F timing did not represent a consistently executed 0.20-s post-contact condition.

<!-- R4.2-P3 -->
Vision locking occurred after task start in all E and F trials, at median offsets of 1.741 and 1.752 s, respectively. Relative to contact, vision lock occurred at a median of 0.755 s before contact in E and 0.941 s before contact in F. However, vision locking followed contact in 5 of 45 E trials and 3 of 45 F trials. The four modes were therefore retained as labels for their realized logged bundled configurations, rather than interpreted as a strict realized 2 × 2 factorial manipulation.

## 4.3 Safety-related outcomes across realized logged configurations

<!-- R4.3-P1 -->
The participant-level mean threshold-referenced excess-force impulse from 0.2 to 1.0 s after contact was 0.8073 N·s in A, 0.7330 N·s in G, 0.4584 N·s in E, and 0.4372 N·s in F. The corresponding participant-level mean initial peak forces from 0 to 0.2 s were 2.2309, 2.2635, 1.8169, and 1.8320 N, respectively. These mode means describe the observed realized logged configurations; the clean-reanalysis paired contrasts are reported below.

<!-- R4.3-P2 -->
The contact-aligned force and stiffness trajectories were aggregated by first averaging trials within each participant and then summarizing the five participant-level curves. At logged contact, the trial-level median logged translational stiffness was 200 N/m in A, 198.3 N/m in G, and 120 N/m in both E and F. The corresponding ranges were 200-200, 178.9-200, 50-200, and 50-200 N/m. By 0.2 s after contact, the median logged stiffness in F was 116.1 N/m (range, 41.1-189.2 N/m). These trajectories were used descriptively to locate the logged force-estimate and commanded-stiffness profiles and were not subjected to trial-level functional significance testing.

## 4.4 Participant-level consistency of the E-A contrast

<!-- R4.4-P1 -->
For the main threshold-referenced excess-force impulse, the participant-level mean E-A difference was -0.3489 N·s (95% t-based CI, -0.6080 to -0.0898; t(4) = -3.739, paired t-test p = 0.0201). The exhaustive two-sided sign-flip test and the exact Wilcoxon signed-rank sensitivity test both yielded p = 0.0625. After Holm correction across the four clean-reanalysis contrasts for this metric, the adjusted p values were 0.0633 for the paired t-test and 0.2500 for both exact sensitivity tests. Thus, the unadjusted t-based result was accompanied by directionally consistent estimates, but the exact small-sample and multiplicity-adjusted analyses did not meet the 0.05 criterion.

<!-- R4.4-P2 -->
Each of the five participant-level E-A impulse differences was negative, ranging from -0.6006 to -0.1331 N·s. In leave-one-participant-out analyses, the mean difference remained negative in all five subsets and ranged from -0.4028 to -0.2860 N·s; one of the five leave-one-participant-out 95% intervals crossed zero. Initial peak force showed a concordant E-A difference of -0.4140 N (95% CI, -0.7483 to -0.0798; paired t-test p = 0.0263), whereas the exact sign-flip and Wilcoxon p values were 0.0625 and the Holm-adjusted paired-t p value was 0.0789.

## 4.5 Safety-efficiency trade-off

<!-- R4.5-P1 -->
The participant-level mean task-start-to-contact time was 0.8974 s in A and 2.6779 s in E. The E-A difference was 1.7805 s (95% CI, 1.5084 to 2.0527; t(4) = 18.165, paired t-test p = 5.40 × 10^-5). All five participant-level differences were positive. The exact sign-flip and Wilcoxon tests both yielded p = 0.0625; after Holm correction, the paired-t p value was 0.000162 and both exact-test p values were 0.2500. Because task start marked system readiness rather than first human movement, this difference describes the logged pre-contact interval and does not directly establish a difference in robot approach duration or operator movement speed.

<!-- R4.5-P2 -->
The participant-level mean total task time was 16.2631 s in A and 17.4758 s in E, corresponding to an E-A difference of 1.2128 s (95% CI, 0.5741 to 1.8514; t(4) = 5.272, paired t-test p = 0.00620). Again, all five participant-level differences were positive. The exact sign-flip and Wilcoxon p values were 0.0625; the Holm-adjusted paired-t p value was 0.0186, whereas both adjusted exact-test p values were 0.2500. Together with the lower E-A force-impulse estimate, these longer time estimates constituted the observed safety-efficiency trade-off pattern.

## 4.6 Limited incremental evidence for G and F configurations

<!-- R4.6-P1 -->
Under the realized logged G implementation, the participant-level G-A difference in threshold-referenced excess-force impulse was -0.0742 N·s (95% CI, -0.1978 to 0.0494; t(4) = -1.667, paired t-test p = 0.1708). Although the five participant differences were negative, the confidence interval included zero, and the Holm-adjusted paired-t p value was 0.3416. This comparison describes the realized logged, predominantly pre-activated G configuration rather than a pure post-contact force-feedback intervention.

<!-- R4.6-P2 -->
The participant-level F-E difference in threshold-referenced excess-force impulse was -0.0212 N·s (95% CI, -0.1433 to 0.1010; t(4) = -0.481, paired t-test p = 0.6556). The exact sign-flip p value was 0.6875 and the Wilcoxon p value was 0.8125. The five individual differences included three negative and two positive values. Across leave-one-participant-out subsets, the mean difference ranged from -0.0537 to 0.0074 N·s and changed sign when P03 was excluded. The clean data therefore showed no stable incremental F-over-E difference under the realized logged implementation.

<!-- R4.6-P3 -->
For completeness, the participant-level F-G threshold-referenced excess-force impulse difference was -0.2958 N·s (95% CI, -0.5000 to -0.0917; t(4) = -4.023, paired t-test p = 0.0158). The exact sign-flip and Wilcoxon p values were both 0.0625, and the Holm-adjusted paired-t p value was 0.0633. Because the timing audit showed different bundled and mistimed realized logged interventions in G and F, this descriptive contrast was not treated as evidence of an isolated visual-force interaction.
