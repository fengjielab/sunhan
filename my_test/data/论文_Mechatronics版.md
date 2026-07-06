# Vision-semantic multi-channel parameter scheduling for an integrated haptic teleoperation mechatronic system

## Structured Abstract

**Purpose**
This paper addresses the challenge that fixed teleoperation parameters are difficult to tune for heterogeneous objects with different fragility, stiffness and grasping requirements. We propose a vision-semantic multi-channel parameter scheduling framework that bridges object-level semantics and low-level mechatronic interface parameters, establishing a three-level mapping from perception to operation-oriented strategies and control parameters before contact.

**Design/methodology/approach**
The mechatronic system integrates an asynchronous RGB-D perception thread, a 200 Hz master–slave Cartesian impedance control loop, a haptic-interface parameter pre-setting module and gripper execution on an Omega.7–Franka Panda–Franka Hand platform. Before contact, an RGB-D camera identifies the target object and maps it to one of three operation-oriented policies: fragility-oriented, balanced and stability-oriented. The proposed scheduler then coordinates slave-side translational/rotational stiffness, damping ratio, master-side haptic-interface gain, force-interface dead zone, gripper closing speed and grasping force through a discrete, interpretable parameter table. Three operators performed 135 grasping trials involving six objects and five modes: fixed parameters, manual selection, full vision-semantic multi-parameter scheduling, visual information only and vision-semantic impedance-only scheduling.

**Findings**
In the tested mechatronic platform and participants, the proposed mode achieved the shortest median completion time (19.57 s [18.41, 20.05] IQR), the highest success rate as a descriptive metric (26/27, 96.3%) and the lowest Raw NASA-TLX (median 48.67 [47.67, 51.83] IQR). Compared with impedance-only scheduling, the proposed mode reduced mean completion time by −1.79 s (Bootstrap 95% CI [−2.51, −1.10] s; relative reduction 8.5%), while all three operators and all six tested objects showed the same directional trend. The trajectory-length difference was smaller (−0.024 m, 95% CI [−0.059, 0.014] m), suggesting that the benefit mainly came from fewer pauses and operation corrections rather than a shorter geometric path. Raw NASA-TLX decreased by −4.87 points (Bootstrap 95% CI [−5.35, −4.39]).

**Originality**
The originality lies in a deployable, system-level bridge between high-level object semantics and low-level mechatronic teleoperation interface parameters, rather than in a new impedance equation or a closed-loop force-feedback method. The proposed three-level mapping coordinates perception, slave-side impedance, pre-contact haptic-interface settings and gripper execution parameters in a unified mechatronic architecture. The asynchronous perception-control separation, the strategy-locking mechanism and the five-mode design constitute a practical integration blueprint that distinguishes perception, manual selection, impedance-only scheduling and full multi-channel pre-contact coordination.

**Keywords:** mechatronic system integration; haptic teleoperation; impedance control; vision semantics; real-time control architecture; human-in-the-loop experiment

---

## 摘要

针对异质对象遥操作抓取中固定控制参数难以同时兼顾易损对象柔顺接触、硬质对象稳定定位和不同夹持需求的问题，本文提出一种视觉语义驱动的多通道接触前机电参数调度方法。作为机电一体化系统，该平台集成异步RGB-D感知线程、200 Hz主从笛卡尔阻抗控制回路、主端触觉接口参数预置模块和夹爪执行模块，运行于Omega.7–Franka Panda–Franka Hand平台。系统利用RGB-D相机识别目标对象类别，将其映射为易损优先、折中和稳定优先三类操作策略，并在接触前协同配置从端平移/旋转刚度、阻尼比、主端触觉接口增益、力接口死区、夹爪闭合速度和夹持力。3名操作者围绕苹果、香蕉、纸杯、瓶子、鼠标和剪刀6种对象完成135次五模式抓取实验。结果显示，在当前机电平台和参与者范围内，视觉多参数模式取得完成时间中位数19.57 s [18.41, 20.05] IQR、最高成功率（26/27, 96.3%）和最低Raw NASA-TLX中位数48.67 [47.67, 51.83] IQR。相较视觉仅阻抗模式，视觉多参数模式平均完成时间降低−1.79 s（Bootstrap 95% CI [−2.51, −1.10] s；相对降幅8.5%），且3名操作者和6种已测试对象均表现出一致方向。主端轨迹长度差异较小（−0.024 m, 95% CI [−0.059, 0.014] m），提示多通道协同的收益更可能来自停顿和操作修正减少，而非几何路径显著缩短。Raw NASA-TLX降低−4.87分（Bootstrap 95% CI [−5.35, −4.39]）。本文不声称提出新的阻抗控制方程，也不把力反馈闭环建模或力觉透明性验证作为本篇贡献，而是提供一种低计算开销、可解释、可部署的机电系统接触前语义参数初始化方案。

---

## 1 引言

遥操作机器人能够把人的判断能力与机器人的远程执行能力结合起来，适用于柔性制造、危险环境作业、服务机器人以及非结构化物体操作等场景。触觉遥操作进一步通过主端力反馈向操作者传递远程接触信息，有助于提高操作者对抓取、接触和滑移风险的感知。从机电一体化系统设计的角度看，一个实用的触觉遥操作平台必须协同集成机械执行机构、人机接口、视觉感知、实时控制和参数调度等多个子系统[1–4]。对于真实抓取任务而言，操作者面对的对象往往具有不同的形状、表面、易损性和夹持需求。若系统始终采用一组固定阻抗和固定夹爪参数，则必须在柔顺接触、响应速度、定位稳定性和夹持可靠性之间折中。

从工业机器人应用角度看，这类问题并不限于实验室桌面抓取。远程维护、危险品处理、柔性分拣、非结构化拆解和人监督机器人操作中也经常出现类似需求：机电系统需要在不完全结构化的环境中处理易损件、易滑件、硬质工具、轻质容器或几何不规则对象。本文所选苹果、香蕉、纸杯、瓶子、鼠标和剪刀并不声称覆盖完整工业对象集，而是作为一个**mechatronic benchmark task set**——六种对象被选用于激发不同的柔顺性需求、触觉接口灵敏度和夹爪执行条件，而非代表完整的工业对象分类体系。

