# Vision-semantic multi-channel parameter scheduling for an integrated haptic teleoperation mechatronic system

## Structured Abstract

**Purpose**
This paper addresses the challenge that fixed teleoperation parameters are difficult to tune for heterogeneous objects with different fragility, stiffness and grasping requirements. We propose a vision-semantic multi-channel parameter scheduling framework that bridges object-level semantics and low-level mechatronic interface parameters, establishing a three-level mapping from perception to operation-oriented strategies and control parameters before contact.

**Design/methodology/approach**
The mechatronic system integrates an asynchronous RGB-D perception thread, a 200 Hz master–slave Cartesian impedance control loop, a haptic-interface parameter pre-setting module and gripper execution on an Omega.7–Franka Panda–Franka Hand platform. Before contact, an RGB-D camera identifies the target object and maps it to one of three operation-oriented policies: fragility-oriented, balanced and stability-oriented. The proposed scheduler then coordinates slave-side translational/rotational stiffness, damping ratio, master-side haptic-interface gain, force-interface dead zone, gripper closing speed and grasping force through a discrete, interpretable parameter table. Three operators performed 135 grasping trials involving six objects and five modes: fixed parameters, manual selection, full vision-semantic multi-parameter scheduling, visual information only and vision-semantic impedance-only scheduling.

**Findings**
In the tested mechatronic platform and participants, the proposed mode achieved the shortest median completion time (19.57 s [18.41, 20.05] IQR), the highest success rate as a descriptive metric (26/27, 96.3%) and the lowest Raw NASA-TLX (median 48.67 [47.67, 51.83] IQR). Compared with impedance-only scheduling, the proposed mode reduced mean completion time by -1.79 s (Bootstrap 95% CI [-2.51, -1.10] s; relative reduction 8.5%), while all three operators and all six tested objects showed the same directional trend. The trajectory-length difference was smaller (-0.024 m, 95% CI [-0.059, 0.014] m), suggesting that the benefit mainly came from fewer pauses and operation corrections rather than a shorter geometric path. Raw NASA-TLX decreased by -4.87 points (Bootstrap 95% CI [-5.35, -4.39]).

**Originality**
The originality lies in a deployable, system-level bridge between high-level object semantics and low-level mechatronic teleoperation interface parameters, rather than in a new impedance equation or a closed-loop force-feedback method. The proposed three-level mapping coordinates perception, slave-side impedance, pre-contact haptic-interface settings and gripper execution parameters in a unified mechatronic architecture. The asynchronous perception-control separation, the strategy-locking mechanism and the five-mode design constitute a practical integration blueprint that distinguishes perception, manual selection, impedance-only scheduling and full multi-channel pre-contact coordination.

**Keywords:** mechatronic system integration; haptic teleoperation; impedance control; vision semantics; real-time control architecture; human-in-the-loop experiment

---

## 1 Introduction

Teleoperated robots combine human judgment with remote robotic execution, which is well-suited for flexible manufacturing, hazardous-environment operations, service robotics, and unstructured object manipulation. Haptic teleoperation further conveys remote contact information to the operator through master-side force feedback, improving the operator's perception of grasping, contact, and slip risks. From a mechatronic system design perspective, a practical haptic teleoperation platform must integrate multiple subsystems including mechanical actuation, human-machine interfaces, visual perception, real-time control, and parameter scheduling [1–4].

In real grasping tasks, operators encounter objects with diverse shapes, surfaces, fragility, and gripping requirements. If the system always uses a fixed set of impedance and gripper parameters, it must compromise among compliant contact, response speed, positioning stability, and grasping reliability. This problem is not limited to laboratory tabletop grasping. Similar requirements arise in remote maintenance, hazardous material handling, flexible sorting, unstructured disassembly, and human-supervised robotic operations, where the mechatronic system needs to handle fragile items, slippery objects, rigid tools, lightweight containers, or geometrically irregular objects in partially structured environments. The six objects selected in this study—apple, banana, paper cup, bottle, mouse, and scissors—do not claim to cover a complete industrial object set. Instead, they serve as a **mechatronic benchmark task set**: they are selected to generate distinct requirements on compliance, haptic-interface sensitivity, and gripper execution, rather than to represent a complete industrial object taxonomy.

Impedance control provides compliance during contact by prescribing the dynamic relationship among robot displacement deviation, velocity deviation, and interaction force [5]. Fixed-impedance control is simple to implement and easy to deploy, but cannot simultaneously accommodate fragile, lightweight, and rigid objects in heterogeneous grasping. Variable impedance control can adjust stiffness and damping online based on contact force, trajectory error, task phase, or human motion states [6–9]. However, online variable impedance typically depends on continuous state estimation, post-contact feedback, and stability constraints. For teleoperation tasks where object categories are identifiable and task procedures are relatively fixed but still require the operator to perform fine grasping and placement, pre-contact object semantics can serve as a low-cost, interpretable task prior.

Prior studies on visual impedance, shared control, and haptic guidance have shown that visual information, task state, or operator intent can improve remote operation efficiency and interaction experience [10–13]. However, in heterogeneous-object haptic teleoperation, object semantics affect not only slave-side arm compliance but also the haptic-interface feedback intensity, dead zone, gripper closing speed, and grasping force that the operator expects. When only visual information is displayed without changing the system dynamics, the operator must still compensate manually. When only impedance is adjusted while default force-feedback and gripper parameters remain unchanged, the grasping and transport phases may still be constrained by the gripper and haptic-feedback channels. Therefore, the question addressed in this paper is: In real haptic teleoperation grasping, does pre-contact, vision-semantic-driven multi-channel mechatronic parameter coordination outperform fixed parameters, manual selection, visual cues, and impedance-only adjustment?

This paper proposes a vision-semantic-driven multi-channel parameter scheduling method from a mechatronic system integration perspective. The system maps the target object to one of three operation-oriented strategies and invokes a discrete, interpretable parameter table before contact, simultaneously configuring slave-side impedance, master-side haptic-interface parameters, and gripper execution parameters. The contributions are as follows:

1. **Mechatronic system architecture integration.** RGB-D perception, 200 Hz real-time control, Cartesian impedance, haptic-interface presetting, and gripper execution are unified within an asynchronous perception-control decoupled mechatronic architecture, with seven explicitly defined subsystem layers and their coordination relationships.
2. **Three-level mapping: vision semantics–operation strategy–control parameters.** Object category is transformed into fragility-oriented, balanced, and stability-oriented strategies, allowing visual information to enter the mechatronic teleoperation system as a pre-contact control prior.
3. **Multi-channel pre-contact parameter coordination.** Beyond adjusting slave-side translational/rotational stiffness and damping ratio, the method simultaneously presets master-side haptic-interface gain, force-interface dead zone, gripper closing speed, and grasping force. This paper does not claim closed-loop force-feedback modeling, contact force estimation, or haptic transparency verification as its contributions.
4. **Five-mode human-in-the-loop ablation validation.** On a real Omega.7–Panda platform, five modes—fixed parameters, manual selection, vision multi-parameter, vision observe only, and vision impedance-only—are configured to distinguish the roles of visual cue, manual parameter selection, impedance-only adjustment, and full multi-channel mechatronic coordination.

