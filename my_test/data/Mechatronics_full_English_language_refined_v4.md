# Object-Conditioned Cross-Channel Mechatronic Parameter Reconfiguration for Haptic Teleoperation of Heterogeneous Objects

## Abstract

Fixed teleoperation settings are poorly suited to objects with different fragility, geometry, and grasping requirements. This paper presents an object-conditioned framework that configures slave-side Cartesian impedance, operator-facing haptic settings, and gripper execution through a common operation strategy. A single-slot frame queue, a two-slot result queue, and non-blocking polling decouple 15-fps visual perception from the nominal 200-Hz supervisory loop. After task initiation, the first detection above the confidence threshold with a valid strategy mapping triggers a one-shot parameter update, and the selected strategy is then locked for the trial. Its timing relative to first contact was not recorded. Three operators completed 135 grasp-and-transfer trials involving six objects and five control modes. The complete coordinated mode achieved the shortest median completion time (19.57 s, IQR [18.41, 20.05]), the highest observed success rate (26/27, 96.3%), and the lowest Raw NASA-TLX score (48.67, IQR [47.67, 51.83]). Compared with impedance-only scheduling, mean completion time decreased by 1.79 s (matched-block bootstrap 95% CI [1.10, 2.51] s), or 8.5%. The direction favored the complete configuration for all three operators and all six objects. Within this three-operator experiment, coordinating the haptic interface and gripper with slave-side impedance improved task-level performance relative to impedance-only scheduling, although the contributions of the added channels were not separated.

**Keywords:** mechatronic systems; haptic teleoperation; object-conditioned reconfiguration; cross-channel coordination; impedance control; human-in-the-loop experiment

---

## 1 Introduction

Teleoperation uses human judgment to perform remote manipulation tasks that remain difficult for autonomous robots, particularly in hazardous environments, flexible manufacturing, and unstructured settings. Haptic feedback further conveys remote contact information to the operator, supporting the assessment of contact, grasp stability, and slip. Previous studies have examined the stability and transparency of bilateral teleoperation and the adaptation of controllers to the environment, operator, and task [1,2]. In practical systems, however, these control functions must operate together with visual perception, mechanical execution, and the human–machine interface.

A single set of control parameters is unlikely to suit fragile objects, lightweight containers, and rigid tools equally well. Lower stiffness and gripping force can promote gentle contact but may compromise positioning and transfer stability. Higher stiffness and gripping force may accelerate manipulation but can increase the risk of impact or deformation. The benchmark objects—an apple, a banana, a paper cup, a bottle, a computer mouse, and a pair of scissors—were selected to represent heterogeneous task demands in compliance, haptic interaction, and gripper execution. This controlled set enabled evaluation of object-conditioned coordinated parameter reconfiguration across heterogeneous grasping tasks.

Impedance control regulates the relationship among displacement, velocity, and interaction force, allowing a robot to remain compliant during contact [3]. Fixed impedance is straightforward to implement but necessarily represents a compromise across objects. Variable-impedance methods instead adapt stiffness and damping according to task state, contact information, or learned policies, while also requiring consideration of the stability implications of time-varying parameters [4,5]. In teleoperation, operators may directly adjust slave-side impedance [6], whereas tele-impedance approaches map human motion and impedance information to the remote robot [7–9]. Such continuous adaptation commonly relies on human measurements, demonstration data, or post-contact state feedback.

Visual information has also been used to select or adapt robot impedance. A vision-and-voice tele-impedance method selected slave-side impedance according to object properties while retaining an operator confirmation or correction step [10], and visual-impedance control has combined visual and force information in a visual-feature space [11]. At the workflow level, intention inference and task-oriented shared control have been used to reduce manual decision-making [12]. More recent visual approaches have derived stiffness from object geometry, material, and environmental relations [13] or generated task-relevant stiffness matrices from visual, gaze, and language inputs [14]. These studies primarily convert task information into slave-side stiffness, impedance, or control-authority decisions.

Automatic switching and passive arbitration further change who controls which part of the task and when that control changes [15,16]. Haptic interfaces have been evaluated for telemanipulation performance [17], while related work has addressed compliant assembly [18], human and environmental stiffness estimation [19], rotational impedance [20], scaling transitions [21], vision-based tactile feedback [22], multi-stiffness interfaces [23], delay-aware shared autonomy [24], and haptic support under restricted vision [25]. These studies adapt individual control or interaction elements. Comparatively little attention has been given to using object semantics as a common task condition for jointly configuring the slave-side mechanical response, the operator-facing haptic interface, and gripper execution. The central question of this study is therefore not whether vision can tune impedance, but whether a strategy-level semantic decision can configure these three mechatronic subsystems as one parameter bundle and provide task-level benefits beyond visual-semantic display, manual selection, and impedance-only scheduling.

We propose an object-semantic-driven framework for cross-channel mechatronic parameter reconfiguration in haptic teleoperation of heterogeneous objects. A three-level mapping from object semantics to an operation-oriented strategy and then to a joint parameter vector converts task information into coordinated settings for slave-side impedance, the master-side haptic interface, and gripper execution. After task initiation, the first detection above the confidence threshold with a valid strategy mapping triggers a single target-parameter update. The selected strategy is then locked for the remainder of the trial to prevent repeated switching caused by subsequent detection fluctuations. Five experimental modes—fixed parameters, operator selection, full cross-channel reconfiguration, a visual-semantic cue with fixed parameters, and impedance-only scheduling—were designed to examine the roles of the individual workflow components. In particular, C–D tests automatic configuration beyond the displayed semantic cue, whereas C–E tests the complete parameter bundle against impedance-only scheduling. The main contributions are as follows:

1. **Strategy-level coordination of mechatronic parameters.** Object-dependent configuration is extended from slave-side impedance alone to three coordinated subsystems: the slave-side mechanical response, the operator-facing haptic interface, and gripper execution. The coordination is imposed by a common operation strategy that assigns a consistent parameter bundle; it is not derived from a dynamic coupling model between channels.
2. **Three-level semantic mapping within a constrained parameter space.** Object classes are abstracted into fragility-priority, balanced, and stability-priority operational strategies and mapped to a seven-dimensional joint parameter vector constrained by hardware capability, task risk, and the operating envelope established in preliminary testing.
3. **Asynchronous, event-triggered one-shot reconfiguration.** Image acquisition at 15 fps and independent YOLO11n inference are connected to a nominal 200-Hz supervisory update through bounded queues. Non-blocking polling prevents the supervisory thread from waiting for perception, strategy locking avoids repeated intra-trial switching caused by detection fluctuations, and an approximately 300-ms transition smooths changes in stiffness and the controller damping-scaling parameter.
4. **Human-in-the-loop system-level evaluation across five modes.** Five modes were implemented on an Omega.7–Panda platform to distinguish the effects of the visual-semantic display, manual strategy selection, impedance-only adaptation, and full cross-channel reconfiguration. The system was evaluated with three operators, six objects, and 135 trials.

The online stage uses discrete, event-triggered parameter reconfiguration instead of post-contact continuous optimization or persistent visual servoing. Beyond parameter lookup, the main contribution is a strategy-level relationship linking object semantics with slave-side impedance, the master-side haptic interface, and gripper execution, together with an asynchronous implementation and strategy locking suitable for a human-in-the-loop teleoperation system. The experiments further examine whether the complete coordinated configuration provides task-level benefits beyond impedance-only scheduling. In mechatronic terms, the work formulates perception, control, haptics, and grasp execution as an integrated reconfiguration problem.

---


## 2 Methods and System Implementation

### 2.1 Mechatronic System Architecture and Asynchronous Execution

The experimental platform comprised an Omega.7 force-feedback master device, a Franka Panda seven-degree-of-freedom robot, a Franka Hand gripper [26], an Intel RealSense D435i camera, and a control computer (Fig. 1). The D435i delivered color images at 424 × 240 pixels and 15 fps; the depth stream was not used. The control computer executed visual detection, the nominal 200-Hz supervisory teleoperation update, parameter setting, haptic rendering, gripper control, and data logging.

![Fig. 1](../drawing/图一.png)

**Fig. 1.** Experimental platform comprising the Omega.7 master device, Franka Panda robot and Franka Hand gripper, D435i camera, and control computer. The camera supplied 424 × 240 color images at 15 fps.

Figure 2(b) expands the asynchronous software path into an illustrative timing diagram.

![Fig. 2(b)](./Figure_2b_timing_double_column.png)

**Fig. 2(b).** Illustrative timing of the asynchronous perception–control implementation. Color frames are acquired at 15 fps and passed through a single-slot frame queue to an independent YOLO11n process; a controlled visual test yielded a mean wall-clock processing time of 48.19 ms per image. Class-confidence results are returned through a two-slot result queue. The nominal 5-ms supervisory update polls this queue without blocking. The first result that reaches the confidence threshold is converted through the class-to-strategy mapping and creates a one-shot strategy event. Modes C and E update their enabled parameters, whereas mode D retains fixed parameters and presents the semantic result. Translational stiffness, rotational stiffness, and the controller damping-scaling parameter follow an approximately 300-ms smoothstep transition, while the enabled haptic-interface and gripper settings change at the event. Subsequent detections do not change the strategy within the same trial. A low-confidence result or absence of a detection leaves the initialized state unchanged; a detected class without an explicit mapping is assigned to the balanced default strategy. The timing is illustrative because synchronized strategy-event and contact timestamps were not retained in the formal trials.

