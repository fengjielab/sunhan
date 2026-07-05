# 视觉语义参数调度用于异质对象触觉遥操作抓取：多通道控制与五模式人在环验证

## Vision-Semantic Parameter Scheduling for Haptic Teleoperation in Heterogeneous Robotic Grasping

**作者：**【投稿前填写】  
**单位：**【投稿前填写】  
**通讯作者：**【投稿前填写】  

> **版本说明：**本版本为面向 *Industrial Robot* 的结构性修改稿，重点强化真实机器人系统、工程可部署性、多通道参数协同和五模式人在环消融验证。正式投稿前请删除本说明，并完成文末"投稿前核验清单"。

---

## Structured Abstract

**Purpose**  
Fixed teleoperation parameters are difficult to tune for heterogeneous objects with different fragility, stiffness and grasping requirements, while manual parameter selection increases the cognitive burden on the operator. This paper proposes a vision-semantic parameter scheduling method that uses object semantics as a contact-before control prior for haptic teleoperation.

**Design/methodology/approach**  
An RGB-D camera is used to identify the target object and map it into three manipulation attributes: soft/fragile, medium and rigid. Before contact, the system schedules a multi-channel parameter set including translational stiffness, rotational stiffness, damping ratio, master-side force feedback gain, force dead zone, gripper closing speed and grasping force. The method is implemented on a real Omega.7–Franka Panda–Franka Hand teleoperation platform. Three operators performed 135 grasping trials involving six objects and five modes: fixed parameters, manual strategy selection, vision-semantic multi-parameter scheduling, visual information only and vision-semantic impedance-only scheduling.

**Findings**  
Descriptive results show that the proposed vision-semantic multi-parameter mode achieved the shortest mean completion time, the highest success rate and the lowest Raw NASA-TLX score among the five modes. Friedman test revealed significant differences across five modes in completion time (χ²(4)=30.904, p<0.001) and Raw NASA-TLX (χ²(4)=36.000, p<0.001). Pairwise Wilcoxon tests with Holm correction showed that the proposed mode significantly outperformed all other four modes (all adjusted p<0.01, r>0.7). Compared with the impedance-only visual scheduling mode, the proposed mode reduced mean completion time, master trajectory length and Raw NASA-TLX by approximately 8.5%, 3.2% and 8.9%, respectively, with the completion time and TLX differences reaching statistical significance (p<0.001 and p=0.008). These results suggest that coordinating force feedback and gripper parameters in addition to impedance scheduling can provide additional benefits in the tested heterogeneous-object teleoperation tasks.

**Originality/value**  
The contribution of this work is not a new impedance equation, but a deployable and interpretable contact-before semantic scheduling framework for haptic teleoperation. The five-mode human-in-the-loop design separates the effects of visual information, manual selection, impedance-only scheduling and full multi-parameter coordination.

**Keywords:** haptic teleoperation; robot grasping; impedance control; vision semantics; force feedback; human-in-the-loop experiment

---

## 摘要

针对异质对象遥操作抓取中固定参数难以兼顾易损对象柔顺性、硬质对象定位稳定性和不同夹持需求的问题，本文提出一种视觉语义驱动的接触前多参数调度方法。系统利用RGB-D视觉识别目标对象类别，将其解释为轻拿轻放、中等和硬质三类操作属性，并在接触前协同调度从端平移/旋转刚度、阻尼比、主端力反馈增益、反馈死区、夹爪闭合速度和夹持力。该方法在Omega.7、Franka Panda、Franka Hand和RealSense D435i构成的真实触觉遥操作平台上实现。3名操作者针对苹果、香蕉、纸杯、瓶子、鼠标和剪刀6种对象，在固定参数、人工选择、视觉多参数、视觉仅观察和视觉仅阻抗五种模式下完成135次抓取实验。描述性结果显示，视觉多参数模式取得最短平均完成时间（19.28±1.30 s）、最高成功率（26/27, 96.3%）和最低Raw NASA-TLX（49.67±3.63）。Friedman检验表明五模式完成时间存在极显著差异（χ²(4)=30.904, p<0.001），配对Wilcoxon经Holm校正后视觉多参数模式显著优于其余四种模式（所有校正后p<0.01, 效应量r>0.7）。相较视觉仅阻抗模式，视觉多参数模式的完成时间、主端轨迹长度和Raw NASA-TLX分别降低约8.5%（p<0.001, r=0.71）、3.2%（p=0.149）和8.9%（p=0.008, r=0.89）。结果表明，在已测试异质对象范围内，接触前视觉语义可作为可解释的控制先验；相较仅调节阻抗，进一步协同力反馈与夹爪参数有助于提升任务效率和操作体验。

### 研究亮点

