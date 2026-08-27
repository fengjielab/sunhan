# Multi-channel vision-semantic parameter scheduling for haptic teleoperation of heterogeneous object grasping

## Structured Abstract

**Purpose**  
Fixed teleoperation parameters are difficult to tune for heterogeneous objects with different fragility, stiffness and grasping requirements. This paper proposes a multi-channel vision-semantic parameter scheduling method that establishes a three-level mapping from vision semantics to operation-oriented strategies and control parameters, using pre-contact object semantics as an interpretable control prior for haptic teleoperation.

**Design/methodology/approach**  
An RGB-D camera identifies the target object and maps it to one of three operation-oriented policies: fragility-oriented, balanced and stability-oriented. Before contact, the system schedules slave-side translational/rotational stiffness, damping ratio, master-side force-feedback gain, force dead zone, gripper speed and grasping force. The method is implemented on a real Omega.7–Franka Panda–Franka Hand platform. Three operators performed 135 grasping trials involving six objects and five modes: fixed parameters, manual selection, full vision-semantic multi-parameter scheduling, visual information only and vision-semantic impedance-only scheduling.

**Findings**  
In the tested platform and participants, the proposed mode achieved the shortest mean completion time, the highest success rate as a descriptive metric and the lowest Raw NASA-TLX score. Compared with impedance-only scheduling, the proposed mode reduced mean completion time from 21.07 s to 19.28 s, while all three operators and all six tested objects showed the same directional trend. The trajectory-length difference was smaller, suggesting that the benefit mainly came from fewer pauses and operation corrections rather than a shorter geometric path.

**Originality**  
The originality lies in a deployable system-level bridge between high-level object semantics and low-level teleoperation interface parameters, rather than in a new impedance equation or a closed-loop force-feedback method. The proposed three-level mapping coordinates slave-side impedance, pre-contact haptic-interface settings and gripper execution parameters, while the five-mode design separates visual information, manual selection, impedance-only scheduling and full multi-channel pre-contact coordination.

**Keywords:** haptic teleoperation; robot grasping; impedance control; vision semantics; force feedback; human-in-the-loop experiment

---

## 摘要

针对异质对象遥操作抓取中固定控制参数难以同时兼顾易损对象柔顺接触、硬质对象稳定定位和不同夹持需求的问题，本文提出一种视觉语义驱动的多通道接触前参数调度方法。系统利用RGB-D相机识别目标对象类别，将其映射为易损优先、折中和稳定优先三类操作策略，并在接触前协同配置从端平移/旋转刚度、阻尼比、主端力反馈增益、反馈死区、夹爪闭合速度和夹持力。该方法在Omega.7、Franka Panda和Franka Hand构成的真实触觉遥操作平台上实现。3名操作者围绕苹果、香蕉、纸杯、瓶子、鼠标和剪刀6种对象完成135次五模式抓取实验。结果显示，在当前平台和参与者范围内，视觉多参数模式取得最短平均完成时间（19.28±1.30 s）、最高成功率（作为描述性指标，26/27，96.3%）和最低Raw NASA-TLX（49.67±3.63）。相较视觉仅阻抗模式，视觉多参数模式平均完成时间由21.07 s降至19.28 s，且3名操作者和6种已测试对象均表现出一致方向。主端轨迹长度差异较小，提示多通道协同的收益更可能来自停顿和操作修正减少，而非几何路径显著缩短。本文不声称提出新的阻抗控制方程，也不把力反馈闭环建模或力觉透明性验证作为本篇贡献，而是提供一种低计算开销、可解释、可部署的接触前语义参数初始化方案。

---

## 1 引言

遥操作机器人能够把人的判断能力与机器人的远程执行能力结合起来，适用于柔性制造、危险环境作业、服务机器人以及非结构化物体操作等场景。触觉遥操作进一步通过主端力反馈向操作者传递远程接触信息，有助于提高操作者对抓取、接触和滑移风险的感知。对于真实抓取任务而言，操作者面对的对象往往具有不同的形状、表面、易损性和夹持需求。若系统始终采用一组固定阻抗和固定夹爪参数，则必须在柔顺接触、响应速度、定位稳定性和夹持可靠性之间折中。

从工业机器人应用角度看，这类问题并不限于实验室桌面抓取。远程维护、危险品处理、柔性分拣、非结构化拆解和人监督机器人操作中也经常出现类似需求：系统需要在不完全结构化的环境中处理易损件、易滑件、硬质工具、轻质容器或几何不规则对象。本文所选苹果、香蕉、纸杯、瓶子、鼠标和剪刀并不声称覆盖完整工业对象集，而是作为桌面代理对象，用于复现异质抓取中常见的操作风险，包括柔顺接触、稳定夹持、滑移风险和姿态定位需求。

阻抗控制通过规定机器人位移偏差、速度偏差与交互力之间的动态关系，为接触操作提供柔顺性[9]。固定阻抗实现简单，工程上较易部署，但在异质对象抓取中难以同时适配易损对象、轻质对象和硬质对象。变阻抗控制能够根据接触力、轨迹误差、任务阶段或人的运动状态在线调节刚度和阻尼[10–13]。然而，在线变阻抗通常依赖连续状态估计、接触后反馈和稳定性约束。对于类别可识别、任务流程相对固定但仍需操作者完成精细抓取与放置的遥操作任务，接触发生前的对象语义可以作为一种低成本、可解释的任务先验。

