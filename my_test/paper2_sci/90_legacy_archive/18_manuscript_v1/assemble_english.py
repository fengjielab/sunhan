from __future__ import annotations

import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig").strip()


def clean_section(text: str) -> str:
    text = re.sub(r"<!--.*?-->\s*", "", text, flags=re.S)
    text = re.sub(
        r"\*\*M\d+(?:\.\d+)*(?:-[A-Za-z0-9]+)?\s+—\s+([^*]+)\*\*",
        r"**\1**",
        text,
    )
    return text.strip()


def insert_after_section(text: str, section_heading: str, insertion: str) -> str:
    pattern = rf"(?ms)(^## {re.escape(section_heading)}\n.*?)(?=^## |\Z)"
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"Section not found: {section_heading}")
    block = match.group(1).rstrip() + "\n\n" + insertion.strip() + "\n\n"
    return text[: match.start()] + block + text[match.end() :]


abstract_package = read("17_abstract_writing/abstract_package.md")
abstract = re.search(
    r"## A\. Version 1[^\n]*\n\n(.*?)(?=\n\n## B\.)",
    abstract_package,
    flags=re.S,
).group(1).strip()

introduction = clean_section(read("15_introduction_related_work/introduction_draft.md"))
related = clean_section(read("15_introduction_related_work/related_work_draft.md"))

methods = read("13_methods_writing/methods_draft.md")
methods = re.sub(r"^# 2\. Methods", "# 3. Methods", methods)
methods = re.sub(r"^## 2\.(\d+)", r"## 3.\1", methods, flags=re.M)
methods = methods.replace("Section 2.4", "Section 3.4")
methods = re.sub(
    r"^> Drafting note:.*?factorial 2 × 2 design\.\s*",
    "",
    methods,
    flags=re.M | re.S,
)
methods = clean_section(methods)

results = clean_section(read("12_results_writing/results_draft.md"))
results = insert_after_section(
    results,
    "4.2 Nominal and realized logged interventions diverged",
    "![Realized force-adaptation activation timing relative to task start and contact.](figures/force_activation_timing_audit.png)\n\n"
    "**Figure 1.** Realized force-adaptation activation timing relative to task start and logged contact. Points denote trials and black bars denote medians; the red dotted line marks the nominal +0.20-s F gate. Trial-level points are shown for implementation auditing and are not treated as independent human samples.",
)
results = insert_after_section(
    results,
    "4.3 Safety-related outcomes across realized logged configurations",
    "![Participant-level threshold-referenced excess-force impulse.](figures/participant_level_primary_outcome.png)\n\n"
    "**Figure 2.** Participant-level threshold-referenced excess-force impulse from 0.20 to 1.00 s after contact under A/G/E/F. Gray lines show the five participant means; the black diamond denotes the participant-level group mean. The display is descriptive; inference is based on paired participant means (n = 5).\n\n"
    "![Contact-aligned force and commanded-stiffness trajectories.](figures/contact_aligned_force_stiffness_clean.png)\n\n"
    "**Figure 3.** Contact-aligned participant-aggregated threshold-referenced excess-force and logged commanded translational-stiffness trajectories. Trials were averaged within participant before group averaging. Logged stiffness denotes commanded software parameters, not an independent physical impedance measurement.",
)

discussion = clean_section(read("14_discussion_writing/discussion_draft.md"))
conclusion_package = read("16_conclusion_writing/conclusion_package.md")
conclusion = re.search(r"# 6\. Conclusion\n\n(.*?)(?=\n\n## Sentence-to-evidence map)", conclusion_package, flags=re.S).group(1).strip()

refs_source = read("15_introduction_related_work/verified_references.md")
references = "\n".join(
    line for line in refs_source.splitlines() if re.match(r"^\d+\. ", line)
)

front = """# Nominal Controller Modes Versus Realized Logged Interventions in Human-in-the-Loop Contact Teleoperation: A Retrospective Log-Audited Analysis

*Working title — manuscript version 1*

**Authors and affiliations:** [TO BE INSERTED]

> **Internal submission-status note.** This first integrated manuscript uses only the frozen clean-analysis materials. Items marked `[NEEDS VERIFICATION]`, especially ethics approval and informed consent, must be verified from contemporaneous records or removed before submission. The three embedded figures are the currently available clean-analysis figures; the complete final journal figure/table package remains to be finalized without changing the reported results.

## Abstract

""" + abstract

manuscript = "\n\n".join(
    [
        front.strip(),
        introduction,
        related,
        methods,
        results,
        discussion,
        "# 6. Conclusion\n\n" + conclusion,
        "# References\n\n" + references,
    ]
) + "\n"

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "figures").mkdir(exist_ok=True)
for name in (
    "force_activation_timing_audit.png",
    "participant_level_primary_outcome.png",
    "contact_aligned_force_stiffness_clean.png",
):
    shutil.copy2(ROOT / "03_clean_analysis" / "figures" / name, OUT / "figures" / name)

(OUT / "manuscript_v1_en.md").write_text(manuscript, encoding="utf-8")

zh_path = OUT / "manuscript_v1_zh.md"
if zh_path.exists():
    zh = zh_path.read_text(encoding="utf-8")
    zh = zh.replace(
        "<!-- 与英文稿相同的28条已核验英文参考文献将在构建步骤中追加；文献题名不翻译。 -->",
        references,
    )
    zh_path.write_text(zh, encoding="utf-8")

readme = """# Manuscript version 1

This directory contains an integrated English manuscript and a section-matched Chinese review translation. The frozen source chapters and the `03_clean_analysis` directory were not modified.

## Source map

- Abstract: `17_abstract_writing/abstract_package.md`, recommended conservative Version 1.
- Introduction and Related Work: `15_introduction_related_work/`.
- Methods: `13_methods_writing/methods_draft.md`, mechanically renumbered from Section 2 to Section 3 in the integrated copy.
- Results: `12_results_writing/results_draft.md`.
- Discussion: `14_discussion_writing/discussion_draft.md`.
- Conclusion: `16_conclusion_writing/conclusion_package.md`, conclusion paragraph only.
- References: the 28 verified core entries in `15_introduction_related_work/verified_references.md`.
- Figures: three existing plots from `03_clean_analysis/figures/`.

## Submission blockers retained in version 1

- Authors and affiliations have not been inserted.
- Ethics approval/exemption and informed-consent information require verification.
- Participant demographics, training details, hardware/software metadata, and contemporaneous documentation for the six replacement acquisitions remain marked where relevant.
- The final Figure 1–6 and Table I–IV journal package is not yet complete; this version embeds only three clean-analysis figures and the existing nominal-configuration table.
"""
(OUT / "README.md").write_text(readme, encoding="utf-8")
print(OUT / "manuscript_v1_en.md")