RGB frames are acquired every 66.7 ms and written to a frame queue with a capacity of one, thereby preventing stale images from accumulating. YOLO11n runs in an independent process and returns class-confidence results through a queue with a capacity of two. The nominal 200-Hz supervisory loop polls this queue every 5 ms without waiting for inference. Camera acquisition, perception, and operator motion therefore proceed in parallel. The measured value of 48.19 ms is the mean wall-clock processing time per image, not the camera sampling period. Formal trial records retained task outcomes and active parameter states but not complete visual-event histories.

**Table 1.** Execution and communication characteristics of the multi-rate mechatronic system.

| Module | Frequency/latency | Input | Output | Blocks the supervisory loop? |
|:---|---:|:---|:---|:---:|
| Master input | 200 Hz | Omega.7 translational position and buttons | $\Delta\mathbf{p}_m$ | No |
| Slave control | 200 Hz | $\mathbf{p}_d,\mathbf{R}_d,\mathbf{K},\mathbf{D}$ | Panda desired pose/impedance command | No |
| Image acquisition | 15 fps (66.7 ms/frame) | D435i color stream | 424 × 240 image | No |
| YOLO11n inference | Mean 48.19 ms/image | Latest available image | Class and confidence | No (independent process) |
| Strategy scheduling | First threshold-qualified result read by the supervisory loop | Class and confidence | Target $\Theta(c)$ | No |
| Haptic rendering | 200 Hz | $\mathbf{F}_{\mathrm{ext}},K_f,d,\theta_{\Omega}$ | Omega.7 force vector | No |
| Gripper command | Button event | Gripper input, $v_g,F_g$ | Franka Hand command | No |

### 2.2 Master–Slave Mapping and Implementation of the Mechatronic Channels

Only translational motion of the Omega.7 was mapped to the Panda. The master-device position increment and desired slave position were updated as

\[
\Delta\mathbf{p}_m(k)=\mathbf{p}_m(k)-\mathbf{p}_m(k-1),
\]

\[
\mathbf{p}_d(k)=\mathbf{p}_d(k-1)+S\mathbf{C}\Delta\mathbf{p}_m(k),
\]

where the position-scaling factor was $S=3.0$ and $\mathbf{C}=\mathrm{diag}(-1,-1,1)$. The desired end-effector orientation $\mathbf{R}_d$ was fixed at its prescribed value throughout each trial; active rotational input from the operator was not mapped. Cartesian impedance control acted on the six-dimensional pose error,

\[
\mathbf{w}_c=\mathbf{K}(c)\mathbf{e}+\mathbf{D}(c)\dot{\mathbf{e}},
\]

\[
\mathbf{K}(c)=\mathrm{diag}(K_t,K_t,K_t,K_r,K_r,K_r),
\]

where $\mathbf{e}$ contains translational error relative to $\mathbf{p}_d$ and rotational error relative to the fixed $\mathbf{R}_d$. Thus, $K_r$ changes resistance to rotational disturbances and the ability to hold the prescribed orientation; it does not scale operator-commanded rotation.

The controller internally generated the damping matrix from the active diagonal stiffness matrix and a scalar API parameter denoted by $\zeta$. For the implementation used here,

\[
\mathbf{D}(c)=2\zeta(c)\sqrt{\mathbf{K}(c)},
\]

where the square root is applied element by element to the diagonal entries. Here, $\zeta$ denotes the dimensionless damping-scaling parameter used by the controller implementation; no Cartesian critical-damping interpretation is assigned because an effective Cartesian mass or inertia matrix was not identified or specified.

The Franka internal state estimator provided the slave-side external-force estimate $\mathbf{F}_{\mathrm{ext}}$ in newtons. The baseline master-side force command in direction $i$ was

\[
u_{h,i}^{\mathrm{base}}=
\operatorname{sgn}\!\left(K_fF_{\mathrm{ext},i}\right)
\max\!\left(\left|K_fF_{\mathrm{ext},i}\right|-d,0\right),
\quad i\in\{x,y,z\},
\]

where $K_f$ is a dimensionless force-scaling factor and $d$ is a per-axis dead-zone threshold in newtons.

A separate positive-$z$ cue was generated solely from the Omega.7 gripper angle $\theta_{\Omega}$:

\[
\alpha_g=\operatorname{clip}\!\left(
\frac{\theta_{\max}-\theta_{\Omega}}
{\theta_{\max}-\theta_{\min}},0,1\right),
\]

\[
u_g=\min\!\left(\alpha_gG_{\mathrm{cue}}F_{\mathrm{cue,max}},F_{\mathrm{cue,max}}\right),
\qquad
u_{h,z}=u_{h,z}^{\mathrm{base}}+u_g.
\]

With $G_{\mathrm{cue}}=0.3$ and $F_{\mathrm{cue,max}}=1.0$ N, the implemented cue was $u_g=0.3\alpha_g$ N and therefore remained within $[0,0.3]$ N. It was updated in every nominal 200-Hz supervisory cycle. A more open Omega.7 gripper produced a larger cue. This signal encodes the Omega.7 gripper aperture and contains no measurement of the Franka Hand aperture, master–slave aperture error, grasp force, or button state.

For Franka Hand execution, $v_g$ was passed as the speed argument of `grasp(width, speed, force, epsilon_inner, epsilon_outer)` and was also used by `move(width, speed)` during opening and non-grasp position adjustments. The strategy value $F_g$ was the requested `force` setting of `grasp()` in newtons, not an independently measured fingertip force. The grasp target width was 0 m. After contact and successful entry into the `HOLDING` state, the command was not transmitted repeatedly; the gripper maintained the grasp internally until `stop()` and the subsequent release or opening command.

The three parameter channels act on different elements of the teleoperation system. Panda impedance defines the slave-side response to pose error and disturbance, the Omega.7 settings determine how estimated external force is presented to the operator, and the Franka Hand settings determine grasp execution. The proposed method assigns these settings in parallel from one operation strategy. Thus, coordination is provided at the strategy layer through a consistent parameter bundle; no dynamic coupling constraint or master–slave impedance-matching law is derived between channels. Haptic transparency and closed-loop fingertip-force accuracy were not evaluated.

### 2.3 Object-Conditioned Cross-Channel Mechatronic Parameter Reconfiguration

The framework uses a three-level mapping from detected object class to an operation-oriented strategy and then to a joint parameter vector,

\[
\Theta(c)=\{K_t,K_r,\zeta,K_f,d,v_g,F_g\}.
\]

The strategy classes capture combined grasping risk and are not based on material softness alone. The apple and banana were assigned to the fragility-priority strategy because lower contact impact, closing speed, and requested grasp force were preferred to reduce squeezing and deformation, while still acknowledging the slip risk of their smooth surfaces. The paper cup and bottle used the balanced strategy. A paper cup can deform under excessive force, but settings that are too low can produce an insecure grasp; the bottle similarly requires a compromise between gentle handling and resistance to slip. The mouse and scissors used the stability-priority strategy because their smooth or irregular surfaces, transfer demands, and, for the scissors, elongated geometry placed greater emphasis on pose retention and grasp stability. These assignments were specific to the present objects, platform, and task.

**Table 2.** Parameter settings for the three operation-oriented strategies.

| Strategy | Objects | $K_t$ (N/m) | $K_r$ (N·m/rad) | $\zeta$ | $K_f$ | $d$ (N) | $v_g$ (m/s) | $F_g$ (N) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Fragility-priority | Apple, banana | 50 | 5 | 0.8 | 0.2 | 0.3 | 0.02 | 8 |
| Balanced | Paper cup, bottle | 150 | 10 | 1.0 | 0.5 | 0.4 | 0.05 | 15 |
| Stability-priority | Mouse, scissors | 200 | 13 | 1.2 | 0.7 | 0.5 | 0.10 | 20 |

When the supervisory loop read the first threshold-qualified result, the parameters enabled in the active mode were updated once and then locked for the remainder of the trial. Translational stiffness, rotational stiffness, and the damping-scaling parameter followed a smoothstep interpolation over approximately $T_s=0.30$ s. With $\tau=\operatorname{clip}((t-t_0)/T_s,0,1)$ and $s(\tau)=3\tau^2-2\tau^3$, each interpolated quantity $q\in\{K_t,K_r,\zeta\}$ was updated as

\[
q(t)=q_0+s(\tau)(q_\mathrm{target}-q_0).
\]

The controller recomputed $\mathbf{D}$ from the current $\mathbf{K}$ and $\zeta$ during this transition. Enabled values of $K_f$, $d$, $v_g$, and $F_g$ changed immediately at the strategy event. Because operator motion was not gated by perception and the formal logs did not synchronize the strategy event with physical contact, the mechanism is described as a one-shot update after task initiation. Its timing relative to first contact is unknown for the main dataset, and pre-contact completion is not claimed.

