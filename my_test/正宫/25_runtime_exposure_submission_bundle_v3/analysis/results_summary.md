# V3 record-layer runtime-exposure results

The locked cohort contains 20 independent participants and 300 planned trials. 294 were evaluable and 6 were safety aborts.

Recorded-state classification was 294/294 (100.0%; exact 95% CI 98.75%–100.00%). Timing absolute-error MAE/P95/max were 2.381/4.957/5.408 ms. Exposure absolute-error MAE/P95/max were 0.001798/0.005996/0.006760.

Threshold rationale: at 200 Hz, 20 ms is four control cycles; 50 ms is ten cycles and equals the contact-confirmation hold interval; Phi=0.02 equals 16 ms in the 0.8 s outcome window. These limits predated the present formal data but were not preregistered.

Among evaluable trials, 65 had a clamp somewhere in the trial and 47 had a clamp in the outcome window. Logged commands are post-clamp software commands; haptic_send_ok is an API return only. Physical delivery was not independently observed.

Participant mean approach durations ranged from 1.3033 to 2.8360 s, while all-trial durations ranged from 0.6145 to 5.3001 s. The 20-person analysis is a human-generated trajectory-variability stress test, not independent hardware validation.

Human force outcomes are exploratory and use the Franka internal external-wrench estimate.