阻抗控制通过规定机器人位移偏差、速度偏差与交互力之间的动态关系，为接触操作提供柔顺性[5]。固定阻抗实现简单，工程上较易部署，但在异质对象抓取中难以同时适配易损对象、轻质对象和硬质对象。变阻抗控制能够根据接触力、轨迹误差、任务阶段或人的运动状态在线调节刚度和阻尼[6–9]。然而，在线变阻抗通常依赖连续状态估计、接触后反馈和稳定性约束。对于类别可识别、任务流程相对固定但仍需操作者完成精细抓取与放置的遥操作任务，接触发生前的对象语义可以作为一种低成本、可解释的任务先验。

已有视觉阻抗、共享控制和触觉引导研究表明，视觉信息、任务状态或操作者意图可用于改善远程操作效率和交互体验[10–13]。但是，在异质对象触觉遥操作中，对象语义不仅影响从端机械臂的柔顺性，还影响操作者期望获得的主端力反馈强度、反馈死区、夹爪闭合速度和夹持力。只显示视觉信息而不改变系统动力学时，操作者仍需通过手动补偿完成任务；只调节阻抗而保留默认力反馈和夹爪参数时，抓取和运输阶段仍可能受到夹爪执行与触觉反馈通道限制。因此，本文关注的问题是：在真实触觉遥操作抓取中，接触前视觉语义驱动的多通道机电参数协同是否比固定参数、人工选择、视觉提示和仅阻抗调节更有效？

本文从机电系统集成的视角提出一种视觉语义驱动的多通道参数调度方法。系统将目标对象映射为三类操作策略，并在接触前调用离散、可解释的参数表，同时配置从端阻抗、主端触觉接口参数和夹爪执行参数。本文贡献如下：

1. **机电系统架构集成（mechatronic system architecture）。** 将RGB-D感知、200 Hz实时控制、笛卡尔阻抗、触觉接口预设和夹爪执行统一在一个异步感知-控制解耦的机电架构中，并明确七层子系统及其协同关系。
2. **视觉语义—操作策略—控制参数三级映射（three-level mapping: vision semantics–operation strategy–control parameters）。** 将目标对象类别转化为易损优先、折中和稳定优先三类操作策略，使视觉信息以接触前控制先验的形式进入机电遥操作系统。
3. **多通道接触前参数协同。** 不仅调节从端平移/旋转刚度和阻尼比，还同步设置主端触觉接口增益、力接口死区、夹爪闭合速度和夹持力。本文不把力反馈闭环建模、接触力估计或力觉透明性验证作为本篇贡献。
4. **五模式人在环消融验证。** 在真实Omega.7–Panda平台上设置固定参数、人工选择、视觉多参数、视觉仅观察和视觉仅阻抗五种模式，区分视觉提示、人工选参、仅阻抗调节和完整多通道机电协同的作用。

不同于侧重新阻抗方程推导或接触后在线自适应控制的研究，本文的创新在于提供一种系统级接触前参数调度范式，将高层对象语义感知与底层机电遥操作接口参数连接起来。本文中的触觉接口增益和死区只作为接触前策略表中的接口预设参数使用，不作为力反馈闭环或力觉透明性研究的独立贡献。本文的核心定位是：一种低计算开销、可解释、可部署的机电系统接触前语义参数初始化方法。

---

## 2 方法与系统实现

### 2.1 Mechatronic System Architecture

本机电遥操作平台由七层子系统协同构成，信息流与系统架构如图1和图2所示。

**图1.** 机电一体化触觉遥操作实验平台，标注Omega.7力反馈主端、Franka Panda七自由度机械臂、Franka Hand夹爪、Intel RealSense D435i RGB-D相机、目标物体操作区和控制计算机。

**图2.** 系统信息流图，包含主端输入、增量位置映射、视觉识别、异步缓冲区、操作策略锁定、参数调度、阻抗控制、夹爪控制和基础触觉接口。图中区分低频视觉线程（约20 Hz）与200 Hz主控制线程，以及参数调度层与安全层的协同关系。

**机械执行层**：Franka Panda七自由度机械臂和Franka Hand夹爪构成执行端。Panda通过笛卡尔阻抗控制响应期望位姿和阻抗参数，Franka Hand以指定速度和夹持力执行开闭动作。

**人机接口层**：Omega.7七自由度力反馈主端采集操作者位移和夹钳输入，并通过基础触觉接口渲染从端交互力。操作者通过夹钳开度控制夹爪闭合程度，系统根据当前策略的参数表设定夹爪速度和夹持力上限。

**感知层**：Intel RealSense D435i RGB-D相机以约20 Hz采集RGB-D图像。YOLO11n目标检测模型运行于独立子进程（与Python GIL解耦），每帧处理时间约50 ms。检测结果通过 `multiprocessing.Queue(maxsize=2)` 传回主控制线程，共享状态由 `threading.Lock` 保护。

**控制层**：200 Hz主控制循环执行：读取Omega.7位姿增量 → 应用位置比例和坐标映射 → 更新从端期望位姿 → 调用Franka笛卡尔阻抗控制器 → 读取从端外力估计 → 渲染主端基础触觉反馈。控制周期为5 ms，不因视觉推理阻塞。

**视觉线程**：视觉子进程异步接收RGB帧（`mp.Queue(maxsize=1)` 仅保留最新帧以避免延迟累积），执行目标检测并返回类别标签和置信度。视觉线程与控制线程完全解耦，视觉推理的最长执行时间（≈50 ms）不会影响200 Hz控制循环的实时性。