已有视觉阻抗、共享控制和触觉引导研究表明，视觉信息、任务状态或操作者意图可用于改善远程操作效率和交互体验[5–8,14,15]。但是，在异质对象触觉遥操作中，对象语义不仅影响从端机械臂的柔顺性，还影响操作者期望获得的主端力反馈强度、反馈死区、夹爪闭合速度和夹持力。只显示视觉信息而不改变系统动力学时，操作者仍需通过手动补偿完成任务；只调节阻抗而保留默认力反馈和夹爪参数时，抓取和运输阶段仍可能受到夹爪执行与触觉反馈通道限制。因此，本文关注的问题是：在真实触觉遥操作抓取中，接触前视觉语义驱动的多通道参数协同是否比固定参数、人工选择、视觉提示和仅阻抗调节更有效？

本文提出一种视觉语义驱动的多通道参数调度方法。系统将目标对象映射为三类操作策略，并在接触前调用离散、可解释的参数表，同时配置从端阻抗、主端基础反馈接口参数和夹爪执行参数。本文贡献如下：

1. **视觉语义—操作策略—控制参数三级映射（three-level mapping: vision semantics–operation strategy–control parameters）。** 将目标对象类别转化为易损优先、折中和稳定优先三类操作策略，使视觉信息以接触前控制先验的形式进入遥操作系统。
2. **多通道接触前参数协同。** 不仅调节从端平移/旋转刚度和阻尼比，还同步设置主端基础反馈接口增益、反馈死区、夹爪闭合速度和夹持力。本文不把力反馈闭环建模、接触力估计或力觉透明性验证作为本篇贡献。
3. **五模式人在环消融验证。** 在真实Omega.7–Panda平台上设置固定参数、人工选择、视觉多参数、视觉仅观察和视觉仅阻抗五种模式，区分视觉提示、人工选参、仅阻抗调节和完整多通道协同的作用。

不同于侧重新阻抗方程推导或接触后在线自适应控制的研究，本文的创新在于提供一种系统级接触前参数调度范式，将高层对象语义感知与底层遥操作接口参数连接起来。本文中的力反馈增益和死区只作为接触前策略表中的基础接口参数使用，不作为力反馈闭环或力觉透明性研究的独立贡献。本文的核心定位是：一种低计算开销、可解释、可部署的接触前语义参数初始化方法。

---

## 2 方法与系统实现

### 2.1 实验平台与系统架构

实验系统由Omega.7七自由度力反馈主端、Franka Panda七自由度机械臂、Franka Hand夹爪和Intel RealSense D435i相机构成。Omega.7采集主端位移与夹钳输入，并渲染从端接触反馈；Panda执行增量位置映射和笛卡尔阻抗控制；D435i采集RGB-D图像，视觉线程使用YOLO11n进行异步目标检测。主控制循环频率为200 Hz，视觉线程与控制线程解耦，以避免低频视觉推理影响主从控制实时性。

**图1.** 触觉遥操作实验平台示意图，标注Omega.7、Franka Panda、Franka Hand、RealSense D435i、目标物体区和控制计算机。

**图2.** 系统信息流图，包含主端输入、增量位置映射、视觉识别、异步缓冲区、操作策略锁定、参数调度、阻抗控制、夹爪控制和基础反馈接口。图中应区分低频视觉线程与200 Hz主控制线程。

### 2.2 主从增量位置映射

主端相邻采样时刻的位置增量为

\[
\Delta\mathbf{x}_m(k)=\mathbf{x}_m(k)-\mathbf{x}_m(k-1).
\]

从端期望位置更新为

\[
\mathbf{x}_d(k)=\mathbf{x}_d(k-1)+S\mathbf{C}\Delta\mathbf{x}_m(k),
\]

其中，位置比例系数固定为\(S=3.0\)，\(\mathbf{C}=\mathrm{diag}(-1,-1,1)\)为坐标映射矩阵。本文不将位置比例作为视觉调度变量，以便把实验差异集中在阻抗、基础反馈接口和夹爪参数上。

### 2.3 从端笛卡尔阻抗控制

从端采用笛卡尔阻抗控制，其等效关系表示为

\[
\mathbf{F}_c=\mathbf{K}(c)(\mathbf{x}_d-\mathbf{x})+\mathbf{D}(c)(\dot{\mathbf{x}}_d-\dot{\mathbf{x}}),
\]

其中\(c\)为操作策略类别，\(\mathbf{K}(c)\)和\(\mathbf{D}(c)\)分别为对应刚度与阻尼矩阵。平移和旋转刚度写为

\[
\mathbf{K}(c)=\mathrm{diag}(K_t,K_t,K_t,K_r,K_r,K_r).
\]

阻尼依据阻尼比\(\zeta(c)\)配置。经典阻抗控制提供柔顺交互的基本机理，本文改进点不在阻抗方程本身，而在于利用接触前对象语义对多通道控制参数进行任务相关初始化。

### 2.4 视觉语义多通道参数调度