- 提出"视觉类别—操作属性—控制策略"的三级映射，把对象语义转化为接触前控制先验；
- 采用多通道参数协同，而非单一阻抗调节，同时覆盖从端阻抗、主端力反馈和夹爪执行参数；
- 在真实Omega.7–Panda触觉遥操作平台上完成五模式人在环实验；
- 通过"视觉仅观察"和"视觉仅阻抗"两个消融模式区分视觉提示、阻抗调节和完整多参数协同的作用；
- 以完成时间、成功率、主端轨迹、NASA-TLX和过程行为指标构建面向应用型机器人期刊的证据链。

---

## 1 引言

遥操作机器人能够把人的判断能力与机器人的远程执行能力结合起来，适用于柔性制造、危险环境作业、服务机器人和非结构化物体操作等场景。触觉遥操作进一步通过主端力反馈向操作者传递接触信息，有助于提高远程操作的可控性和沉浸感。对于真实抓取任务而言，操作者面对的对象往往具有不同的刚度、易损性、尺寸和夹持需求。若控制系统始终采用一组固定阻抗和固定夹爪参数，则难以同时满足易损对象的柔顺接触、硬质对象的稳定定位以及中等对象的效率要求。

阻抗控制通过规定机器人位移偏差、速度偏差与交互力之间的动态关系，为接触操作提供柔顺性[9]。固定阻抗实现简单、稳定性较易控制，但在异质对象抓取中需要在安全性、响应速度和定位稳定性之间折中。变阻抗控制能够根据接触力、轨迹误差或人的运动状态在线调节刚度和阻尼[10–12]，但这类方法通常依赖连续状态估计和接触后的反馈调节，也可能引入额外的稳定性约束和参数整定成本。对于类别可识别、任务流程相对固定但仍需操作者进行精细放置的遥操作抓取，接触发生前的对象语义可以作为一种低成本、可解释的任务先验。

已有视觉阻抗和共享控制研究表明，视觉信息、任务状态或操作者意图能够改善机器人操作效率[5,13,14]。然而，在异质对象触觉遥操作中，对象语义不仅影响从端机械臂应采用的柔顺性，也会影响操作者期望获得的力反馈强度、反馈死区、夹爪闭合速度和夹持力。若只显示视觉信息而不改变系统动力学，操作者仍需通过手动补偿完成任务；若只调节阻抗，则夹爪执行和力反馈通道仍可能限制抓取效率。因此，本文关注的问题是：**在真实触觉遥操作抓取中，接触前视觉语义驱动的多通道参数协同是否比固定参数、人工选择、视觉提示和仅阻抗调节更有效？**

本文提出一种视觉语义驱动的多参数调度方法。系统将目标对象映射为轻拿轻放、中等和硬质三类操作属性，并在接触前调用离散、可解释的参数策略，同时配置从端平移/旋转阻抗、主端力反馈和夹爪执行参数。本文的贡献如下：

1. **视觉语义—操作属性—控制策略三级映射。** 将对象类别转化为操作属性，并进一步转化为遥操作控制参数，使视觉信息以接触前控制先验的形式进入系统。
2. **多通道参数协同策略。** 不仅调节从端阻抗参数，还同步调节主端力反馈增益、反馈死区、夹爪闭合速度和夹持力，面向异质对象抓取形成完整操作策略。
3. **五模式人在环消融验证。** 在真实Omega.7–Panda遥操作平台上设置固定参数、人工选择、视觉多参数、视觉仅观察和视觉仅阻抗五种模式，区分视觉提示、人工选参、单一阻抗调节和完整多参数协同的作用。

本文不声称提出新的阻抗控制方程，也不把方法表述为在线自适应阻抗控制。本文的核心定位是：**一种低计算开销、可解释、可部署的接触前语义参数初始化方法**。

---

## 2 方法与系统实现

### 2.1 实验平台与系统架构

实验系统由Omega.7七自由度力反馈主端、Franka Panda七自由度机械臂、Franka Hand夹爪和Intel RealSense D435i相机构成。Omega.7采集主端位移与夹钳输入，并渲染从端接触反馈；Panda执行增量位置映射与笛卡尔阻抗控制；D435i采集RGB-D图像，视觉线程使用YOLO11n进行异步目标检测。主控制循环频率为200 Hz，视觉线程与控制线程解耦，避免低频视觉推理影响主从控制实时性。

【图1：系统实物图。建议标注Omega.7、Franka Panda、Franka Hand、D435i、对象区域和控制计算机。】

【图2：信息流图。建议包含主端输入、从端期望位姿、视觉检测、语义属性映射、策略锁定、阻抗控制、夹爪控制和主端力反馈。】

### 2.2 主从增量位置映射

主端相邻采样时刻的位置增量为

\[
\Delta\mathbf{x}_m(k)=\mathbf{x}_m(k)-\mathbf{x}_m(k-1).
\]

从端期望位置更新为