**参数调度层**：视觉结果传入参数调度层后，根据对象类别→操作策略映射关系，从预设参数表中查找对应策略的七个参数（\(K_t, K_r, \zeta, K_f, d, v_g, F_g\)），并通过原子更新写入控制回路中的共享变量。参数更新仅在首次有效检测后的策略锁定事件中触发，此后参数在本次任务内保持不变。

**安全层**：当视觉未锁定或检测结果不可映射时，系统使用折中策略默认参数作为安全回退。任务内策略锁定避免视觉抖动导致参数频繁跳变。机械臂自身碰撞检测、程序退出零力命令、统一初始姿态和操作者人工急停共同构成基础安全措施。

### 2.2 Real-time Implementation and Synchronization

表1总结了各系统模块的频率/时间特性、输入输出和是否阻塞主控制线程。

**Table 1.** Real-time characteristics of mechatronic system modules.

| Module | Rate / Latency | Input | Output | Blocks main loop? |
|:---|---:|---:|---|:---:|
| Master input | 200 Hz | Omega.7 pose & buttons | \(\Delta\mathbf{x}_m\) | No |
| Slave control | 200 Hz | \(\mathbf{x}_d, \mathbf{K}, \mathbf{D}\) | Panda torque command | No |
| Vision detection (YOLO11n) | ~20 Hz (50 ms/frame) | RGB-D image | object class, confidence | No (sub-process) |
| Strategy scheduler | Event-based (on first valid detection) | class, confidence | \(\Theta(c)\) parameter set | No |
| Haptic rendering | 200 Hz | \(\mathbf{F}_{ext}, K_f, d\) | Omega.7 force vector | No |
| Gripper command | Event-based (gripper button) | gripper input, \(v_g, F_g\) | Franka Hand grasp/goal | No |

视觉检测和策略调度均为事件驱动且不阻塞主控制回路。视觉子进程运行于独立Python进程，通过`multiprocessing.Queue`以生产者-消费者模式传递检测结果。帧队列长度限制为1（仅保留最新帧），检测结果队列长度限制为2。主控制线程在每个5 ms周期开始时非阻塞地读取结果队列，若队列为空则沿用上一次锁定的策略，若视觉尚从未锁定则保持默认折中参数。策略锁定发生在接近阶段开始前——一旦主控制线程检测到有效类别且置信度≥0.25，立即锁定策略并一次性设置全部7个参数，此后该任务周期内参数不再改变。

### 2.3 主从增量位置映射

主端相邻采样时刻的位置增量为

\[
\Delta\mathbf{x}_m(k)=\mathbf{x}_m(k)-\mathbf{x}_m(k-1).
\]

从端期望位置更新为

\[
\mathbf{x}_d(k)=\mathbf{x}_d(k-1)+S\mathbf{C}\Delta\mathbf{x}_m(k),
\]

其中，位置比例系数固定为\(S=3.0\)，\(\mathbf{C}=\mathrm{diag}(-1,-1,1)\)为坐标映射矩阵。本文不将位置比例作为视觉调度变量，以便把实验差异集中在阻抗、触觉接口和夹爪参数上。

### 2.4 从端笛卡尔阻抗控制

从端采用笛卡尔阻抗控制，其等效关系表示为

\[
\mathbf{F}_c=\mathbf{K}(c)(\mathbf{x}_d-\mathbf{x})+\mathbf{D}(c)(\dot{\mathbf{x}}_d-\dot{\mathbf{x}}),
\]

其中\(c\)为操作策略类别，\(\mathbf{K}(c)\)和\(\mathbf{D}(c)\)分别为对应刚度与阻尼矩阵。平移和旋转刚度写为

\[
\mathbf{K}(c)=\mathrm{diag}(K_t,K_t,K_t,K_r,K_r,K_r).
\]

阻尼依据阻尼比\(\zeta(c)\)配置。经典阻抗控制提供柔顺交互的基本机理，本文改进点不在阻抗方程本身，而在于利用接触前对象语义对多通道机电控制参数进行任务相关初始化。

### 2.5 Haptic-interface Parameter Implementation

Omega.7具备主端力反馈能力，从端外力估计值\(F_{\mathrm{ext}}\)由Franka机器人内置的关节力矩估计器提供。主端基础触觉反馈按以下接口级公式渲染：

\[
u_h = \mathcal{D}_{d}\!\left(K_f \cdot \|\mathbf{F}_{\mathrm{ext}}\|\right) \cdot \mathrm{sign}(\mathbf{F}_{\mathrm{ext}}),
\]

其中\(\mathcal{D}_{d}(\cdot)\)为死区算子：当输入幅值小于\(d\)时输出零，否则输出输入幅值减去\(d\)。\(K_f\)和\(d\)仅作为接触前策略表中的接口预设参数，在任务过程中不实时更新，也不作为独立的力反馈闭环控制器。**This term is only an interface setting in the present study, not a closed-loop force-feedback contribution.** 本文不研究接触后外力估计的精度、力觉透明性、力反馈稳定性、力反馈有无对比，也不引入力反馈驱动的在线阻抗自适应。本文的实验只能支持"完整接触前多参数策略优于仅阻抗调节"这一整体机电系统级结论，不能单独证明触觉接口参数或夹爪参数的独立因果贡献。接触后外力估计、力反馈闭环修正及力觉感知验证将作为后续研究单独展开。

### 2.6 视觉语义多通道参数调度

视觉检测输出目标类别后，系统将类别映射为三类**操作策略**而非严格材料类别：易损优先策略、折中策略和稳定优先策略。苹果和香蕉映射为易损优先策略，纸杯和瓶子映射为折中策略，鼠标和剪刀映射为稳定优先策略。该映射依据的是本实验任务中的操作风险与夹持需求，而不是材料刚度的通用物理分类。首次有效检测达到置信度阈值0.25后，系统锁定本次任务策略；若无有效类别或类别不可映射，则保持折中策略默认参数作为安全回退。任务内策略锁定用于避免检测抖动导致频繁切换。

完整策略定义为

\[
\Theta(c)=\{K_t,K_r,\zeta,K_f,d,v_g,F_g\},
\]