视觉检测输出目标类别后，系统将类别映射为三类**操作策略**而非严格材料类别：易损优先策略、折中策略和稳定优先策略。苹果和香蕉映射为易损优先策略，纸杯和瓶子映射为折中策略，鼠标和剪刀映射为稳定优先策略。该映射依据的是本实验任务中的操作风险与夹持需求，而不是材料刚度的通用物理分类。首次有效检测达到置信度阈值0.25后，系统锁定本次任务策略；若无有效类别或类别不可映射，则保持折中策略默认参数作为安全回退。任务内策略锁定用于避免检测抖动导致频繁切换。

完整策略定义为

\[
\Theta(c)=\{K_t,K_r,\zeta,K_f,d,v_g,F_g\},
\]

其中\(K_f\)为主端基础反馈接口增益，\(d\)为反馈死区，\(v_g\)和\(F_g\)分别为夹爪闭合速度与夹持力设定。

| 操作策略 | 对应对象 | \(K_t\)/(N/m) | \(K_r\)/(N·m/rad) | \(\zeta\) | \(K_f\) | \(d\)/N | \(v_g\)/(m/s) | \(F_g\)/N |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 易损优先 | 苹果、香蕉 | 50 | 5 | 0.8 | 0.2 | 0.3 | 0.02 | 8 |
| 折中 | 纸杯、瓶子 | 150 | 10 | 1.0 | 0.5 | 0.4 | 0.05 | 15 |
| 稳定优先 | 鼠标、剪刀 | 200 | 13 | 1.2 | 0.7 | 0.5 | 0.10 | 20 |

### 2.5 主端反馈接口参数的使用边界

Omega.7具备主端力反馈能力，本文也将\(K_f\)和\(d\)纳入接触前策略表。然而，本文只把二者作为遥操作接口的预设参数，而不把力反馈闭环作为独立研究对象。换言之，本文不研究接触后外力估计的精度、力觉透明性、力反馈稳定性、力反馈有无对比，也不引入力反馈驱动的在线阻抗自适应。本文的实验只能支持“完整接触前多参数策略优于仅阻抗调节”这一整体结论，不能单独证明力反馈参数或夹爪参数的独立因果贡献。接触后外力估计、力反馈闭环修正及力觉感知验证将作为后续研究单独展开。

### 2.6 参数选择依据与预实验

参数选择遵循“对象操作风险—控制响应—硬件约束”的工程逻辑。易损优先策略采用较低平移/旋转刚度、较低基础反馈接口增益、较低夹爪速度和较低夹持力，以降低对易损或表面易滑对象的冲击和挤压风险。稳定优先策略采用较高刚度、较强的基础反馈接口增益和更快夹爪动作，以提高硬质对象的定位稳定性和操作效率。折中策略用于夹持需求介于两者之间的对象。

参数范围由Franka控制接口、Omega.7反馈接口舒适性、Franka Hand执行能力和预实验共同约束。预实验由两名研究人员在正式实验前完成，覆盖三类对象的抓取操作，用于排除明显不安全、明显低效或操作者主观不可接受的参数组合。正式实验前参数表被冻结，并对所有操作者和所有正式试次保持一致。B模式使用相同参数表，但由操作者手动选择策略。因此，B模式在本文中被定义为**人工选参工作流基线**，而不是纯粹的自动/手动控制器性能对比。人工选择时间计入B模式总完成时间，因此B模式用于评价包含人工判断与切换成本的实际工作流，而不作为纯控制器执行时间基线。

### 2.7 方法流程

**Algorithm 1: Vision-semantic multi-channel parameter scheduling**

1. 初始化系统，加载折中策略默认参数\(\Theta(balanced)\)；
2. 读取RGB-D图像并执行目标检测；
3. 若检测类别属于预定义对象集合且置信度不低于0.25，则将对象类别映射为操作策略\(c\)；
4. 根据操作策略调用参数组\(\Theta(c)=\{K_t,K_r,\zeta,K_f,d,v_g,F_g\}\)；
5. 锁定本次任务策略，避免任务过程中因视觉抖动频繁切换；
6. 将\(K_t,K_r,\zeta\)发送至从端阻抗控制器，将\(K_f,d\)作为主端基础反馈接口参数，将\(v_g,F_g\)用于夹爪控制；
7. 若检测失败或类别不可映射，则保持折中策略默认参数；
8. 任务结束后复位系统，准备下一次试验。

### 2.8 安全回退与工程约束

视觉未锁定或检测结果不可映射时，系统使用折中策略默认参数。任务内策略锁定避免视觉抖动造成参数频繁跳变。机械臂自身碰撞检测、程序退出零力命令、统一初始姿态和操作者人工急停共同构成基础安全措施。本文主要关注接触前参数初始化，不讨论接触后在线最优调参。

---

## 3 实验设计

### 3.1 研究问题与假设

本文围绕以下问题展开：

- **RQ1:** 视觉语义多参数前馈是否优于固定参数、人工选择和视觉仅观察？
- **RQ2:** 完整多通道调度是否优于视觉语义仅阻抗调节？
- **RQ3:** 视觉识别与属性触发是否满足任务开始阶段的实时性和基础可靠性？
- **RQ4:** 方法收益是否在不同操作者和不同已测试对象之间表现出一致方向？

相应假设为：与基线模式相比，视觉多参数模式能够降低完成时间和主端轨迹长度，提高成功率（作为描述性指标）并降低主观负荷；相较视觉仅阻抗模式，完整多通道模式能够减少停顿或操作修正，从而体现完整接触前参数策略相对于仅阻抗调节的整体附加作用。