Unlike studies focusing on novel impedance equations or online adaptive post-contact control, the novelty of this paper lies in providing a system-level pre-contact parameter scheduling paradigm that bridges high-level object semantic perception and low-level mechatronic teleoperation interface parameters. The haptic-interface gain and dead zone in this paper are used only as interface presets in the pre-contact strategy table, not as independent contributions to closed-loop force feedback or haptic transparency research. The core positioning of this paper is: a low-computation, interpretable, deployable mechatronic-system pre-contact semantic parameter initialization method.

---

## 2 Method and System Implementation

### 2.1 Mechatronic System Architecture

The mechatronic teleoperation platform consists of seven subsystem layers working in coordination. The information flow and system architecture are illustrated in Figs. 1 and 2.

**Fig. 1.** Mechatronic haptic teleoperation experimental platform, labeling the Omega.7 force-feedback master, Franka Panda 7-DOF arm, Franka Hand gripper, Intel RealSense D435i RGB-D camera, target object area, and control computer.

**Fig. 2.** System information flow diagram, including master input, incremental position mapping, visual recognition, asynchronous buffer, strategy locking, parameter scheduling, impedance control, gripper control, and basic haptic interface. The figure distinguishes the low-frequency vision thread (~20 Hz) from the 200 Hz main control thread, as well as the coordination between the parameter scheduling layer and the safety layer.

**Mechanical execution layer**: The Franka Panda 7-DOF robot arm and Franka Hand gripper constitute the execution side. The Panda responds to desired pose and impedance parameters via Cartesian impedance control; the Franka Hand executes open/close actions at a specified speed and grasping force.

**Human-machine interface layer**: The Omega.7 7-DOF force-feedback master device captures the operator's displacement and gripper input, and renders slave-side interaction forces through the basic haptic interface. The operator controls gripper closure via the gripper opening; the system sets the gripper speed and force upper bounds according to the current strategy's parameter table.

**Perception layer**: An Intel RealSense D435i RGB-D camera captures RGB-D images at approximately 20 Hz. The YOLO11n object detection model runs in an independent sub-process (decoupled from the Python GIL), with per-frame processing time of approximately 50 ms. Detection results are transmitted back to the main control thread via `multiprocessing.Queue(maxsize=2)`, with shared state protected by `threading.Lock`.

**Control layer**: The 200 Hz main control loop executes: read Omega.7 pose increment → apply position scale and coordinate mapping → update slave desired pose → call Franka Cartesian impedance controller → read slave-side external force estimate → render master-side basic haptic feedback. The control period is 5 ms and is not blocked by vision inference.

**Vision thread**: The vision sub-process asynchronously receives RGB frames (`mp.Queue(maxsize=1)` retains only the latest frame to avoid latency accumulation), performs object detection, and returns class labels and confidence. The vision thread is fully decoupled from the control thread; the maximum vision inference time (~50 ms) does not affect the real-time performance of the 200 Hz control loop.

**Parameter scheduling layer**: After vision results enter the scheduling layer, the object-class-to-strategy mapping looks up the seven-parameter set (\(K_t, K_r, \zeta, K_f, d, v_g, F_g\)) from the preset parameter table and writes them into the control-loop shared variables via atomic updates. Parameter updates are triggered only at the strategy-lock event after the first valid detection; thereafter, parameters remain unchanged for the entire task episode.

**Safety layer**: When vision is not locked or the detection result is unmappable, the system uses the default balanced-strategy parameters as a safe fallback. Intra-task strategy locking prevents frequent parameter jumps due to vision jitter. The arm's built-in collision detection, program-exit zero-force command, unified initial pose, and manual emergency stop jointly constitute the basic safety measures.

### 2.2 Real-time Implementation and Synchronization

Table 1 summarizes the frequency/timing characteristics, inputs, outputs, and whether each system module blocks the main control loop.

**Table 1.** Real-time characteristics of mechatronic system modules.

| Module | Rate / Latency | Input | Output | Blocks main loop? |
|:---|---:|---:|---|:---:|
| Master input | 200 Hz | Omega.7 pose & buttons | \(\Delta\mathbf{x}_m\) | No |
| Slave control | 200 Hz | \(\mathbf{x}_d, \mathbf{K}, \mathbf{D}\) | Panda torque command | No |
| Vision detection (YOLO11n) | ~20 Hz (50 ms/frame) | RGB-D image | object class, confidence | No (sub-process) |
| Strategy scheduler | Event-based (on first valid detection) | class, confidence | \(\Theta(c)\) parameter set | No |
| Haptic rendering | 200 Hz | \(\mathbf{F}_{ext}, K_f, d\) | Omega.7 force vector | No |
| Gripper command | Event-based (gripper button) | gripper input, \(v_g, F_g\) | Franka Hand grasp/goal | No |

Vision detection and strategy scheduling are both event-driven and do not block the main control loop. The vision sub-process runs as an independent Python process, using `multiprocessing.Queue` in a producer-consumer pattern to pass detection results. The frame queue length is limited to 1 (retaining only the latest frame), and the result queue length is limited to 2. At the start of each 5 ms period, the main control thread non-blockingly reads the result queue; if the queue is empty, the previously locked strategy is retained; if vision has never locked, the default balanced parameters are maintained. Strategy locking occurs before the approach phase begins: once the main control thread detects a valid class with confidence ≥ 0.25, it immediately locks the strategy and sets all seven parameters atomically; thereafter, parameters remain unchanged for the entire task episode.

**Control-loop jitter.** Per-cycle timing instrumentation (via `time.perf_counter()`) was not performed during the formal 135 trials because the trajectory CSV logged the system clock (`time.time()`) for timestamping, which has insufficient resolution for cycle-level profiling. Therefore, the present paper reports the non-blocking software architecture design—specifically, the vision sub-process (`mp.Process`) is fully decoupled from the 200 Hz main control thread via `multiprocessing.Queue`, meaning that the ~50 ms YOLO inference does not occupy the main-thread time slice. The system-level implications of this architecture are discussed in §5.4; formal cycle-level profiling remains future work.

### 2.3 Master-Slave Incremental Position Mapping

The master-side position increment between adjacent sampling instants is

\[
\Delta\mathbf{x}_m(k)=\mathbf{x}_m(k)-\mathbf{x}_m(k-1).
\]

