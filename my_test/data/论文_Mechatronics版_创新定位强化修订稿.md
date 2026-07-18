# 面向异质对象触觉遥操作的对象条件化跨通道机电参数协同配置

*Object-Conditioned Cross-Channel Mechatronic Reconfiguration for Haptic Teleoperation of Heterogeneous Objects*

## Abstract

Fixed teleoperation settings are poorly suited to objects that differ in fragility, geometry, and grasping requirements. This paper presents an object-conditioned framework for coordinated cross-channel reconfiguration of a haptic teleoperation system. Object semantics are mapped through an operation-oriented strategy layer to a joint parameter vector spanning slave-side Cartesian impedance, operator-facing haptic-interface settings, and gripper execution. Temporally, a single-slot frame queue, a two-slot result queue, and non-blocking polling decouple 15 fps visual perception from the nominal 200 Hz supervisory loop. The first valid mapped result triggers a one-shot target update, after which strategy locking prevents repeated intra-trial switching. Three operators performed 135 grasp-and-transfer trials with six objects and five control modes. Full cross-channel configuration produced the shortest median completion time (19.57 s, IQR [18.41, 20.05]), the highest descriptive success rate (26/27, 96.3%), and the lowest Raw NASA-TLX score (48.67, IQR [47.67, 51.83]). Compared with impedance-only scheduling, mean completion time decreased by 1.79 s (matched-block bootstrap 95% CI [1.10, 2.51] s), or 8.5%. The same direction was observed for all three operators and all six objects. Within the current three-operator experiment, coordinating the haptic interface and gripper with slave impedance was more effective than impedance-only scheduling, although the contribution of each added channel remains unresolved.

**Keywords:** mechatronic systems; haptic teleoperation; object-conditioned reconfiguration; cross-channel coordination; impedance control; human-in-the-loop experiment

---

## 1 引言

遥操作利用人的判断完成远端机器人难以自主处理的操作，常见于危险环境、柔性制造和非结构化场景。触觉反馈进一步把远端接触信息传回主端，帮助操作者判断接触、夹持和滑移状态。已有研究分别讨论了双边遥操作的稳定性与透明性，以及如何根据环境、操作者和任务调整控制器 [1,2]。在实际系统中，这些控制功能还必须与视觉感知、机械执行和人机接口共同运行。

同一组控制参数很难同时适合易损物体、轻质容器和刚性工具。较低刚度和夹持力有利于温和接触，却可能降低定位和转运稳定性；较高刚度和夹持力可能加快操作，但增加挤压或冲击风险。本文选取苹果、香蕉、纸杯、瓶子、鼠标和剪刀构成受控基准任务集，使实验在柔顺性需求、触觉线索强度和夹爪执行条件上形成可区分的操作要求，从而评价对象条件化跨通道参数配置在不同抓取任务中的系统表现。

阻抗控制通过设定位移、速度与交互力之间的关系，使机器人在接触时保持柔顺 [3]。固定阻抗易于实现，但只能为不同对象提供折中设置。变阻抗方法则根据任务状态、接触信息或学习结果调整刚度和阻尼，同时需要处理时变参数带来的稳定性问题 [4,5]。在遥操作中，操作者可以直接调节从端阻抗 [6]，tele-impedance 也可把人体运动和阻抗信息映射到远端机器人 [7–9]。这类连续调节通常依赖人体测量、示教数据或接触后的状态反馈。

视觉信息已被用于预先选择或在线调整机器人阻抗。视觉—语音 tele-impedance 根据对象属性选择从端阻抗，并保留操作者确认或修正的入口 [10]；视觉阻抗方法在视觉特征空间中融合视觉与力信息 [11]。Siegemund 等根据对象几何、材料及环境关系计算刚度 [13]，Jekel 等则结合视觉、注视和语言生成任务相关刚度矩阵 [14]。这些工作的共同点是把视觉任务信息转化为从端刚度或阻抗设置。

除阻抗调节外，遥操作研究还通过意图推断、自动切换和共享控制减轻操作者的决策负担 [12,15,16,24]，并利用触觉反馈改善受限视觉或不同硬度对象下的操作表现 [17,22,25]。其他工作涉及接触装配、人体与环境刚度估计、转动阻抗、缩放切换和多刚度交互界面 [18–21,23]。这些研究分别改变控制权、从端阻抗或反馈形式，但较少把对象语义作为同一个任务条件，同时配置从端机械响应、操作者交互界面和夹爪执行。因而，本文关注的并非“视觉能否用于调节阻抗”，而是对象语义能否驱动跨越三个机电子系统的联合配置，以及这种完整配置是否比视觉提示、人工选择和仅阻抗调度带来额外的系统级收益。

本文提出一种面向异质对象触觉遥操作的对象语义驱动跨通道机电参数协同配置框架。系统通过“对象语义—操作策略—联合参数向量”三级映射，将任务信息转化为从端阻抗、主端触觉接口和夹爪执行三个通道的统一配置。任务开始后，首个有效映射结果触发一次目标参数更新；策略锁定使所选配置在当前试验内保持不变，避免后续检测波动引起反复切换。为评价各组成环节的作用，实验设置固定参数、操作者选择、完整跨通道配置、仅视觉提示和仅阻抗调度五种模式。本文的主要贡献如下：

1. **跨通道机电参数协同配置。** 将对象相关参数设置由单一从端阻抗扩展到从端机械响应、操作者触觉接口和夹爪执行三个关联子系统，形成面向完整遥操作链路的联合配置。
2. **三级语义映射与受约束参数空间。** 将对象类别抽象为易损优先、折中和稳定优先三类操作策略，并映射到受硬件能力、任务风险和预实验工作包络约束的七维联合参数向量。
3. **异步事件触发的一次性重配置。** 15 fps 图像采集和独立 YOLO11n 推理通过有界队列接入名义 200 Hz 监督式更新；非阻塞读取避免主线程等待，策略锁定防止检测波动引发试验内反复切换，约 300 ms 的平滑过渡降低阻抗参数突变。
4. **五模式人在环系统级验证。** 在 Omega.7–Panda 实机平台上设置五种模式，逐层区分视觉提示、人工策略选择、仅阻抗适配和完整跨通道配置的作用，并通过三名操作者、六种对象和 135 次试验评价完整配置相对于各类基线的系统表现。