其中\(K_f\)为主端触觉接口增益，\(d\)为力接口死区，\(v_g\)和\(F_g\)分别为夹爪闭合速度与夹持力设定。

**Table 2.** Parameter table for the three operation-oriented strategies.

| Strategy | Objects | \(K_t\) (N/m) | \(K_r\) (N·m/rad) | \(\zeta\) | \(K_f\) | \(d\) (N) | \(v_g\) (m/s) | \(F_g\) (N) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Fragility-oriented | Apple, Banana | 50 | 5 | 0.8 | 0.2 | 0.3 | 0.02 | 8 |
| Balanced | Paper cup, Bottle | 150 | 10 | 1.0 | 0.5 | 0.4 | 0.05 | 15 |
| Stability-oriented | Mouse, Scissors | 200 | 13 | 1.2 | 0.7 | 0.5 | 0.10 | 20 |

### 2.7 Parameter Design Space and Rationale

参数选择遵循"对象操作风险—控制响应—硬件约束"的工程逻辑。表3给出了每个参数的设计空间：低值和高值分别对应的物理意义，以及约束本文取值的硬件/安全边界。

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

易损优先策略采用较低平移/旋转刚度、较低接口增益、较低夹爪速度和较低夹持力，以降低对易损或表面易滑对象的冲击和挤压风险。稳定优先策略采用较高刚度、较强的接口增益和更快夹爪动作，以提高硬质对象的定位稳定性和操作效率。折中策略用于夹持需求介于两者之间的对象。

参数范围由Franka控制接口、Omega.7反馈接口舒适性、Franka Hand执行能力和预实验共同约束。预实验由两名研究人员在正式实验前完成，覆盖三类对象的抓取操作，用于排除明显不安全、明显低效或操作者主观不可接受的参数组合。正式实验前参数表被冻结，并对所有操作者和所有正式试次保持一致。B模式使用相同参数表，但由操作者手动选择策略。因此，B模式在本文中被定义为**人工选参工作流基线**，而不是纯粹的自动/手动控制器性能对比。人工选择时间计入B模式总完成时间，因此B模式用于评价包含人工判断与切换成本的实际工作流，而不作为纯控制器执行时间基线。

### 2.8 方法流程

**Algorithm 1: Vision-semantic multi-channel parameter scheduling for the integrated mechatronic system**

1. 系统初始化，加载折中策略默认参数\(\Theta(\text{balanced})\)，启动200 Hz主控制循环和视觉子进程；
2. 视觉子进程异步读取RGB-D图像并执行YOLO11n目标检测（不阻塞主循环）；
3. 主控制线程非阻塞读取检测结果队列；若检测类别属于预定义对象集合且置信度不低于0.25，则将对象类别映射为操作策略\(c\)；
4. 首次有效检测触发策略锁定事件：调用参数组\(\Theta(c)=\{K_t,K_r,\zeta,K_f,d,v_g,F_g\}\)，原子更新控制回路共享变量；
5. 锁定后本次任务周期内参数不再改变，避免视觉抖动频繁切换；
6. 将\(K_t,K_r,\zeta\)发送至从端阻抗控制器，将\(K_f,d\)作为主端基础触觉接口参数，将\(v_g,F_g\)用于夹爪控制；
7. 若检测失败或类别不可映射，则保持折中策略默认参数；
8. 任务结束后复位系统，策略解锁，准备下一次试验。

### 2.9 安全回退与工程约束

视觉未锁定或检测结果不可映射时，系统使用折中策略默认参数。任务内策略锁定避免视觉抖动造成参数频繁跳变。机械臂自身碰撞检测、程序退出零力命令、统一初始姿态和操作者人工急停共同构成基础安全措施。本文主要关注接触前参数初始化，不讨论接触后在线最优调参。

---

## 3 实验设计

### 3.1 研究问题与假设

本文围绕以下问题展开：

- **RQ1:** 视觉语义多参数前馈是否优于固定参数、人工选择和视觉仅观察？
- **RQ2:** 完整多通道机电参数调度是否优于视觉语义仅阻抗调节？
- **RQ3:** 异步视觉感知与控制线程集成是否满足任务开始阶段的实时性和基础可靠性要求？
- **RQ4:** 方法收益是否在不同操作者和不同已测试对象之间表现出一致方向？

相应假设为：与基线模式相比，视觉多参数模式能够降低完成时间和主端轨迹长度，提高成功率（作为描述性指标）并降低主观负荷；相较视觉仅阻抗模式，完整多通道模式能够减少停顿或操作修正，从而体现完整接触前机电参数策略相对于仅阻抗调节的整体附加作用。

### 3.2 操作者与实验对象

3名操作者（P01–P03，23–24岁男性，右利手）参与主实验。三名操作者均具有基础遥操作训练经验，并在每次正式实验前完成10–15分钟训练试次。所有操作者均签署知情同意书。本研究不涉及医学干预，也不采集可识别个人身份的信息。

实验覆盖六种对象，构成一个**mechatronic benchmark task set**，用于激发不同的顺应性、触觉接口灵敏度和夹爪执行条件。六种对象归入易损优先、折中和稳定优先三类操作策略。该分类用于本实验任务中的参数调度，不声称代表对象材料属性的普适物理分类。

| Object | Strategy | Mass (g) | Surface | Size (mm) | Primary task risk |
|:---:|:---:|---:|:---|:---|:---|
| Apple | Fragility-oriented | ~200 | Smooth | Ø70–80 | Impact/slip risk; requires gentle contact |
| Banana | Fragility-oriented | ~120 | Smooth | 20×180 | Crush deformation and slip risk |
| Paper cup | Balanced | ~5 | Paper | Ø75×90 | Easily deformable; requires stable grip |
| Bottle | Balanced | ~30 | Smooth plastic | Ø65×200 | Slippery; requires efficiency–stability balance |
| Mouse | Stability-oriented | ~100 | Smooth plastic | 65×120×35 | Rigid, irregular surface; transport slip risk |
| Scissors | Stability-oriented | ~150 | Metal+plastic | 50×170×15 | Rigid, elongated; high pose-precision requirement |