The slave-side desired position update is

\[
\mathbf{x}_d(k)=\mathbf{x}_d(k-1)+S\mathbf{C}\Delta\mathbf{x}_m(k),
\]

where the position scaling factor is fixed at \(S=3.0\) and \(\mathbf{C}=\mathrm{diag}(-1,-1,1)\) is the coordinate mapping matrix. The position scaling factor is not included in the visual scheduling variables, so that experimental differences are concentrated on impedance, haptic-interface, and gripper parameters.

### 2.4 Slave-Side Cartesian Impedance Control

The slave side uses Cartesian impedance control, whose equivalent relationship is

\[
\mathbf{F}_c=\mathbf{K}(c)(\mathbf{x}_d-\mathbf{x})+\mathbf{D}(c)(\dot{\mathbf{x}}_d-\dot{\mathbf{x}}),
\]

where \(c\) is the strategy class, and \(\mathbf{K}(c)\) and \(\mathbf{D}(c)\) are the corresponding stiffness and damping matrices. Translational and rotational stiffness are written as

\[
\mathbf{K}(c)=\mathrm{diag}(K_t,K_t,K_t,K_r,K_r,K_r).
\]

Damping is configured according to the damping ratio \(\zeta(c)\). Classical impedance control provides the basic mechanism for compliant interaction. The improvement in this paper lies not in the impedance equation itself, but in the task-relevant initialization of multi-channel mechatronic control parameters using pre-contact object semantics.

### 2.5 Haptic-interface Parameter Implementation

The Omega.7 master device is capable of force-feedback rendering. The slave-side external force estimate \(\mathbf{F}_{\mathrm{ext}}\) is provided by the Franka robot's built-in joint-torque estimator. The master-side basic haptic feedback is rendered according to the following interface-level formula:

\[
\mathbf{u}_h =
\begin{cases}
\mathbf{0}, & \|\mathbf{F}_{\mathrm{ext}}\| \le d,\\[4pt]
K_f\bigl(\|\mathbf{F}_{\mathrm{ext}}\|-d\bigr)\,
\dfrac{\mathbf{F}_{\mathrm{ext}}}{\|\mathbf{F}_{\mathrm{ext}}\|}, & \|\mathbf{F}_{\mathrm{ext}}\| > d.
\end{cases}
\]

Here \(\mathbf{u}_h\) is the three-dimensional force-feedback vector sent to the Omega.7 master device, and \(d\) is the dead-zone threshold. The dead-zone operator outputs only the portion exceeding \(d\) along the external-force direction, attenuating small perturbations and haptic-interface jitter. **\(K_f\) and \(d\) are only used to scale and threshold the basic haptic cue rendered on the master side. They are not updated online during the task and are not evaluated as an independent force-feedback controller. In this study, this term is only an interface setting, not a closed-loop force-feedback contribution.** This paper does not study the accuracy of post-contact external force estimation, haptic transparency, force-feedback stability, or the comparison of force feedback vs. no force feedback, nor does it introduce force-feedback-driven online impedance adaptation. The experiments in this paper can only support the overall mechatronic-system-level conclusion that "the full pre-contact multi-parameter strategy outperforms impedance-only adjustment"; they cannot independently prove the causal contributions of the haptic-interface parameters or gripper parameters. Post-contact external force estimation, force-feedback closed-loop correction, and operator haptic perception validation are reserved for subsequent studies.

### 2.6 Vision-semantic Multi-channel Parameter Scheduling

After visual detection outputs the target class, the system maps the class to one of three **operation-oriented strategies** rather than strict material categories: fragility-oriented strategy, balanced strategy, and stability-oriented strategy. Apple and banana map to the fragility-oriented strategy; paper cup and bottle map to the balanced strategy; mouse and scissors map to the stability-oriented strategy. This mapping is based on the operational risks and grasping requirements in the present experimental tasks, not on a universal physical classification of material stiffness. After the first valid detection with confidence ≥ 0.25, the system locks the strategy for the current task episode. If no valid class is detected or the class is unmappable, the balanced-strategy default parameters are retained as a safe fallback. Intra-task strategy locking prevents frequent switching due to detection jitter.

The full strategy is defined as

\[
\Theta(c)=\{K_t,K_r,\zeta,K_f,d,v_g,F_g\},
\]

where \(K_f\) is the master-side haptic-interface gain, \(d\) is the force-interface dead zone, and \(v_g\) and \(F_g\) are the gripper closing speed and grasping force setting, respectively.

**Table 2.** Parameter table for the three operation-oriented strategies.

| Strategy | Objects | \(K_t\) (N/m) | \(K_r\) (N·m/rad) | \(\zeta\) | \(K_f\) | \(d\) (N) | \(v_g\) (m/s) | \(F_g\) (N) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Fragility-oriented | Apple, Banana | 50 | 5 | 0.8 | 0.2 | 0.3 | 0.02 | 8 |
| Balanced | Paper cup, Bottle | 150 | 10 | 1.0 | 0.5 | 0.4 | 0.05 | 15 |
| Stability-oriented | Mouse, Scissors | 200 | 13 | 1.2 | 0.7 | 0.5 | 0.10 | 20 |

### 2.7 Parameter Design Space and Rationale

Parameter selection follows the engineering logic of "object operational risk → control response → hardware constraint." Table 3 presents the design space for each parameter: the physical meaning of low and high values, and the hardware/safety boundaries that constrain the values used in this study.

**Table 3.** Parameter design space: physical meaning of low and high values, hardware constraints, and the values used in this study.

| Parameter | Low-value implication | High-value implication | Hardware/safety constraint | Value used |
|:---|:---|:---|:---|:---|
| \(K_t\) | Soft compliance, low impact | Precise positioning stability | Panda impedance loop stability range | 50 / 150 / 200 |
| \(K_r\) | Compliant orientation | Stable orientation | Rotational response stability | 5 / 10 / 13 |
| \(\zeta\) | Fast response, potential oscillation | Stronger damping | Overshoot avoidance | 0.8 / 1.0 / 1.2 |
| \(K_f\) | Subtle haptic cue | Strong contact awareness | Omega.7 comfort range | 0.2 / 0.5 / 0.7 |
| \(d\) | Sensitive to small forces | Noise suppression | Haptic-interface jitter | 0.3 / 0.4 / 0.5 |
| \(v_g\) | Low-impact closure | Fast grasping | Franka Hand execution limits | 0.02 / 0.05 / 0.10 |
| \(F_g\) | Gentle grip | High grasping stability | Gripper force limits | 8 / 15 / 20 |