The class-to-strategy relation is manually engineered. If an existing detector already provides a stable label for a new object, that label can be added to the mapping without retraining the controller. If the detector cannot identify or distinguish the object reliably, the detector must be retrained or replaced before a strategy is assigned. The present system does not infer fragility, friction, or other physical attributes automatically from an unseen class.

### 2.4 Experimental Modes and Parameter Rationale

The fixed baseline vector was

\[
\Theta_0=(150,\ 10,\ 1.0,\ 0.5,\ 0.3,\ 0.10,\ 20),
\]

with the same element order as $\Theta(c)$. Table 3 summarizes the default interface, scheduling scope, and fallback behavior of the five modes.

**Table 3.** Interface, parameter scope, and fallback behavior of the five experimental modes.

| Mode | Visual interface shown by default | Parameter action | No detection or confidence $<0.25$ | Detected class without an explicit mapping |
|:---:|:---|:---|:---|:---|
| A: Fixed parameters | None | Retain $\Theta_0$ throughout | Not applicable | Not applicable |
| B: Operator selection | None | After task timing starts, the operator identifies the object and selects one complete strategy; all seven parameters are then set | Vision not used | Vision not used |
| C: Full cross-channel | Class, strategy label, confidence, and colored bounding box | Update all seven parameters | Retain initialized $\Theta_0$ | Apply the balanced default strategy |
| D: Visual-semantic cue only | Class, strategy label, confidence, and colored bounding box | No parameter update; retain $\Theta_0$ | Retain $\Theta_0$ | Display the balanced default strategy label; retain $\Theta_0$ |
| E: Impedance only | Class, strategy label, confidence, and colored bounding box | Update $K_t$, $K_r$, and $\zeta$ only; retain $0.5,0.3,0.10,20$ for $K_f,d,v_g,F_g$ | Retain initialized $\Theta_0$ | Apply the balanced default strategy to the impedance channel |

The camera window could be closed by pressing `q`, and window visibility was not logged during the formal experiment. The interface descriptions in Table 3 therefore reflect the default software behavior; continuous visibility was not verified for every trial.

The parameter values were selected as discrete engineering operating points. Two researchers screened candidate combinations on representative objects before the formal experiment and excluded settings associated with sustained oscillation, clear haptic discomfort, grasp failure, or visible object damage. The final values were fixed before the 135 formal trials. The low fragility-priority point used 50 N/m translational stiffness, 8 N requested grasp force, and 0.02 m/s gripper speed to reduce contact and closing severity. The balanced point used 150 N/m, 15 N, and 0.05 m/s to avoid both excessive deformation and unreliable holding. The stability-priority point used 200 N/m, 20 N, and 0.10 m/s to favor pose retention and transfer stability. These engineering working points were selected through qualitative screening for the present setup and should not be interpreted as material-specific damage limits.

**Table 4.** Parameter design space: physical interpretation of low and high values, engineering constraints, and values used in this study.

| Parameter | Interpretation of low value | Interpretation of high value | Engineering constraint | Values used |
|:---|:---|:---|:---|:---|
| $K_t$ | Greater translational compliance and lower impact | Greater positional stability | Stable Panda impedance-control range | 50 / 150 / 200 |
| $K_r$ | Greater rotational compliance about the fixed desired orientation | Greater resistance to rotational disturbance | Stable rotational response | 5 / 10 / 13 |
| $\zeta$ | Lower controller damping scaling | Higher controller damping scaling | Avoid sustained oscillation and excessive sluggishness | 0.8 / 1.0 / 1.2 |
| $K_f$ | Weaker rendered external-force cue | Stronger rendered external-force cue | Acceptable Omega.7 response | 0.2 / 0.5 / 0.7 |
| $d$ | Greater sensitivity to small forces | Greater suppression of small signals | Haptic-interface jitter and noise | 0.3 / 0.4 / 0.5 |
| $v_g$ | Lower-impact gripper motion | Faster grasp establishment | Franka Hand execution range | 0.02 / 0.05 / 0.10 |
| $F_g$ | Lower requested grasp force | Higher requested grasp force | Franka Hand force setting | 8 / 15 / 20 |

### 2.5 Execution Procedure

**Algorithm 1: Object-conditioned cross-channel parameter scheduling**

1. Load the mode-specific initialization in Table 3 and start the nominal 200-Hz supervisory update. Start the visual process only in modes C–E.
2. Run object detection asynchronously. The supervisory thread reads results without blocking and checks the confidence threshold.
3. If no detection reaches the threshold, retain the initialized state. If the detected label has no explicit class-to-strategy entry, assign the balanced default strategy.
4. Use the first threshold-qualified strategy to update the parameter channels enabled by the current mode. Interpolate $K_t$, $K_r$, and the controller parameter $\zeta$ over approximately 300 ms and update the enabled haptic-interface and gripper settings immediately.
5. Lock the selected strategy for the remainder of the trial and continue teleoperation, haptic rendering, and gripper execution without further visual switching.
6. Record the active parameter state, task trajectory, duration, and outcome, and reset the system after the prescribed terminal procedure.

### 2.6 Bounded Fallback and Safety Measures

A misclassification as another known class invoked the strategy assigned to that class. A detected label without an explicit mapping invoked the balanced default strategy, whereas a missing or low-confidence detection caused no update. Every fallback outcome was confined to one of the three predefined parameter sets, although a bounded parameter set may still be inappropriate for a misclassified object. Per-trial visual-event histories were not retained, so the frequencies of misclassification and default-branch activation in the main experiment are unknown.

Robot collision detection, Franka Hand force settings, zero-force commands on exit, a standardized initial pose, and a manual emergency stop supported experimental operation. The Omega.7 was operated through its standard driver and hardware configuration. The added master-gripper-aperture cue was limited by the implemented mapping to 0.3 N. The base force-feedback command was transmitted without an additional software saturation layer; saturation status was not logged, and no specific driver-level force clamp is assumed in the present analysis. These measures supported experimental operation but do not constitute a safety certification for perception or parameter-selection errors.

## 3 Experimental Design

### 3.1 Research Questions and Hypotheses

The study addressed the following research questions:

- **RQ1:** Does the full cross-channel mode C outperform the fixed-parameter mode A, the operator-selection mode B, and the visual-semantic-cue-only mode D?
- **RQ2:** Does the full cross-channel mode C outperform the impedance-only mode E?
- **RQ3:** Can visual inference be integrated without blocking the nominal 200-Hz supervisory update?
- **RQ4:** Is the direction of the C–E difference consistent across all three operators and six objects?

The primary hypothesis was that mode C would reduce task completion time. Success rate and Raw NASA-TLX were used to examine whether the observed pattern was also reflected in task success and subjective workload. Master-side trajectory length and pause count were included as exploratory process measures. The C–E comparison was used to determine whether adding the haptic-interface and gripper parameters produced a time advantage that was not reproduced by impedance-only scheduling.

### 3.2 Operators and Test Objects

Three operators completed the main experiment (P01–P03; 23–24 years old; two male and one female; all right-handed). The Omega.7 was positioned to the left of the operator and was controlled with the left hand in every trial. All operators had received basic teleoperation training and completed an additional 10–15 min familiarization session before each formal experiment to practice master-device motion, gripper input, and the task procedure. All participants provided written informed consent.

The six objects were selected to represent different contact, grasping, and transfer requirements and were assigned to the fragility-priority, balanced, or stability-priority strategy. These assignments served only the parameter settings used in this experiment and should not be interpreted as a general classification of material properties.

| Object | Strategy | Mass (g) | Surface | Dimensions (mm) | Principal task risk |
|:---:|:---:|---:|:---|:---|:---|
| Apple | Fragility-priority | ~200 | Smooth | Ø70–80 | Impact or slip; gentle contact required |
| Banana | Fragility-priority | ~120 | Smooth | 20 × 180 | Compression-induced deformation and slip |
| Paper cup | Balanced | ~5 | Paper | Ø75 × 90 | Easily deformed; stable grasp required |
| Bottle | Balanced | ~30 | Smooth plastic | Ø65 × 200 | Slip; balance between efficiency and stability |
| Mouse | Stability-priority | ~100 | Smooth plastic | 65 × 120 × 35 | Rigid irregular surface; transfer slip |
| Scissors | Stability-priority | ~150 | Metal and plastic | 50 × 170 × 15 | Rigid elongated geometry; high orientation demand |

### 3.3 Experimental Modes and Trial Structure

The experiment included five modes:

| Mode | Configuration | Default visual interface | Purpose |
|:---:|:---|:---|:---|
| A | Fixed parameters | None | Fixed-control baseline |
| B | Operator selection of the complete strategy | None | Manual selection workflow baseline |
| C | Full cross-channel scheduling | Class, strategy, confidence, and bounding box | Proposed method |
| D | Visual-semantic cue with fixed parameters | Same as C | Separate automatic parameter reconfiguration from the displayed semantic cue |
| E | Scheduling of $K_t$, $K_r$, and $\zeta$ only | Same as C | Compare full cross-channel and impedance-only reconfiguration |

