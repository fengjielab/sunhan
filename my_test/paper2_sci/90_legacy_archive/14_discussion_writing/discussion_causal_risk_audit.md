# Causal-overinterpretation audit

## F. Sentences requiring the greatest caution

| Draft sentence or phrase | Risk level | Why it could be overread | Boundary retained in the draft |
|---|---|---|---|
| “Lower commanded stiffness around contact could have limited the force developed during early interaction.” | Medium | Suggests a mechanical pathway without a single-factor manipulation or physical impedance measurement | Uses “could have”; immediately states that stiffness was not isolated and only commands were logged |
| “Participants may have altered when they initiated motion, how they paused, or how they responded...” | Medium | Behavioral intent and motion segmentation were not directly measured | Uses “may”; lists alternatives; states that attention, caution, intent, onset, and speed were unavailable |
| “The longer pre-contact interval is consistent with more conservative interaction timing...” | Medium | Could be converted into “participants moved more slowly” | Explicitly says slower physical approach cannot be distinguished from delayed initiation or pauses |
| “The paired pattern is consistent with an observed safety-efficiency trade-off.” | Medium | “Safety” could be overread as injury prevention or universal safety | Restricted to safety-related force exposure and described as an observed pattern, not a mechanism |
| “The audited wall-clock/monotonic-clock mismatch did not reliably enforce that gate.” | Low | Could be overextended to claim the bug alone explains every F activation | Used only to delimit F-E; does not quantify an isolated causal contribution to outcomes |
| “Per-trial realized timing is needed to interpret asynchronous interventions.” | Low | Could sound like a universal standard | Discussion says the observations “illustrate” importance and offers practical reporting considerations, not a universal mandate |
| “A manifest protects acquisition-level provenance.” | Low | Could be read as proof that all other pipelines are invalid | Scoped to preventing the documented cross-attempt join risk in similar analyses |

## Sentences that must not replace the current wording

| Forbidden causal wording | Why unsupported | Safe replacement already used |
|---|---|---|
| “Vision significantly improved safety.” | E is bundled; n=5; exact and adjusted inference are limited; safety was not independently measured | “E was associated with lower threshold-referenced early force exposure under the realized bundled configuration.” |
| “Vision reduced force because stiffness was lower.” | Vision and stiffness were not isolated; several other parameters changed | “Lower logged commanded stiffness is one plausible context, but the individual contributions cannot be distinguished.” |
| “Force feedback was ineffective.” | G was pre-activated and F was mistimed | “The realized G/F comparisons do not estimate correctly contact-gated force policies.” |
| “F failed.” | Implementation timing diverged, but descriptive F data remain valid | “F did not reliably realize its nominal 0.20-s gate.” |
| “Participants deliberately slowed down.” | Intent and movement onset/speed were not measured | “The longer pre-contact interval may reflect delayed initiation, pauses, slower approach, or other interaction changes.” |
| “Our method is universally safer.” | No universal population, independent safety endpoint, or confirmatory evidence | “The present dataset showed lower safety-related force exposure under E relative to A.” |
| “The audit proves previous robotics studies are unreliable.” | No evidence about other studies | “The present observations highlight the value of logging realized intervention timing.” |
| “180 independent experiments demonstrated...” | Only five independent human participants | “The analysis included 180 repeated trials from five independent participants.” |

## Final causal-language check

- No draft sentence attributes E-A uniquely to vision, translational stiffness, damping, haptic feedback, or gripper force.
- No draft sentence interprets G as a pure post-contact intervention.
- No draft sentence interprets F-E as a correctly gated 0.20-s refinement effect.
- No draft sentence equates logged commanded stiffness with independently measured physical impedance.
- No draft sentence equates task-start-to-contact time with direct movement duration or operator speed.
- No draft sentence converts the unadjusted paired-t result into a strong confirmatory conclusion.