The fragility-oriented strategy adopts lower translational/rotational stiffness, lower interface gain, lower gripper speed, and lower grasping force to reduce the risk of impact and crushing for fragile or surface-slippery objects. The stability-oriented strategy adopts higher stiffness, stronger interface gain, and faster gripper motion to improve positioning stability and operational efficiency for rigid objects. The balanced strategy is used for objects with intermediate grasping requirements.

The parameter ranges are jointly constrained by the Franka control interface, Omega.7 feedback-interface comfort, Franka Hand execution capability, and pre-experiments. Pre-experiments were performed by two researchers before the formal experiment, covering grasping operations for all three object categories, to exclude parameter combinations that were obviously unsafe, inefficient, or subjectively unacceptable to the operator. **The parameter table was finalized before the formal 135 trials and was not modified after observing the formal experimental results.** Mode B uses the same parameter table, but the operator manually selects the strategy. Therefore, Mode B is defined in this paper as a **manual-selection workflow baseline**, not a pure automatic-vs-manual controller performance comparison. Manual selection time is included in the total completion time for Mode B; thus, Mode B evaluates the actual workflow including human judgment and switching overhead, rather than serving as a pure controller execution-time baseline.

### 2.8 Algorithm Flow

**Algorithm 1: Vision-semantic multi-channel parameter scheduling for the integrated mechatronic system**

1. Initialize the system, load the balanced-strategy default parameters \(\Theta(\text{balanced})\), start the 200 Hz main control loop and the vision sub-process.
2. The vision sub-process asynchronously reads RGB-D images and performs YOLO11n object detection (does not block the main loop).
3. The main control thread non-blockingly reads the detection result queue; if the detected class belongs to the predefined object set and confidence ≥ 0.25, map the object class to the operation-oriented strategy \(c\).
4. The first valid detection triggers a strategy-lock event: invoke parameter set \(\Theta(c)=\{K_t,K_r,\zeta,K_f,d,v_g,F_g\}\) and atomically update the control-loop shared variables.
5. After locking, parameters remain unchanged for the entire task episode, preventing frequent switching due to vision jitter.
6. Send \(K_t,K_r,\zeta\) to the slave impedance controller, use \(K_f,d\) as master-side basic haptic-interface parameters, and use \(v_g,F_g\) for gripper control.
7. If detection fails or the class is unmappable, retain the balanced-strategy default parameters.
8. After task completion, reset the system, unlock the strategy, and prepare for the next trial.

### 2.9 Safety Fallback and Engineering Constraints

When vision is not locked or the detection result is unmappable, the system uses the default balanced-strategy parameters. Intra-task strategy locking prevents frequent parameter jumps due to vision jitter. The arm's built-in collision detection, program-exit zero-force command, unified initial pose, and manual emergency stop jointly constitute the basic safety measures. This paper focuses on pre-contact parameter initialization and does not discuss online post-contact optimal tuning.

---

## 3 Experimental Design

### 3.1 Research Questions and Hypotheses

This paper addresses the following research questions:

- **RQ1:** Does vision-semantic multi-parameter feedforward outperform fixed parameters, manual selection, and vision-only observation?
- **RQ2:** Does full multi-channel mechatronic parameter scheduling outperform vision-semantic impedance-only scheduling?
- **RQ3:** Does the asynchronous vision-perception and control-thread integration meet the real-time and basic reliability requirements of the task-start phase?
- **RQ4:** Does the benefit of the method show consistent direction across different operators and across different tested objects?

The corresponding hypotheses are: compared with baseline modes, the vision multi-parameter mode can reduce completion time and master trajectory length, increase success rate (as a descriptive metric), and lower subjective workload; compared with the vision impedance-only mode, the full multi-channel mode can reduce pauses or operation corrections, thereby demonstrating the overall additional benefit of the full pre-contact mechatronic parameter strategy relative to impedance-only adjustment.

### 3.2 Operators and Experimental Objects

Three operators (P01–P03, 23–24 years old, male, right-handed) participated in the main experiment. All three operators had basic teleoperation training experience and completed 10–15 minutes of warm-up trials before each formal session. All operators provided written informed consent. This study does not involve medical intervention and does not collect personally identifiable information.

The experiment covers six objects, forming a **mechatronic benchmark task set** designed to generate distinct requirements on compliance, haptic-interface sensitivity, and gripper execution conditions. The six objects are assigned to fragility-oriented, balanced, and stability-oriented strategies. This classification is used for parameter scheduling in the present experimental task and does not claim to represent a universal physical classification of object material properties.

| Object | Strategy | Mass (g) | Surface | Size (mm) | Primary task risk |
|:---:|:---:|---:|:---|:---|:---|
| Apple | Fragility-oriented | ~200 | Smooth | Ø70–80 | Impact/slip risk; requires gentle contact |
| Banana | Fragility-oriented | ~120 | Smooth | 20×180 | Crush deformation and slip risk |
| Paper cup | Balanced | ~5 | Paper | Ø75×90 | Easily deformable; requires stable grip |
| Bottle | Balanced | ~30 | Smooth plastic | Ø65×200 | Slippery; requires efficiency–stability balance |
| Mouse | Stability-oriented | ~100 | Smooth plastic | 65×120×35 | Rigid, irregular surface; transport slip risk |
| Scissors | Stability-oriented | ~150 | Metal+plastic | 50×170×15 | Rigid, elongated; high pose-precision requirement |

### 3.3 Experimental Modes and Trial Structure

The experiment includes five modes:

| Mode | Setting | Purpose |
|:---:|:---|:---|
| A | Fixed parameters, no visual scheduling | Fixed-control baseline |
| B | Operator manually selects full parameter strategy | Manual-selection workflow baseline |
| C | Vision-semantic automatic scheduling of full parameter set | Our method (full mechatronic scheduling) |
| D | Visual information displayed, fixed parameters maintained | Isolate effect of visual cue alone |
| E | Vision-semantic scheduling of \(K_t, K_r, \zeta\) only | Impedance-only ablation |

Mode A tests the compromise limitation of fixed parameters on heterogeneous objects. Mode B tests whether the manual-selection workflow introduces additional judgment and switching burden. Mode D distinguishes the role of visual cues from control-parameter changes. Mode E tests whether impedance-only adjustment suffices to reproduce the complete multi-channel mechatronic parameter strategy. The C–E comparison is the core ablation in this paper, because both modes share vision semantics and impedance adjustment, with the difference being that Mode C additionally sets master-side haptic-interface parameters and gripper execution parameters. This paper does not separate the independent contributions of haptic-interface parameters and gripper parameters within this comparison.

The trial structure uses 27 matched blocks as the fundamental unit. Each matched block consists of all five modes (A–E) under the same operator, same object/strategy, and same repetition index, yielding a total of \(27\times5=135\) trials. The distribution of the six objects across the 27 matched blocks is:

