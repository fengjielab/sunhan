# Citation sentence map

This map identifies claims that need external references. Sentences describing the present study, its dataset, research questions, reconstruction procedure, or frozen findings should instead be supported by the paper's Methods/Results and do not require a related-work citation merely to repeat the study description.

## Introduction

| Location | Claim requiring support | Recommended reference(s) | Citation status in draft |
|---|---|---|---|
| P1-S1 | Teleoperation extends human capability to remote, hazardous, inaccessible, or insufficiently structured tasks | Hokayem and Spong (2006); Peternel and Ajoudani (2023) | Add at sentence end if journal requires support for broad application claim |
| P1-S2 | Contact teleoperation is a coupled operator–master–robot–controller–environment system | Hannaford (1989); Hokayem and Spong (2006) | Present |
| P1-S3–S4 | Coupling creates competing contact-loading, responsiveness, transparency, and efficiency objectives | Lawrence (1993); Passenberg et al. (2010); Louca et al. (2024) | Present across paragraph; optional extra citation after S4 |
| P1-S5 | Haptic benefits depend on task and timing | Lawrence (1993); Huang et al. (2019); Louca et al. (2024) | Present |
| P1-S6 | Operators adapt behavior to dynamics/delay | Rakita et al. (2020); Louca et al. (2024) | Present |
| P1-S7 | Evaluation should include physical and operator-mediated task measures | Huang et al. (2019); Rakita et al. (2020); Louca et al. (2024); Gong et al. (2024) | Supported by preceding citations; add direct citation if reviewer requests |
| P2-S1 | Impedance control shapes motion–force interaction | Hogan (1985) | Present |
| P2-S2 | Variable impedance changes parameters using state, sensing, learning, or human commands | Buchli et al. (2011); Abu-Dakka et al. (2018); Abu-Dakka and Saveriano (2020) | Present |
| P2-S3 | Teleoperation systems transmit stiffness or adapt contact behavior using force/learned structure | Walker et al. (2010); Ajoudani et al. (2012); Michel et al. (2021); Peternel and Ajoudani (2023); Michel et al. (2023) | Present |
| P2-S4 | Vision can provide object/environment information before force contact | Huang et al. (2021); Siegemund et al. (2024) | Supported by following sentence; direct citation optional |
| P2-S5 | Material/geometry/relationship information has been mapped to impedance before contact | Huang et al. (2021); Siegemund et al. (2024); Jekel et al. (2026) | Present |
| P2-S6 | Visual object information to impedance is established prior art | Huang et al. (2021); Siegemund et al. (2024) | Inherits immediately preceding citations; retain both works nearby |
| P3-S1 | Human, vision, contact, adaptation, and parameter processes can evolve on different timelines | Rakita et al. (2020); Aldana-López et al. (2023); Marchesi et al. (2024) | Add Marchesi et al. (2024) if a citation is desired directly after this sentence |
| P3-S2 | Perception latency is a control issue and small visual–haptic offsets can be perceptible | Vogels (2004); Aldana-López et al. (2023) | Present |
| P3-S3 | Delay type can alter performance and operator compensation | Rakita et al. (2020); Louca et al. (2024) | Present |
| P3-S4 | A designed event-triggered transition need not occur at the intended stage in every execution | Aldana-López et al. (2023); Marchesi et al. (2024), plus present-study Methods/Results | External literature is adjacent, not direct proof; present study provides the direct example |
| P3-S5–S6 | Nominal code, logged commands, and physical realization are different evidential levels | No exact established terminology was found; cite present-study Methods for operational definitions | Do not attach a fake external citation; these are definitions used by this study |
| P4-S1 | Robotics/HRI emphasizes reproducibility, reporting, and artifacts | Bonsignorio and del Pobil (2015); Bonsignorio (2017); Gunes et al. (2022); Bagchi et al. (2023) | Present |
| P4-S2 | Interactive HRI has measured realized robot-response timing | Marchesi et al. (2024) | Present |
| P4-S3 | The relevant questions are distributed across separate literatures | Use the route-defining reviews: Hokayem and Spong (2006); Abu-Dakka and Saveriano (2020); Peternel and Ajoudani (2023); Gunes et al. (2022) | Add only if editor requests; the full Related Work substantiates this synthesis |
| P4-S4 | Joint per-acquisition reconstruction receives relatively less explicit attention in the reviewed contact-teleoperation literature | Cite Related Work Section 2.3 and its matrix; no single paper can prove a negative | Wording is deliberately bounded to “reviewed for this study” |
| P4-S5–S7 | Boundary and rationale of the gap | Present study's audit plus Marchesi et al. (2024) and reproducibility literature | No universal absence claim is made |
| P5-S1–S3 | Dataset, reconstruction, and three RQs | Present-study Methods | Internal evidence; no external citation needed |
| P5-S4–S8 | Contributions and minimal result direction | Present-study Methods and Results | Internal evidence; no external citation needed |
| P5-S9 | No isolated causal attribution | Present-study Methods, Results, and Discussion | Internal evidence; no external citation needed |