本文在在线阶段采用轻量化的离散参数配置，不依赖接触后的连续优化或持续视觉伺服。其核心并非单次参数调用，而是建立对象语义与从端阻抗、主端触觉接口和夹爪执行之间的联合配置关系，并通过异步事件触发和策略锁定将其部署于人在环遥操作系统。本文进一步检验这种跨通道配置能否带来仅阻抗调度未能复现的系统级收益。

---

## 2 方法与系统实现

### 2.1 机电系统架构与异步执行

实验平台包括 Omega.7 力反馈主端、Franka Panda 7 自由度机械臂、Franka Hand 夹爪 [26]、Intel RealSense D435i 相机和控制计算机（Fig. 1）。D435i 以 424×240、15 fps 输出彩色图像；本文未使用深度流。控制计算机运行视觉检测、名义 200 Hz 监督式遥操作更新、参数设置、触觉渲染、夹爪控制和数据记录。

![Fig. 1](../drawing/图一.png)

**Fig. 1.** Experimental platform with the Omega.7 master device, Franka Panda robot and Franka Hand gripper, D435i camera, and control computer. The camera supplied 424 × 240 color images at 15 fps.

Figure 2(b) expands the asynchronous software path into an illustrative timing view.

![Fig. 2(b)](./Figure_2b_timing_double_column.png)

**Fig. 2(b).** Illustrative software timing of the asynchronous perception–control implementation. Color frames are acquired at 15 fps and passed through a single-slot frame queue to an independent YOLO11n process; the controlled visual test gave a mean wall-clock processing time of 48.19 ms per image. Class-confidence results return through a two-slot result queue. The nominal 5-ms supervisory update polls this queue non-blockingly, so visual inference is not a synchronous prerequisite for each teleoperation update. The first valid mapped result with confidence $\geq0.25$ triggers a one-shot target-parameter update; stiffness and damping then transition over approximately 300 ms, and later detections do not cause intra-trial switching. If no valid mapped result is available, the mode-specific initialization is retained. The diagram is illustrative: the formal trials did not record the strategy-event time relative to physical contact.

RGB frames are acquired every 66.7 ms and written to a frame queue with capacity 1, preventing stale images from accumulating. YOLO11n runs in an independent process and returns class-confidence results through a queue with capacity 2. The nominal 200 Hz supervisory loop polls this queue every 5 ms without waiting for inference. When the first valid mapped result becomes available, the loop issues a one-shot target update; otherwise, the current mode retains its initialization. Camera acquisition, perception, and operator motion therefore proceed in parallel. The measured 48.19 ms value describes mean processing time rather than camera frequency.

**表 1.** 多速率机电系统的执行与通信特征。

| 模块 | 频率/延迟 | 输入 | 输出 | 是否阻塞主环？ |
|:---|---:|---:|---|:---:|
| 主端输入 | 200 Hz | Omega.7 位姿与按钮 | \\(\Delta\mathbf{x}_m\\) | 否 |
| 从端控制 | 200 Hz | \\(\mathbf{x}_d, \mathbf{K}, \mathbf{D}\\) | Panda 期望位姿/阻抗命令 | 否 |
| 图像采集 | 15 fps（66.7 ms/帧） | D435i 彩色流 | 424×240 图像 | 否 |
| YOLO11n 推理 | 平均 48.19 ms/图 | 最新可用图像 | 类别、置信度 | 否（独立进程） |
| 策略调度 | 首个有效映射结果被主循环读取时 | 类别、置信度 | \\(\Theta(c)\\) 目标值 | 否 |
| 触觉渲染 | 200 Hz | \\(\mathbf{F}_{ext},K_f,d\\) | Omega.7 力向量 | 否 |
| 夹爪命令 | 按钮事件 | 夹爪输入、\\(v_g,F_g\\) | Franka Hand 命令 | 否 |

### 2.2 主从映射与机电通道实现

主端相邻采样时刻的位置增量及从端期望位置更新为

\[
\Delta\mathbf{x}_m(k)=\mathbf{x}_m(k)-\mathbf{x}_m(k-1),
\]

\[
\mathbf{x}_d(k)=\mathbf{x}_d(k-1)+S\mathbf{C}\Delta\mathbf{x}_m(k),
\]

其中，位置缩放因子 \\(S=3.0\\)，坐标映射矩阵 \\(\mathbf{C}=\mathrm{diag}(-1,-1,1)\\)。从端采用笛卡尔阻抗控制：

\[
\mathbf{F}_c=\mathbf{K}(c)(\mathbf{x}_d-\mathbf{x})+\mathbf{D}(c)(\dot{\mathbf{x}}_d-\dot{\mathbf{x}}),
\]

\[
\mathbf{K}(c)=\mathrm{diag}(K_t,K_t,K_t,K_r,K_r,K_r),
\]

其中，\\(c\\) 为策略类别，阻尼矩阵 \\(\mathbf{D}(c)\\) 根据阻尼比 \\(\zeta(c)\\) 配置。

Franka 内部状态估计提供从端外力 \\(\mathbf{F}_{\mathrm{ext}}\\)。Omega.7 的触觉增益 \\(K_f\\) 和逐轴死区 \\(d\\) 按策略设置，第 \\(i\\) 个方向的基础触觉命令为

\[
u_{h,i}=\operatorname{sgn}\!\left(K_fF_{\mathrm{ext},i}\right)
\max\!\left(\left|K_fF_{\mathrm{ext},i}\right|-d,0\right),
\quad i\in\{x,y,z\}.
\]