Modes C, D, and E used the same default visual-semantic display. The C–D contrast therefore compares full automatic parameter reconfiguration with the displayed semantic information alone, while the C–E contrast compares full cross-channel reconfiguration with impedance-only reconfiguration without a designed interface difference. Mode D versus A assesses the combined visual-semantic cue—class, mapped strategy, confidence, and bounding box—and does not isolate the class name. Mode B required manual identification and button selection after timing had started and before robot motion could begin. Its comparison with mode C consequently includes both automation of the selection workflow and differences in visual-interface presentation; the separate decision time was not logged.

The experiment comprised 27 matched task blocks. Each block was defined by a fixed operator, object, and repetition index and contained one trial in each of modes A–E, yielding $27\times5=135$ trials. Within each operator and strategy category, the two objects were assigned to the three repetitions in a fixed 2:1 ratio. The assignment was identical across the five modes for that operator and strategy, preserving the matched comparison, and the 2:1 direction was exchanged across operators. This produced the following approximate 5:4 balance within each strategy:

| Strategy | Object | No. of blocks | No. of trials (×5 modes) |
|---|---|---:|---:|
| Fragility-priority | Apple | 4 | 20 |
| Fragility-priority | Banana | 5 | 25 |
| Balanced | Paper cup | 5 | 25 |
| Balanced | Bottle | 4 | 20 |
| Stability-priority | Mouse | 5 | 25 |
| Stability-priority | Scissors | 4 | 20 |
| Total | Six objects | 27 | 135 |

The five mode orders were preassigned at the operator-by-strategy group level using nine different sequences; no single fixed order was used. The schedule distributed the modes across early and late positions but was not a complete Latin-square design. The exact sequences are reported in Supplementary Table S2. Order, object, and operator effects could not be fully separated with three operators.

### 3.4 Task and Procedure

Before each trial, the test object was placed manually within a predefined work region and in an approximately prescribed orientation. Small reset errors in position and orientation were therefore present, but the same placement protocol was used in all modes. Only translational master motion was mapped; the desired Panda end-effector orientation remained fixed throughout the trial.

Each trial comprised reset, approach, grasp, transfer, release, and termination (Fig. 3). In modes C–E, camera acquisition, visual inference, and teleoperation began concurrently at task initiation; visual output did not gate operator motion. In mode B, timing began before object judgment and strategy selection, and the operator was allowed to move the robot only after completing the button selection. No separate timestamp marked the end of this selection step.

A trial was classified as successful when grasping, transfer, and placement were completed without a drop, observable slip, or visible damage. Complete separation of the object from the gripper was classified as a drop; visible relative motion between object and gripper during grasp or transfer was classified as slip; and a clear indentation, crushing deformation, or other visible damage was classified as damage. A designated researcher applied these predefined criteria in real time. Trials were not systematically video-recorded, and the labels were not independently or blindly re-evaluated.

A failure did not stop the timer immediately. Regrasping after a drop was not permitted; the failure was recorded, and the operator completed the prescribed return-and-termination procedure until the robot and gripper reached the predefined terminal state. The same timing endpoint was therefore used for successful and failed trials. The system recorded master-side trajectory, gripper input, active control parameters, task duration, and outcome, but not a complete per-trial history of visual detections, confidence values, interface visibility, or fallback events.

![Fig. 3](../drawing/revision_submission/Figure_3.png)

**Fig. 3.** Human-in-the-loop task and five experimental modes. (a) The one-shot strategy event $\Theta(c)$ updates the enabled slave-impedance, master haptic-interface, and gripper parameters without gating operator motion. (b) Modes A–E use fixed parameters, operator selection, full scheduling, a visual-semantic cue with fixed parameters, and impedance-only scheduling, respectively. Check marks indicate the channels updated in each mode; initialization and fallback settings are listed in Table 3.

### 3.5 Evaluation Measures

Task completion time was the primary endpoint. Success rate was reported descriptively, and master-side trajectory length and pause count were used as exploratory process measures. Subjective workload was assessed with Raw NASA-TLX [27]. Each of the six dimensions was rated from 0 to 100, and their unweighted arithmetic mean was used as the Raw NASA-TLX score.

Each operator completed one questionnaire immediately after the three trials belonging to a given strategy × mode condition. The three trials combined the two objects assigned to that strategy in the operator-specific 2:1 ratio. The workload dataset therefore contained $3$ operators $\times3$ strategies $\times5$ modes $=45$ questionnaires. These scores represent strategy-level workload under each mode and do not support object-specific workload comparisons.

Visual performance was characterized using class accuracy, class-to-strategy mapping accuracy, confidence, and per-image processing time in a separate controlled image test. Pause count was considered only as an exploratory process measure; because its final processing version was not retained in the frozen analysis package, no numerical pause result is reported or used for inference.

### 3.6 Statistical Analysis

Completion time across the five modes was first compared using the Friedman test. When the omnibus test was significant, paired Wilcoxon signed-rank tests were conducted with Holm–Bonferroni correction for multiple comparisons. The pairing unit was the task block defined by the same operator, object, and repetition index. For the primary C–E comparison, we report the paired mean difference, relative change, and a 95% bootstrap confidence interval obtained from 10,000 resamples of the matched task blocks. We also examined the direction of the effect for each operator. A leave-one-operator-out analysis was used to assess whether the overall difference was dominated by a single operator. Raw NASA-TLX was paired descriptively across nine operator × strategy units per mode; each score summarized three mixed-object trials, and no bootstrap interval was calculated. Because the 27 task blocks were nested within only three operators, the inferential tests characterize repeated-measures differences in the present sample and do not support population-level inference across operators. Results are reported as both median [IQR] and mean ± SD. Trajectory length and pause count were treated as exploratory measures, whereas success rate was treated descriptively. Figures 4–7 were generated from frozen data using verified Python/Matplotlib scripts.

---

## 4 Results

### 4.1 Visual Recognition, Semantic Mapping, and Asynchronous Integration

The separate visual test set contained 30 photographs per class, for a total of 180 images. These images were not used for model training or parameter selection and were acquired under fixed viewpoint, background, and lighting conditions. The model correctly classified all 180 images and mapped all predictions to the intended strategy. Mean confidence was 0.853, and mean wall-clock processing time was 48.19 ms per image (Fig. 4). These results characterize the six object instances and controlled imaging conditions used in this test; they are not evidence that every formal teleoperation trial produced a correct class result or parameter trigger.

| Object | No. of images | Class accuracy | Strategy-mapping accuracy | Mean confidence | Time (ms) |
|---|---:|---:|---:|---:|---:|
| Apple | 30 | 100% | 100% | 0.771 | 49.89 |
| Banana | 30 | 100% | 100% | 0.948 | 48.02 |
| Bottle | 30 | 100% | 100% | 0.726 | 48.57 |
| Paper cup | 30 | 100% | 100% | 0.820 | 46.62 |
| Mouse | 30 | 100% | 100% | 0.914 | 46.79 |
| Scissors | 30 | 100% | 100% | 0.938 | 49.27 |

![Fig. 4](../drawing/revision_submission/Figure_4.png)

**Fig. 4.** Results of the separate 180-image visual test (30 images per class). (a) Confusion matrix. (b) Detection confidence by class; dotted and dashed lines indicate the decision threshold and overall mean. (c) Wall-clock processing time per image. Boxes show the IQR and median, and diamonds show mean $\pm$ SD.

The independent YOLO process, bounded queues, and non-blocking polling removed visual inference from the synchronous call path of the nominal 200-Hz supervisory update. The implementation demonstrates asynchronous integration, but hard real-time performance is not claimed. The main trial logs did not contain a complete sequence of visual events or synchronized timestamps for the strategy event and physical contact. They consequently cannot establish per-trial trigger correctness, fallback frequency, or whether every update was completed before contact.

### 4.2 Results Across the Five Modes

**Table 5.** Experimental results for the five modes: completion time, master-side trajectory length, success rate, and Raw NASA-TLX. Values are reported as median [IQR], with mean ± SD in parentheses.

| Mode | Completion time (s) | Trajectory length (m) | Success rate | Raw NASA-TLX |
|:---:|:---:|:---:|:---:|:---:|
| A: Fixed parameters | 21.18 [20.62, 22.08] (21.42 ± 1.58) | 0.757 [0.693, 0.816] (0.763 ± 0.098) | 22/27 (81.5%) | 62.50 [59.67, 64.50] (62.59 ± 3.95) |
| B: Operator selection | 20.89 [20.12, 21.83] (21.01 ± 1.61) | 0.787 [0.721, 0.861] (0.799 ± 0.115) | 21/27 (77.8%) | 56.17 [55.00, 59.33] (57.15 ± 3.68) |
| **C: Full cross-channel** | **19.57 [18.41, 20.05] (19.28 ± 1.30)** | **0.697 [0.660, 0.769] (0.715 ± 0.092)** | **26/27 (96.3%)** | **48.67 [47.67, 51.83] (49.67 ± 3.63)** |
| D: Visual-semantic cue only | 20.79 [20.32, 21.16] (20.91 ± 1.10) | 0.722 [0.678, 0.768] (0.734 ± 0.085) | 24/27 (88.9%) | 60.33 [57.33, 62.50] (60.22 ± 3.85) |
| E: Impedance only | 20.73 [19.95, 22.25] (21.07 ± 1.56) | 0.732 [0.678, 0.799] (0.739 ± 0.084) | 24/27 (88.9%) | 53.67 [51.83, 57.83] (54.54 ± 4.09) |

