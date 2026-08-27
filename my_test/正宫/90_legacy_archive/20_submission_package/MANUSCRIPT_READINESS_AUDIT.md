# Framework-first manuscript readiness audit

**Audit status:** analytically reproducible and structurally framework-first, but **not yet submission-ready** because human-participant ethics/consent information and journal-facing declarations remain unresolved.

## 1. Completed in the current baseline

| Area | Status | Evidence |
|---|---|---|
| Framework-first narrative | Complete | Section 2 precedes the case study; fidelity Results 4.1–4.3 precede exploratory outcomes in Section 5 |
| Four-layer framework | Complete | Nominal (N_m) → executable (C_m) → realized logged (R_i) → outcome (Y_i) |
| Operational metrics | Complete | Event order, executable/nominal gates, timing error, pre-contact activation, latencies, parameter-state fidelity, exposure, provenance, and clock integrity |
| Admissible-estimand boundary | Complete | Main Table II separates admissible from non-admissible interpretations without treating the estimand as an isolated causal effect |
| Fidelity discrepancy taxonomy | Complete | Semantic/estimand mismatch, temporal/parameter runtime noncompliance, exposure heterogeneity, and provenance inconsistency; classes are explicitly non-exclusive |
| Retrospective case application | Complete | 180 clean trials, 45 per A/G/E/F configuration, with participant (n=5) used for human-outcome inference |
| Main fidelity results | Complete | A 45/45; G executable 45/45 and pre-contact 43/45; F nominal timing 3/45, median +0.0533 s and error −0.1467 s; E/F exposure classes reported |
| Provenance | Complete | 180/180 selected intervention–outcome links and 540 selected-file hashes verified |
| Exploratory outcomes | Complete and bounded | E–A, G–A, F–E, and F–G are reported at participant level with exact and multiplicity-adjusted sensitivity analyses |
| Figures | Complete | Main Figures 1–5; Supplementary Figures S1–S2; source extracts, scripts, hashes, and figure manifest retained |
| Supplement | Complete | Metric dictionary, configuration fidelity, full exploratory contrasts, historical-versus-clean sensitivity, LOPO, and lineage examples |
| Automated QA | Pass | Clean 38/38; fidelity 30/30; figure suite pass; manuscript 44/44 |

## 2. Submission-blocking items

These items must be recovered from contemporaneous records or supplied by the authors. They cannot be solved by wording changes.

1. Ethics committee or documented exemption, approval/exemption identifier, and informed-consent procedure.
2. Final author list/order, affiliations, corresponding author, and contact details.
3. Funding, competing interests, author contributions, and acknowledgements.
4. Data- and code-availability statements with a stable repository location, access restrictions, version/tag, and license.
5. Target journal selection, followed by journal-specific formatting, reference style, figure/table limits, declarations, and any reporting checklist.

The authoritative completion checklist is `SUBMISSION_REQUIRED_INFORMATION.md`.

## 3. Important non-blocking weaknesses that must remain explicit

| Weakness | Required boundary |
|---|---|
| One system and one retrospective dataset | Present the framework as operationalized in this case, not universally or externally validated |
| Five independent participants | Treat 180 trials as fidelity observations/repeats, never as 180 independent human samples |
| Retrospective 0.20–1.00-s outcome window | Describe outcomes as exploratory; do not imply prospective preregistration |
| Bundled E/F configurations | Do not attribute E–A to vision alone, stiffness alone, semantics, haptic gain, or gripper settings |
| G realized before contact in 43/45 | Do not call G a pure post-contact force-only intervention |
| F nominal gate met in 3/45 | Do not interpret F–E as the effect of a correctly gated +0.20-s refinement |
| Mixed clock in F | Do not claim that the clock discrepancy caused, attenuated, or biased the F–E numerical result in a known direction; the archive supports an estimand boundary, not a counterfactual correction |
| Logged commanded stiffness | Do not call it independently measured physical impedance |
| `task_start` is system readiness | Do not equate task-start-to-contact time with measured voluntary approach duration or conclude that operators moved more slowly |
| Internal estimated wrench | Do not describe the force channel as an independently logged external force/torque sensor |
| Incomplete participant/object/order metadata | Recover if possible; otherwise retain as limitations and avoid demographic, object-generalization, or counterbalancing claims |

## 4. Packaging decisions

- The main paper uses Figures 1–5 and Tables I–II. LOPO and lineage examples are Supplementary Figures S1–S2; full small-sample statistics and historical-versus-clean comparisons are Supplementary Tables S3–S4.
- The separate confirmatory-experiment design in `../10_confirmatory_experiment/` is **not** incorporated as a claimed contribution or completed study. The current paper uses existing data only. It may inform future work, but including a full unexecuted protocol in the supplement would broaden the manuscript and could confuse the evidentiary boundary.
- The earlier Chinese manuscript is not synchronized with the framework-first English baseline and should be treated as a review aid only.
- The suggestion that the F–E null pattern may have been driven downward by the mixed-clock implementation was deliberately not adopted: the available data cannot identify the direction or magnitude of the counterfactual bias.

## 5. Current size and likely journal-format work

The Markdown manuscript contains approximately 11,183 space-delimited words before the references, including headings, captions, equations, and table text. Approximate section counts are: Introduction 1,196; Framework 1,769; Case Study 3,114; Fidelity Results 1,459; Exploratory Outcomes 1,015; Discussion 2,128; Conclusion 217. Whether this requires compression depends on the selected journal. The Methods/Case Study and Discussion are the first places to shorten without weakening the framework.

## 6. Final pre-submission gate

A submission candidate should be released only when all of the following are true:

- clean QA, fidelity QA, figure QA, and manuscript QA pass;
- all `[NEEDS VERIFICATION]` markers have been replaced by verified facts or converted into transparent limitations, except ethics/consent, which must be positively resolved;
- author/declaration and data/code availability fields are complete;
- every main and supplementary file is versioned in a frozen release;
- the selected journal's author instructions have been applied;
- a final PDF rendering confirms that equations, tables, citations, and vector figures render correctly.