软件还在 \\(z\\) 方向叠加由主端夹爪输入生成并限幅的状态提示 \\(u_g\\)，即 \\(u_{h,z}\leftarrow u_{h,z}+u_g\\)。Franka Hand 按当前策略中的闭合速度 \\(v_g\\) 和抓取力 \\(F_g\\) 执行命令。

三个参数通道分别作用于遥操作系统的不同机电环节：Panda 的笛卡尔阻抗参数调节从端对位姿偏差和接触扰动的机械响应；Omega.7 的触觉增益和力死区分别改变外力估计在主端呈现的幅值及其对小信号的敏感度；夹爪闭合速度和抓取力则影响抓取建立阶段的执行过程。本文根据对象语义对三个通道进行联合配置，使从端机械响应、操作者接收的触觉线索和夹爪执行条件与当前任务需求保持一致。该配置属于任务相关的跨通道参数重配置，而非基于动力学模型推导的主从阻抗匹配律；本文评价的是其任务级系统表现，触觉透明性和闭环力控制性能不在本实验的评价范围内。

### 2.3 对象条件化跨通道机电参数配置

本文采用“对象语义—操作策略—联合参数向量”三级映射。检测到的对象先被归入一种面向操作的策略，再由该策略配置三个机电子系统。苹果和香蕉采用易损优先设置，纸杯和瓶子采用折中设置，鼠标和剪刀采用稳定优先设置。这一分组依据当前实验中的抓取风险，而不是材料刚度分类。联合参数向量写为

\[
\Theta(c)=\{K_t,K_r,\zeta,K_f,d,v_g,F_g\}.
\]

当名义 200 Hz 监督式循环以非阻塞方式读取到首个置信度不低于 0.25 的有效映射结果时，调度器触发一次目标参数更新。平移与转动刚度及相应阻尼参数在约 300 ms 内按照 smoothstep 曲线平滑过渡，触觉接口和夹爪参数则根据当前模式更新；此后的检测结果不再改变本次试验的目标配置。由于操作者可以在识别完成前开始移动，且正式日志未同步记录策略事件与物理接触时刻，本文将该机制定义为任务早期重配置，而不将其表述为已在每次试验中验证的接触前切换。

**表 2.** 三类面向操作策略的参数表。

| 策略 | 对象 | \\(K_t\\) (N/m) | \\(K_r\\) (N·m/rad) | \\(\zeta\\) | \\(K_f\\) | \\(d\\) (N) | \\(v_g\\) (m/s) | \\(F_g\\) (N) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 易损优先 | 苹果、香蕉 | 50 | 5 | 0.8 | 0.2 | 0.3 | 0.02 | 8 |
| 折中 | 纸杯、瓶子 | 150 | 10 | 1.0 | 0.5 | 0.4 | 0.05 | 15 |
| 稳定优先 | 鼠标、剪刀 | 200 | 13 | 1.2 | 0.7 | 0.5 | 0.10 | 20 |

### 2.4 实验模式配置与参数依据

固定基线向量定义为

\[
\Theta_0=(150,\ 10,\ 1.0,\ 0.5,\ 0.3,\ 0.10,\ 20),
\]

其元素顺序与 \\(\Theta(c)\\) 一致。表 3 列出五种模式的初始化、调度范围和无有效视觉结果时的状态。

**表 3.** 五种实验模式的参数作用范围、初始化条件与回退行为。

| 模式 | 任务开始/触发前参数 | 选择或触发后的参数 | 无效或不可映射视觉结果 |
|:---:|:---|:---|:---|
| A 固定参数 | 全程使用 \\(\Theta_0\\) | 无参数选择事件 | 视觉未启用；保持 \\(\Theta_0\\) |
| B 操作者选择 | 从表 2 选择完整策略 | 所选策略设置七个参数；选择时间计入任务时间 | 视觉不参与，无视觉回退 |
| C 完整多通道 | 使用 \\(\Theta_0\\) | 首次有效结果设置全部七个参数 | 保持 \\(\Theta_0\\) |
| D 仅视觉提示 | 全程使用 \\(\Theta_0\\) | 仅显示提示，不更新参数 | 保持 \\(\Theta_0\\) |
| E 仅阻抗调度 | 使用 \\(\Theta_0\\) | 仅设置 \\(K_t,K_r,\zeta\\)；其余保持 \\(0.5,0.3,0.10,20\\) | 保持 \\(\Theta_0\\) |

表 4 汇总了三组参数工作点及其工程选择依据。候选值综合考虑 Panda 笛卡尔阻抗控制的稳定运行、Omega.7 触觉输出的可接受性、Franka Hand 的执行范围以及测试对象的夹持风险。正式实验前，两名研究人员分别使用三类策略的代表对象进行定性预实验，剔除出现持续振荡、明显触觉不适、夹持失败或可见损伤的参数组合，并据此选定低、中、高三组离散工作点。所有参数配置均在 135 次正式试验开始前固定；本文将其视为满足当前平台与任务条件的工程配置，而不解释为全局最优解。每次目标参数更新时，从端刚度和阻尼均由当前值在约 300 ms 内平滑过渡至目标值。

**表 4.** 参数设计空间：低值和高值的物理含义、硬件约束及本文取值。

| 参数 | 低值含义 | 高值含义 | 硬件/安全约束 | 本文取值 |
|:---|:---|:---|:---|:---|
| \\(K_t\\) | 柔顺性强、冲击小 | 定位稳定性高 | Panda 阻抗环稳定范围 | 50 / 150 / 200 |
| \\(K_r\\) | 姿态更柔顺 | 姿态更稳定 | 转动响应稳定性 | 5 / 10 / 13 |
| \\(\zeta\\) | 响应快、可能振荡 | 阻尼更强 | 避免超调 | 0.8 / 1.0 / 1.2 |
| \\(K_f\\) | 触觉线索较弱 | 接触感知更强 | Omega.7 舒适范围 | 0.2 / 0.5 / 0.7 |
| \\(d\\) | 对小力敏感 | 抑制噪声 | 触觉接口抖动 | 0.3 / 0.4 / 0.5 |
| \\(v_g\\) | 低冲击闭合 | 快速抓取 | Franka Hand 执行限制 | 0.02 / 0.05 / 0.10 |
| \\(F_g\\) | 温和抓取 | 抓取稳定性高 | 夹爪力限制 | 8 / 15 / 20 |