| Strategy | Specific object | Block count | Trials (×5 modes) |
|---|---|---|---:|---:|
| Fragility-oriented | Apple | 4 | 20 |
| Fragility-oriented | Banana | 5 | 25 |
| Balanced | Paper cup | 5 | 25 |
| Balanced | Bottle | 4 | 20 |
| Stability-oriented | Mouse | 5 | 25 |
| Stability-oriented | Scissors | 4 | 20 |
| Total | Six objects | 27 | 135 |

Mode order was partially balanced during the experiment to reduce learning or fatigue bias from a single fixed sequence. Since strict full randomization was not performed and all objects, operators, and order factors were not completely decoupled, this paper does not claim that order effects were fully eliminated; rather, these are conservatively discussed in the limitations section. The complete trial-by-trial execution sequence is provided as supplementary material.

### 3.4 Task and Procedure

Each trial consists of six phases: reset, approach, grasp, transport, release, and task end. Success is defined as completing grasp–transfer–placement within the time limit without dropping, observable slip, or visible damage to the object. Master trajectory, gripper input, control parameters, and task duration are recorded for each trial. In Mode B, the operator selects the strategy via keypress, and the manual selection time is included in the total completion time; therefore, Mode B represents a workflow baseline including human judgment and switching overhead.

**Fig. 3.** Experimental task flow and vision-semantic parameter scheduling framework, including the six-phase timeline and mechatronic parameter configuration points.

### 3.5 Evaluation Metrics

The primary endpoint is completion time. Secondary objective endpoints include success rate, master trajectory length, pause count, direction-reversal count, and motion smoothness. Subjective workload is assessed using unweighted Raw NASA-TLX, the arithmetic mean of six dimensions. NASA-TLX scores are collected at the "operator × object strategy × mode" level. The vision module reports class-level recognition accuracy, strategy-trigger accuracy, confidence, and per-frame processing time.

Process-behavior metrics were defined and fixed before formal statistical analysis. Pause is defined as master velocity below 0.005 m/s for a duration of at least 0.30 s, detected in real time by differencing velocity from the raw master trajectory CSV (sampled at approximately 200 Hz).

### 3.6 Statistical Analysis

Considering that trials are nested within a small number of operators, statistical results emphasize paired trends, operator-level directionality, and effect sizes, and do not treat the 135 trials as 135 independent participant samples. Five-mode completion times are compared globally with the Friedman test; after global significance, paired Wilcoxon signed-rank tests are performed with Holm-Bonferroni correction for multiple comparisons. The C–E comparison, as the core ablation, reports paired mean difference, Bootstrap 95% confidence interval (10,000 re-samples, block-level bootstrap), relative change, effect size, and operator-level aggregated trends. Raw NASA-TLX is analyzed with the same non-parametric framework, but because only three independent operators are available, subjective workload results are interpreted as preliminary human-in-the-loop evidence. Success rate is reported descriptively. Results report median [IQR] alongside mean ± SD to align with the non-parametric analysis framework.

---

## 4 Experimental Results

### 4.1 Visual Recognition and Strategy-Trigger Validation

Under controlled viewpoint, background, and illumination, 30 images per object class, 180 images total. Class recognition and strategy triggering achieved 180/180 (100%), with mean confidence 0.853 and per-frame wall-clock processing time 50.08 ms. This result indicates that visual triggering was not a major source of error under the present experimental conditions, but does not generalize to occlusion, strong illumination variation, cluttered backgrounds, unknown objects, or untested classes.

| Object | Images | Class accuracy | Strategy trigger accuracy | Mean confidence | Time (ms) |
|---|---|---|---|---|---:|---:|---:|---:|
| Apple | 30 | 100% | 100% | 0.771 | 56.66 |
| Banana | 30 | 100% | 100% | 0.948 | 50.45 |
| Bottle | 30 | 100% | 100% | 0.726 | 49.71 |
| Cup | 30 | 100% | 100% | 0.820 | 47.61 |
| Mouse | 30 | 100% | 100% | 0.914 | 46.79 |
| Scissors | 30 | 100% | 100% | 0.938 | 49.27 |

**Fig. 4.** Visual recognition validation results, including confusion matrix, confidence distribution, and per-frame processing time distribution.

### 4.2 Five-Mode Experimental Results

**Table 4.** Five-mode experimental results: completion time, master trajectory length, success rate, and Raw NASA-TLX. Values reported as median [IQR] with mean±SD in parentheses.

| Mode | Completion time (s) | Trajectory (m) | Success rate | Raw NASA-TLX |
|:---:|:---:|:---:|:---:|:---:|
| A Fixed | 21.18 [20.62, 22.08] (21.42±1.58) | 0.741 [0.692, 0.811] (0.763±0.098) | 22/27 (81.5%) | 62.00 [60.33, 65.67] (62.59±3.95) |
| B Manual | 20.89 [20.12, 21.83] (21.01±1.61) | 0.793 [0.735, 0.875] (0.799±0.115) | 21/27 (77.8%) | 57.00 [54.33, 59.83] (57.15±3.68) |
| **C Vision multi-param** | **19.57 [18.41, 20.05] (19.28±1.30)** | **0.697 [0.660, 0.769] (0.715±0.092)** | **26/27 (96.3%)** | **48.67 [47.67, 51.83] (49.67±3.63)** |
| D Vision observe | 20.79 [20.32, 21.16] (20.91±1.10) | 0.716 [0.684, 0.779] (0.734±0.085) | 24/27 (88.9%) | 59.00 [57.83, 62.83] (60.22±3.85) |
| E Vision impedance-only | 20.73 [19.95, 22.25] (21.07±1.56) | 0.732 [0.678, 0.799] (0.739±0.084) | 24/27 (88.9%) | 53.67 [51.83, 57.83] (54.54±4.09) |

Descriptive results show that Mode C achieves the shortest median completion time, shortest master trajectory, highest success rate, and lowest Raw NASA-TLX among all five modes. Compared with Modes A, B, D, and E, Mode C's mean completion time is reduced by approximately 10.0%, 8.2%, 7.8%, and 8.5%, respectively.

The Friedman test on five-mode completion times shows significant global differences (χ²(4)=30.904, p<0.001). Paired Wilcoxon tests with Holm correction indicate that Mode C completion time is significantly lower than Modes A, B, D, and E (p < 0.01, effect size r > 0.7). Because trials are nested within three operators, these results are interpreted as paired evidence within the current mechatronic platform, object set, and participant pool, rather than as general-population statistical conclusions. Raw NASA-TLX also shows the lowest direction for Mode C, but subjective workload results are interpreted cautiously given the small sample and non-blinded conditions.

**Fig. 5.** Five-mode completion time comparison: boxplot overlaid with individual matched-block scatter points (each point represents one block), bar charts are avoided. Left panel: completion time; right panels: master trajectory length and Raw NASA-TLX sub-panels.

