# Discussion logic map

## A. Overall argumentative flow

```text
Audited finding
    E-A: lower threshold-referenced early force exposure in the same direction for 5/5 participants
        |
        +-- inferential boundary: n=5; exact p=0.0625; Holm-adjusted results do not support a strong confirmatory claim
        |
        +-- possible explanations
        |      +-- lower logged commanded stiffness around contact
        |      +-- bundled vision-selected changes in damping, haptics, and gripper force
        |      +-- human timing/behavioral adaptation
        |      `-- none can be isolated with the present design
        |
        +-- paired temporal observation
        |      +-- longer task-start-to-contact time
        |      +-- longer total task time
        |      `-- observed safety-efficiency trade-off pattern, not a proven mechanism
        |
        `-- interpretation boundary
               effect associated with the realized vision-enabled bundled configuration

Implementation audit
    G: raw-force adaptation, no baseline-ready/contact gate, usually active before task/contact
    F: nominal 0.20-s gate, but wall-clock/monotonic-clock mismatch and earlier realized activation
        |
        `-- A/G/E/F cannot be treated as a clean realized 2 × 2 factorial intervention

Methodological implication
    nominal configuration -> commanded configuration -> realized logged intervention
        |
        +-- event and parameter trajectories must be retained
        +-- raw/event/scalar files must share acquisition identity
        +-- participant remains the independent human unit
        `-- software-log success is not independent physical verification
```

## B. Core question answered by each subsection

| Section | Core question | Evidence used | Interpretive endpoint | Prohibited endpoint |
|---|---|---|---|---|
| 5.1 Main findings | What are the three findings that govern the entire Discussion? | E-A participant direction and inference; timing outcomes; G/F timing audit | Directionally consistent but exploratory E-A association, observed trade-off pattern, and non-factorial realized configurations | “E significantly improved safety”; “four modes formed a 2 × 2 design” |
| 5.2 Lower early force exposure under E | What mechanisms are compatible with the lower E-A force estimate, and which can be isolated? | Logged commanded-stiffness profiles, vision-enabled bundled parameters, initial peak direction, task-start-to-contact difference | Effect associated with the realized vision-enabled bundled configuration | Isolated visual, stiffness, damping, haptic, or gripper effect |
| 5.3 Force exposure and pre-contact interval | What does the joint force/time pattern mean? | Threshold-referenced impulse, task-start-to-contact time, total task time | Observed safety-efficiency trade-off pattern and need for joint physical/temporal evaluation | Participants deliberately or physically moved more slowly |
| 5.4 Nominal versus realized interventions | How do the G/F deviations change the meaning of G-A and F-E? | G pre-task/pre-contact activation; raw-force gate; F early activation and clock mismatch | Contrasts among realized logged bundled configurations | Isolated post-contact force-feedback or correctly gated refinement effect |
| 5.5 Methodological implications | What reporting and analysis practices follow directly from this audit? | Event trajectories, master manifest, participant aggregation, asynchronous timing, success definition | Practical reporting considerations for similar human-in-the-loop studies | A universal new standard or proof that other robotics studies are unreliable |
| 5.6 Limitations | What prevents stronger generalization or causal attribution? | n=5, retrospective window, bundling, order uncertainty, force estimate, missing object/participant metadata, software success, G/F deviations | Transparent scope of inference | Hiding limitations or treating 180 trials as 180 independent humans |

## Argument discipline

- A statement is **data-supported** only when it is directly present in frozen Results or confirmed Methods.
- An **interpretation** connects observed results without asserting an isolated causal mechanism.
- A **speculation** is retained only when explicitly marked by phrases such as “may reflect,” “one possible explanation,” or “is consistent with.”
- The Discussion uses “safety-related force exposure,” not independently verified safety, injury prevention, or universal system safety.
- No literature claim or reference is introduced in this draft; literature integration can occur later only with verified sources and without changing the evidence boundaries above.