### 2.5 执行流程

**算法 1：视觉语义多通道参数调度**

1. 加载表 3 所列模式参数，并同时启动视觉进程和名义 200 Hz 监督式遥操作更新。
2. 视觉进程异步检测对象；监督式线程非阻塞读取结果，并判断类别是否可映射且置信度是否达到阈值。
3. 首个有效映射结果按模式更新相应目标参数，其中刚度和阻尼平滑过渡；无有效结果时保持表 3 的初始化状态。
4. 遥操作、触觉渲染和夹爪执行持续运行；已选择策略不因后续检测而切换。
5. 到达统一任务终点后记录结果并重置系统。

### 2.6 有界回退与安全措施

若对象被误分为另一个已知类别，系统会调用表 2 中对应的另一组参数。所有参数仍在预先确定的范围内，但错误策略可能不适合该对象。低置信度或不可映射的结果不改变模式初始参数。机械臂碰撞检测、夹爪力限制、退出时零力命令、统一初始位姿和人工急停用于实验安全，但这些措施不等同于面向误分类的安全认证。

---

## 3 实验设计

### 3.1 研究问题与假设

本文回答以下研究问题：

- **RQ1：** 完整调度模式 C 的任务表现是否优于固定参数 A、操作者选择 B 和仅视觉提示 D？
- **RQ2：** 完整调度 C 是否优于仅阻抗调度 E？
- **RQ3：** 视觉推理能否在不阻塞名义 200 Hz 监督式更新的条件下接入系统？
- **RQ4：** C–E 差异在三名操作者和六种对象上是否保持相同方向？

主要假设是模式 C 能缩短完成时间。成功率和 Raw NASA-TLX 用于观察结果是否在任务成功和主观负荷上保持一致；轨迹长度和停顿次数用于探索过程差异。C–E 比较用于判断增加触觉接口和夹爪参数后，是否出现仅阻抗调度无法获得的时间优势。

### 3.2 操作者与实验对象

主实验由三名操作者完成（P01–P03，23–24 岁；2 名男性、1 名女性；均为右利手）。Omega.7 固定放在操作者左侧，并在所有试验中由左手操作。三人均接受过基础遥操作训练，每次正式实验前另进行 10–15 分钟热身，以熟悉主端运动、夹爪输入和任务流程。所有参与者均签署书面知情同意。

六种对象用于覆盖不同的接触、夹持和转运要求，并分别归入易损优先、折中和稳定优先策略。这里的分组只服务于本实验的参数设置，不代表材料属性的通用分类。

| 对象 | 策略 | 质量 (g) | 表面 | 尺寸 (mm) | 主要任务风险 |
|:---:|:---:|---:|:---|:---|:---|
| 苹果 | 易损优先 | ~200 | 光滑 | Ø70–80 | 冲击/滑移风险，需要温和接触 |
| 香蕉 | 易损优先 | ~120 | 光滑 | 20×180 | 挤压变形和滑移风险 |
| 纸杯 | 折中 | ~5 | 纸质 | Ø75×90 | 易变形，需要稳定抓取 |
| 瓶子 | 折中 | ~30 | 光滑塑料 | Ø65×200 | 易滑，需要效率—稳定性折中 |
| 鼠标 | 稳定优先 | ~100 | 光滑塑料 | 65×120×35 | 刚性、不规则表面，转运滑移风险 |
| 剪刀 | 稳定优先 | ~150 | 金属+塑料 | 50×170×15 | 刚性、细长，对姿态精度要求高 |

### 3.3 实验模式与试验结构

实验包含五种模式：

| 模式 | 设置 | 目的 |
|:---:|:---|:---|
| A | 固定参数，无视觉调度 | 固定控制基线 |
| B | 操作者选择完整参数策略 | 操作者选择工作流基线 |
| C | 完整多通道调度 | 本文方法 |
| D | 仅视觉提示，保持固定参数 | 隔离视觉提示本身的作用 |
| E | 仅调度 \\(K_t,K_r,\zeta\\) | 仅阻抗对比 |

模式 A 提供固定参数基线；模式 B 保留完整参数表，但由操作者选择策略；模式 D 只显示视觉提示；模式 E 只更新阻抗参数。C 与 E 都使用同一视觉结果和阻抗策略，区别仅在于 C 同时更新主端触觉接口和夹爪参数。因此，C–E 是判断完整参数组是否优于仅阻抗调度的主要比较。

实验共包含 27 个匹配任务块。每个任务块固定操作者、对象和重复序号，并依次包含 A–E 五种模式，因此共有 \\(27\times5=135\\) 次试验。各对象对应的任务块数量如下：

| 策略 | 具体对象 | Block 数 | 试验数（×5 模式） |
|---|---|---:|---:|
| 易损优先 | 苹果 | 4 | 20 |
| 易损优先 | 香蕉 | 5 | 25 |
| 折中 | 纸杯 | 5 | 25 |
| 折中 | 瓶子 | 4 | 20 |
| 稳定优先 | 鼠标 | 5 | 25 |
| 稳定优先 | 剪刀 | 4 | 20 |
| 合计 | 六种对象 | 27 | 135 |

模式顺序经过部分平衡，避免所有试验采用同一固定次序。Supplementary Table S1 给出 27 个任务块的组成、各模式的完成时间、主端轨迹长度和成功结果。表中 A–E 按分析顺序排列，不代表实际执行顺序。由于样本较小，顺序、对象和操作者因素仍不能完全分离。