### 3.3 实验模式与试验结构

实验包括五种模式：

| Mode | Setting | Purpose |
|:---:|:---|:---|
| A | Fixed parameters, no visual scheduling | Fixed-control baseline |
| B | Operator manually selects full parameter strategy | Manual-selection workflow baseline |
| C | Vision-semantic automatic scheduling of full parameter set | Our method (full mechatronic scheduling) |
| D | Visual information displayed, fixed parameters maintained | Isolate effect of visual cue alone |
| E | Vision-semantic scheduling of \(K_t, K_r, \zeta\) only | Impedance-only ablation |

A模式用于检验固定参数在异质对象上的折中局限；B模式用于检验人工选参工作流是否会引入额外判断与切换负担；D模式用于区分视觉提示与控制参数改变的作用；E模式用于检验单独调节阻抗是否足以复现完整多通道机电参数策略。C与E的比较是本文核心消融，因为两者共享视觉语义和阻抗调节，差异在于C额外设置主端触觉接口参数和夹爪执行参数。本文不在该比较中分离触觉接口参数与夹爪参数的独立贡献。

试验结构以27个匹配块为基本单位。每个匹配块由同一操作者、同一对象/操作策略和同一重复编号下的A–E五个模式组成，因此总试次数为\(27\times5=135\)。六种对象在27个匹配块中的分布如下：

| Strategy | Specific object | Block count | Trials (×5 modes) |
|---|---|---|---:|---:|
| Fragility-oriented | Apple | 4 | 20 |
| Fragility-oriented | Banana | 5 | 25 |
| Balanced | Paper cup | 5 | 25 |
| Balanced | Bottle | 4 | 20 |
| Stability-oriented | Mouse | 5 | 25 |
| Stability-oriented | Scissors | 4 | 20 |
| Total | Six objects | 27 | 135 |

模式顺序在实验中进行了部分平衡，以降低单一固定顺序造成的学习或疲劳偏差。由于未执行严格完全随机化，也未将所有对象、操作者和顺序因素完全解耦，本文不将顺序效应视为已完全排除，而是在局限性中保守解释。完整的逐试次执行顺序作为补充材料提供。

### 3.4 实验任务与流程

每次试验包括复位、接近、抓取、运输、释放和任务结束六个阶段。成功定义为在规定时间内完成抓取—转移—放置，且物体未掉落、未发生明显滑移或可观察损伤。每次任务记录主端轨迹、夹钳输入、控制参数和任务持续时间。B模式中操作者通过按键选择策略，手动选择时间计入总完成时间；因此B模式代表包含人工判断与切换成本的工作流基线。

**图3.** 实验任务流程与视觉语义参数调度框架，包含六阶段时间线和机电参数配置点。

### 3.5 评价指标

主要终点为完成时间。次要客观终点包括成功率、主端轨迹长度、停顿次数、方向反转次数和运动平滑性。主观负荷采用未加权Raw NASA-TLX，即六个维度的算术平均。NASA-TLX按"操作者×对象策略×模式"采集六维评分。视觉模块报告类别识别正确率、策略触发正确率、置信度和单帧处理时间。

过程行为指标在正式统计前固定定义。停顿定义为：主端速度低于0.005 m/s且持续时间不短于0.30 s，由原始主端轨迹CSV（采样频率约200 Hz）通过差分计算速度后实时检测。

### 3.6 统计分析

考虑到试次嵌套在少数操作者内部，统计结果以配对趋势、操作者级方向性和效应大小为主，不将135次试验视为135个独立参与者样本。五模式完成时间采用Friedman检验进行总体比较；总体显著后进行配对Wilcoxon符号秩检验，并采用Holm-Bonferroni方法校正多重比较。C–E比较作为核心消融，报告配对均值差、Bootstrap 95%置信区间（10,000次重抽样，配对块bootstrap）、相对变化、效应量和操作者级聚合趋势。Raw NASA-TLX采用相同的非参数框架，但由于独立操作者数量仅为3名，主观负荷结果解释为初步人在环证据。成功率以描述性报告为主。结果同时报告median [IQR]以适配非参数分析框架。

---

## 4 实验结果

### 4.1 视觉识别与策略触发验证

在受控视角、背景和光照下，6种对象各30幅图像，共180幅。类别识别和策略触发均为180/180，平均置信度0.853，单帧墙钟处理时间50.08 ms。该结果说明在本文实验条件下视觉触发没有成为主要误差来源，但不外推至遮挡、强光变化、复杂背景、未知对象或未测试类别。

| Object | Images | Class accuracy | Strategy trigger accuracy | Mean confidence | Time (ms) |
|---|---|---|---|---|---:|---:|---:|---:|
| Apple | 30 | 100% | 100% | 0.771 | 56.66 |
| Banana | 30 | 100% | 100% | 0.948 | 50.45 |
| Bottle | 30 | 100% | 100% | 0.726 | 49.71 |
| Cup | 30 | 100% | 100% | 0.820 | 47.61 |
| Mouse | 30 | 100% | 100% | 0.914 | 46.79 |
| Scissors | 30 | 100% | 100% | 0.938 | 49.27 |

**图4.** 视觉识别验证结果，包括混淆矩阵、置信度分布和单帧处理时间分布。

### 4.2 五模式实验结果

**Table 4.** Five-mode experimental results: completion time, master trajectory length, success rate, and Raw NASA-TLX. Values reported as median [IQR] with mean±SD in parentheses.