Mode C had the lowest median completion time and master-side trajectory length, the highest observed success rate, and the lowest Raw NASA-TLX score (Fig. 5). Based on the mean values, completion time in mode C was 10.0%, 8.2%, 7.8%, and 8.5% lower than in modes A, B, D, and E, respectively. Subsequent inferential analyses focused on completion time as the primary endpoint.

Across the 27 matched task blocks, the Friedman test indicated a difference in completion time among the five modes ($\chi^2(4)=30.904$, $p<0.001$). In the Holm-adjusted paired Wilcoxon tests, completion time in mode C was lower than in modes A, B, D, and E (all $p<0.01$, $r>0.7$). Because task blocks were nested within only three operators, these statistics describe repeated-measures differences in the present sample and do not support population-level inference across operators. Mode C also had the lowest Raw NASA-TLX score in each of the nine operator × strategy units, but three operators are insufficient for a population-level workload conclusion.

![Fig. 5](../drawing/revision_submission/Fig5_combined_final.png)

**Fig. 5.** Results for the five modes: fixed parameters (A), operator selection (B), full cross-channel scheduling (C), visual-semantic cue only (D), and impedance-only scheduling (E). Panels show (a) task duration, (b) master-side trajectory length, (c) Raw NASA-TLX, and (d) success rate. In (a) and (b), each marker represents one of the 27 matched task blocks, and marker shape identifies the operator. Boxes show the IQR, median, and 1.5 × IQR whiskers. In (c), small markers denote questionnaire units and connected large markers denote operator means. Panel (d) reports the number of successful trials out of 27. In (a), brackets and double asterisks identify the prespecified comparisons of mode C with A, B, D, and E; all were significant in Holm-adjusted paired Wilcoxon tests ($p<0.01$).

### 4.3 Primary Comparison: Full Cross-Channel Versus Impedance-Only Scheduling

**Table 6.** Primary C–E comparison: median [IQR], paired improvement $\Delta T=T_E-T_C$, matched-task-block bootstrap 95% CI for the objective measures (10,000 resamples), and operator-level direction. Positive values indicate better performance in mode C. No bootstrap interval is reported for NASA-TLX.

| Measure | C (median [IQR]) | E (median [IQR]) | Descriptive mean improvement $\Delta$ (E−C) | Matched-block bootstrap 95% CI | Direction |
|:---|---:|---:|---:|---:|:---|
| Completion time (s) | 19.57 [18.41, 20.05] | 20.73 [19.95, 22.25] | 1.79 | [1.10, 2.51] | 3/3 operators favored C |
| Trajectory length (m) | 0.697 [0.660, 0.769] | 0.732 [0.678, 0.799] | 0.024 | [−0.014, 0.059] | Mixed |
| Raw NASA-TLX | 48.67 [47.67, 51.83] | 53.67 [51.83, 57.83] | 4.87 | — | 3/3 operators favored C |

The C–E comparison is the primary system-level contrast in this study. Both modes used the same class-to-strategy mapping, the same impedance settings, and the same visual-semantic interface by default. Mode C additionally updated the master-side haptic gain, force deadband, gripper speed, and requested grasp-force setting. This design removes both additional channel groups simultaneously and does not ablate individual parameters. It can therefore assess the overall difference between the complete parameter set and impedance-only scheduling, but it cannot identify the contribution of each added channel.

The median completion times were 19.57 s in mode C and 20.73 s in mode E (Fig. 6). With $\Delta T=T_E-T_C$, the mean paired difference was 1.79 s and the bootstrap 95% CI was [1.10, 2.51] s, corresponding to a mean reduction of 8.5%. The mean differences for P01, P02, and P03 were 1.66, 2.56, and 1.16 s, respectively. Across the six objects, the relative differences ranged from 3.3% to 13.2% (Fig. 7).

The median master-side trajectory lengths were 0.697 m in mode C and 0.732 m in mode E. The mean paired difference was 0.024 m, with a bootstrap 95% CI of [−0.014, 0.059] m. Because this interval crossed zero, the completion-time advantage of mode C cannot be attributed simply to a shorter geometric path. Pause count was retained only as an exploratory process measure and is not used to establish movement continuity or any other behavioral mechanism.

![Fig. 6](../drawing/revision_submission/Figure_6.png)

**Fig. 6.** Paired task durations for modes C and E. (a) Results for the 27 matched task blocks; points below the identity line indicate a shorter duration in mode C. (b) Paired difference $\Delta T=T_E-T_C$, where positive values indicate a shorter duration in mode C. Marker shape identifies the operator. The violin, horizontal segment, and diamond show the distribution, median, and mean, respectively.

### 4.4 Exploratory Process Measure: C–E Pause Analysis

Pause count was considered as an exploratory process measure derived from the master-side trajectory. The final pause-processing version could not be reconstructed from the frozen analysis package; numerical pause-count results are therefore not reported. No formal hypothesis test was prespecified or performed for this measure, and pause count is not used to establish movement continuity or any other behavioral mechanism.

### 4.5 Failure Analysis

Eighteen failures occurred across the 135 trials, with 5, 6, 1, 3, and 3 failures in modes A–E, respectively. Failures included object drops, observable slip, and visible damage, as summarized below. Outcomes were recorded in real time by one designated researcher using the predefined criteria in Section 3.4; no systematic video record or independent re-rating was available.

| Mode | Failures/total | Representative observations |
|:---:|:---:|:---|
| A: Fixed parameters | 5/27 | Paper-cup deformation and unstable positioning of the scissors |
| B: Operator selection | 6/27 | The manual-selection workflow included additional judgment and switching steps; the available records do not support attribution of specific failure causes |
| **C: Full cross-channel** | **1/27** | Slip of the mouse during transfer due to its smooth surface |
| D: Visual-semantic cue only | 3/27 | Object drops or loss of grasp during holding |
| E: Impedance only | 3/27 | Instability during grasp establishment or transfer for some objects |

Mode C had one failure in 27 trials, the lowest observed failure count among the five modes under the present experimental conditions. Because the experiment evaluated the combined configuration and did not isolate causal effects of slave-side impedance, the master-side haptic interface, and gripper execution, the failure results cannot be attributed to any single parameter channel.

### 4.6 Consistency Across Operators and Objects

Figure 7 reports the paired C–E differences by operator and object. The mean difference favored mode C for all three operators. Mode C also had the shortest mean completion time among the five modes for each of the six objects:

| Object | A: Fixed (s) | B: Operator selection (s) | **C: Full cross-channel (s)** | D: Visual-semantic cue only (s) | E: Impedance only (s) |
|:---:|---:|---:|---:|---:|---:|
| Apple | 20.46 | 21.40 | **19.25** | 20.81 | 20.94 |
| Banana | 20.07 | 20.85 | **19.49** | 21.06 | 20.64 |
| Paper cup | 22.36 | 20.27 | **18.69** | 20.38 | 21.17 |
| Bottle | 22.11 | 22.14 | **19.63** | 20.78 | 20.30 |
| Mouse | 21.74 | 20.93 | **19.75** | 20.74 | 21.64 |
| Scissors | 21.79 | 20.70 | **18.84** | 21.83 | 21.70 |

Relative to mode E, the mean completion-time reductions in mode C were 3.3% for the bottle, 5.5% for the banana, 8.1% for the apple, 8.7% for the mouse, 11.7% for the paper cup, and 13.2% for the scissors. The direction was consistent across all objects, although the magnitude varied.

The mean paired differences $\Delta T=T_E-T_C$ for P01, P02, and P03 were 1.66, 2.56, and 1.16 s, respectively. The corresponding median [IQR] differences were 1.91 [0.60, 3.14], 2.63 [2.19, 3.34], and 1.60 [−0.53, 1.73] s. Mode C was faster in 7/9, 9/9, and 6/9 task blocks, respectively. After successively excluding P01, P02, or P03, the mean differences in the remaining task blocks were 1.86, 1.41, and 2.11 s, and all continued to favor mode C. The mean C–E difference remained positive after each operator was excluded in turn, although the participant sample remained limited to three individuals.

![Fig. 7](../drawing/revision_submission/Figure_7.png)

**Fig. 7.** C–E task-duration differences by operator and object. Positive $\Delta T=T_E-T_C$ indicates a shorter duration in mode C. (a) Nine matched blocks for each operator. (b) Four or five matched blocks for each object, ordered by mean difference. Markers show block-level differences, diamonds show means, and horizontal bars show $\pm1$ SD. Labels report the mean difference and the number of blocks in which mode C was faster.

---


## 5 Discussion

### 5.1 Interpretation of Differences Among the Five Modes