### 3.4 任务与流程

每次试验依次经历复位、接近、抓取、转运、释放和结束六个阶段（Fig. 3）。任务开始后，相机采集、视觉推理和遥操作同步启动，视觉结果不作为操作者运动启动的门限。模式 C 和 E 在监督式循环读取到首个有效映射结果后更新相应参数，但试验日志未同步记录该事件与物理接触的相对时刻。成功要求操作者在统一任务终点前完成抓取、转运和放置，且未出现掉落、可观察滑移或可见损伤；失败试验同样计时至该终点。系统记录主端轨迹、夹爪输入、控制参数和任务时长。模式 B 的任务时间还包括操作者判断对象并按键选择策略所需的时间。

![Fig. 3](../drawing/revision_submission/Figure_3.png)

**Fig. 3.** Human-in-the-loop task and five experimental modes. (a) The one-shot strategy event $\Theta(c)$ updates the enabled slave-impedance, master haptic-interface, and gripper parameters without gating operator motion. (b) Modes A–E use fixed parameters, operator selection, full scheduling, visual cue only, and impedance-only scheduling. Check marks indicate the parameters updated in each mode; initialization and fallback settings are listed in Table 3.

### 3.5 评价指标

完成时间为主要终点。成功率作描述性统计，主端轨迹长度和停顿次数用于探索操作过程。主观负荷采用六个维度等权平均的 Raw NASA-TLX [27]，问卷在“操作者 × 对象策略 × 模式”层级填写。视觉性能以类别准确率、策略映射准确率、置信度和单图处理时间报告。

过程行为指标在正式统计分析前定义并固定。停顿定义为主端速度低于 0.005 m/s 且持续至少 0.30 s，由约 200 Hz 采样的原始主端轨迹 CSV 通过速度差分检测得到。

### 3.6 统计分析

五种模式的完成时间先用 Friedman 检验比较；若全局检验显著，再进行配对 Wilcoxon 符号秩检验，并用 Holm–Bonferroni 方法校正多重比较。配对单元为同一操作者、同一对象和同一重复序号构成的任务块。对主要的 C–E 比较，本文报告配对均值差、相对变化及 10,000 次任务块重采样得到的 Bootstrap 95% 置信区间，并检查三名操作者的结果方向。Leave-one-operator-out 分析用于判断总体差异是否由单名操作者主导。Raw NASA-TLX 以九个“操作者 × 策略”单元进行配对描述，不计算 Bootstrap 区间。由于 27 个任务块嵌套于三名操作者，相关检验只反映当前样本中的重复测量差异。结果同时给出 median [IQR] 和 mean ± SD；轨迹长度与停顿次数为探索性指标，成功率为描述性指标。Fig. 4–7 均由冻结数据和经核验的 Python/Matplotlib 脚本生成。

---

## 4 实验结果

### 4.1 视觉识别、语义映射与异步集成验证

视觉测试集包含每类 30 张照片，共 180 张；这些照片未用于模型训练或参数选择，并在固定视角、背景和光照下采集。模型正确识别并映射了全部 180 张图像，平均置信度为 0.853，平均 wall-clock 处理时间为 48.19 ms（Fig. 4）。这些数值只反映当前对象实例和受控拍摄条件。

| 对象 | 图像数 | 类别准确率 | 策略触发准确率 | 平均置信度 | 时间 (ms) |
|---|---:|---:|---:|---:|---:|
| 苹果 | 30 | 100% | 100% | 0.771 | 49.89 |
| 香蕉 | 30 | 100% | 100% | 0.948 | 48.02 |
| 瓶子 | 30 | 100% | 100% | 0.726 | 48.57 |
| 纸杯 | 30 | 100% | 100% | 0.820 | 46.62 |
| 鼠标 | 30 | 100% | 100% | 0.914 | 46.79 |
| 剪刀 | 30 | 100% | 100% | 0.938 | 49.27 |

![Fig. 4](../drawing/revision_submission/Figure_4.png)

**Fig. 4.** Visual-test results for 180 images (30 per class). (a) Confusion matrix. (b) Detection confidence by class; the dotted and dashed lines indicate the threshold and overall mean. (c) Wall-clock processing time per image. Boxes show the IQR and median, and diamonds show mean $\pm$ SD.

独立 YOLO 进程、有界队列和非阻塞读取将视觉推理移出名义 200 Hz 监督式更新的同步调用路径。周期日志的中位周期约为 5.07 ms，但分布存在长尾，说明该实现支持视觉模块的异步集成，但不足以证明硬实时性能。由于日志未同步记录策略事件与物理接触时刻，本文也不据此判断每次参数更新是否发生在接触前。

### 4.2 五模式实验结果

**表 5.** 五模式实验结果：完成时间、主端轨迹长度、成功率和 Raw NASA-TLX。数值以 median [IQR] 报告，括号内为 mean±SD。

| 模式 | 完成时间 (s) | 轨迹长度 (m) | 成功率 | Raw NASA-TLX |
|:---:|:---:|:---:|:---:|:---:|
| A 固定参数 | 21.18 [20.62, 22.08] (21.42±1.58) | 0.757 [0.693, 0.816] (0.763±0.098) | 22/27 (81.5%) | 62.50 [59.67, 64.50] (62.59±3.95) |
| B 操作者选择 | 20.89 [20.12, 21.83] (21.01±1.61) | 0.787 [0.721, 0.861] (0.799±0.115) | 21/27 (77.8%) | 56.17 [55.00, 59.33] (57.15±3.68) |
| **C 完整多通道** | **19.57 [18.41, 20.05] (19.28±1.30)** | **0.697 [0.660, 0.769] (0.715±0.092)** | **26/27 (96.3%)** | **48.67 [47.67, 51.83] (49.67±3.63)** |
| D 仅视觉提示 | 20.79 [20.32, 21.16] (20.91±1.10) | 0.722 [0.678, 0.768] (0.734±0.085) | 24/27 (88.9%) | 60.33 [57.33, 62.50] (60.22±3.85) |
| E 仅阻抗调度 | 20.73 [19.95, 22.25] (21.07±1.56) | 0.732 [0.678, 0.799] (0.739±0.084) | 24/27 (88.9%) | 53.67 [51.83, 57.83] (54.54±4.09) |