| Mode | Completion time (s) | Trajectory (m) | Success rate | Raw NASA-TLX |
|:---:|:---:|:---:|:---:|:---:|
| A Fixed | 21.18 [20.62, 22.08] (21.42±1.58) | 0.741 [0.692, 0.811] (0.763±0.098) | 22/27 (81.5%) | 62.00 [60.33, 65.67] (62.59±3.95) |
| B Manual | 20.89 [20.12, 21.83] (21.01±1.61) | 0.793 [0.735, 0.875] (0.799±0.115) | 21/27 (77.8%) | 57.00 [54.33, 59.83] (57.15±3.68) |
| **C Vision multi-param** | **19.57 [18.41, 20.05] (19.28±1.30)** | **0.697 [0.660, 0.769] (0.715±0.092)** | **26/27 (96.3%)** | **48.67 [47.67, 51.83] (49.67±3.63)** |
| D Vision observe | 20.79 [20.32, 21.16] (20.91±1.10) | 0.716 [0.684, 0.779] (0.734±0.085) | 24/27 (88.9%) | 59.00 [57.83, 62.83] (60.22±3.85) |
| E Vision impedance-only | 20.73 [19.95, 22.25] (21.07±1.56) | 0.732 [0.678, 0.799] (0.739±0.084) | 24/27 (88.9%) | 53.67 [51.83, 57.83] (54.54±4.09) |

描述性结果显示，C模式在五种模式中取得最短median完成时间、最短主端轨迹、最高成功率和最低Raw NASA-TLX。C模式相较A、B、D和E的mean完成时间分别降低约10.0%、8.2%、7.8%和8.5%。

五模式完成时间的Friedman检验显示总体差异显著（χ²(4)=30.904, p<0.001）。配对Wilcoxon检验经Holm校正后，C模式完成时间显著低于A、B、D和E（p < 0.01，效应量 r > 0.7）。由于试次嵌套在3名操作者内部，本文将这些结果解释为当前机电平台、对象集合和参与者内的配对证据，而非一般操作者群体的总体统计结论。Raw NASA-TLX同样呈现C模式最低的方向，但主观负荷结果结合小样本和非盲法条件进行谨慎解释。

**图5.** 五模式完成时间对比——箱线图叠加配对散点（每个点代表一个匹配块），不采用柱状图。左侧面板：完成时间；右侧面板：主端轨迹长度和Raw NASA-TLX分子图。

### 4.3 核心消融：完整多参数策略 vs 仅阻抗调节

**Table 5.** Core C–E ablation: median [IQR], paired mean difference, Bootstrap 95% CI (10,000 re-samples, block-level bootstrap), and operator-level direction.

| Metric | C (median [IQR]) | E (median [IQR]) | Δ (C−E) | Bootstrap 95% CI | Direction |
|:---|---:|---:|---:|---:|:---|
| Completion time (s) | 19.57 [18.41, 20.05] | 20.73 [19.95, 22.25] | −1.79 | [−2.51, −1.10] | 3/3 operators ↓ |
| Trajectory (m) | 0.697 [0.660, 0.769] | 0.732 [0.678, 0.799] | −0.024 | [−0.059, 0.014] | mixed |
| Raw NASA-TLX | 48.67 [47.67, 51.83] | 53.67 [51.83, 57.83] | −4.87 | [−5.35, −4.39] | 3/3 operators ↓ |

C–E比较是本文最关键的消融。两种模式均使用视觉语义和阻抗调节，区别在于C模式额外设置主端触觉接口增益、力接口死区、夹爪闭合速度和夹持力。该设计用于检验一个工程问题：仅改变从端柔顺性是否足以覆盖异质对象抓取需求，还是需要同时初始化操作者感知通道和夹爪执行通道。需要强调的是，该比较只能说明完整接触前多参数策略相较仅阻抗调节具有整体机电系统级优势，不能单独证明触觉接口参数或夹爪参数各自的独立贡献。

在27个匹配块中，C模式median完成时间为19.57 s，E模式为20.73 s，配对均值差为−1.79 s（Bootstrap 95% CI [−2.51, −1.10] s），相对降低约8.5%。CI不包含零，支持C模式在完成时间上的显著改善。操作者级聚合结果显示，三名操作者均表现出C快于E的方向：P01为18.94 s vs 20.60 s（−8.1%），P02为19.09 s vs 21.66 s（−11.8%），P03为19.80 s vs 20.95 s（−5.5%）。六种对象层面也均表现出C快于E的方向（降幅范围3.3%–13.2%）。

主端轨迹长度差异较小（0.697 m vs 0.732 m），Bootstrap 95% CI为[−0.059, 0.014] m，穿过零点，说明轨迹长度差异在统计上不稳健。结合停顿分析，本文将C–E差异解释为操作效率改善的初步证据，即多通道机电参数协同可能减少了抓取、运输或释放阶段的停顿与修正。该机制解释与现有实验结果保持一致，但其因果性仍有待通过更细粒度的阶段标注与消融实验进一步验证。

**图6.** C–E核心消融结果。图中展示27个匹配块C–E完成时间配对散点（对角线以下为C更快），三名操作者分面图，六对象分层箱线图。图注声明Bootstrap CI仅作为配对证据解释。

### 4.4 过程行为指标：C–E停顿分析

从原始主端轨迹CSV（采样频率约200 Hz）计算停顿次数。停顿定义为主端速度低于0.005 m/s且持续不少于0.30 s。C模式每试次median停顿次数为3 [2, 3.5] IQR（mean: 2.74±1.23），E模式为3 [2, 5] IQR（mean: 3.41±1.67）。分策略看，易损优先、折中和稳定优先三类均表现出C模式停顿较少的方向。该结果与C模式完成时间更短而轨迹长度差异较小的现象一致，支持"多通道协同的附加收益主要来自操作效率提升（机电参数协同减少了停顿和修正），而非路径缩短"的解释。未来工作将通过引入阶段级时间标注（如接近、抓取、运输与释放），以实现对机电系统行为的更细粒度归因分析。

### 4.5 失败案例分析

135次试次中共发生9次失败，失败形式包括掉落、明显滑移或可观察损伤。各模式失败分布如下：

