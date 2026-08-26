# Realized-Intervention Fidelity Framework Results

This report is generated from the existing clean 180-trial dataset. It does not rerun outcome significance tests and does not exclude noncompliant trials.

## Stable metrics

- Event times, contact-aligned activation latency, pre-contact activation, landmark commanded parameters, window-specific adaptation exposure, Kt exposure, provenance consistency, analysis timeline integrity, and control-cycle distributions are directly computable.
- A fixed-command negative control passed in 45/45 trials.
- G pre-contact activation occurred in 43/45 trials; this is descriptive timing relative to contact, not a G timing-error score.
- F pre-contact activation occurred in 0/45 trials; 3/45 met the nominal +0.20-s activation target.

## Partially observable metrics

- Vision-lock-to-first-parameter-change is a CSV-resolution command latency, not end-to-end perception-to-physical-impedance latency.
- Transition completion is exact when the target command vector is logged. When F immediately departs from its vision base under fusion, the first fusion execution supplies only an upper bound; the observation type is retained per trial.
- Logged commanded stiffness is not an independent physical impedance measurement.

## Mode interpretation

- A is a usable pass/negative control for fixed logged commands.
- G is primarily a semantic/estimand mismatch: executable logic intentionally has no baseline-ready or contact gate. The logged behavior is generally code-consistent, even though it cannot support an isolated post-contact interpretation.
- F is a temporal runtime-fidelity failure relative to the nominal +0.20-s gate, caused by a mixed-clock comparison. Its logged analysis timeline remains reconstructable.
- The vision-selected transition was complete by the outcome-window start in E 39/45 and F 42/45 trials.
- E vision-configuration exposure in the outcome window was zero/partial/full in 4/2/39 trials. F vision exposure was 3/0/42, while F force-adaptation exposure was 3/7/35. This is direct outcome-window exposure heterogeneity, not a subgroup efficacy analysis.
- Provenance is valid for 180/180 clean trials. The repair changes which records may be used and therefore restores admissible record-level linkage; it did not by itself reverse the principal E-A numerical pattern.

## Framework conclusion

The data support the bounded proposition: realized-intervention reconstruction can change the admissible interpretation of nominal controller comparisons. The strongest support is a change in estimand/mechanistic interpretation, not a universal claim that numerical rankings must reverse.
