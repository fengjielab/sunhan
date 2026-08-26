# THMS v4 logic and evidence traceability

| Claim or decision | Stage A evidence/rule | Stage B consequence | Wording boundary |
|---|---|---|---|
| A condition label is not a specification | `N-01`; artifact must be contemporaneous and explicit | `nominal_spec=unavailable` forces `n_to_c=not_evaluable` | Do not infer nominal semantics from a label |
| G has no recoverable post-contact specification | Structured G audit; archived source hash | Realized raw-force configuration only | Do not call G a pure post-contact effect |
| G delivery is replayable | 12,196 command-update rows; max error below (10^{-10}) | `c_to_r=pass` | Replay consistency does not restore missing N |
| F has a clock-domain mismatch | `NC-02`; exact archived source signatures | `n_to_c=fail: clock` | 53 ms is downstream realized timing |
| F exposure is recoverable but full replay is not | Logged activation/exposure; incomplete per-cycle predicate inputs | `c_to_r=not_evaluable` plus known exposure | Describe recorded trajectory; do not assert (C=R) |
| Approximately 1 ms is partial exposure | `EX-01`; strict interior fraction | `PARTIAL_WINDOW_EXPOSURE` | Do not round it to zero |
| Missing trace is not zero exposure | `EX-01`; trace/window completeness precondition | `exposure=unavailable` | Do not impute absence of intervention |
| Provenance is valid for 180 selected records | `P-01`; exact identities/paths/hashes | Intervention–outcome pairs remain evaluable | Provenance does not prove fidelity |
| Causality is outside the framework | No outcome fields in either interface | Fixed `outside_fidelity_framework` status | Fidelity never authorizes causal wording alone |

The semantic mapping is a structured author audit. No independent dual-review or inter-rater agreement claim is made.