| Mode | Failures / Total | Typical observation |
|:---:|:---:|:---|
| A Fixed | 5/27 | Cup crush deformation, scissors positioning instability |
| B Manual | 6/27 | Manual strategy mis-selection or high switch cost |
| **C Vision multi-param** | **1/27** | Mouse surface slippery, slip during transport |
| D Vision observe | 3/27 | Inadequate grip force on medium objects |
| E Vision impedance-only | 3/27 | Unstable grasp on medium objects |

失败案例分析表明，C模式在本实验中具有最低失败率（1/27）。各模式失败主要表现出不同机制特征，说明多通道机电参数协同对抑制失败具有系统级作用。

### 4.6 跨操作者与六对象一致性

三名操作者均表现出C模式完成时间低于E模式的方向。六种对象层面的median值也显示C模式均为五模式中最短完成时间。对象层面结果如下：

| Object | A Fixed (s) | B Manual (s) | **C Vision multi-param (s)** | D Observe (s) | E Impedance-only (s) |
|:---:|---:|---:|---:|---:|---:|
| Apple | 20.46 | 21.40 | **19.25** | 20.81 | 20.94 |
| Banana | 20.07 | 20.85 | **19.49** | 21.06 | 20.64 |
| Paper cup | 22.36 | 20.27 | **18.69** | 20.38 | 21.17 |
| Bottle | 22.11 | 22.14 | **19.63** | 20.78 | 20.30 |
| Mouse | 21.74 | 20.93 | **19.75** | 20.74 | 21.64 |
| Scissors | 21.79 | 20.70 | **18.84** | 21.83 | 21.70 |

C相对E的时间降幅范围为瓶子3.3%、香蕉5.5%、苹果8.1%、鼠标8.7%、纸杯11.7%和剪刀13.2%。这说明方法在六种已测试对象上具有方向一致性，但不外推至未测试对象或复杂遮挡场景。

---

## 5 讨论

### 5.1 为什么接触前视觉语义前馈能够改善机电系统表现

固定参数模式必须用单一折中参数覆盖三类操作策略，因此难以同时满足易损对象的柔顺性和硬质对象的稳定定位。人工选择模式虽然能够调用不同策略，但把对象判断和策略切换责任交给操作者，增加了工作流负担。视觉仅观察模式改善了场景信息，却没有改变系统动力学和夹爪行为。视觉多参数模式利用对象语义在接触前完成机电参数策略初始化，使操作者不必在任务过程中持续补偿不合适的手感、夹爪速度或夹持力。这一机制与C模式较短完成时间、较低停顿次数和较低主观负荷趋势一致。

### 5.2 完整接触前机电参数策略相对仅阻抗调节的意义

C与E均根据视觉语义调整平移刚度、旋转刚度和阻尼比，因此两者共享柔顺性适配机制。C额外设置主端触觉接口增益、力接口死区、夹爪闭合速度和夹持力。当前数据中，C相较E的mean完成时间降低约8.5%（Bootstrap 95% CI [−2.51, −1.10] s），而主端轨迹长度降低约3.2%（95% CI [−0.059, 0.014] m，穿过零点）。这表明附加收益更可能来自抓取、运输或释放阶段的操作效率，而非大幅改变几何路径。

这一结果对应用型机电遥操作系统的工程意义在于：操作者面对的不仅是从端末端柔顺性，还包括主端触觉接口增益、力接口死区以及夹爪执行速度和夹持力构成的完整机电交互体验。单独调节阻抗可能无法覆盖异质对象抓取中的全部机电系统需求。例如，易损或易滑对象不仅需要较低刚度，还需要较慢的夹爪闭合和较低夹持力，以降低挤压与滑移风险；硬质或几何不规则对象则可能需要更明确的接口反馈和更稳定的夹持执行，以减少操作者在抓取建立和运输阶段的反复修正。力接口死区的工程作用主要是削弱小幅扰动和触觉接口噪声，使操作者感受到更稳定的接触提示，而不是作为接触力闭环控制律。多通道机电参数协同能够把对象语义转化为更完整的操作手感和执行策略。

### 5.3 与相关研究的区别

已有任务分解和共享控制研究通常通过切换控制方式、约束输入空间或提供引导来提高完成效率并降低操作者负荷[10–13]。视觉阻抗研究则从视觉与力特征空间统一控制目标[9]。本文区别在于：不进行连续视觉伺服，不依赖在线轨迹规划，也不声称接触后的外力闭环自适应或最优控制，而是把对象语义作为接触前任务先验，以低计算开销调用可解释的多通道机电参数策略。换言之，本文提供的是一种机电系统级桥接范式：将高层视觉语义转换为低层机电遥操作接口参数，使操作者在接触发生前获得更适合当前对象的从端柔顺性、触觉接口设置和夹爪执行行为。该定位适合类别可识别、环境相对结构化、但仍需要操作者完成精细抓取与放置的工程遥操作场景。

### 5.4 对机电遥操作系统的设计启示

本节从机电系统设计视角提炼三点启示：

**1. Perception should not only inform the operator; it should initialize low-level interface parameters.** 本研究表明，将视觉语义信息从"操作者提示"升级为"机电参数前馈"，能够在不增加操作者认知负担的前提下改善系统级表现。视觉感知模块不应只是显示器上的信息，而应作为机电参数初始化链路的一环。

**2. Compliance adaptation alone is incomplete for grasping.** 仅调节从端阻抗（C–E消融中的E模式）虽然提供了柔顺性适配，但不能覆盖夹爪执行速度和夹持力，也不能调整操作者感知到的触觉接口强度和死区。一个完整的机电遥操作抓取系统需要将阻抗、触觉接口和夹爪执行作为耦合的参数组进行协同调度。

**3. Asynchronous perception-control separation improves deployability.** 本文的异步架构（视觉子进程≈20 Hz，控制回路200 Hz，策略锁定只在首次检测时触发）既保证了控制实时性，又避免了视觉推理延迟对主从跟随的影响。这种感知-控制解耦的机电设计模式降低了视觉模块的实时性要求，使系统更容易部署到现有的遥操作平台上，而无需对控制回路进行实质性改造。