## Related Work

| Location | Claim requiring support | Recommended reference(s) | Citation status in draft |
|---|---|---|---|
| 2.1-P1-S1–S2 | Coupled teleoperation model; stability/transparency/delay history | Hannaford (1989); Lawrence (1993); Hokayem and Spong (2006) | Present |
| 2.1-P1-S3 | Environment/operator/task information can enter controller design | Passenberg et al. (2010) | Present |
| 2.1-P1-S4–S6 | Human studies use multi-domain metrics; feedback and delay affect performance/strategy | Huang et al. (2019); Rakita et al. (2020); Louca et al. (2024); Gong et al. (2024) | Present |
| 2.1-P2-S1 | Impedance foundation | Hogan (1985) | Present |
| 2.1-P2-S2 | Analytic/learning variable-impedance branches | Buchli et al. (2011); Abu-Dakka et al. (2018); Abu-Dakka and Saveriano (2020) | Present |
| 2.1-P2-S3–S5 | User-controlled teleimpedance, human stiffness modulation, adaptive/shared contact control | Walker et al. (2010); Ajoudani et al. (2012); Peternel et al. (2018); Michel et al. (2021, 2023) | Present |
| 2.1-P2-S6 | Diversity of teleimpedance interfaces and feedback pathways | Peternel and Ajoudani (2023) | Present |
| 2.1-P3-S1–S2 | Controller papers define/evaluate conditions and may report trajectories, but this differs from a legacy fidelity audit | Synthesis of Michel et al. (2021, 2023), Huang et al. (2021), Siegemund et al. (2024) | Do not cite as proof that others failed; wording distinguishes research purpose |
| 2.2-P1-S1 | Visual information can precede force contact | Huang et al. (2021); Siegemund et al. (2024) | Supported in paragraph |
| 2.2-P1-S2 | Camera scene representations/virtual fixtures in telemanipulation | Huang et al. (2019) | Present |
| 2.2-P1-S3 | Vision/property/voice semi-autonomous teleimpedance | Huang et al. (2021) | Present |
| 2.2-P1-S4 | Geometry/material/environment-relation stiffness selection | Siegemund et al. (2024) | Present |
| 2.2-P1-S5 | Gaze/speech/VLM 3D stiffness commands | Jekel et al. (2026) | Present |
| 2.2-P2-S1–S2 | These works establish vision→property→impedance as prior art | Huang et al. (2021); Siegemund et al. (2024) | References immediately precede; retain both |
| 2.2-P2-S3–S5 | Present study's narrower timing/bundle question | Present-study Methods and Results | Internal evidence; no external citation needed |
| 2.3-P1-S1–S4 | Visual–haptic delay, teleoperation delay, and perception latency | Vogels (2004); Rakita et al. (2020); Louca et al. (2024); Aldana-López et al. (2023) | Present |
| 2.3-P2-S1–S4 | Reproducibility and reporting literature; realized response timing | Bonsignorio and del Pobil (2015); Bonsignorio (2017); Gunes et al. (2022); Bagchi et al. (2023); Marchesi et al. (2024) | Present |
| 2.3-P3-S1–S2 | Narrow gap across the reviewed literature | Entire related-work matrix; no single citation can establish a universal negative | Wording explicitly avoids a universal claim |
| 2.3-P3-S3–S5 | Present study's three-level reconstruction and evidential boundary | Present-study Methods Sections 2.4 and 2.5 | Internal evidence; no external citation needed |

## Citations that must remain near the novelty boundary

The following references should not be removed during shortening because they directly constrain novelty:

1. Huang et al. (2021) — prior vision/material-to-impedance teleoperation.
2. Siegemund et al. (2024) — closest geometry/material-aware semi-autonomous teleimpedance.
3. Peternel and Ajoudani (2023) — teleimpedance survey.
4. Rakita et al. (2020) — timing type and operator adaptation.
5. Marchesi et al. (2024) — realized robot response timing in reproducible interactive HRI.
6. Gunes et al. (2022) or Bagchi et al. (2023) — reproducibility/reporting boundary.
