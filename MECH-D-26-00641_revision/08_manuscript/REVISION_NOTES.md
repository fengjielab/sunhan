# Manuscript revision notes

The working manuscript is extracted from commit `1c1ad02` under
`working/elsarticle/elsarticle-v3.5`. Do not edit the original submitted tree.

## Evidence-dependent restructuring

- Present the original 135-trial study as exploratory/descriptive and remove
  population-level inference based on 27 nested blocks.
- Add the confirmatory 2x2 ablation as the primary validation study.
- Replace C/D/E causal comparisons with `I`, `I_H`, `I_G`, `I_H_G` factorial effects.
- Add phase timing, participant plots, online perception/update timing, haptic-command
  traces, estimated force by phase, saturation and loop-jitter results.
- Report requested gripper force separately from measured aperture and never describe
  the request as realized fingertip force.
- Rename the master-gripper-angle term “master-aperture cue,” not remote grasp-force
  feedback.
- Limit conclusions to predefined object classes, mappings, hardware and task.

## Non-data corrections

- Define pose-error sign convention.
- Clarify Franka API damping-ratio semantics and units.
- Report `d/Kf` for every haptic setting.
- Explain fixed target width/tolerance and actual aperture measurement.
- Clarify 200 Hz as the application/supervisory loop and document inner device loops
  only from authoritative sources.
- Add ethics issuer/reference/date and public data/code availability statement.
- Verify suggested haptics literature and inspect every figure at final column width.

Results, abstract, discussion and conclusion must not be rewritten with numerical
claims until the locked confirmatory analysis outputs exist.