模式 C 的完成时间中位数和主端轨迹中位数最低，成功率最高，Raw NASA-TLX 也最低（Fig. 5）。按均值计算，C 相比 A、B、D 和 E 分别缩短 10.0%、8.2%、7.8% 和 8.5%。后续统计检验以完成时间为主要终点。

在当前 27 个匹配任务块中，Friedman 检验显示五种模式的完成时间存在差异（$\chi^2(4)=30.904$, $p<0.001$）。Holm 校正后的配对 Wilcoxon 检验中，C 的完成时间低于 A、B、D 和 E（均为 $p<0.01$，$r>0.7$）。任务块嵌套于三名操作者，因此这些统计量只描述当前重复测量样本，不构成参与者总体推断。Raw NASA-TLX 的九个“操作者 × 策略”单元同样以 C 最低，但三名操作者不足以支持人群层面的工作负荷结论。

![Fig. 5](../drawing/revision_submission/Fig5_combined_final.png)

**Fig. 5.** Results for the five modes: fixed parameters (A), operator selection (B), full visual scheduling (C), visual cue only (D), and impedance-only scheduling (E). Panels show (a) task duration, (b) master-side trajectory length, (c) Raw NASA-TLX, and (d) success rate. In (a) and (b), each marker is one of 27 matched task blocks and marker shape identifies the operator. Boxes show the IQR, median, and 1.5×IQR whiskers. In (c), small markers denote questionnaire units and connected large markers denote operator means. Panel (d) reports successful trials out of 27.

### 4.3 核心比较：完整多通道调度与仅阻抗调度

**表 6.** 核心 C–E 比较：median [IQR]、配对改善量 $\Delta T=T_E-T_C$、客观指标的匹配任务块级 Bootstrap 95% CI（10,000 次重采样）和操作者层面方向。正值表示模式 C 的指标更优；NASA-TLX 不报告 Bootstrap 区间。

| 指标 | C (median [IQR]) | E (median [IQR]) | 描述性平均改善 Δ (E−C) | 匹配任务块级 Bootstrap 95% CI | 方向 |
|:---|---:|---:|---:|---:|:---|
| 完成时间 (s) | 19.57 [18.41, 20.05] | 20.73 [19.95, 22.25] | 1.79 | [1.10, 2.51] | 3/3 操作者支持 C 更快 |
| 轨迹长度 (m) | 0.697 [0.660, 0.769] | 0.732 [0.678, 0.799] | 0.024 | [−0.014, 0.059] | mixed |
| Raw NASA-TLX | 48.67 [47.67, 51.83] | 53.67 [51.83, 57.83] | 4.87 | — | 3/3 操作者支持 C 更低 |

C–E 是本文的主要系统级比较。两种模式使用相同的视觉类别和阻抗参数，C 额外更新主端触觉增益、力死区、夹爪闭合速度和抓取力。该设计相当于同时移除两个附加通道组，而不是逐个参数的组件级消融；因此，它只能评价完整参数组相对于仅阻抗调度的整体差异。

C 的完成时间中位数为 19.57 s，E 为 20.73 s（Fig. 6）。以 $\Delta T=T_E-T_C$ 计算，平均配对差为 1.79 s，Bootstrap 95% CI 为 [1.10, 2.51] s，相当于平均缩短 8.5%。P01、P02 和 P03 的平均差分别为 1.66、2.56 和 1.16 s；六种对象的相对差异为 3.3%–13.2%（Fig. 7）。

模式 C 和 E 的主端轨迹长度中位数分别为 0.697 m 和 0.732 m，平均配对差为 0.024 m，Bootstrap 95% CI 为 [−0.014, 0.059] m。轨迹长度差异的区间跨越零，说明模式 C 的完成时间优势不能简单归因于运动路径缩短。停顿次数整体呈现有利于 C 的方向，进一步表明完整跨通道配置的收益可能更多体现于操作节奏和过程修正，而非几何路径变化。该过程性解释仍需结合阶段耗时和重新抓取记录进一步检验。

![Fig. 6](../drawing/revision_submission/Figure_6.png)

**Fig. 6.** Paired task durations for modes C and E. (a) Results for 27 matched task blocks; points below the identity line indicate a shorter duration in C. (b) Paired difference $\Delta T=T_E-T_C$, where positive values indicate a shorter duration in C. Marker shape identifies the operator. The violin, horizontal segment, and diamond show the distribution, median, and mean.

### 4.4 过程行为指标：C–E 停顿分析

停顿次数作为探索性过程指标，由约 200 Hz 的主端轨迹计算。本文将主端速度低于 0.005 m/s 且持续至少 0.30 s 的连续区间定义为一次停顿，以排除瞬时减速并识别较为持续的运动中断。模式 C 的停顿次数为 3 [2, 3.5]，均值为 2.74±1.23；模式 E 为 3 [2, 5]，均值为 3.41±1.67。尽管两种模式的中位数均为 3，模式 C 在三类策略下的平均停顿次数均较低，与其完成时间优势方向一致。因此，该结果仅作为完整跨通道配置可能减少操作中断的描述性线索，而不用于独立建立具体过程机制。


### 4.5 失败案例分析

135 次试验中有 18 次失败，A–E 分别为 5、6、1、3 和 3 次。失败包括掉落、可观察滑移和可见损伤，具体分布如下：