The five modes differed in both their use of object information and the channels that were reconfigured. Mode A used one fixed parameter vector and no visual interface. Mode B also had no visual interface; after timing started, the operator identified the object, selected a strategy, and only then began robot motion. The B–C difference therefore includes removal of a manual decision-and-selection step and cannot be interpreted as a pure controller comparison. Mode D presented the same class, mapped strategy, confidence, and bounding box shown by default in mode C but retained fixed parameters. The C–D contrast is consequently the clearest test of automatic full-parameter reconfiguration beyond the visual-semantic cue itself. Modes C and E also shared the same default interface and impedance strategy, while mode E retained fixed haptic-interface and gripper settings. Their difference is the bundled contribution of the added haptic-interface and gripper settings.

Mode C had the shortest completion time and lowest Raw NASA-TLX in the present sample. The C–D and C–E comparisons support a task-level benefit of automatic parameter reconfiguration that was not reproduced by the default visual-semantic display or by impedance-only reconfiguration. Window visibility was not logged, so these comparisons refer to the designed default interfaces rather than verified continuous display in every trial. The pause-count pattern was exploratory and does not establish fewer interruptions or any causal process.

### 5.2 Full Cross-Channel Versus Impedance-Only Scheduling

Modes C and E used the same object-semantic mapping, impedance parameters, and default visual-semantic interface. Mode C additionally changed the dimensionless haptic force-scaling factor, force dead zone, gripper speed, and requested Franka Hand grasp-force setting. The paired mean E–C completion-time difference was 1.79 s, with a matched-block bootstrap 95% CI of [1.10, 2.51] s. The confidence interval for master-side trajectory length crossed zero, so the time difference was not explained by an evident reduction in geometric path length. Pause count was not used to infer a movement-continuity mechanism because the final exploratory processing version was not available in the frozen analysis package.

The C–E comparison shows that impedance reconfiguration alone did not reproduce the performance of the complete parameter bundle on this platform. The impedance settings change the robot response to pose error and disturbance; the master-side settings alter the rendering of the estimated external force; and the gripper settings alter the speed and requested force used to establish the grasp. The experiment evaluates these added haptic-interface and gripper settings together. It does not identify their separate contributions or show that the commanded Franka Hand force equals the actual fingertip contact force.

### 5.3 Distinction From Related Work

Tele-impedance and variable-impedance teleoperation commonly adapt remote impedance according to human state, contact force, demonstrations, or task phase [6–9,18–21]. Visual approaches have converted object attributes, geometry, and vision–language inputs into stiffness or impedance matrices [10,11,13,14]. Automatic switching, shared control, and multi-stiffness interfaces have addressed mode selection and control-authority allocation [12,15,16,23,24]. The present work does not claim the first use of vision to adjust impedance. Its distinction lies in the system-level formulation and experimental question: an operation strategy assigns one coordinated parameter bundle to the slave-side mechanical response, the operator-facing haptic interface, and gripper execution. The coordination is semantic and task-level rather than a dynamically derived coupling law. Low-rate perception is decoupled from the nominal high-rate supervisory update through bounded queues, and strategy locking maintains one selected configuration within each trial. The five-mode experiment distinguishes the complete configuration from fixed parameters, manual selection, a visual-semantic cue with fixed parameters, and impedance-only scheduling.

### 5.4 Implications for Mechatronic Teleoperation Design

The results support three observations for the present system.

**1. Displaying semantic information and acting on it are different interventions.** Modes C and D were designed to present the same class, mapped strategy, confidence, and bounding box. Mode C was faster and had lower Raw NASA-TLX while also reconfiguring the full parameter vector. The C–D comparison provides evidence that automatic parameter configuration offered an additional task-level benefit beyond the default visual-semantic display. By contrast, D–A represents the effect of the complete displayed cue, not a class-name-only comparison.

**2. The full bundle was not reproduced by impedance reconfiguration alone.** Modes C and E used the same mapping, default interface, and impedance settings. The shorter completion time in mode C is therefore associated with the added haptic-interface and gripper settings as a bundle. Channel-specific ablations are needed before attributing the difference to either group separately.

**3. A one-shot update does not require perception to run at the supervisory-loop rate.** Image acquisition at 15 fps and independent inference exchanged bounded data with the nominal 200-Hz update. The single-slot frame queue limited stale images, and non-blocking polling prevented the supervisory loop from waiting for visual output. This architecture is suitable when perception is used for one configuration event after task initiation rather than for continuous visual servoing; the present logs do not establish whether that event preceded first contact in every trial.

The same design principle may be useful in flexible sorting, remote maintenance, and unstructured dismantling, where a limited set of recurring object or task classes can be associated with validated operating strategies. Scaling beyond a small class set would require systematic mapping maintenance and may require more than three strategy levels. Additional sensing, such as tactile or contact-state information, could support post-contact verification or correction without requiring the visual process to enter the high-rate supervisory path.

### 5.5 Object-Dependent Differences

Mode C was faster than mode E for all six objects, with mean reductions ranging from 3.3% to 13.2%. The differences were smaller for the bottle and banana and larger for the paper cup and scissors. These variations may be related to differences in grasp pose, deformation risk, and orientation-stability requirements. Because only four or five matched task blocks were available for each object, we report the direction and magnitude descriptively and do not assign a specific mechanism to the object-level differences.

### 5.6 Limitations and Future Work

The most important evidence limitation is that the main logs did not preserve a complete per-trial visual-event history or synchronized timestamps for the strategy event and physical contact. The 180-image test establishes recognition performance only for its controlled image set; it cannot establish trigger correctness, fallback frequency, interface visibility, or pre-contact completion in the 135 teleoperation trials. Misclassification to another known class and use of the balanced-default strategy therefore cannot be excluded. The reported mechanism should be interpreted as a one-shot update after task initiation whose timing relative to first contact is unknown for the main dataset.

The study involved three operators and repeated measurements from the same participants. The inferential tests describe within-sample repeated-measures differences; a larger participant study is required for population-level generalizability. All operators were right-handed but used the left-positioned Omega.7 with the left hand. Only translational master motion was mapped, while the end-effector orientation remained fixed. Objects were manually reset within a prescribed region and approximate orientation, and the nine preassigned mode sequences did not provide complete positional balance. The results therefore apply to the present device layout, training conditions, motion mapping, object-placement protocol, and participant sample.

The class-to-strategy mapping is manual. A new label can be added without controller retraining only when the detector already recognizes it reliably; otherwise, a new or retrained detector is required. The system does not infer unseen physical properties or an appropriate strategy automatically. The three strategy levels are practical operating abstractions for the present task and may not remain sufficient as the number and diversity of objects increase.

The parameter sets were engineering working points chosen through qualitative screening and were not optimized or derived from material-strength testing. The C–E comparison removes the haptic-interface and gripper groups together and cannot separate their contributions. Future ablations should remove haptic-gain scheduling, dead-zone scheduling, and gripper scheduling separately. The base Omega.7 force-feedback command had no additional software saturation, saturation status was not logged, and no specific driver-level force clamp is claimed. Future implementations should add an explicit software force limit and log both commanded and limited output. The Franka Hand `force` value specified a requested grasp setting and was not measured at the fingertips; direct fingertip-force measurement is needed to validate its physical effect.

Success and failure were judged in real time by one designated researcher using predefined criteria. Trials were not systematically video-recorded or independently re-rated, so slip and visible-damage labels retain an observational component. A failure did not end timing immediately, and a dropped object could not be regrasped; the operator instead completed the common terminal procedure. This avoids artificially short failure times but does not provide stage-specific failure durations. The records also lack separate selection time in mode B, quantitative contact quality, and a direct measure of corrective action.

Pause count was explored from the master-side trajectory, but the final processing version was not retained in the frozen analysis package; no numerical pause result is therefore used in the present interpretation. Visual inference was removed from the synchronous call path of the nominal 200-Hz update, but hard real-time performance is not claimed. Future work should add synchronized perception, contact, interface, mode-selection, and full-cycle timing logs; predefine and archive pause-processing rules with sensitivity analysis; record video for independent outcome assessment; include active orientation control and less constrained object placement; and recruit a larger and more diverse participant sample.

## 6 Conclusion

This paper presents an object-conditioned method for coordinated mechatronic parameter reconfiguration in haptic teleoperation of heterogeneous objects. A three-level mapping from object semantics to an operational strategy and then to a joint parameter set assigned slave-side impedance, the master-side haptic interface, and gripper execution as one strategy-level bundle. An asynchronous one-shot update after task initiation integrated the configuration process while keeping low-rate perception outside the synchronous supervisory path. Because synchronized trigger-contact timestamps were not retained, pre-contact completion is not claimed for every trial.

In 135 physical trials involving three operators, six objects, and five modes, the full cross-channel mode C achieved the shortest completion time, the highest observed success rate, and the lowest Raw NASA-TLX score. Relative to mode E, which used the same semantic mapping and impedance settings, mode C reduced mean completion time by 1.79 s, with a matched-task-block bootstrap 95% CI of [1.10, 2.51] s. The direction favored mode C for all three operators and all six objects. No clear difference was observed in master-side trajectory length, indicating that the time advantage could not be explained simply by path shortening.