\[
\mathbf{x}_d(k)=\mathbf{x}_d(k-1)+S\mathbf{C}\Delta\mathbf{x}_m(k),
\]

其中，位置比例系数固定为\(S=3.0\)，\(\mathbf{C}=\mathrm{diag}(-1,-1,1)\)为坐标轴映射矩阵。本文不将位置比例作为视觉调度变量，以便把实验差异集中在阻抗、力反馈和夹爪参数上。

### 2.3 从端笛卡尔阻抗控制

从端采用笛卡尔阻抗控制，其等效关系表示为

\[
\mathbf{F}_c=\mathbf{K}(c)(\mathbf{x}_d-\mathbf{x})+
\mathbf{D}(c)(\dot{\mathbf{x}}_d-\dot{\mathbf{x}}),
\]

其中\(c\in\{soft,medium,hard\}\)为操作属性，\(\mathbf{K}(c)\)和\(\mathbf{D}(c)\)分别为对应刚度与阻尼矩阵。平移和旋转刚度写为

\[
\mathbf{K}(c)=\mathrm{diag}(K_t,K_t,K_t,K_r,K_r,K_r).
\]

阻尼依据阻尼比\(\zeta(c)\)配置。经典阻抗控制提供了柔顺交互的基本机理，本文的改进点不在阻抗方程本身，而在于利用接触前视觉语义对多通道控制参数进行任务相关初始化。

### 2.4 视觉语义多参数调度

视觉检测输出COCO类别后，通过固定映射转换为操作属性：苹果和香蕉映射为轻拿轻放类，水瓶和杯映射为中等类，鼠标和剪刀映射为硬质类。首次有效检测达到置信度阈值0.25后，系统锁定本次任务策略；若无有效类别或类别不可映射，则保持中等类默认参数作为安全回退。任务内锁定策略可避免检测抖动导致频繁切换。

完整策略定义为

\[
\Theta(c)=\{K_t,K_r,\zeta,K_f,d,v_g,F_g\},
\]

其中\(K_f\)为主端力反馈增益，\(d\)为反馈死区，\(v_g\)和\(F_g\)分别为夹爪闭合速度与夹持力设定。

| 属性 | \(K_t\)/(N/m) | \(K_r\)/(N·m/rad) | \(\zeta\) | \(K_f\) | \(d\)/N | \(v_g\)/(m/s) | \(F_g\)/N |
|---|---:|---:|---:|---:|---:|---:|---:|
| 轻拿轻放 | 50 | 5 | 0.8 | 0.2 | 0.3 | 0.02 | 8 |
| 中等 | 150 | 10 | 1.0 | 0.5 | 0.4 | 0.05 | 15 |
| 硬质 | 200 | 13 | 1.2 | 0.7 | 0.5 | 0.10 | 20 |

### 2.5 参数选择依据

参数选择遵循"对象属性—操作需求—控制响应"的工程逻辑。轻拿轻放类对象更关注柔顺接触和低夹持风险，因此采用较低平移/旋转刚度、较低力反馈增益、较小夹爪速度和较低夹持力。硬质类对象更关注定位稳定性和操作效率，因此采用较高刚度、更强力反馈和更快夹爪动作。中等类对象采用折中参数，以兼顾柔顺性、夹持稳定性和任务效率。上述参数由机器人接口安全范围、Omega.7力反馈舒适性、Franka Hand执行能力和预实验经验共同确定。本文验证的是离散语义策略在真实任务中的有效性，而非各参数的全局最优性。

正式投稿前，应以实际运行程序、控制日志和逐试次CSV为准核对表中参数。若历史说明文件与运行日志不一致，应以运行日志为准，并在数据可用性说明中公开参数表和分析脚本。

### 2.6 方法流程

**Algorithm 1: Vision-semantic multi-parameter scheduling**

1. 初始化系统，加载中等类默认参数\(\Theta(medium)\)；
2. 读取RGB-D图像并执行目标检测；
3. 若检测类别属于预定义对象集合且置信度高于阈值0.25，则将对象类别映射为操作属性\(c\)；
4. 根据操作属性调用参数组\(\Theta(c)=\{K_t,K_r,\zeta,K_f,d,v_g,F_g\}\)；
5. 锁定本次任务策略，避免任务过程中因视觉抖动造成频繁切换；
6. 将\(K_t,K_r,\zeta\)发送至从端阻抗控制器，将\(K_f,d\)用于主端力反馈渲染，将\(v_g,F_g\)用于夹爪控制；
7. 若检测失败或类别不可映射，则保持中等类默认参数；
8. 任务结束后复位系统，准备下一次试验。

### 2.7 安全回退与工程约束

视觉未锁定或检测结果不可映射时，系统使用中等类默认参数；任务内策略锁定避免检测抖动造成参数频繁跳变。机械臂自身碰撞检测、程序退出零力命令、统一初始姿态和操作者人工急停共同构成基础安全措施。正式投稿版本应补充碰撞阈值、急停方式、训练流程、知情同意和伦理审批/豁免信息。