### 3.2 操作者与实验对象

3名操作者（P01–P03，23–24岁男性，右利手）参与主实验。三名操作者均具有基础遥操作训练经验，并在每次正式实验前完成10–15分钟训练试次。所有操作者均签署知情同意书。本研究不涉及医学干预，也不采集可识别个人身份的信息。

实验覆盖苹果、香蕉、纸杯、瓶子、鼠标和剪刀6种对象，并归入易损优先、折中和稳定优先三类操作策略。该分类用于本实验任务中的参数调度，不声称代表对象材料属性的普适物理分类。

| 对象 | 操作策略 | 质量/g | 表面特性 | 尺寸/mm | 任务中主要操作风险 |
|:---:|:---:|---:|:---|:---|:---|
| 苹果 | 易损优先 | ~200 | 光滑 | Ø70–80 | 碰撞/滑移风险，需轻柔接触 |
| 香蕉 | 易损优先 | ~120 | 光滑 | 20×180 | 挤压变形与滑移风险 |
| 纸杯 | 折中 | ~5 | 纸质 | Ø75×90 | 易变形，但任务中需保持夹持稳定 |
| 瓶子 | 折中 | ~30 | 光滑塑料 | Ø65×200 | 易滑移，需兼顾效率与稳定 |
| 鼠标 | 稳定优先 | ~100 | 光滑塑料 | 65×120×35 | 硬质、不规则曲面，运输中易滑移 |
| 剪刀 | 稳定优先 | ~150 | 金属+塑料 | 50×170×15 | 硬质、细长、姿态定位要求较高 |

### 3.3 实验模式与试验结构

实验包括五种模式：

| 模式 | 设置 | 目的 |
|:---:|:---|:---|
| A | 固定参数，无视觉调度 | 固定控制基线 |
| B | 操作者人工选择完整参数策略 | 人工选参工作流基线 |
| C | 视觉语义自动调度完整参数组 | 本文方法 |
| D | 显示视觉信息但保持固定参数 | 排除视觉提示本身的作用 |
| E | 视觉语义仅调度\(K_t,K_r,\zeta\) | 仅阻抗消融 |

A模式用于检验固定参数在异质对象上的折中局限；B模式用于检验人工选参工作流是否会引入额外判断与切换负担；D模式用于区分视觉提示与控制参数改变的作用；E模式用于检验单独调节阻抗是否足以复现完整多通道策略。C与E的比较是本文核心消融，因为两者共享视觉语义和阻抗调节，差异在于C额外设置主端基础反馈接口参数和夹爪执行参数。本文不在该比较中分离力反馈接口参数与夹爪参数的独立贡献。

试验结构以27个匹配块为基本单位。每个匹配块由同一操作者、同一对象/操作策略和同一重复编号下的A–E五个模式组成，因此总试次数为\(27\times5=135\)。六种对象在27个匹配块中的分布如下：

| 操作策略 | 具体对象 | 匹配块数 | 五模式试次数 |
|---|---|---:|---:|
| 易损优先 | 苹果 | 4 | 20 |
| 易损优先 | 香蕉 | 5 | 25 |
| 折中 | 纸杯 | 5 | 25 |
| 折中 | 瓶子 | 4 | 20 |
| 稳定优先 | 鼠标 | 5 | 25 |
| 稳定优先 | 剪刀 | 4 | 20 |
| 合计 | 六种对象 | 27 | 135 |

模式顺序在实验中进行了部分平衡，以降低单一固定顺序造成的学习或疲劳偏差。由于未执行严格完全随机化，也未将所有对象、操作者和顺序因素完全解耦，本文不将顺序效应视为已完全排除，而是在局限性中保守解释。完整的逐试次执行顺序作为补充材料提供。

### 3.4 实验任务与流程

每次试验包括复位、接近、抓取、运输、释放和任务结束六个阶段。成功定义为在规定时间内完成抓取—转移—放置，且物体未掉落、未发生明显滑移或可观察损伤。每次任务记录主端轨迹、夹钳输入、控制参数和任务持续时间。B模式中操作者通过按键选择策略，手动选择时间计入总完成时间；因此B模式代表包含人工判断与切换成本的工作流基线。

**图3.** 实验任务流程与视觉语义参数调度框架。

### 3.5 评价指标

主要终点为完成时间。次要客观终点包括成功率、主端轨迹长度、停顿次数、方向反转次数和运动平滑性。主观负荷采用未加权Raw NASA-TLX，即六个维度的算术平均。NASA-TLX按“操作者×对象策略×模式”采集六维评分。视觉模块报告类别识别正确率、策略触发正确率、置信度和单帧处理时间。

过程行为指标在正式统计前固定定义。本文采用的停顿定义为：主端速度低于0.005 m/s且持续时间不短于0.30 s。方向反转和平滑性未作为本文核心结论；若在扩展分析中报告，则需统一滤波频率、阶段截取范围和阈值，并在查看组间差异前冻结。

### 3.6 统计分析

考虑到试次嵌套在少数操作者内部，统计结果以配对趋势、操作者级方向性和效应大小为主，不将135次试验视为135个独立参与者样本。五模式完成时间采用Friedman检验进行总体比较；总体显著后进行配对Wilcoxon符号秩检验，并采用Holm-Bonferroni方法校正多重比较。C–E比较作为核心消融，报告配对均值差、相对变化、效应量和操作者级聚合趋势。置换检验可作为补充的配对分析，但不用于声称完全消除了伪重复问题。Raw NASA-TLX采用相同的非参数框架，但由于独立操作者数量仅为3名，主观负荷结果解释为初步人在环证据。成功率以描述性报告为主。