### 4.3 Core Ablation: Full Multi-Parameter Strategy vs. Impedance-Only

**Table 5.** Core C–E ablation: median [IQR], paired mean difference, Bootstrap 95% CI (10,000 re-samples, block-level bootstrap), and operator-level direction.

| Metric | C (median [IQR]) | E (median [IQR]) | Δ (C−E) | Bootstrap 95% CI | Direction |
|:---|---:|---:|---:|---:|:---|
| Completion time (s) | 19.57 [18.41, 20.05] | 20.73 [19.95, 22.25] | −1.79 | [−2.51, −1.10] | 3/3 operators ↓ |
| Trajectory (m) | 0.697 [0.660, 0.769] | 0.732 [0.678, 0.799] | −0.024 | [−0.059, 0.014] | mixed |
| Raw NASA-TLX | 48.67 [47.67, 51.83] | 53.67 [51.83, 57.83] | −4.87 | [−5.35, −4.39] | 3/3 operators ↓ |

The C–E comparison is the most critical ablation in this paper. Both modes use vision semantics and impedance adjustment; the difference is that Mode C additionally sets master-side haptic-interface gain, force-interface dead zone, gripper closing speed, and grasping force. This design tests an engineering question: whether adjusting slave-side compliance alone is sufficient to cover heterogeneous-object grasping requirements, or whether the operator's perception channels and gripper execution channels need to be simultaneously initialized. It should be emphasized that this comparison can only demonstrate that the full pre-contact multi-parameter strategy has an overall mechatronic-system-level advantage over impedance-only adjustment; it cannot independently prove the causal contributions of haptic-interface parameters or gripper parameters.

In the 27 matched blocks, Mode C median completion time is 19.57 s and Mode E is 20.73 s, with a paired mean difference of −1.79 s (Bootstrap 95% CI [−2.51, −1.10] s), representing a relative reduction of approximately 8.5%. The CI excludes zero, supporting a real improvement in completion time for Mode C. Operator-level aggregated results show that all three operators exhibit a C-faster-than-E direction: P01 18.94 s vs. 20.60 s (−8.1%), P02 19.09 s vs. 21.66 s (−11.8%), P03 19.80 s vs. 20.95 s (−5.5%). All six objects also show C-faster-than-E direction (reduction range 3.3%–13.2%).

The master trajectory length difference is small (0.697 m vs. 0.732 m), with Bootstrap 95% CI [−0.059, 0.014] m crossing zero, indicating that the trajectory-length difference is not statistically robust. Combined with the pause analysis, this paper interprets the C–E difference as preliminary evidence for operational efficiency improvement: multi-channel mechatronic parameter coordination may have reduced pauses and corrections during the grasping, transport, or release phases. This mechanistic interpretation is consistent with the present experimental results, but its causality still requires further verification through finer-grained phase annotation and additional ablation experiments.

**Fig. 6.** Core C–E ablation results. The figure shows 27 matched-block C–E completion-time paired scatter points (below the diagonal indicates C faster), three-operator facet plots, and six-object stratified boxplots. The figure caption states that Bootstrap CIs are interpreted only as paired evidence.

### 4.4 Process-Behavior Metric: C–E Pause Analysis

Pause counts were computed from the raw master trajectory CSVs (sampled at approximately 200 Hz). A pause is defined as master velocity below 0.005 m/s for a duration of at least 0.30 s. Mode C per-trial median pause count is 3 [2, 3.5] IQR (mean: 2.74±1.23), and Mode E is 3 [2, 5] IQR (mean: 3.41±1.67). By strategy, fragility-oriented, balanced, and stability-oriented categories all show a direction of fewer pauses in Mode C. This result is consistent with the observation that Mode C has shorter completion time while trajectory-length difference is small, supporting the interpretation that the additional benefit of multi-channel coordination mainly comes from operational efficiency improvement (mechatronic parameter coordination reduced pauses and corrections) rather than path shortening. Future work will introduce phase-level time annotation (e.g., approach, grasp, transport, release) for finer-grained attribution analysis of mechatronic system behavior.

### 4.5 Failure Case Analysis

Nine failures occurred across the 135 trials, including drops, observable slip, or visible damage. The failure distribution by mode is:

| Mode | Failures / Total | Typical observation |
|:---:|:---:|:---|
| A Fixed | 5/27 | Cup crush deformation, scissors positioning instability |
| B Manual | 6/27 | Manual strategy mis-selection or high switch cost |
| **C Vision multi-param** | **1/27** | Mouse surface slippery, slip during transport |
| D Vision observe | 3/27 | Inadequate grip force on medium objects |
| E Vision impedance-only | 3/27 | Unstable grasp on medium objects |

Mode C recorded the lowest failure count (1/27) in the present experiment. This observation is consistent with the interpretation that the full multi-channel parameter strategy may improve grasping stability, but due to the absence of phase-level logs, contact-force measurements, and slip measurements, this paper does not interpret the failure count difference as a directly proven causal mechanism.

### 4.6 Cross-Operator and Six-Object Consistency

All three operators exhibit a C-faster-than-E direction in completion time. At the per-object level, Mode C also shows the shortest mean completion time among all five modes for all six tested objects. Per-object results are:

| Object | A Fixed (s) | B Manual (s) | **C Vision multi-param (s)** | D Observe (s) | E Impedance-only (s) |
|:---:|---:|---:|---:|---:|---:|
| Apple | 20.46 | 21.40 | **19.25** | 20.81 | 20.94 |
| Banana | 20.07 | 20.85 | **19.49** | 21.06 | 20.64 |
| Paper cup | 22.36 | 20.27 | **18.69** | 20.38 | 21.17 |
| Bottle | 22.11 | 22.14 | **19.63** | 20.78 | 20.30 |
| Mouse | 21.74 | 20.93 | **19.75** | 20.74 | 21.64 |
| Scissors | 21.79 | 20.70 | **18.84** | 21.83 | 21.70 |

The C-over-E time reduction ranges from 3.3% (bottle) through 5.5% (banana), 8.1% (apple), 8.7% (mouse), 11.7% (paper cup) to 13.2% (scissors). This indicates directional consistency across the six tested objects, but does not extrapolate to untested objects or complex occlusion scenarios.

---

## 5 Discussion

### 5.1 Why Pre-Contact Vision-Semantic Feedforward Improves Mechatronic System Performance