---

## 3 实验设计

### 3.1 研究问题与假设

本文围绕以下研究问题展开：

- **RQ1:** 视觉语义多参数前馈是否优于固定参数、人工选择和视觉仅观察？
- **RQ2:** 完整多参数调度是否优于视觉语义仅阻抗调节？
- **RQ3:** 视觉识别与属性触发是否满足任务开始阶段的实时性和可靠性？
- **RQ4:** 方法收益是否在不同操作者和不同操作属性下保持一致？

相应假设为：与基线模式相比，视觉多参数模式能够降低完成时间和主端轨迹长度，提高成功率并降低主观负荷；相较视觉仅阻抗模式，完整多参数模式能够进一步减少无效操作、停顿或抓取修正，从而体现力反馈与夹爪参数协同的附加作用。

### 3.2 操作者与实验对象

3名操作者参与主实验。第1–3组、第4–6组和第7–9组分别对应操作者P01、P02和P03；每位操作者在每个"操作属性×模式"条件下完成3次重复。实验覆盖轻拿轻放、中等和硬质三类操作属性。

正式投稿版本需报告参与者年龄或年龄区间、性别、优势手、遥操作经验、训练时长、知情同意和伦理审批/豁免状态。若机构不要求正式伦理审批，也应在声明中说明豁免依据和参与者知情同意流程。

各实验目录中的`_experiment_objects.md`逐组保存了实验员、组次、对象名称和对象属性，因此135次试验均可追溯到具体对象类型。人在环实验共覆盖苹果、香蕉、纸杯、瓶子、鼠标和剪刀6种对象，并归入轻拿轻放、中等和硬质三类操作属性。每个组次中的具体对象均在A–E五种模式下测试，因而可同时进行对象属性层面和具体对象层面的配对分析。

| 操作属性 | 具体对象 | 组次数 | 五模式试次数 |
|---|---:|---:|---:|
| 轻拿轻放 | 苹果 | 4 | 20 |
| 轻拿轻放 | 香蕉 | 5 | 25 |
| 中等 | 纸杯 | 5 | 25 |
| 中等 | 瓶子 | 4 | 20 |
| 硬质 | 鼠标 | 5 | 25 |
| 硬质 | 剪刀 | 4 | 20 |

六种对象均由3名操作者覆盖，且每名操作者在每一属性下均接触到两种具体对象。该设计用于检验方法在六种已测试对象之间的一致性。本文将其表述为"跨已测试对象的一致性"或"对象集合内泛化证据"，不外推至未测试类别、未知对象或复杂遮挡场景。

### 3.3 实验模式

实验包括五种模式：

| 模式 | 设置 | 目的 |
|---|---|---|
| A | 固定参数，无视觉调度 | 固定控制基线 |
| B | 操作者人工选择完整策略 | 人工选参基线 |
| C | 视觉语义自动调度完整参数组 | 本文方法 |
| D | 显示视觉信息但保持固定参数 | 排除视觉提示本身的作用 |
| E | 视觉语义仅调度\(K_t,K_r,\zeta\) | 仅阻抗消融 |

A模式用于检验固定参数在异质对象上的折中局限；B模式用于检验人工选参是否会因额外判断和切换成本降低效率；D模式用于区分视觉提示与控制参数改变的作用；E模式用于检验单独调节阻抗是否足以复现完整多参数策略。C与E的比较是本文消融实验的核心，因为两者共享视觉语义和阻抗调节，差异仅在于C额外调节主端力反馈和夹爪参数。

五模式实验采用相同平台、操作者划分、对象属性、任务流程和重复结构，并在同一实验研究中完成。A–D四种模式构成108次试验，新增E模式包含27次试验，因此总规模为\(3\text{类}\times5\text{模式}\times9\text{组}=135\)次。正式投稿版本应补充模式顺序、对象顺序、休息时间、失败后的重复规则和超时阈值；若未随机化，应在局限性中明确学习效应和疲劳效应无法完全排除。

### 3.4 实验任务与流程

每次试验包括复位、接近、抓取、运输、释放和任务结束六个阶段。成功定义为在规定时间内完成抓取—转移—放置，且物体未掉落、明显滑移或发生可观察损伤。每次任务记录主端轨迹、夹钳输入、控制参数和任务持续时间；新版E模式日志额外记录视觉置信度、锁定事件和阶段信息。

【图3：实验流程图。建议展示复位、检测、策略锁定、接近、抓取、运输、释放和任务结束。】

### 3.5 评价指标