---

## 4 实验结果

### 4.1 视觉识别与策略触发验证

在受控视角、背景和光照下，6种对象各30幅图像，共180幅。类别识别和策略触发均为180/180，平均置信度0.853，单帧墙钟处理时间50.08 ms。该结果说明在本文实验条件下视觉触发没有成为主要误差来源，但不外推至遮挡、强光变化、复杂背景、未知对象或未测试类别。

| 对象 | 图像数 | 类别正确率 | 策略触发正确率 | 平均置信度 | 时间/ms |
|---|---:|---:|---:|---:|---:|
| 苹果 | 30 | 100% | 100% | 0.771 | 56.66 |
| 香蕉 | 30 | 100% | 100% | 0.948 | 50.45 |
| 水瓶 | 30 | 100% | 100% | 0.726 | 49.71 |
| 杯 | 30 | 100% | 100% | 0.820 | 47.61 |
| 鼠标 | 30 | 100% | 100% | 0.914 | 46.79 |
| 剪刀 | 30 | 100% | 100% | 0.938 | 49.27 |

**图4.** 视觉识别验证结果，包括混淆矩阵、置信度分布和单帧处理时间。

### 4.2 五模式实验结果

| 模式 | 完成时间/s | 主端轨迹/m | 成功率 | Raw TLX |
|---|---:|---:|---:|---:|
| A 固定参数 | 21.42±1.58 | 0.763±0.098 | 22/27 (81.5%) | 62.59±3.95 |
| B 人工选择 | 21.01±1.61 | 0.799±0.115 | 21/27 (77.8%) | 57.15±3.68 |
| C 视觉多参数 | **19.28±1.30** | **0.715±0.092** | **26/27 (96.3%)** | **49.67±3.63** |
| D 视觉仅观察 | 20.91±1.10 | 0.734±0.085 | 24/27 (88.9%) | 60.22±3.85 |
| E 视觉仅阻抗 | 21.07±1.56 | 0.739±0.084 | 24/27 (88.9%) | 54.54±4.09 |

描述性结果显示，C模式在五种模式中取得最短平均完成时间、最短主端轨迹、最高成功率（作为描述性指标）和最低Raw NASA-TLX。C模式相较A、B、D和E的平均完成时间分别降低约10.0%、8.2%、7.8%和8.5%。C模式总体轨迹相较A、B、D和E分别减少约6.3%、10.5%、2.6%和3.2%。C模式Raw TLX较A、B、D和E分别降低约20.6%、13.1%、17.5%和8.9%。

五模式完成时间的Friedman检验显示总体差异显著（χ²(4)=30.904, p<0.001）。配对Wilcoxon检验经Holm校正后，C模式完成时间低于A、B、D和E。由于试次嵌套在3名操作者内部，本文将这些结果解释为当前平台、对象集合和参与者内的配对证据，而非一般操作者群体的总体统计结论。Raw NASA-TLX同样呈现C模式最低的方向，但主观负荷结果结合小样本和非盲法条件进行谨慎解释。

**图5.** 五模式完成时间、主端轨迹、成功率和Raw NASA-TLX对比。建议采用箱线图结合散点/配对连线呈现分布，避免只使用柱状图。

### 4.3 完整多参数策略与仅阻抗消融比较

| 模式 | 完成时间/s | 主端轨迹/m | 成功率 | Raw NASA-TLX |
|---|---:|---:|---:|---:|
| C 视觉多参数 | **19.28±1.30** | **0.715±0.092** | **26/27 (96.3%)** | **49.67±3.63** |
| E 视觉仅阻抗 | 21.07±1.56 | 0.739±0.084 | 24/27 (88.9%) | 54.54±4.09 |

C–E比较是本文最关键的消融。两种模式均使用视觉语义和阻抗调节，区别在于C模式额外设置主端基础反馈接口增益、反馈死区、夹爪闭合速度和夹持力。该设计用于检验一个工程问题：仅改变从端柔顺性是否足以覆盖异质对象抓取需求，还是需要同时初始化操作者感知通道和夹爪执行通道。需要强调的是，该比较只能说明完整接触前多参数策略相较仅阻抗调节具有整体优势，不能单独证明力反馈接口参数或夹爪参数各自的独立贡献。在27个匹配块中，C模式平均完成时间为19.28 s，E模式为21.07 s，平均差为-1.79 s，相对降低约8.5%。操作者级聚合结果显示，三名操作者均表现出C快于E的方向：P01为18.94 s vs 20.60 s，P02为19.09 s vs 21.66 s，P03为19.80 s vs 20.95 s。六种对象层面也均表现出C快于E的方向。

主端轨迹长度差异较小（0.715 m vs 0.739 m），提示C模式的时间收益不主要来自几何路径缩短。结合停顿分析，本文将C–E差异解释为操作效率改善的初步证据，即多通道参数协同可能减少了抓取、运输或释放阶段的停顿与修正。该机制解释与现有实验结果保持一致，但其因果性仍有待通过更细粒度的阶段标注与消融实验进一步验证。相关闭环力觉与接触过程分析为该机制提供了辅助支持，但本文主要聚焦于多通道参数协同策略，该部分内容将作为后续研究进一步展开。

