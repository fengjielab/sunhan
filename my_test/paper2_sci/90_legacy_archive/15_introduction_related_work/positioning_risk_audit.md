# Novelty, gap, causal-language, and frozen-section audit

## K1. Novelty-overstatement audit

| Risky or forbidden formulation | Why unsupported | Safe formulation used in the drafts |
|---|---|---|
| “We propose a novel vision–force controller.” | The study is retrospective; the controller already existed in the archived experiment | “The contribution is methodological and interpretive rather than the proposal of a new vision–force controller.” |
| “We are the first to use vision/material recognition to select impedance.” | Huang et al. (2021) and Siegemund et al. (2024) are direct prior art; Jekel et al. (2026) extends the route | “The general concept of mapping visual object information to an impedance setting is already established.” |
| “Variable impedance is a contribution of this work.” | Variable impedance and teleimpedance are mature fields | The draft treats variable impedance as controller context and prior art |
| “We introduce a new timing-aware controller.” | No new controller or prospective timing design was implemented | The draft describes retrospective timing reconstruction |
| “We establish a universal intervention-fidelity framework.” | One legacy dataset cannot establish a universal standard | “A log-based reconstruction ... for a repeated-measures contact-teleoperation experiment.” |
| “First ever nominal–commanded–realized analysis.” | The targeted search cannot prove global priority, and adjacent realized-timing work exists | No first/novelty priority claim is made |

## K2. Gap-overstatement audit

| Draft/gap phrase | Risk assessment | Required boundary |
|---|---|---|
| “relatively less explicit attention is given to jointly reconstructing...” | Acceptable but still a literature-synthesis claim | Must retain “in the ... literature reviewed for this study” or equivalent |
| “mode labels alone may be insufficient...” | Defensible for asynchronous event-gated configurations | Keep “may” and the event-gated context; do not universalize to all teleoperation modes |
| “an acquisition-level audit can be necessary...” | Defensible as an interpretive recommendation | Do not change to “is always required” |
| “the concerns are usually treated in separate literatures” | Moderate risk if “usually” is read quantitatively | Prefer “the relevant concerns are treated in several partly separate literatures” at final copy-edit |

The following formulations must not enter the manuscript:

- “No previous work has considered realized controller timing.”
- “Teleoperation studies commonly fail to verify their controllers.”
- “Existing experiments rely only on nominal mode labels.”
- “This is the first data-provenance audit in robotics.”
- “Prior vision-informed impedance studies did not log timing,” unless each cited paper has been exhaustively audited and the statement is narrowed to a specific field.

## K3. Causal-overstatement audit

| Potential overread | Current safe boundary |
|---|---|
| E-A is an isolated visual effect | E is always called a “vision-enabled bundled configuration”; the final sentence explicitly says vision, stiffness, and force adaptation are not isolated |
| Lower force exposure proves improved safety | The draft uses “early threshold-referenced force exposure” and “undesirable contact loading,” not injury prevention or universal safety |
| Longer task-start-to-contact means slower operator motion | The Introduction says “pre-contact timing”; it does not call the metric approach speed or movement duration |
| G is pure post-contact force feedback | G is not characterized as a clean force-feedback ablation in either draft |
| F realizes a correct 0.20-s gate | F is not used as evidence of a correctly gated policy in either draft |
| Logged stiffness equals physical impedance | Introduction and Related Work explicitly distinguish logged commands from independent physical measurement |
| The audit caused the observed E-A difference | The audit is presented as changing the evidential interpretation, not causing the force outcome |
| The force–time pattern is a general mechanism | The Introduction reports a within-dataset association and does not claim a universal safety–efficiency law |

## K4. Contribution wording audit

### Contribution 1

**Current wording:** “A log-based reconstruction of nominal, commanded, and realized logged interventions for a repeated-measures contact-teleoperation experiment.”