主要终点为完成时间。次要客观终点包括成功率、主端轨迹长度、停顿次数/时长、方向反转次数和运动平滑性。成功以逐试次评分表中的物体掉落、破损及任务完成情况判定。主观负荷采用未加权Raw NASA-TLX，即六个维度的算术平均；另将1–5分效率、操作负荷和抓取品质作为探索性主观指标，不与NASA-TLX混合。NASA-TLX按"操作者×对象属性×模式"采集六维评分，共形成45条记录。视觉模块报告类别识别正确率、属性触发正确率、置信度和单帧处理时间。

为避免结果导向的阈值选择，过程行为指标应在查看模式差异前冻结。建议采用以下定义并在正式分析脚本中固定：

- **停顿：**主端速度低于预设阈值且持续时间超过最短持续时间，例如速度<0.005 m/s且持续≥0.30 s；
- **方向反转：**滤波后速度符号发生变化，且反转前后有效位移均超过最小位移阈值，例如≥2 mm；
- **平滑性：**采用归一化jerk或log dimensionless jerk，并统一滤波频率、阶段截取和采样处理方式。

### 3.6 统计分析

实验采用与重复测量结构匹配的非参数分析。以"操作者×对象属性×组次"为匹配块（27个匹配块，对应3操作者×3属性×3组次），对A–E模式完成时间执行Friedman检验；总体显著后进行配对Wilcoxon符号秩检验，并采用Holm-Bonferroni方法校正多重比较（10对）。所有比较同时报告效应量r = Z/√N和Cohen's d，不仅报告P值。C–E聚焦配对分析，重点检验完整多参数调度相对仅阻抗调节的附加作用。Raw NASA-TLX采用相同非参数框架（9个匹配块，对应3操作者×3属性）。成功率以描述性报告为主。

分析结果表明：完成时间Friedman检验χ²(4)=30.904, p<0.001；配对Wilcoxon经Holm校正后，C模式（视觉多参数）显著优于A（p_adj=0.001, r=0.76）、B（p_adj<0.001, r=0.84）、D（p_adj=0.001, r=0.73）和E（p_adj=0.002, r=0.71），其余模式间两两无显著差异（所有校正后p>0.05）。C–E核心消融：完成时间均值差-1.79s（8.5%, p<0.001, r=0.71, d=0.94），Raw NASA-TLX均值差-4.87（8.9%, p=0.008, r=0.89）。NASA-TLX Friedman检验χ²(4)=36.000, p<0.001。

统计软件为Python 3.13 + SciPy 1.18.0；显著性阈值α=0.05（双尾）；无缺失值或异常值剔除。鉴于独立操作者数量为3名，本文不将135次试验视为135个独立参与者样本。统计解释应以配对结构、个体趋势、效应量和置信区间为主，主观负荷结论表述为真实平台上的初步人在环证据。

---

## 4 实验结果

### 4.1 视觉识别与属性触发验证

在受控视角、背景和光照下，6种对象各30幅图像，共180幅。类别识别和属性触发均为180/180，平均置信度0.853，单帧墙钟处理时间50.08 ms。该结果证明了受控实验条件下视觉触发的基础可靠性，但不外推至遮挡、强光变化、复杂背景、未知对象或未测试类别。

| 对象 | 图像数 | 类别正确率 | 属性触发正确率 | 平均置信度 | 时间/ms |
|---|---:|---:|---:|---:|---:|
| 苹果 | 30 | 100% | 100% | 0.771 | 56.66 |
| 香蕉 | 30 | 100% | 100% | 0.948 | 50.45 |
| 水瓶 | 30 | 100% | 100% | 0.726 | 49.71 |
| 杯 | 30 | 100% | 100% | 0.820 | 47.61 |
| 鼠标 | 30 | 100% | 100% | 0.914 | 46.79 |
| 剪刀 | 30 | 100% | 100% | 0.938 | 49.27 |

【图4：视觉混淆矩阵与置信度分布。建议同时保存原图、真值和逐图预测CSV，保证结果可审计。】

### 4.2 五模式实验结果

| 模式 | 完成时间/s | 主端轨迹/m | 成功率 | Raw TLX |
|---|---:|---:|---:|---:|
| A 固定参数 | 21.42±1.58 | 0.763±0.098 | 22/27 (81.5%) | 62.59±3.95 |
| B 人工选择 | 21.01±1.61 | 0.799±0.115 | 21/27 (77.8%) | 57.15±3.68 |
| C 视觉多参数 | **19.28±1.30** | **0.715±0.092** | **26/27 (96.3%)** | **49.67±3.63** |
| D 视觉仅观察 | 20.91±1.10 | 0.734±0.085 | 24/27 (88.9%) | 60.22±3.85 |
| E 视觉仅阻抗 | 21.07±1.56 | 0.739±0.084 | 24/27 (88.9%) | 54.54±4.09 |