The fixed-parameter mode must cover all three strategy categories with a single compromise parameter set, making it difficult to simultaneously satisfy the compliance needs of fragile objects and the stable positioning needs of rigid objects. Although the manual-selection mode can invoke different strategies, it transfers the object-judgment and strategy-switching responsibility to the operator, increasing workflow burden. The vision-observe-only mode improves scene information but does not change the system dynamics or gripper behavior. The vision multi-parameter mode uses object semantics to complete mechatronic parameter strategy initialization before contact, so the operator does not need to continuously compensate for inappropriate hand-feel, gripper speed, or grasping force during the task. This mechanism is consistent with Mode C's shorter completion time, lower pause count, and lower subjective workload trend.

### 5.2 Significance of the Full Pre-Contact Mechatronic Parameter Strategy Relative to Impedance-Only Adjustment

Both Mode C and Mode E adjust translational stiffness, rotational stiffness, and damping ratio based on vision semantics, so they share the compliance-adaptation mechanism. Mode C additionally presets master-side haptic-interface gain, force-interface dead zone, gripper closing speed, and grasping force. In the present data, Mode C's mean completion time is reduced by approximately 8.5% relative to Mode E (Bootstrap 95% CI [−2.51, −1.10] s), whereas the master trajectory length is reduced by approximately 3.2% (95% CI [−0.059, 0.014] m, crossing zero). This indicates that the additional benefit is more likely from operational efficiency during the grasping, transport, or release phases, rather than from substantially changing the geometric path.

The engineering significance of this result for application-oriented mechatronic teleoperation systems is that what the operator faces is not only slave-side end-effector compliance, but a complete mechatronic interaction experience comprising master-side haptic-interface gain, force-interface dead zone, gripper execution speed, and grasping force. Adjusting impedance alone may not cover all the mechatronic system requirements in heterogeneous-object grasping. For example, fragile or slippery objects require not only lower stiffness but also slower gripper closure and lower grasping force to reduce crushing and slip risk; rigid or geometrically irregular objects may require clearer interface feedback and more stable gripping execution to reduce operator corrections during grasp establishment and transport phases. The engineering role of the force-interface dead zone is mainly to attenuate small perturbations and haptic-interface noise, providing the operator with more stable contact cues rather than serving as a closed-loop contact-force control law. Multi-channel mechatronic parameter coordination can translate object semantics into a more complete operational hand-feel and execution strategy.

### 5.3 Differences from Related Work

Existing task-decomposition and shared-control studies typically improve completion efficiency and reduce operator workload by switching control modes, constraining input spaces, or providing guidance [10–13]. Visual-impedance studies unify control objectives in the visual-and-force feature space [9]. The difference of this paper is that it does not perform continuous visual servoing, does not rely on online trajectory planning, and does not claim closed-loop external-force adaptation or optimal control after contact; instead, it uses object semantics as a pre-contact task prior, invoking interpretable multi-channel mechatronic parameter strategies with low computational overhead. In other words, this paper provides a mechatronic-system-level bridging paradigm: transforming high-level visual semantics into low-level mechatronic teleoperation interface parameters so that the operator obtains slave-side compliance, haptic-interface settings, and gripper execution behavior more suitable for the current object before contact. This positioning is suitable for engineering teleoperation scenarios where object categories are identifiable, the environment is relatively structured, but the operator is still required to perform fine grasping and placement.

### 5.4 Design Implications for Mechatronic Teleoperation Systems

This section distills three design insights from a mechatronic system perspective:

**1. Perception should not only inform the operator; it should initialize low-level interface parameters.** This study demonstrates that upgrading visual semantic information from "operator cue" to "mechatronic parameter feedforward" can improve system-level performance without increasing the operator's cognitive burden. The visual perception module should not merely be information on a display; it should be a link in the mechatronic parameter initialization chain.

**2. Compliance adaptation alone is incomplete for grasping.** Adjusting only slave-side impedance (Mode E in the C–E ablation) provides compliance adaptation but cannot cover gripper execution speed and grasping force, nor can it adjust the haptic-interface intensity and dead zone perceived by the operator. A complete mechatronic teleoperation grasping system needs to co-schedule impedance, haptic-interface, and gripper execution as a coupled parameter set.

**3. Asynchronous perception-control separation improves deployability.** The asynchronous architecture in this paper separates the approximately 20 Hz vision sub-process from the nominal 200 Hz control loop, preventing vision inference from directly blocking master–slave control. Although cycle-level jitter was not logged during the formal trials, the non-blocking design (independent `mp.Process` for YOLO, `mp.Queue` with bounded capacity, and atomic shared-variable updates) prevents the ~50 ms vision inference from occupying the main-thread time slice. This perception-control-decoupled mechatronic design pattern lowers the real-time requirements on the vision module, making the system easier to deploy onto existing teleoperation platforms without substantial modification to the control loop. Formal cycle-level profiling remains future work.

### 5.5 Why the Benefit Magnitude Differs Across Objects

All six objects show a C-faster-than-E direction, but the reduction magnitude is not uniform. The smaller reductions for bottle and banana may be because their grasping actions are relatively familiar, and operators could compensate for default gripper parameters through experience even in Mode E. The larger reductions for paper cup and scissors may be related to higher grasping risk and pose-stability requirements: the paper cup requires avoidance of deformation and unstable gripping, and the scissors require more explicit positioning and stable transport. This mechanistic interpretation can be further verified through finer-grained data including phase-level durations, re-grasp behavior, and gripper state logs.

### 5.6 Limitations

1. Only three independent operators participated; 135 repeated task trials cannot substitute for a larger participant sample. Subjective workload and cross-operator conclusions should be considered preliminary human-in-the-loop evidence on a real mechatronic platform.
2. Trials are nested within operators, objects, and repetition blocks; statistical results are not interpreted as strong general-population-level conclusions. Bootstrap CIs serve only as auxiliary quantification of paired evidence.
3. Mode order was partially balanced but not strictly fully randomized; learning effects and fatigue effects cannot be fully excluded.
4. Manual-selection Mode B includes selection time; it is thus a manual-selection workflow baseline rather than a pure controller execution-time baseline.
5. The human-in-the-loop experiment covers six specific objects with limited trials per object category; the results support consistent direction across the tested objects but do not extrapolate to unknown objects, complex occlusions, or open-world scenarios.
6. Vision validation was performed under controlled viewpoint, background, and illumination; the 100% accuracy represents only controlled experimental conditions and does not extrapolate to occlusion, cluttered backgrounds, or untested classes.
7. The current data do not provide independently sensor-calibrated contact force, slip quantity, or object damage measurements; therefore, this paper does not directly claim to have demonstrated "protection of fragile objects."
8. Parameters were determined by engineering experience, safety ranges, and pre-experiments. This paper demonstrates the effectiveness of discrete semantic strategies in the current mechatronic task, not the global optimality of the parameters.

---

## 6 Conclusion