| 模式 | 失败/总数 | 典型观察 |
|:---:|:---:|:---|
| A 固定参数 | 5/27 | 纸杯挤压变形，剪刀定位不稳定 |
| B 操作者选择 | 6/27 | 人工选择流程包含额外判断与切换步骤；现有记录不足以归因具体失败原因 |
| **C 完整多通道** | **1/27** | 鼠标表面较滑，转运中滑移 |
| D 仅视觉提示 | 3/27 | 出现掉落或夹持保持失败 |
| E 仅阻抗调度 | 3/27 | 部分对象在抓取或转运过程中失稳 |

模式 C 仅出现 1/27 次失败，为五种模式中最低，表明完整跨通道配置在当前任务条件下具有较好的任务级稳健性。由于本实验关注联合配置的整体作用，而未对从端阻抗、主端触觉接口和夹爪执行进行逐通道因果拆分，因此该结果不用于归因某一单独参数通道。

### 4.6 跨操作者与六对象一致性

Fig. 7 分别按操作者和对象给出 C–E 配对差。三名操作者的平均值均为 C 更快；六种对象中，C 也均具有五种模式里最短的平均完成时间。各对象均值如下：

| 对象 | A 固定参数 (s) | B 操作者选择 (s) | **C 完整多通道 (s)** | D 仅视觉提示 (s) | E 仅阻抗调度 (s) |
|:---:|---:|---:|---:|---:|---:|
| 苹果 | 20.46 | 21.40 | **19.25** | 20.81 | 20.94 |
| 香蕉 | 20.07 | 20.85 | **19.49** | 21.06 | 20.64 |
| 纸杯 | 22.36 | 20.27 | **18.69** | 20.38 | 21.17 |
| 瓶子 | 22.11 | 22.14 | **19.63** | 20.78 | 20.30 |
| 鼠标 | 21.74 | 20.93 | **19.75** | 20.74 | 21.64 |
| 剪刀 | 21.79 | 20.70 | **18.84** | 21.83 | 21.70 |

C 相比 E 的平均时间降幅为：瓶子 3.3%、香蕉 5.5%、苹果 8.1%、鼠标 8.7%、纸杯 11.7%、剪刀 13.2%。所有对象的方向相同，但差异幅度并不一致。

P01、P02 和 P03 的平均 $\Delta T=T_E-T_C$ 分别为 1.66、2.56 和 1.16 s。配对差中位数 [IQR] 分别为 1.91 [0.60, 3.14]、2.63 [2.19, 3.34] 和 1.60 [−0.53, 1.73] s，C 更快的任务块为 7/9、9/9 和 6/9。依次删除 P01、P02 或 P03 后，剩余任务块的平均差为 1.86、1.41 和 2.11 s，均保持 C 更快。结果没有由单名操作者独立造成，但样本仍只有三人。

![Fig. 7](../drawing/revision_submission/Figure_7.png)

**Fig. 7.** C–E task-duration differences by operator and object. Positive $\Delta T=T_E-T_C$ indicates a shorter duration in C. (a) Nine matched blocks for each operator. (b) Four or five matched blocks for each object, ordered by mean difference. Markers show block-level differences, diamonds show means, and horizontal bars show $\pm1$ SD. Labels give the mean difference and the number of blocks in which C was faster.

---

## 5 讨论

### 5.1 五种模式差异的解释

五种模式的结果差异与其信息使用方式和参数作用范围相符。模式 A 对所有对象采用同一组折中参数；模式 B 允许操作者选择策略，但对象判断和参数切换均由人工完成；模式 D 仅向操作者提供对象信息，不改变控制器和夹爪设置；模式 E 根据视觉结果调整从端阻抗，但主端触觉接口和夹爪参数保持不变；模式 C 则在任务早期自动完成三个通道的联合配置。因此，模式 C 既省去了模式 B 中的人工判断与切换，也比模式 D 和 E 更充分地将对象信息作用于遥操作系统。模式 C 较短的完成时间和较低的 Raw NASA-TLX 与这一设计相符；特别是其相对于模式 E 的优势，支持完整跨通道配置能够提供超出仅阻抗调度的额外收益。停顿次数呈现相同方向，可作为操作中断可能减少的辅助线索，但不用于单独建立具体过程机制。

### 5.2 完整调度与仅阻抗调度

模式 C 和 E 采用相同的对象语义映射及阻抗参数，两者的差别在于，C 还同步调整触觉增益、力死区、夹爪闭合速度和抓取力。当前实验中，E–C 的配对平均完成时间差为 1.79 s，Bootstrap 95% CI 为 [1.10, 2.51] s。主端轨迹长度差异的置信区间跨越零，说明 C 的时间优势并不是因为操作者走了明显更短的路径。C 的停顿次数整体较少，这可能与操作过程更加连贯有关，但仅凭现有记录还不能判断差异主要出现在抓取、转运还是释放阶段。

C 和 E 的比较还说明，仅调整从端阻抗并未复现完整参数配置的效果。实际抓取不仅受机械臂柔顺性影响，操作者接收到的力提示以及夹爪的闭合过程也会改变操作行为。在本文系统中，阻抗参数调节机械臂对位姿偏差和接触扰动的响应；触觉增益和力死区影响小幅外力信号在主端的呈现；夹爪速度和抓取力则直接作用于抓取建立过程。三类参数共同变化，可能是 C 相对于 E 获得额外时间收益的原因。

需要指出的是，C–E 对比验证的是完整配置相对于仅阻抗调度的整体效果，不能进一步分离触觉接口参数和夹爪参数各自的贡献。这需要增加相应的消融模式。

### 5.3 与相关工作的差异

Tele-impedance 和变阻抗遥操作通常根据人体状态、接触力、示教结果或任务阶段连续调节远端阻抗 [6–9,18–21]。视觉方法也已把对象属性、几何和视觉—语言输入转化为刚度或阻抗矩阵 [10,11,13,14]；自动切换、共享控制和多刚度界面则处理模式选择和控制权分配 [12,15,16,23,24]。本文并不首次提出“用视觉调阻抗”，其差异在于研究对象和系统组织方式：对象语义先经过操作策略层，再一次性配置从端机械响应、操作者触觉接口和夹爪执行；低频感知通过有界队列与名义高频监督式更新解耦，策略锁定则保持试验内配置稳定。五种实验模式进一步把完整跨通道配置与固定参数、人工选择、视觉提示和仅阻抗调度区分开来。