描述性结果显示，C模式在五种模式中取得最短平均完成时间、最短主端轨迹、最高成功率和最低Raw NASA-TLX。C模式相较A、B、D和E的平均完成时间分别降低约10.0%、8.2%、7.8%和8.5%。C模式总体轨迹相较A、B、D和E分别减少约6.3%、10.5%、2.6%和3.2%。C模式Raw TLX较A、B、D和E分别降低约20.6%、13.1%、17.5%和8.9%。C模式的心理需求、体力需求、时间需求、绩效、努力和挫折六维均值分别为51.89、49.22、50.33、50.11、50.33和46.11，均低于其余模式。

Friedman检验表明五模式完成时间存在极显著差异（χ²(4)=30.904, p<0.001）。配对Wilcoxon检验经Holm校正后，C模式完成时间显著优于A（p_adj=0.001, r=0.76）、B（p_adj<0.001, r=0.84）、D（p_adj=0.001, r=0.73）和E（p_adj=0.002, r=0.71），其余模式间两两无显著差异（所有校正后p>0.05）。Raw NASA-TLX的Friedman检验同样显示五模式间极显著差异（χ²(4)=36.000, p<0.001）。

正式结果图建议采用配对散点图或雨云图展示每个匹配块在五模式下的变化，而不仅报告均值表。

### 4.3 多参数与仅阻抗消融比较

| 模式 | 完成时间/s | 主端轨迹/m | 成功率 | Raw NASA-TLX |
|---|---:|---:|---:|---:|
| C 视觉多参数 | **19.28±1.30** | **0.715±0.092** | **26/27 (96.3%)** | **49.67±3.63** |
| E 视觉仅阻抗 | 21.07±1.56 | 0.739±0.084 | 24/27 (88.9%) | 54.54±4.09 |

C–E比较是本文最关键的消融。配对Wilcoxon检验表明，C模式完成时间显著低于E模式（均值差=-1.79s, 相对降幅8.5%, W=35.0, p<0.001, 效应量r=0.71, Cohen's d=0.94）。Raw NASA-TLX同样显著降低（均值差=-4.87, 相对降幅8.9%, p=0.008, r=0.89）。主端轨迹差异不显著（p=0.149, r=0.28），提示时间收益主要来自操作效率提升而非路径缩短。

分属性看，C在轻拿轻放类（19.38 vs 20.77s, p=0.038, r=0.69）、中等类（19.11 vs 20.78s, p=0.028, r=0.73）和硬质类（19.35 vs 21.66s, p=0.051, r=0.65）均表现出方向一致的时间优势。这说明仅改变阻抗并未复现完整多参数策略的总体效率；额外的力反馈和夹爪执行参数可能减少了抓取、运输或释放阶段的操作修正。

需要注意的是，C相较E的时间收益明显大于轨迹长度收益。这提示多参数协同的附加价值可能并非主要来自几何路径缩短，而是来自更少停顿、更少方向反转、更快夹爪闭合、更少重抓或更稳定的运输阶段。正式投稿版本应补充停顿/反转/抓取阶段耗时等过程指标，以支撑该机制解释。

### 4.4 操作行为与跨操作者一致性

三名操作者在主实验中均表现出C模式完成时间最短的一致趋势。P01（C: 18.94s vs E: 20.60s, 差1.66s, p=0.066）、P02（19.09s vs 21.66s, 差2.57s, p=0.008）、P03（19.80s vs 20.95s, 差1.15s, p=0.051）。P02的C–E差异在统计上显著，P01和P03的趋势方向一致。轨迹收益方面，P01与P03在C模式下轨迹更短，而P02的E模式平均轨迹更短，存在操作者差异。

当前旧日志中的最大速度和速度标准差存在离散微分尖峰，且新旧日志的统计区间不同，因此不直接用于跨模式结论。正式版本应在统一重算、滤波和任务阶段截取后报告停顿、方向反转和平滑性，并用个体趋势图展示P01–P03是否存在一致方向。

【图5：完成时间、主端轨迹、成功率和Raw NASA-TLX的五模式对比图。】

【图6：C–E消融的过程指标图，建议包括停顿时长、方向反转次数、抓取阶段耗时和失败案例。】

---

## 5 讨论

### 5.1 视觉语义前馈为何改善遥操作表现

固定参数模式必须用单一折中参数覆盖三类对象，因此难以同时满足易损对象的柔顺性和硬质对象的定位稳定性。人工选择模式虽然能够调用不同策略，但会增加操作者判断和切换步骤。视觉仅观察模式改善了场景信息，却没有改变系统动力学和夹爪行为。视觉多参数模式则利用对象语义在接触前完成策略初始化，使操作者不必在任务过程中持续补偿不合适的手感或夹爪行为。这一机制与C模式较短完成时间、较高成功率和较低Raw NASA-TLX的描述性结果一致。

### 5.2 多参数协同相对仅阻抗调节的意义