**图6.** C–E核心消融结果。图中展示27个匹配块配对点、三名操作者分面图和六对象分层图，并在图注中说明统计检验仅作为配对证据解释。

### 4.4 过程行为指标：C–E停顿分析

从原始主端轨迹CSV（采样频率约200 Hz）计算停顿次数。停顿定义为主端速度低于0.005 m/s且持续不少于0.30 s。C模式每试次平均停顿次数为2.74±1.23，E模式为3.41±1.67。分策略看，易损优先、折中和稳定优先三类均表现出C模式停顿较少的方向。该结果与C模式完成时间更短而轨迹长度差异较小的现象一致，支持“多通道协同的附加收益主要来自操作效率提升，而非路径缩短”的解释。未来工作将通过引入阶段级时间标注（如接近、抓取、运输与释放），以实现对系统行为的更细粒度归因分析

### 4.5 失败案例分析

135次试次中共发生9次失败，失败形式包括掉落、明显滑移或可观察损伤。各模式失败分布如下：

| 模式 | 失败/总数 | 典型观察 |
|:---:|:---:|:---|
| A 固定参数 | 5/27 | 纸杯夹持变形、剪刀定位不稳 |
| B 人工选择 | 6/27 | 手动策略选择错误或切换成本较高 |
| C 视觉多参数 | **1/27** | 鼠标表面光滑，运输阶段发生滑移 |
| D 视觉仅观察 | 3/27 | 中等对象夹持力度不当 |
| E 视觉仅阻抗 | 3/27 | 中等对象抓取不稳 |

失败案例分析表明，C模式在本实验中具有最低失败率（1/27）。各模式失败主要表现出不同机制特征，例如A模式主要与夹持变形相关，B模式与策略切换成本相关，而D与E模式更多与视觉观测及抓取稳定性有关。说明多通道信息在抑制失败中起主要作用。

当前失败分析基于任务级日志数据，缺乏对操作过程的细粒度阶段标注，因此分析仍停留在任务层面，无法进一步进行阶段级归因。

### 4.6 跨操作者与六对象一致性

三名操作者均表现出C模式完成时间低于E模式的方向。六种对象层面的均值也显示C模式均为五模式中最短完成时间。对象层面结果如下：

| 对象 | A 固定/s | B 人工/s | C 视觉多参数/s | D 仅观察/s | E 仅阻抗/s |
|:---:|---:|---:|---:|---:|---:|
| 苹果 | 20.46 | 21.40 | **19.25** | 20.81 | 20.94 |
| 香蕉 | 20.07 | 20.85 | **19.49** | 21.06 | 20.64 |
| 纸杯 | 22.36 | 20.27 | **18.69** | 20.38 | 21.17 |
| 瓶子 | 22.11 | 22.14 | **19.63** | 20.78 | 20.30 |
| 鼠标 | 21.74 | 20.93 | **19.75** | 20.74 | 21.64 |
| 剪刀 | 21.79 | 20.70 | **18.84** | 21.83 | 21.70 |

C相对E的时间降幅范围为瓶子3.3%、香蕉5.5%、苹果8.1%、鼠标8.7%、纸杯11.7%和剪刀13.2%。这说明方法在六种已测试对象上具有方向一致性，但不外推至未测试对象或复杂遮挡场景。

---

## 5 讨论

### 5.1 为什么接触前视觉语义前馈能够改善表现

固定参数模式必须用单一折中参数覆盖三类操作策略，因此难以同时满足易损对象的柔顺性和硬质对象的稳定定位。人工选择模式虽然能够调用不同策略，但把对象判断和策略切换责任交给操作者，增加了工作流负担。视觉仅观察模式改善了场景信息，却没有改变系统动力学和夹爪行为。视觉多参数模式利用对象语义在接触前完成策略初始化，使操作者不必在任务过程中持续补偿不合适的手感、夹爪速度或夹持力。这一机制与C模式较短完成时间、较低停顿次数和较低主观负荷趋势一致。

### 5.2 完整接触前多参数策略相对仅阻抗调节的意义

C与E均根据视觉语义调整平移刚度、旋转刚度和阻尼比，因此两者共享柔顺性适配机制。C额外设置主端基础反馈接口增益、反馈死区、夹爪闭合速度和夹持力。当前数据中，C相较E的平均完成时间降低约8.5%，而主端轨迹长度降低约3.2%。这表明附加收益更可能来自抓取、运输或释放阶段的操作效率，而非大幅改变几何路径。

这一结果对应用型遥操作系统具有工程意义：操作者面对的不仅是从端末端柔顺性，还包括主端基础反馈接口设置、反馈死区以及夹爪执行速度和夹持力。单独调节阻抗可能无法覆盖异质对象抓取中的全部操作需求。例如，易损或易滑对象不仅需要较低刚度，还需要较慢的夹爪闭合和较低夹持力，以降低挤压与滑移风险；硬质或几何不规则对象则可能需要更明确的接口反馈和更稳定的夹持执行，以减少操作者在抓取建立和运输阶段的反复修正。反馈死区的工程作用主要是削弱小幅扰动和反馈接口噪声，使操作者感受到更稳定的接触提示，而不是作为接触力闭环控制律。多通道参数协同能够把对象语义转化为更完整的操作手感和执行策略。需要指出的是，本文尚未直接测量接触力、滑移量及对象损伤程度，因此当前对“性能提升源于多通道协同”的解释仍基于系统层面的间接证据，而非严格因果验证。相关反馈闭环机制与力感知增益的定量分析有待后续通过独立实验进一步验证。

