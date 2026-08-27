# Framework-first SCI submission bundle

This folder is the consolidated handoff package for the manuscript **Realized-Intervention Fidelity in Asynchronous Human-in-the-Loop Teleoperation: An Operational Framework and Retrospective Case Study**.

The package was assembled by copying derived analysis products and submission materials. Existing source directories and original experimental acquisitions were not moved, overwritten, or deleted.

## Folder map

| Folder | Contents |
|---|---|
| `03_clean_analysis/` | Frozen clean manifests, trial/participant metrics, timing and lineage audits, fidelity outputs, statistics, QA, and analysis scripts |
| `18_manuscript_v1/` | Framework-first English manuscript, earlier Chinese review translation, and manuscript notes |
| `19_publication_figures/` | Main and supplementary figures in PDF/SVG/PNG, source-data extracts, plotting scripts, manifests, and figure QA |
| `20_submission_package/` | Supplementary Material, manuscript-readiness audit, submission blockers, requirements, and manuscript QA |
| `acquisition_code_snapshot/` | Read-only handoff copy of `interactive_teleop.py`; this is not a modified acquisition program |

## Primary files

- Manuscript: `18_manuscript_v1/manuscript_v1_en.md`
- Supplement: `20_submission_package/supplementary_material.md`
- Readiness audit: `20_submission_package/MANUSCRIPT_READINESS_AUDIT.md`
- Required-information checklist: `20_submission_package/SUBMISSION_REQUIRED_INFORMATION.md`
- Figure reproduction: `19_publication_figures/FIGURE_REPRODUCTION_README.md`
- Machine-readable manuscript QA: `20_submission_package/manuscript_qa_report.json`

The Chinese manuscript is an earlier review translation and has not been synchronized to the framework-first English structure. It must not be used as the submission source.

## Verify the included clean results and manuscript

Run from this bundle root:

```powershell
python -m pip install -r 20_submission_package/requirements-analysis.txt
python 03_clean_analysis/scripts/qa_clean_analysis.py
python 03_clean_analysis/scripts/qa_fidelity_analysis.py
python 20_submission_package/scripts/qa_manuscript.py --root .
```

Expected results are clean QA `38/38`, fidelity QA `30/30`, and manuscript QA `44/44`.

## Reproduce all figures

```powershell
python 19_publication_figures/scripts/generate_all_figures.py --root .
```

This regenerates Figures 1–7 from the included clean derived files. Main Figures 1–5 are referenced by the manuscript; Figures 6–7 are mapped to Supplementary Figures S1–S2.

## Scope boundary

This bundle includes the frozen clean analysis and enough evidence to regenerate figures and verify reported claims. It does **not** duplicate the raw human-participant acquisition archive. Re-running `clean_analysis.py` from raw acquisitions therefore still requires the original read-only archive at its documented external location. The included clean QA, fidelity QA, figure generation, and manuscript QA operate on the copied derived files.

Ethics/consent, authorship, declarations, repository identifiers, and target-journal formatting remain unresolved submission blockers. See `20_submission_package/SUBMISSION_REQUIRED_INFORMATION.md`.

## Bundle integrity

`bundle_manifest_sha256.json` records a SHA-256 digest for every handoff file except the manifest itself and transient Python cache files.

```powershell
python verify_bundle.py verify
```