Under the present heterogeneous-object teleoperation conditions, the complete configuration produced better task-level performance than either impedance-only scheduling or the default visual-semantic cue with fixed parameters. The experiments provide system-level evidence for the overall effect of the complete parameter bundle on the current platform, while the causal contribution of each channel remains unresolved. Larger participant studies are needed to test population-level generality, synchronized visual-contact logging is needed to verify trigger timing, and channel-specific ablations are required to distinguish the contributions of haptic-interface and gripper scheduling.

---

## Supplementary Material

**Supplementary Table S1.** Trial-level results for the 27 matched task blocks (135 trials). Each row lists task duration, master-side trajectory length, and outcome for modes A–E. S and F denote success and failure. The paired difference is $\Delta T=T_E-T_C$, so positive values indicate a shorter duration in mode C. Modes are presented in analytical order; their chronological order is reported separately in Supplementary Table S2.

| Block | Operator | Group | Strategy | Object | A Fixed | B Operator-selected | C Full multi-channel | D Visual cue only | E Impedance-only | $\Delta T$ (s) |
|:---:|:---:|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|---:|
| MB01 | P01 | 1 | Fragility-priority | Apple | 19.76 / 0.626 / S | 20.36 / 0.571 / F | 18.23 / 0.708 / S | 20.12 / 0.747 / S | 18.83 / 0.732 / S | 0.60 |
| MB02 | P01 | 1 | Balanced | Paper cup | 20.24 / 0.695 / S | 18.83 / 0.664 / S | 18.04 / 0.584 / S | 19.12 / 0.678 / F | 19.95 / 0.671 / S | 1.91 |
| MB03 | P01 | 1 | Stability-priority | Mouse | 21.97 / 0.633 / F | 17.37 / 0.648 / S | 16.45 / 0.570 / S | 20.73 / 0.768 / S | 22.25 / 0.648 / S | 5.80 |
| MB04 | P01 | 2 | Fragility-priority | Banana | 19.09 / 0.755 / S | 20.41 / 0.835 / S | 19.57 / 0.665 / S | 20.07 / 0.671 / S | 20.39 / 0.832 / S | 0.82 |
| MB05 | P01 | 2 | Balanced | Paper cup | 25.96 / 0.949 / S | 20.15 / 0.755 / S | 17.88 / 0.638 / S | 20.79 / 0.801 / S | 21.06 / 0.794 / S | 3.18 |
| MB06 | P01 | 2 | Stability-priority | Mouse | 22.18 / 0.790 / S | 19.39 / 0.670 / F | 19.61 / 0.681 / S | 20.67 / 0.722 / S | 22.04 / 0.755 / S | 2.43 |
| MB07 | P01 | 3 | Fragility-priority | Banana | 21.37 / 0.898 / S | 20.76 / 0.781 / S | 20.61 / 0.670 / S | 21.36 / 0.712 / S | 18.89 / 0.793 / S | -1.72 |
| MB08 | P01 | 3 | Balanced | Bottle | 21.19 / 0.755 / S | 20.66 / 0.674 / S | 19.58 / 0.669 / S | 20.91 / 0.734 / F | 18.40 / 0.692 / S | -1.18 |
| MB09 | P01 | 3 | Stability-priority | Scissors | 20.66 / 0.595 / S | 20.89 / 0.988 / F | 20.49 / 0.758 / S | 20.90 / 0.600 / S | 23.64 / 0.718 / F | 3.14 |
| MB10 | P02 | 4 | Fragility-priority | Apple | 20.95 / 0.728 / S | 22.42 / 0.739 / S | 20.00 / 0.846 / S | 20.30 / 0.678 / S | 22.26 / 0.806 / S | 2.26 |
| MB11 | P02 | 4 | Balanced | Bottle | 21.62 / 0.653 / S | 22.79 / 0.869 / S | 18.75 / 0.601 / S | 20.63 / 0.724 / S | 18.91 / 0.666 / S | 0.16 |
| MB12 | P02 | 4 | Stability-priority | Scissors | 22.11 / 0.823 / S | 20.10 / 0.765 / F | 17.19 / 0.656 / S | 24.44 / 0.700 / S | 20.73 / 0.680 / S | 3.54 |
| MB13 | P02 | 5 | Fragility-priority | Apple | 20.68 / 0.717 / S | 20.89 / 0.829 / S | 18.35 / 0.888 / S | 21.10 / 0.706 / S | 20.54 / 0.804 / S | 2.19 |
| MB14 | P02 | 5 | Balanced | Bottle | 21.18 / 0.764 / F | 21.47 / 0.645 / S | 21.32 / 0.779 / S | 19.98 / 0.664 / S | 23.95 / 0.638 / F | 2.63 |
| MB15 | P02 | 5 | Stability-priority | Scissors | 21.11 / 0.678 / F | 19.75 / 0.776 / F | 17.58 / 0.754 / S | 20.96 / 0.647 / S | 22.85 / 0.535 / S | 5.27 |
| MB16 | P02 | 6 | Fragility-priority | Banana | 20.85 / 0.843 / S | 20.24 / 1.010 / S | 19.19 / 0.902 / S | 22.96 / 0.769 / S | 22.53 / 0.916 / S | 3.34 |
| MB17 | P02 | 6 | Balanced | Paper cup | 23.16 / 0.784 / F | 21.07 / 0.787 / S | 19.84 / 0.585 / S | 22.32 / 0.867 / S | 20.64 / 0.713 / S | 0.80 |
| MB18 | P02 | 6 | Stability-priority | Mouse | 22.82 / 0.660 / S | 19.17 / 0.802 / S | 19.63 / 0.822 / S | 20.75 / 0.867 / S | 22.53 / 0.665 / S | 2.90 |
| MB19 | P03 | 7 | Fragility-priority | Apple | 20.43 / 0.757 / S | 21.94 / 0.852 / S | 20.41 / 0.690 / S | 21.70 / 0.722 / S | 22.14 / 0.748 / S | 1.73 |
| MB20 | P03 | 7 | Balanced | Paper cup | 20.91 / 0.977 / S | 21.49 / 0.917 / F | 18.54 / 0.704 / S | 20.85 / 0.719 / S | 20.68 / 0.749 / F | 2.14 |
| MB21 | P03 | 7 | Stability-priority | Mouse | 22.06 / 0.691 / S | 24.50 / 0.841 / S | 22.23 / 0.798 / F | 20.34 / 0.823 / S | 21.43 / 0.738 / S | -0.80 |
| MB22 | P03 | 8 | Fragility-priority | Banana | 20.58 / 0.810 / S | 21.73 / 0.902 / S | 19.60 / 0.730 / S | 20.20 / 0.763 / S | 21.20 / 0.861 / S | 1.60 |
| MB23 | P03 | 8 | Balanced | Paper cup | 21.55 / 0.804 / S | 19.79 / 0.704 / S | 19.12 / 0.647 / S | 18.81 / 0.617 / S | 23.51 / 0.677 / S | 4.39 |
| MB24 | P03 | 8 | Stability-priority | Mouse | 19.70 / 0.835 / S | 24.20 / 1.019 / S | 20.82 / 0.743 / S | 21.21 / 0.692 / S | 19.95 / 0.717 / S | -0.87 |
| MB25 | P03 | 9 | Fragility-priority | Banana | 18.48 / 0.706 / S | 21.10 / 0.907 / S | 18.48 / 0.847 / S | 20.73 / 0.645 / S | 20.16 / 0.848 / S | 1.68 |
| MB26 | P03 | 9 | Balanced | Bottle | 24.45 / 0.910 / F | 23.65 / 0.765 / S | 18.88 / 0.697 / S | 21.60 / 0.803 / S | 19.95 / 0.852 / S | 1.07 |
| MB27 | P03 | 9 | Stability-priority | Scissors | 23.26 / 0.770 / S | 22.08 / 0.852 / S | 20.10 / 0.664 / S | 21.02 / 0.984 / F | 19.57 / 0.696 / S | -0.53 |

**Supplementary Table S2.** Preassigned mode order for the nine operator-by-strategy groups.

| Operator/group | Chronological mode order |
|:---|:---|
| P01–group 1 | A → D → C → B → E |
| P01–group 2 | B → E → D → C → A |
| P01–group 3 | C → A → E → D → B |
| P02–group 4 | D → B → C → E → A |
| P02–group 5 | E → C → A → B → D |
| P02–group 6 | A → D → B → C → E |
| P03–group 7 | B → E → A → D → C |
| P03–group 8 | C → B → D → A → E |
| P03–group 9 | D → A → E → C → B |

---

## Declarations