### 5.3 与相关研究的区别

已有任务分解和共享控制研究通常通过切换控制方式、约束输入空间或提供引导来提高完成效率并降低操作者负荷[5,6,14,15]。视觉阻抗研究则从视觉与力特征空间统一控制目标[13]。本文区别在于：不进行连续视觉伺服，不依赖在线轨迹规划，也不声称接触后的外力闭环自适应或最优控制，而是把对象语义作为接触前任务先验，以低计算开销调用可解释的多通道参数策略。换言之，本文提供的是一种系统级桥接范式：将高层视觉语义转换为低层遥操作接口参数，使操作者在接触发生前获得更适合当前对象的从端柔顺性、基础反馈接口设置和夹爪执行行为。该定位适合类别可识别、环境相对结构化、但仍需要操作者完成精细抓取与放置的工程遥操作场景。

### 5.4 对Industrial Robot读者的应用价值

从工业机器人应用角度看，本文方法具有三个现实特点。第一，系统基于现有RGB-D相机、力反馈主端、Franka机械臂和夹爪实现，不依赖额外接触传感器或复杂在线优化，便于集成到已有遥操作平台。第二，策略表由对象操作风险直接解释，便于工程人员检查、调整和移植。第三，任务内策略锁定和默认安全参数降低了视觉抖动对控制稳定性的影响。因此，该方法更适合作为半结构化场景中的人机协同遥操作辅助模块，而非完全自主抓取算法。

本文实验对象为桌面代理对象，但其对应的操作需求与若干工业遥操作任务具有相似性。例如，纸杯和瓶子代表轻质、易变形或易滑容器类对象；剪刀代表具有细长几何和明确姿态要求的硬质工具；鼠标代表表面光滑且几何不规则的精密部件代理对象。这类需求可对应到远程维护、柔性物流分拣、非结构化拆解和危险环境下的人监督抓取任务。本文提出了一种可迁移的系统级参数调度思路，可为工业遥操作任务中的策略设计提供参考。

### 5.5 为什么不同对象收益幅度不同

六种对象均表现出C模式完成时间低于E模式，但降幅并不相同。瓶子和香蕉的降幅较小，可能是因为其抓取动作较熟悉，操作者即使在E模式下也能通过经验补偿默认夹爪参数。纸杯和剪刀的降幅较大，可能与其抓取风险和姿态稳定要求更高有关：纸杯需要避免变形和不稳定夹持，剪刀则需要更明确的定位和稳定运输。该机制解释可通过引入阶段耗时、重抓行为及夹爪状态日志等多源数据进行进一步细粒度验证。

### 5.6 局限性

1. 独立操作者仅3名，135次重复任务不能替代更大参与者样本；主观负荷和跨操作者结论应视为真实平台上的初步人在环证据。
2. 试次嵌套在操作者、对象和重复块内部，统计结果不解释为一般人群层面的强显著结论。
3. 模式顺序进行了部分平衡，但未执行严格完全随机化，学习效应和疲劳效应不能完全排除。
4. 人工选择模式B包含选择时间，因此它是人工选参工作流基线，而不是纯控制器执行时间基线。
5. 人在环实验覆盖六种具体对象，每类对象数量有限，结果支持已测试对象间的一致方向，不外推至未知对象、复杂遮挡和开放场景。
6. 视觉验证来自受控视角、背景和光照，100%正确率仅代表受控实验条件，不外推至遮挡、复杂背景和未测试类别。
7. 现有数据未提供经独立传感器校准的接触力、滑移量和物体损伤量，因此本文不直接声称已证明“保护易损对象”。
8. 参数由工程经验、安全范围和预实验确定，本文证明的是离散语义策略在当前任务中的有效性，而非参数全局最优性。

---

## 6 结论

本文提出一种面向异质对象触觉遥操作抓取的视觉语义多通道参数调度方法。该方法将目标对象类别解释为易损优先、折中和稳定优先三类操作策略，并在接触前协同配置从端阻抗、主端基础反馈接口和夹爪执行参数。真实平台五模式实验显示，在当前3名操作者、6种对象和135次试验范围内，视觉多参数模式取得最短平均完成时间、最高成功率（作为描述性指标）和最低Raw NASA-TLX。与视觉仅阻抗模式相比，完整多通道模式平均完成时间降低约8.5%，且3名操作者和6种对象均表现出一致方向。停顿分析进一步提示，附加收益可能主要来自操作停顿和修正减少，而非几何路径显著缩短。

总体而言，本文为无需复杂在线优化的异质对象触觉遥操作提供了一种可解释、低成本、可部署的接触前参数初始化方案。其统计普适性和外部泛化能力仍需通过更多操作者、严格随机化顺序、对象实例级记录、阶段过程指标以及接触质量指标进一步验证。接触后外力估计、力反馈闭环修正和操作者力觉感知增益属于后续研究范围，不由本文数据单独证明。

---

## Declarations