This paper proposes a vision-semantic multi-channel parameter scheduling method for heterogeneous-object haptic teleoperation grasping from a mechatronic system integration perspective. The method interprets the target object category as one of three operation-oriented strategies—fragility-oriented, balanced, and stability-oriented—and coordinates slave-side impedance, master-side haptic-interface parameters, and gripper execution parameters before contact, forming an asynchronous perception-control-decoupled mechatronic teleoperation system. Real-platform five-mode experiments show that, within the current three-operator, six-object, 135-trial mechatronic benchmark task set, the vision multi-parameter mode achieves the shortest median completion time (19.57 s [18.41, 20.05] IQR), the highest success rate (26/27, 96.3%), and the lowest Raw NASA-TLX (median 48.67 [47.67, 51.83] IQR). Compared with the vision impedance-only mode, the full multi-channel mode reduces mean completion time by −1.79 s (Bootstrap 95% CI [−2.51, −1.10] s), with all three operators and all six objects showing a consistent direction. Pause analysis and Bootstrap CIs further suggest that the additional benefit may mainly come from reduced operational pauses and corrections through mechatronic parameter coordination, rather than from a significantly shorter geometric path.

Overall, this paper provides an interpretable, low-cost, deployable mechatronic-system pre-contact parameter initialization method for heterogeneous-object haptic teleoperation without requiring complex online optimization. Its statistical generalizability and external validity still require further verification through more operators, strictly randomized order, object-instance-level recording, phase-level process metrics, and contact-quality metrics. Post-contact external force estimation, force-feedback closed-loop correction, and operator haptic perception validation belong to the scope of subsequent studies and are not independently demonstrated by the data in this paper.

---

## Declarations

- **Ethical approval:** This study was exempt from formal ethics review because it involved non-medical teleoperation tasks and did not collect personally identifiable information.
- **Informed consent:** All participants provided written informed consent before the experiment.
- **Funding:** Not applicable.
- **Conflict of interest:** The authors declare no conflict of interest.
- **Data availability:** De-identified trial data and analysis scripts are available from the corresponding author upon reasonable request.

---

## References

1. Lawrence, D.A. (1993), "Stability and transparency in bilateral teleoperation", *IEEE Transactions on Robotics and Automation*, Vol. 9 No. 5, pp. 624–637.
2. Niemeyer, G. and Slotine, J.J.E. (1991), "Stable adaptive teleoperation", *IEEE Journal of Oceanic Engineering*, Vol. 16 No. 1, pp. 152–162.
3. Sheridan, T.B. (1992), *Telerobotics, Automation, and Human Supervisory Control*, MIT Press, Cambridge, MA.
4. Passenberg, C., Peer, A. and Buss, M. (2010), "A survey of environment-, operator-, and task-adapted controllers for teleoperation systems", *Mechatronics*, Vol. 20 No. 7, pp. 787–801.
5. Hogan, N. (1985), "Impedance control: An approach to manipulation", *Journal of Dynamic Systems, Measurement, and Control*, Vol. 107 No. 1, pp. 1–24.
6. Kronander, K. and Billard, A. (2016), "Stability considerations for variable impedance control", *IEEE Transactions on Robotics*, Vol. 32 No. 5, pp. 1298–1305.
7. Abu-Dakka, F.J., Rozo, L. and Caldwell, D.G. (2018), "Force-based variable impedance learning for robotic manipulation", *Robotics and Autonomous Systems*, Vol. 109, pp. 156–167.
8. Duan, J., Gan, Y., Chen, M. and Dai, X. (2018), "Adaptive variable impedance control for dynamic contact force tracking in uncertain environment", *Robotics and Autonomous Systems*, Vol. 102, pp. 54–65.
9. Abu-Dakka, F.J. and Saveriano, M. (2020), "Variable impedance control and learning — A review", *Frontiers in Robotics and AI*, Vol. 7, 590681.
10. Losey, D.P., McDonald, C.G., Battaglia, E. and O'Malley, M.K. (2018), "A review of intent detection, arbitration, and communication aspects of shared control for physical human–robot interaction", *Applied Mechanics Reviews*, Vol. 70 No. 1, 010804.
11. Bowman, M., Zhang, J. and Zhang, X. (2024), "Intent-based task-oriented shared control for intuitive telemanipulation", *Journal of Intelligent & Robotic Systems*, Vol. 110, 167.
12. Oliva, A.A., Giordano, P.R. and Chaumette, F. (2021), "A general visual-impedance framework for effectively combining vision and force sensing in feature space", *IEEE Robotics and Automation Letters*, Vol. 6 No. 3, pp. 4441–4448.
13. Peternel, L., Tsagarakis, N. and Ajoudani, A. (2016), "Towards multi-modal intention interfaces for human–robot co-manipulation", in *Proceedings of the IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)*, pp. 2663–2669.
14. [To be supplied: mechatronic system design reference — e.g., mechatronic teleoperation system architecture or human-machine interface design]
15. [To be supplied: real-time robotic control architecture reference — e.g., from IEEE/ASME Trans. Mechatronics or Robotics and Autonomous Systems]
16. [To be supplied: haptic teleoperation implementation reference — e.g., from IEEE Trans. Haptics or ICRA/IROS]
17. [To be supplied: perception-control integration reference — e.g., visual servoing with real-time constraints]
18. [To be supplied: gripper control / grasping execution reference — e.g., from IEEE RA-L or ICRA]
19. Albu-Schaffer, A., Haddadin, S., Ott, C., Stemmer, A., Wimbock, T. and Hirzinger, G. (2007), "The DLR lightweight robot: design and control concepts for robots in human environments", *Industrial Robot*, Vol. 34 No. 5, pp. 376–385.
20. Haddadin, S., Parusel, S., Johannsmeier, L. et al. (2022), "The Franka Emika robot: A reference platform for robotics research and education", *IEEE Robotics & Automation Magazine*, Vol. 29 No. 2, pp. 46–64.
21. Hart, S.G. and Staveland, L.E. (1988), "Development of NASA-TLX (Task Load Index): Results of empirical and theoretical research", in Hancock, P.A. and Meshkati, N. (Eds.), *Human Mental Workload*, North-Holland, Amsterdam, pp. 139–183.
22. Boessenkool, H., Abbink, D.A., Heemskerk, C.J.M., van der Helm, F.C.T. and Wildenbeest, J.G.W. (2011), "Haptic shared control improves teleoperated task performance toward performance in direct control", in *Proceedings of the IEEE World Haptics Conference*, pp. 433–438.
23. Abbott, J.J., Marayong, P. and Okamura, A.M. (2007), "Haptic virtual fixtures for robot-assisted manipulation", in Thrun, S., Brooks, R. and Durrant-Whyte, H. (Eds.), *Robotics Research*, Springer Tracts in Advanced Robotics, Vol. 28, Springer, Berlin, pp. 49–64.