- **Ethics approval:** **[SUBMISSION-BLOCKING ITEM]** The authors are applying to the relevant school or institutional body for a formal ethics approval, exemption, or determination that approval is not required. Once a written decision has been obtained, this statement must specify the institution, decision type, date, and reference number. An exemption must not be claimed without formal documentation.
- **Informed consent:** All participants provided written informed consent before the experiment. The authors retain the associated documentation and can provide it upon journal request.
- **Images and generative AI:** Figure 1 is a photograph of the actual experimental platform. No generative AI was used to add, remove, replace, or reposition experimental elements. The submitted versions of Figs. 2–3 were redrawn by the authors using Python/Matplotlib, and Figs. 4–7 were generated from experimental data. Generative AI was used only during early layout discussion; the authors verified the logic, text, and data mapping in the final figures.
- **Generative-AI-assisted preparation:** During manuscript preparation, the authors used OpenAI Codex to assist with language editing, consistency checks, early layout discussion, and drafting Python/Matplotlib code. The authors subsequently reviewed and revised the text, redrew the submitted explanatory figures, verified all technical statements and plotted data, and take full responsibility for the manuscript.
- **Funding:** This research received no external funding.
- **Conflicts of interest:** The authors declare no conflicts of interest.
- **Data availability:** De-identified trial data are available from the corresponding author upon reasonable request.

---

## References

1. Lawrence, D.A. (1993), "Stability and transparency in bilateral teleoperation", *IEEE Transactions on Robotics and Automation*, Vol. 9 No. 5, pp. 624–637. https://doi.org/10.1109/70.258054.
2. Passenberg, C., Peer, A. and Buss, M. (2010), "A survey of environment-, operator-, and task-adapted controllers for teleoperation systems", *Mechatronics*, Vol. 20 No. 7, pp. 787–801. https://doi.org/10.1016/j.mechatronics.2010.04.005.
3. Hogan, N. (1985), "Impedance control: An approach to manipulation: Part I—Theory", *Journal of Dynamic Systems, Measurement, and Control*, Vol. 107 No. 1, pp. 1–7. https://doi.org/10.1115/1.3140702.
4. Kronander, K. and Billard, A. (2016), "Stability considerations for variable impedance control", *IEEE Transactions on Robotics*, Vol. 32 No. 5, pp. 1298–1305. https://doi.org/10.1109/TRO.2016.2593492.
5. Abu-Dakka, F.J. and Saveriano, M. (2020), "Variable impedance control and learning—A review", *Frontiers in Robotics and AI*, Vol. 7, 590681. https://doi.org/10.3389/frobt.2020.590681.
6. Walker, D.S., Wilson, R.P. and Niemeyer, G. (2010), "User-controlled variable impedance teleoperation", in *Proceedings of the IEEE International Conference on Robotics and Automation (ICRA)*, pp. 5352–5357. https://doi.org/10.1109/ROBOT.2010.5509811.
7. Ajoudani, A., Tsagarakis, N.G. and Bicchi, A. (2012), "Tele-impedance: Teleoperation with impedance regulation using a body–machine interface", *The International Journal of Robotics Research*, Vol. 31 No. 13, pp. 1642–1656. https://doi.org/10.1177/0278364912464668.
8. Laghi, M., Ajoudani, A., Catalano, M.G. and Bicchi, A. (2020), "Unifying bilateral teleoperation and tele-impedance for enhanced user experience", *The International Journal of Robotics Research*, Vol. 39 No. 4, pp. 514–539. https://doi.org/10.1177/0278364919891773.
9. Michel, Y., Rahal, R., Pacchierotti, C., Robuffo Giordano, P. and Lee, D. (2021), "Bilateral teleoperation with adaptive impedance control for contact tasks", *IEEE Robotics and Automation Letters*, Vol. 6 No. 3, pp. 5429–5436. https://doi.org/10.1109/LRA.2021.3066974.
10. Huang, Y.-C., Abbink, D.A. and Peternel, L. (2021), "A semi-autonomous tele-impedance method based on vision and voice interfaces", in *Proceedings of the 20th International Conference on Advanced Robotics (ICAR)*, pp. 180–186. https://doi.org/10.1109/ICAR53236.2021.9659427.
11. Oliva, A.A., Giordano, P.R. and Chaumette, F. (2021), "A general visual-impedance framework for effectively combining vision and force sensing in feature space", *IEEE Robotics and Automation Letters*, Vol. 6 No. 3, pp. 4441–4448. https://doi.org/10.1109/LRA.2021.3068911.
12. Bowman, M., Zhang, J. and Zhang, X. (2024), "Intent-based task-oriented shared control for intuitive telemanipulation", *Journal of Intelligent & Robotic Systems*, Vol. 110 No. 4, 167. https://doi.org/10.1007/s10846-024-02185-1.
13. Siegemund, G., Díaz Rosales, A., Glodde, A., Dietrich, F. and Peternel, L. (2024), "Semi-autonomous teleimpedance based on visual detection of object geometry and material and its relation to environment", in *Proceedings of the IEEE-RAS 23rd International Conference on Humanoid Robots (Humanoids)*, pp. 779–786. https://doi.org/10.1109/Humanoids58906.2024.10769858.
14. Jekel, H.H.A., Díaz Rosales, A. and Peternel, L. (2026), "Visio-verbal teleimpedance interface: Enabling semi-autonomous control of physical interaction via eye tracking and speech", *Frontiers in Robotics and AI*, Vol. 13, 1749105. https://doi.org/10.3389/frobt.2026.1749105.
15. Li, W., Huang, F., Chen, Z. and Chen, Z. (2024), "Automatic-switching-based teleoperation framework for mobile manipulator with asymmetrical mapping and force feedback", *Mechatronics*, Vol. 99, 103164. https://doi.org/10.1016/j.mechatronics.2024.103164.
16. Balachandran, R., De Stefano, M., Mishra, H., Ott, C. and Albu-Schäffer, A. (2023), "Passive arbitration in adaptive shared control of robots with variable force and stiffness scaling", *Mechatronics*, Vol. 90, 102930. https://doi.org/10.1016/j.mechatronics.2022.102930.
17. Park, S., Park, Y. and Bae, J. (2022), "Performance evaluation of a tactile and kinesthetic finger feedback system for teleoperation", *Mechatronics*, Vol. 87, 102898. https://doi.org/10.1016/j.mechatronics.2022.102898.
18. Li, R., Cheng, M. and Ding, R. (2023), "Passivity-based bilateral shared variable impedance control for teleoperation compliant assembly", *Mechatronics*, Vol. 95, 103057. https://doi.org/10.1016/j.mechatronics.2023.103057.
19. Wang, Z., Xu, X., Yang, D., Güleçyüz, B., Meng, F. and Steinbach, E. (2024), "Teleoperation with haptic sensor-aided variable impedance control based on environment and human stiffness estimation", *IEEE Sensors Journal*, Vol. 24 No. 14, pp. 22168–22177. https://doi.org/10.1109/JSEN.2024.3369758.
20. Michel, Y., Abdelhalem, Y. and Cheng, G. (2024), "Passivity-based teleoperation with variable rotational impedance control", *IEEE Robotics and Automation Letters*, Vol. 9 No. 12, pp. 11658–11665. https://doi.org/10.1109/LRA.2024.3490260.
21. Lee, H., Han, J. and Yang, G.-H. (2024), "Development of variable scaling teleoperation framework for improving teleoperation performance", *International Journal of Control, Automation and Systems*, Vol. 22 No. 3, pp. 936–945. https://doi.org/10.1007/s12555-022-1099-z.
22. Lippi, M., Welle, M.C., Wozniak, M.K., Gasparri, A. and Kragic, D. (2024), "Low-cost teleoperation with haptic feedback through vision-based tactile sensors for rigid and soft object manipulation", in *Proceedings of the 33rd IEEE International Conference on Robot and Human Interactive Communication (RO-MAN)*, pp. 1963–1969. https://doi.org/10.1109/RO-MAN60168.2024.10731383.
23. Díaz Rosales, A., Rodriguez-Nogueira, J., Matheson, E., Abbink, D.A. and Peternel, L. (2024), "Interactive multi-stiffness mixed reality interface: Controlling and visualizing robot and environment stiffness", in *Proceedings of the IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)*, pp. 13479–13486. https://doi.org/10.1109/IROS58592.2024.10801866.
24. Güleçyüz, B., Balachandran, R., Panzirsch, M., Singh, H., Hulin, T., Xu, X. and Steinbach, E. (2025), "Enhancing shared autonomy in teleoperation under network delay: Transparency- and confidence-aware arbitration", *IEEE Robotics and Automation Letters*, Vol. 10 No. 10, pp. 9654–9661. https://doi.org/10.1109/LRA.2025.3596436.
25. Riaziat, N.D., Erin, O., Krieger, A. and Brown, J.D. (2024), "Investigating haptic feedback in vision-deficient millirobot telemanipulation", *IEEE Robotics and Automation Letters*, Vol. 9 No. 7, pp. 6178–6185. https://doi.org/10.1109/LRA.2024.3397529.
26. Haddadin, S., Parusel, S., Johannsmeier, L. et al. (2022), "The Franka Emika robot: A reference platform for robotics research and education", *IEEE Robotics & Automation Magazine*, Vol. 29 No. 2, pp. 46–64. https://doi.org/10.1109/MRA.2021.3138382.
27. Hart, S.G. (2006), "NASA-Task Load Index (NASA-TLX); 20 years later", in *Proceedings of the Human Factors and Ergonomics Society Annual Meeting*, Vol. 50 No. 9, pp. 904–908. https://doi.org/10.1177/154193120605000909.