- **Ethical approval:** This study was exempt from formal ethics review because it involved non-medical teleoperation tasks and did not collect personally identifiable information.
- **Informed consent:** All participants provided written informed consent before the experiment.
- **Funding:** Not applicable.
- **Conflict of interest:** The authors declare no conflict of interest.
- **Data availability:** De-identified trial data, analysis scripts and vision validation results are available from the corresponding author upon reasonable request. A public repository link can be added when available.

---

## References

1. Lawrence, D.A. (1993), “Stability and transparency in bilateral teleoperation”, *IEEE Transactions on Robotics and Automation*, Vol. 9 No. 5, pp. 624–637.
2. Niemeyer, G. and Slotine, J.J.E. (1991), “Stable adaptive teleoperation”, *IEEE Journal of Oceanic Engineering*, Vol. 16 No. 1, pp. 152–162.
3. Sheridan, T.B. (1992), *Telerobotics, Automation, and Human Supervisory Control*, MIT Press, Cambridge, MA.
4. Passenberg, C., Peer, A. and Buss, M. (2010), “A survey of environment-, operator-, and task-adapted controllers for teleoperation systems”, *Mechatronics*, Vol. 20 No. 7, pp. 787–801.
5. Losey, D.P., McDonald, C.G., Battaglia, E. and O’Malley, M.K. (2018), “A review of intent detection, arbitration, and communication aspects of shared control for physical human–robot interaction”, *Applied Mechanics Reviews*, Vol. 70 No. 1, 010804.
6. Bowman, M., Zhang, J. and Zhang, X. (2024), “Intent-based task-oriented shared control for intuitive telemanipulation”, *Journal of Intelligent & Robotic Systems*, Vol. 110, 167.
7. Han, J. and Yang, G.-H. (2022), “Improving teleoperator efficiency using position–rate hybrid controllers and task decomposition”, *Applied Sciences*, Vol. 12 No. 19, 9672.
8. Huang, K., Chitrakar, D., Rydén, F. and Chizeck, H.J. (2019), “Evaluation of haptic guidance virtual fixtures and 3D visualization methods in telemanipulation—a user study”, *Intelligent Service Robotics*, Vol. 12, pp. 289–301.
9. Hogan, N. (1985), “Impedance control: An approach to manipulation”, *Journal of Dynamic Systems, Measurement, and Control*, Vol. 107 No. 1, pp. 1–24.
10. Kronander, K. and Billard, A. (2016), “Stability considerations for variable impedance control”, *IEEE Transactions on Robotics*, Vol. 32 No. 5, pp. 1298–1305.
11. Abu-Dakka, F.J., Rozo, L. and Caldwell, D.G. (2018), “Force-based variable impedance learning for robotic manipulation”, *Robotics and Autonomous Systems*, Vol. 109, pp. 156–167.
12. Duan, J., Gan, Y., Chen, M. and Dai, X. (2018), “Adaptive variable impedance control for dynamic contact force tracking in uncertain environment”, *Robotics and Autonomous Systems*, Vol. 102, pp. 54–65.
13. Abu-Dakka, F.J. and Saveriano, M. (2020), “Variable impedance control and learning — A review”, *Frontiers in Robotics and AI*, Vol. 7, 590681.
14. Oliva, A.A., Giordano, P.R. and Chaumette, F. (2021), “A general visual-impedance framework for effectively combining vision and force sensing in feature space”, *IEEE Robotics and Automation Letters*, Vol. 6 No. 3, pp. 4441–4448.
15. Peternel, L., Tsagarakis, N. and Ajoudani, A. (2016), “Towards multi-modal intention interfaces for human–robot co-manipulation”, in *Proceedings of the IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)*, pp. 2663–2669.
16. Boessenkool, H., Abbink, D.A., Heemskerk, C.J.M., van der Helm, F.C.T. and Wildenbeest, J.G.W. (2011), “Haptic shared control improves teleoperated task performance toward performance in direct control”, in *Proceedings of the IEEE World Haptics Conference*, pp. 433–438.
17. Abbott, J.J., Marayong, P. and Okamura, A.M. (2007), “Haptic virtual fixtures for robot-assisted manipulation”, in Thrun, S., Brooks, R. and Durrant-Whyte, H. (Eds.), *Robotics Research*, Springer Tracts in Advanced Robotics, Vol. 28, Springer, Berlin, pp. 49–64.
18. O’Malley, M.K. and Ambrose, R.O. (2003), “Haptic feedback applications for Robonaut”, *Industrial Robot: An International Journal*, Vol. 30, pp. 531–542.
19. Albu-Schäffer, A., Haddadin, S., Ott, C., Stemmer, A., Wimböck, T. and Hirzinger, G. (2007), “The DLR lightweight robot: design and control concepts for robots in human environments”, *Industrial Robot*, Vol. 34 No. 5, pp. 376–385.
20. Haddadin, S., Parusel, S., Johannsmeier, L. et al. (2022), “The Franka Emika robot: A reference platform for robotics research and education”, *IEEE Robotics & Automation Magazine*, Vol. 29 No. 2, pp. 46–64.
21. Hart, S.G. and Staveland, L.E. (1988), “Development of NASA-TLX (Task Load Index): Results of empirical and theoretical research”, in Hancock, P.A. and Meshkati, N. (Eds.), *Human Mental Workload*, North-Holland, Amsterdam, pp. 139–183.