C与E均根据视觉语义调整平移刚度、旋转刚度和阻尼比，因此两者共享柔顺性适配机制。C额外调节力反馈增益、反馈死区、夹爪闭合速度和夹持力。当前数据中，C相较E的平均完成时间降低约8.5%（配对Wilcoxon, p<0.001, r=0.71），而主端轨迹长度降低约3.2%（p=0.149, 未达显著），说明附加收益可能更多来自抓取、运输或释放阶段的时间效率，而不是大幅改变几何路径。

这一结果对应用型遥操作系统具有工程意义：在异质对象任务中，操作者感受到的不仅是机械臂末端柔顺性，还包括主端反馈强度、反馈死区和夹爪执行速度。单独调节阻抗可能无法覆盖抓取过程中的全部操作需求。多通道参数协同能够把"对象语义"转化为更完整的操作手感和执行策略。正式版本仍需通过停顿、反转、重抓和夹爪过程指标进一步验证该解释。

### 5.3 与相关研究的区别

已有任务分解和共享控制研究通过根据子任务切换控制方式、约束输入空间或提供引导，提高完成效率并降低NASA-TLX[6,14]。视觉阻抗研究则从特征空间统一视觉与力控制[13]。本文区别在于：不进行连续视觉伺服，不依赖在线轨迹规划，也不声称接触后的自适应最优控制，而是把对象语义作为接触前任务先验，以低计算开销调用可解释的多参数策略。这一定位适合类别可识别、环境相对结构化、但仍需要操作者完成精细抓取与放置的工程遥操作场景。

### 5.4 面向Industrial Robot的应用价值

从工业机器人应用角度看，本文方法具有三个现实优点。第一，系统基于现有RGB-D相机、力反馈主端、Franka机械臂和夹爪实现，不依赖额外接触传感器或复杂在线优化。第二，策略表由对象属性直接解释，便于工程人员检查和调整。第三，任务内策略锁定和默认安全参数降低了视觉抖动对控制稳定性的影响。因此，该方法更适合作为半结构化场景中的人机协同遥操作辅助模块，而非完全自主抓取算法。

### 5.5 局限性

1. 独立操作者仅3名，135次重复任务不能替代更大参与者样本；主观负荷和跨操作者结论应视为真实平台上的初步人在环证据。
2. 人在环实验覆盖六种具体对象，每类两种对象的组次数为4/5组，属于近似平衡而非完全平衡设计；结果支持六种已测试对象之间的一致性，尚不能外推到未见对象。
3. 当前正式数据未结构化记录五模式随机执行顺序，学习效应和疲劳效应不能完全排除。
4. 独立视觉验证来自受控视角、背景和光照条件，100%正确率不能外推至遮挡、复杂背景和未知对象。
5. 部分旧日志未完整保存逐次视觉标签、置信度和策略锁定事件，限制了对视觉触发失败的回溯分析。
6. 现有数据未提供经独立传感器校准的接触力和物体损伤量，因此不能把"保护易损对象"表述为已被直接证明的结论。
7. 参数由机理、工程经验、安全范围和预实验确定，本文证明的是离散语义策略的任务有效性，而非参数全局最优性。

---

## 6 结论

本文提出一种面向异质对象遥操作抓取的视觉语义多参数调度方法。该方法将对象类别解释为轻拿轻放、中等和硬质三类操作属性，并在接触前协同配置从端阻抗、主端力反馈和夹爪执行参数。真实平台五模式实验的描述性结果显示，视觉多参数模式在当前样本中取得最短平均完成时间（19.28±1.30 s）、最高成功率（96.3%）和最低Raw NASA-TLX（49.67±3.63）。Friedman检验表明五模式完成时间存在极显著差异（χ²(4)=30.904, p<0.001），配对Wilcoxon经Holm校正后C模式显著优于A/B/D/E（所有校正后p<0.01, r>0.7）。与视觉仅阻抗模式相比，完整多参数模式平均完成时间降低约8.5%（p<0.001, r=0.71），主端轨迹减少约3.2%（p=0.149），Raw NASA-TLX降低约8.9%（p=0.008, r=0.89），提示力反馈和夹爪参数协同可能带来阻抗调节之外的附加收益。

总体而言，本文为无需复杂在线优化的异质对象触觉遥操作提供了一种可解释、低成本、可部署的接触前参数初始化方案。其统计普适性和外部泛化能力仍需通过更多操作者、随机化模式顺序、对象实例级记录、过程行为指标和接触质量指标进一步验证。

---

## Declarations（投稿前补齐）

- **Ethical approval:** 【填写伦理审批编号；若豁免，说明豁免机构和依据】
- **Informed consent:** 【填写参与者知情同意情况】
- **Funding:** 【填写基金项目；无则写 Not applicable】
- **Conflict of interest:** The authors declare that they have no conflict of interest. 【投稿前核对】
- **Data availability:** 【建议公开脱敏后的逐试次数据、统计脚本、视觉逐图预测表和参数表】
- **Author contributions:** 【按CRediT分类填写】