**Assessment:** Supported by Methods Sections 2.4 and 2.6. “Realized logged” must remain; shortening to “realized physical intervention” would exceed the evidence.

### Contribution 2

**Current wording:** “A participant-level reanalysis ... including a directionally consistent association between the vision-enabled bundled configuration and lower early threshold-referenced force exposure relative to the fixed configuration, together with longer pre-contact and overall task timing.”

**Assessment:** Consistent with Results Sections 4.4–4.5 and Discussion Sections 5.1–5.3. It does not say “significant improvement,” “safer,” or “vision effect.” For maximum terminological identity at final assembly, “pre-contact timing” may be replaced by “task-start-to-contact time” and “overall task timing” by “total task time.”

### Contribution 3

**Current wording:** “It demonstrates within this dataset how intervention timing, acquisition provenance, and selection of the independent experimental unit constrain the interpretation of bundled controller comparisons.”

**Assessment:** Supported by the G/F timing audit, replacement-record lineage reconstruction, and participant-level inference. The qualifier “within this dataset” is essential. Do not change to a field-wide claim.

## K5. Conflicts with frozen Methods, Results, and Discussion

### Content conflicts

No substantive conflict was found:

- The outcome is consistently called **threshold-referenced excess-force impulse/exposure**, not baseline-corrected impulse.
- The timing measure is described as **pre-contact timing** or **task timing**, never as directly measured operator approach speed.
- The three levels **nominal configuration / commanded configuration / realized logged intervention** are preserved.
- The drafts do not treat logged commanded stiffness as independently measured physical impedance.
- E-A is not isolated to vision, stiffness, semantic information, damping, haptic gain, or gripper force.
- G is not described as pure post-contact force feedback.
- F is not described as a correctly realized 0.20-s post-contact gate.
- The participant is the inferential unit; no claim treats 180 trials or 45 blocks as independent human samples.
- No exact p-value or confidence interval is introduced in the Introduction or Related Work.

### Structural numbering conflict

There is one manuscript-assembly conflict, not a scientific-content conflict:

- The recommended structure makes **Related Work Section 2** and **Methods Section 3**.
- The frozen Methods file is currently numbered `# 2. Methods` with subsections `2.1–2.7` and internal references to Section 2.4.
- Results and Discussion are already Sections 4 and 5, respectively.

Because the user instructed that frozen Methods not be modified in this stage, no numbering was changed. At final manuscript assembly, either:

1. renumber Methods and all Methods internal cross-references from 2.x to 3.x; or
2. integrate Related Work into Introduction and retain Methods as Section 2.

Given the positioning burden, option 1 remains recommended.

## K6. Sentences worth tightening at final copy-edit

| Current sentence fragment | Reason | Safer/tighter option |
|---|---|---|
| “the relevant concerns are usually treated in separate literatures” | “Usually” may sound quantitative | “the relevant concerns are treated in several partly separate literatures” |
| “An acquisition-level timing and provenance audit can therefore be necessary...” | Strong but defensible | “An acquisition-level timing and provenance audit can therefore be important...” if the target journal prefers softer language |
| “changes in task time, motion strategy, or contact behavior may accompany...” | Generalized synthesis | Keep Rakita/Louca citations adjacent |
| “directionally consistent association...” | Could be misread as confirmatory if separated from sample context | Keep “participant-level,” “realized,” and “bundled” in the same sentence; Results/Discussion carry the n=5 caveat |

## K7. Reference-integrity audit

- All 28 core references have a verified DOI and/or publisher/institutional bibliographic record.
- No placeholder author, journal, year, DOI, or article title appears in the drafts.
- Wang et al. (2026), *Stiffness Copilot*, is explicitly separated as an arXiv preprint/IROS 2026 “to appear” item and is not used as a required archival citation in the drafts.
- No sentence requires an invented citation. Where no exact external source defines the study's nominal/commanded/realized terminology, the citation map directs the author to the present Methods rather than fabricating precedent.
