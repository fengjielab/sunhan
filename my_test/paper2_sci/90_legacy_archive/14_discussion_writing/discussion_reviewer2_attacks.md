# Reviewer 2 attack test for the Discussion

## G. Five most likely attacks

### 1. “The Discussion still overstates evidence from only five participants.”

**Why the reviewer may raise it:** The unadjusted paired t-test for E-A is below 0.05, which can tempt confirmatory wording despite the exact-test floor and multiplicity correction.

**Current defense:** The opening paragraph leads with n=5, reports exact \(p=0.0625\), states that Holm-adjusted inference does not support a strong confirmatory conclusion, and calls the evidence exploratory and directional.

**Residual vulnerability:** Even “safety-efficiency trade-off” may sound general. Keep “observed ... pattern,” “in the present dataset,” and “safety-related force exposure” in the final manuscript.

### 2. “The proposed explanation is post hoc because E changes many parameters.”

**Why the reviewer may raise it:** E jointly changed stiffness, damping, haptic, and gripper settings, while vision selected the bundle.

**Current defense:** Section 5.2 presents lower logged commanded stiffness only as one plausible context, explicitly rejects single-factor attribution, and defines the result as associated with the realized vision-enabled bundled configuration.

**Residual vulnerability:** A schematic or caption that labels E simply “vision” could undo this protection. Figure/Table labels must preserve the bundled-configuration wording.

### 3. “The claimed efficiency cost is not a measured approach-speed cost.”

**Why the reviewer may raise it:** `task_start` indicates readiness, not movement onset, so the interval includes multiple unobserved components.

**Current defense:** Section 5.3 calls it task-start-to-contact time or the pre-contact interval and explicitly lists reaction, hesitation, movement, and pauses as indistinguishable components.

**Residual vulnerability:** Do not later write in the Abstract, Introduction, caption, or Conclusion that participants “moved more slowly.”

### 4. “G and F implementation defects invalidate the force-policy conclusions.”

**Why the reviewer may raise it:** G lacked a contact gate and F did not reliably realize the nominal 0.20-s delay.

**Current defense:** The Discussion agrees that G-A and F-E cannot identify correctly gated force-policy effects. It retains only descriptive comparisons among realized logged configurations and does not claim that force feedback is ineffective.

**Residual vulnerability:** The paper's contribution must remain the log-audited interpretation of existing configurations, not a performance ranking of nominal algorithms.

### 5. “Measurement and reporting gaps limit reproducibility and generalization.”

**Why the reviewer may raise it:** Force came from the internal wrench estimate; object identity, prospective order, participant metadata, and independent success adjudication are incomplete; ethics and consent remain unresolved.

**Current defense:** Section 5.6 states each limitation directly and confines material claims to archived categories and success claims to software logs.

**Residual vulnerability:** Ethics approval/exemption and informed consent are submission blockers, not optional limitations. They must be confirmed before submission. If demographic, training, hardware, or object records remain unavailable, the manuscript must preserve the limitation wording rather than silently filling the gaps.