---

## 参考文献（初稿，投稿前需按期刊格式统一）

1. Lawrence DA. Stability and transparency in bilateral teleoperation. *IEEE Transactions on Robotics and Automation*. 1993;9(5):624–637.
2. Niemeyer G, Slotine JJE. Stable adaptive teleoperation. *IEEE Journal of Oceanic Engineering*. 1991;16(1):152–162.
3. Passenberg C, Peer A, Buss M. A survey of environment-, operator-, and task-adapted controllers for teleoperation systems. *Mechatronics*. 2010;20(7):787–801.
4. Losey DP, McDonald CG, Battaglia E, O'Malley MK. A review of intent detection, arbitration, and communication aspects of shared control for physical human–robot interaction. *Applied Mechanics Reviews*. 2018;70(1):010804.
5. Bowman M, Zhang J, Zhang X. Intent-based task-oriented shared control for intuitive telemanipulation. *Journal of Intelligent & Robotic Systems*. 2024;110:167. https://doi.org/10.1007/s10846-024-02185-1
6. Han J, Yang G-H. Improving teleoperator efficiency using position–rate hybrid controllers and task decomposition. *Applied Sciences*. 2022;12(19):9672. https://doi.org/10.3390/app12199672
7. Huang K, Chitrakar D, Rydén F, Chizeck HJ. Evaluation of haptic guidance virtual fixtures and 3D visualization methods in telemanipulation—a user study. *Intelligent Service Robotics*. 2019;12:289–301. https://doi.org/10.1007/s11370-019-00283-w
8. 【待核对作者】Investigating haptic feedback in vision-deficient millirobot telemanipulation. 2024. 【待补正式期刊、卷期、DOI】
9. Hogan N. Impedance control: An approach to manipulation. *Journal of Dynamic Systems, Measurement, and Control*. 1985;107(1):1–24.
10. Kronander K, Billard A. Stability considerations for variable impedance control. *IEEE Transactions on Robotics*. 2016;32(5):1298–1305.
11. Abu-Dakka FJ, Rozo L, Caldwell DG. Force-based variable impedance learning for robotic manipulation. *Robotics and Autonomous Systems*. 2018;109:156–167.
12. Duan J, Gan Y, Chen M, et al. Adaptive variable impedance control for dynamic contact force tracking in uncertain environment. *Robotics and Autonomous Systems*. 2018;102:54–65.
13. Oliva AA, Giordano PR, Chaumette F. A general visual-impedance framework for effectively combining vision and force sensing in feature space. *IEEE Robotics and Automation Letters*. 2021;6(3):4441–4448.
14. Peternel L, Tsagarakis N, Ajoudani A. Towards multi-modal intention interfaces for human–robot co-manipulation. In: *IEEE/RSJ International Conference on Intelligent Robots and Systems*. 2016:2663–2669.
15. Haddadin S, Parusel S, Johannsmeier L, et al. The Franka Emika robot: A reference platform for robotics research and education. *IEEE Robotics & Automation Magazine*. 2022;29(2):46–64.
16. Hart SG, Staveland LE. Development of NASA-TLX. In: Hancock PA, Meshkati N, editors. *Human Mental Workload*. Amsterdam: North-Holland; 1988:139–183.
17. 【待补近5年文献】视觉语义辅助遥操作/共享控制论文3–5篇。
18. 【待补近5年文献】可变阻抗与多参数协同控制论文3–5篇。

---

## 投稿前核验清单

- [ ] 删除本文开头"版本说明"和所有内部提醒；
- [ ] 核对参数表与实际运行程序、逐试次CSV完全一致；
- [ ] 补齐参与者年龄/性别/优势手/经验/训练时长；
- [ ] 补齐知情同意和伦理审批/豁免说明；
- [ ] 冻结停顿、方向反转和平滑性定义，并重算全部135次原始轨迹；
- [x] 完成A–E重复测量总体检验、Holm校正事后比较、效应量与95%CI；
- [x] 完成C–E配对分析，重点报告完成时间、轨迹、NASA-TLX；
- [ ] 补充C–E停顿、反转、抓取阶段耗时过程指标；
- [ ] 补失败案例分析，说明失败发生在夹取、运输、释放还是识别阶段；
- [ ] 将对象名称合并到135行试次级分析表，补充六对象分层统计与"模式×对象"配对图；
- [ ] 恢复/归档180幅原图、真值和逐图预测CSV；
- [ ] 绘制系统图、信息流图、实验流程图、五模式结果图、C–E消融图和视觉混淆矩阵；
- [ ] 补近5年Industrial Robot/Robotica/RA-L/RAS相关文献；
- [ ] 按 *Industrial Robot* 结构化摘要、关键词、图表和参考文献格式统一全文。