### 5.4 对机电遥操作系统设计的启示

从对象条件化跨通道配置的角度，实验结果带来三点系统设计上的观察：

**1. 对象信息的使用方式会影响任务表现。** 模式 D 只向操作者显示识别结果，模式 C 则将识别结果用于任务早期的参数配置。当前实验中，C 的完成时间和 Raw NASA-TLX 均低于 D，说明仅提供类别提示没有达到自动配置完整参数组的效果。

**2. 完整配置的收益不只来自阻抗调整。** 模式 C 和 E 采用相同的对象语义映射及阻抗设置，但 C 的完成时间更短。由此可见，仅调整从端阻抗没有复现完整配置的表现，主端触觉接口和夹爪参数作为一个附加参数组带来了额外收益。两类参数各自的作用还需通过进一步的通道对比加以区分。

**3. 一次性参数更新不要求视觉模块与监督式循环同频运行。** 如 Fig. 2(b) 所示，15 fps 图像采集、平均 48.19 ms 的视觉推理与名义 200 Hz 监督式更新分别运行，并通过有界队列传递结果。单槽帧队列限制旧图像积累，非阻塞读取避免监督式循环等待视觉结果。对于只需在任务早期完成一次配置的场景，这种异步接入方式避免了视觉推理成为监督式循环的同步前置步骤。

### 5.5 对象间差异

六种对象均表现为 C 快于 E，降幅为 3.3%–13.2%。瓶子和香蕉的差异较小，纸杯和剪刀较大，这可能与抓取姿态、变形风险和姿态稳定要求不同有关。由于各对象的匹配任务块数量有限，这里仅报告差异方向，不进一步解释其具体机制。

### 5.6 局限性与进一步工作

本研究仅包含三名操作者，135次试验来自同一批参与者的重复测量。三人均为右利手并使用左手操作Omega.7，模式顺序也只进行了部分平衡，因此结果主要适用于当前设备布置、训练条件和参与者样本。

视觉测试采用独立照片，但视角、背景、光照和对象实例受到控制。180/180的识别结果说明模型覆盖了本实验的视觉条件，不代表其在遮挡、杂乱背景、新实例或未知类别下仍有相同表现。误分类仍可能调用不适合当前对象的参数组。

参数组由硬件范围、任务要求和预实验确定，并非优化结果。C–E比较评价的是完整参数组相对于仅阻抗调度的整体差异，不能分离触觉接口和夹爪参数各自的贡献。现有日志也缺少阶段耗时、重新抓取和定量接触质量记录，因此停顿和失败结果主要用于辅助解释总体表现。

视觉推理没有进入名义200 Hz更新的同步调用路径，但周期日志仍存在长尾，本文不据此主张硬实时性能。策略更新与物理接触也没有同步时间戳，因此无法判断每次更新是否发生在接触前。

---

## 6 结论

本文提出了一种面向异质对象触觉遥操作的对象条件化跨通道参数配置方法。对象信息经由“对象语义—操作策略—联合参数组”三级映射，同时配置从端阻抗、主端触觉接口和夹爪执行参数，并通过异步的一次性更新机制接入遥操作系统。

在三名操作者、六种对象和五种模式组成的135次实机试验中，完整跨通道配置模式C获得了最短完成时间、最高的描述性成功率和最低Raw NASA-TLX。与采用相同语义映射和阻抗设置的模式E相比，C的平均完成时间缩短1.79 s，任务块Bootstrap 95% CI为[1.10, 2.51] s；三名操作者和六种对象均保持相同方向。主端轨迹长度没有出现明确差异，表明该时间优势不能简单归因于运动路径缩短。

结果表明，在当前异质对象遥操作任务中，同时配置从端机械响应、主端触觉接口和夹爪执行，获得了优于仅阻抗调度的系统级表现。本文验证的是完整参数组在当前平台和实验条件下的整体作用。更大规模的参与者实验可检验这一结果是否保持，通道级消融则可进一步区分触觉接口和夹爪参数的贡献。

---

## Supplementary material

**Supplementary Table S1.** Trial-level results for the 27 matched task blocks (135 trials). Each row lists task duration, master-side trajectory length, and outcome for modes A–E. S and F denote success and failure. The paired difference is $\Delta T=T_E-T_C$, so positive values indicate a shorter duration in C. Modes are shown in analytical rather than chronological order.

---

## 声明

- **伦理审批：** [投稿阻断项] 作者正在向所在学校或学院申请本研究的正式伦理批准、豁免或不适用判断；取得书面决定后，须在此填写机构名称、决定类型、日期和编号，不得自行宣称豁免。
- **知情同意：** 所有参与者在实验前均签署书面知情同意；相关文件由作者保存并可在期刊要求时提供。
- **图像与生成式 AI：** Fig. 1 为真实实验平台照片，未使用生成式 AI 增加、删除、替换或移动实验元素。Fig. 2–3 的投稿版本由作者使用 Python/Matplotlib 重绘，Fig. 4–7 由实验数据生成。生成式 AI 仅用于早期版式讨论；作者核验了最终图示逻辑、文字和数据映射。
- **生成式 AI 辅助声明：** During manuscript preparation, the authors used OpenAI Codex to assist with language editing, consistency checks, early layout discussion, and drafting Python/Matplotlib code. The authors subsequently reviewed and revised the text, redrew the submitted explanatory figures, verified all technical statements and plotted data, and take full responsibility for the manuscript.
- **资助：** 无。
- **利益冲突：** 作者声明无利益冲突。
- **数据可用性：** 去标识化试验数据可根据合理请求向通讯作者获取。

---

## 参考文献

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