### 5.5 为什么不同对象收益幅度不同

六种对象均表现出C模式完成时间低于E模式，但降幅并不相同。瓶子和香蕉的降幅较小，可能是因为其抓取动作较熟悉，操作者即使在E模式下也能通过经验补偿默认夹爪参数。纸杯和剪刀的降幅较大，可能与其抓取风险和姿态稳定要求更高有关：纸杯需要避免变形和不稳定夹持，剪刀则需要更明确的定位和稳定运输。该机制解释可通过引入阶段耗时、重抓行为及夹爪状态日志等多源数据进行进一步细粒度验证。

### 5.6 局限性

1. 独立操作者仅3名，135次重复任务不能替代更大参与者样本；主观负荷和跨操作者结论应视为真实机电平台上的初步人在环证据。
2. 试次嵌套在操作者、对象和重复块内部，统计结果不解释为一般人群层面的强显著结论。Bootstrap CI仅作为配对证据的辅助量化。
3. 模式顺序进行了部分平衡，但未执行严格完全随机化，学习效应和疲劳效应不能完全排除。
4. 人工选择模式B包含选择时间，因此它是人工选参工作流基线，而不是纯控制器执行时间基线。
5. 人在环实验覆盖六种具体对象，每类对象数量有限，结果支持已测试对象间的一致方向，不外推至未知对象、复杂遮挡和开放场景。
6. 视觉验证来自受控视角、背景和光照，100%正确率仅代表受控实验条件，不外推至遮挡、复杂背景和未测试类别。
7. 现有数据未提供经独立传感器校准的接触力、滑移量和物体损伤量，因此本文不直接声称已证明"保护易损对象"。
8. 参数由工程经验、安全范围和预实验确定，本文证明的是离散语义策略在当前机电任务中的有效性，而非参数全局最优性。

---

## 6 结论

本文从机电系统集成的视角提出一种面向异质对象触觉遥操作抓取的视觉语义多通道参数调度方法。该方法将目标对象类别解释为易损优先、折中和稳定优先三类操作策略，并在接触前协同配置从端阻抗、主端触觉接口和夹爪执行参数，构成一个异步感知-控制解耦的机电遥操作系统。真实平台五模式实验显示，在当前3名操作者、6种对象和135次试验组成的mechatronic benchmark task set范围内，视觉多参数模式取得最短median完成时间（19.57 s [18.41, 20.05] IQR）、最高成功率（26/27, 96.3%）和最低Raw NASA-TLX（median 48.67 [47.67, 51.83] IQR）。与视觉仅阻抗模式相比，完整多通道模式mean完成时间降低−1.79 s（Bootstrap 95% CI [−2.51, −1.10] s），且3名操作者和6种对象均表现出一致方向。停顿分析和Bootstrap CI进一步提示，附加收益可能主要来自机电参数协同带来的操作停顿和修正减少，而非几何路径显著缩短。

总体而言，本文为无需复杂在线优化的异质对象触觉遥操作提供了一种可解释、低成本、可部署的机电系统接触前参数初始化方案。其统计普适性和外部泛化能力仍需通过更多操作者、严格随机化顺序、对象实例级记录、阶段过程指标以及接触质量指标进一步验证。接触后外力估计、力反馈闭环修正和操作者力觉感知验证属于后续研究范围，不由本文数据单独证明。

---

## Declarations

- **Ethical approval:** This study was exempt from formal ethics review because it involved non-medical teleoperation tasks and did not collect personally identifiable information.
- **Informed consent:** All participants provided written informed consent before the experiment.
- **Funding:** Not applicable.
- **Conflict of interest:** The authors declare no conflict of interest.
- **Data availability:** De-identified trial data, analysis scripts and vision validation results are available from the corresponding author upon reasonable request. A public repository link can be added when available.

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
14. [TODO: Mechatronic system design reference — e.g., mechatronic teleoperation system architecture or human–machine interface design]
15. [TODO: Real-time robotic control architecture reference — e.g., from IEEE Trans. Mechatronics or Robotics and Autonomous Systems]
16. [TODO: Haptic teleoperation implementation reference — e.g., from IEEE Trans. Haptics or ICRA/IROS]
17. [TODO: Perception-control integration reference — e.g., visual servoing with real-time constraints]
18. [TODO: Gripper control / grasping execution reference — e.g., from IEEE RA-L or ICRA]
19. Albu-Schäffer, A., Haddadin, S., Ott, C., Stemmer, A., Wimböck, T. and Hirzinger, G. (2007), "The DLR lightweight robot: design and control concepts for robots in human environments", *Industrial Robot*, Vol. 34 No. 5, pp. 376–385.
20. Haddadin, S., Parusel, S., Johannsmeier, L. et al. (2022), "The Franka Emika robot: A reference platform for robotics research and education", *IEEE Robotics & Automation Magazine*, Vol. 29 No. 2, pp. 46–64.
21. Hart, S.G. and Staveland, L.E. (1988), "Development of NASA-TLX (Task Load Index): Results of empirical and theoretical research", in Hancock, P.A. and Meshkati, N. (Eds.), *Human Mental Workload*, North-Holland, Amsterdam, pp. 139–183.
22. Boessenkool, H., Abbink, D.A., Heemskerk, C.J.M., van der Helm, F.C.T. and Wildenbeest, J.G.W. (2011), "Haptic shared control improves teleoperated task performance toward performance in direct control", in *Proceedings of the IEEE World Haptics Conference*, pp. 433–438.
23. Abbott, J.J., Marayong, P. and Okamura, A.M. (2007), "Haptic virtual fixtures for robot-assisted manipulation", in Thrun, S., Brooks, R. and Durrant-Whyte, H. (Eds.), *Robotics Research*, Springer Tracts in Advanced Robotics, Vol. 28, Springer, Berlin, pp. 49–64.