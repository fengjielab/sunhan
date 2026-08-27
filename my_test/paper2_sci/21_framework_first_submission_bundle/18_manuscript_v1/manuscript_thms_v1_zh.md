# 从名义控制器标签到实际干预：异步人机遥操作实验评价的保真度框架

*THMS定向中文审批稿（第二版：概念校准与窗口敏感性）*

**英文拟题：** *From Nominal Controller Labels to Realized Interventions: A Fidelity Framework for Experimental Evaluation of Asynchronous Human–Machine Teleoperation*

**作者与单位：** `[投稿前必须补充]`

> **审批与投稿状态。** 本稿是依据冻结的清理后再分析结果形成的THMS定向中文审批稿。伦理审批或豁免机构、编号、日期及知情同意程序必须依据同期机构记录补齐：`[ETHICS RECORD REQUIRED—DO NOT SUBMIT]`。作者、单位、基金、利益冲突、作者贡献、致谢以及数据和代码可用性声明亦须在投稿前完成。上述项目不得根据现有数据推断，也不得仅作为一般局限删除或绕过。

## 摘要

异步人机系统实验通常以固定、自适应、视觉使能或组合模式等名义标签定义实验条件，但标签本身不能证明耦合人—机器系统在结局窗口内实际经历了相应干预。若可执行守卫、运行时时序、参数轨迹或窗口暴露偏离名义语义，标签分组比较可能回答不同于原研究问题的问题。本文提出实际干预保真度框架，将有文档支持的名义干预、源代码实际实现、实际记录干预与结局连接为\(N_m\rightarrow C_m\rightarrow R_i\rightarrow Y_i\)证据链，并由事件时序、结局窗口暴露、时钟完整性和精确采集溯源共同限定证据可容许的统计比较与科学解释。框架被回顾性应用于5名参与者在4种存档配置下完成的180次重复遥操作试次；参与者是人体结局推断的独立实验单位。精确采集溯源得到验证。G在45/45次试次中遵循可执行原始力规则，却有43/45次在接触前激活；由于现有血缘未恢复独立的接触后名义规范，G标签本身不能支持接触后效应解释。F没有接触前激活，但混合时钟实现与名义接触后+0.20 s要求不一致，仅3/45次实现该名义时序。由此，存档证据不支持孤立的接触后力效应、正确门控的增量细化效应或视觉×力析因解释。在这些边界建立后，E分配下具有异质实际视觉暴露的捆绑配置相对固定配置A的阈值参照超额力冲量差为−0.3489 N·s（95% CI，−0.6080至−0.0898），5名参与者方向一致；四个固定相邻窗口中的差值亦均为负，但精确小样本检验和多重性校正不支持确认性推断。该案例表明，实际干预保真度不是附加的软件检查，而是有效评价异步人机系统的推断前提。

**关键词：** 人机系统评价；实际干预保真度；异步遥操作；结局窗口暴露；可容许估计目标；采集溯源

# 1. 引言

人机闭环遥操作把人的感知、决策和适应能力与触觉接口、感知管线、监督控制器、远端机器人及物理环境耦合起来。接触性能因而不是控制器的孤立输出，而是人在反馈回路中持续行动和响应所形成的系统结局（Hannaford, 1989; Lawrence, 1993; Hokayem and Spong, 2006; Passenberg et al., 2010）。触觉引导和自然化触觉反馈、视觉/语音辅助、共享控制、阻抗调节及力相关学习都可能改变交互安全性与效率（Huang et al., 2019; Hogan, 1985; Peternel et al., 2018; Abu-Dakka et al., 2018; Abu-Dakka and Saveriano, 2020; Gong et al., 2024; Michel et al., 2023; Huang et al., 2021; Siegemund et al., 2024; Jekel et al., 2026）。然而，这些组成部分往往运行在不同线程、调度周期和时钟域中（Walker et al., 2010; Buchli et al., 2011; Ajoudani et al., 2012; Michel et al., 2021; Peternel and Ajoudani, 2023）。因此，对人机系统的实验评价不仅需要说明“分配了什么条件”，还需要证明“人机系统实际经历了什么干预”。

实验通常使用*固定*、*视觉使能*、*力自适应*或*组合*等标签操作化科学条件。每个标签都隐含参数、守卫、事件顺序和持续时间：视觉相关预设应在何时可用，力相关更新应由何事件允许，以及相应状态应覆盖结局窗口的哪一部分。然而，图像采集与推理、人的主端运动、接触检测、参数转换和控制循环可能并行发生。名义上的接触前配置可能直到接触后才完成，名义上的接触后机制也可能提前激活。即使程序执行了某条代码路径，结局窗口仍可能只得到部分暴露。由此，名义条件分配、程序实现、实际交付和统计结局之间可能形成不同类型的断点。

这一问题的组成部分已分别出现在时延研究、运行时验证、可重复性、实施保真度和estimand研究中，但尚缺少面向异步人机实验评价的联合推断规则。表I总结这些研究路线与本文所补充的连接。

**表I. 与人机实验评价相关的方法学路线及尚未解决的连接。**

| 研究路线 | 已直接处理的问题 | 本文补充的连接 |
|---|---|---|
| 时延与感知调度（Vogels, 2004; Rakita et al., 2020; Louca et al., 2024; Aldana-López et al., 2023） | 时延、跨模态时间代价、操作者响应与稳定性 | 将逐试次时序转化为结局窗口暴露，并限定比较含义 |
| 机器人运行时验证（Huang et al., 2014） | 可执行命令和消息是否满足形式属性 | 区分“程序按实现执行”与“实现符合名义实验语义” |
| 机器人/HRI可重复性（Bonsignorio and del Pobil, 2015; Bonsignorio, 2017; Gunes et al., 2022; Bagchi et al., 2023; Marchesi et al., 2024） | 透明报告、产物保存与复现 | 在同源数据得到证明后，重建该采集实际交付的干预 |
| 实施保真度（Carroll et al., 2007） | 计划干预与实际交付内容、频率和覆盖的差异 | 将交付概念落实为控制器守卫、事件、时钟和轨迹证据 |
| Estimand定义（Lundberg et al., 2021） | 使统计目标量与理论问题对应 | 根据实际干预证据决定名义估计目标是否仍受支持 |
| **本文** | **联合重建\(N_m\rightarrow C_m\rightarrow R_i\rightarrow Y_i\)** | **把保真度断点转化为对可容许人机系统比较的约束** |

本文回答三个研究问题：

- **RQ1（案例实现）：** 在本回顾性异步遥操作案例中，名义控制器标签、可执行逻辑与实际记录干预之间呈现哪些一致和偏离模式？
- **RQ2（推断后果）：** 当名义干预与实际干预偏离时，这种偏离如何改变控制器比较在科学上允许支持的解释？
- **RQ3（案例示范）：** 完成实际干预重建之后，现有案例数据仍支持哪些有边界的结局模式？

本文有两项方法学贡献，并通过一个真实回顾性遥操作案例进行操作化展示。第一，提出名义—可执行—实际—结局四层证据链，把人机事件背景、控制器守卫、参数轨迹和时钟域纳入同一评价流程。第二，将语义、运行时和窗口暴露证据映射到证据可容许的统计比较目标与科学解释，而不是用综合分数或事后“合规”亚组代替推断判断。5名参与者的180次重复试次提供案例证据，不被列为独立的概念贡献，也不被用于声称框架已得到外部验证。

# 2. 面向人机实验评价的实际干预保真度框架

## 2.1 四层证据链

框架把一次人机实验比较表示为：

\[
N_m\rightarrow C_m\rightarrow R_i\rightarrow Y_i.
\]

其中，\(N_m\)是由同期规范、协议或可追溯代码说明支持的模式\(m\)科学意图，包括预期参数、激活守卫、更新规则、事件顺序和预期结局窗口暴露；模式名称本身不能补足缺失的名义规范。\(C_m\)是采集程序源代码实际实现的守卫、时钟域、初始化和更新逻辑。\(R_i=\{\mathcal{E}_i,a_i(t),\boldsymbol{\theta}^{log}_i(t)\}\)是试次\(i\)中由干预相关事件、激活状态和指令参数轨迹重建的实际记录干预；\(Y_i\)是从明确窗口内、按预先声明的独立实验单位计算的结局。精确采集溯源\(\mathcal{P}_i\)作为把\(R_i\)可靠连接到\(Y_i\)的数据完整性前提单独处理，而不是实际干预的组成部分。

人体主端输入和其他可观测人机轨迹另记为\(H_i(t)\)。它们可以帮助解释异步事件背景和耦合系统行为，但不是控制器实际交付干预\(R_i\)的默认组成部分。人的意图并未被直接记录；主端输入的存在也不自动形成有效人体行为指标。记录的控制器指令定义存档能够支持的干预证据，但不等同于独立测量的物理阻抗或完整的人—机器人状态。

![四层实际干预保真度框架与异步人机时间链。](../19_publication_figures/figures/Fig01_realized_intervention_framework.png)

**图1.** 有文档支持的名义干预经源代码实际实现转化为试次特异的实际记录干预，并进入结局窗口和证据可容许解释。简化异步时间线说明人体输入、感知、控制器激活和接触可能错位，因而实现与实际交付均不能由标签默认成立。采集溯源作为\(R_i\rightarrow Y_i\)连接的正交数据完整性前提，见图2。

## 2.2 时序、窗口暴露与证据可容许估计目标

若名义干预规定目标激活时间\(t^{N}_{act,i}\)，实际记录时间为\(t^{R}_{act,i}\)，则激活时序误差为：

\[
\epsilon_{act,i}=t^{R}_{act,i}-t^{N}_{act,i}.
\]

负值表示早于规定时间，正值表示晚于规定时间。只有在目标事件和时钟映射有证据支持时才计算该量。软件日志时延不能在没有传感、通信和物理响应测量的情况下被称为端到端物理时延。

干预在试次中出现并不意味着它覆盖了结局。对二元激活状态\(a_i(t)\)及窗口\(W=[t_0,t_1]\)，实际窗口暴露比例为：

\[
\Phi_i(W)=\frac{1}{|W|}\int_{t_0}^{t_1}\mathbb{I}[a_i(t)=1]dt.
\]

\(\Phi_i=1\)、\(0<\Phi_i<1\)和\(\Phi_i=0\)分别表示完全、部分和零暴露。这些类别用于描述实际进入结局的干预，不是观察结局后排除试次的规则。

名义比较\(\Delta^N_{m_1,m_0}\)只有在相应语义和暴露得到支持时，才能按其标签解释。否则，存档能够支持的是实际干预类别之间的比较：

\[
\Delta^R_{m_1,m_0}=\mathbb{E}[Y\mid R\in\mathcal{R}_{m_1}]-\mathbb{E}[Y\mid R\in\mathcal{R}_{m_0}].
\]

本文保留*可容许估计目标（admissible estimand）*这一术语，但严格限定其含义：它是现有干预证据允许表述的最窄**统计比较目标**，不是无需额外识别假设即可赋予因果含义的causal estimand。\(R_i\)是干预实现后的记录状态，可能与人体动作、系统状态和运行时时序共同变化；因此，条件于\(R_i\)的均值差本身不能证明因果效应。本文的\(\Delta^R\)用于界定描述性比较和科学措辞，任何因果解释仍需研究设计、可交换性、一致性及其他识别条件的独立支持。保真度分析因此可以改变解释，而不必改变试次入选或结局数值。

## 2.3 干预偏差与正交的溯源前提

干预交付保真度包含三个可以共存的断点：\(N\neq C\)表示有文档支持的科学规范没有被源代码实现，包括缺失守卫或不相容时钟域；\(C\neq R\)仅表示依据实际实现及其记录输入应产生的状态或参数轨迹没有在运行记录中再现；实际干预与结局窗口不匹配表示暴露偏差。它们不应压缩为单一“正确/错误”评分。与此不同，采集溯源完整性不是干预是否按计划交付的属性，而是把\(R_i\)可信地连接到\(Y_i\)的正交数据完整性前提。若干预来源与结局来源不属于同一精确采集，则无法评价该干预—结局对，即使控制器本身可能按计划运行。

**表II. 人机干预评价的最低证据包。**

| 证据 | 评价用途 |
|---|---|
| 带版本的名义干预规范 | 定义预期参数、守卫、事件顺序和暴露 |
| 可执行守卫、初始化、更新规则与时钟域 | 建立程序实际实现的语义 |
| 人体输入、感知、控制器和机器事件时间戳 | 重建异步事件顺序 |
| 激活状态与指令参数轨迹 | 重建试次特异的实际干预 |
| 明确定义的结局窗口 | 确定进入结局的暴露内容和比例 |
| 独立实验单位 | 确定有效推断层级 |
| 精确采集ID、文件连接与哈希 | 证明干预和结局来自同一次采集 |

实际应用分三阶段进行。采集前冻结名义干预、守卫、时钟、窗口和实验单位；采集中记录人体输入、感知事件、激活状态、参数轨迹、接触事件和采集身份；推断前验证\(N\rightarrow C\)、\(C\rightarrow R\)，并以溯源完整性验证\(R\xleftrightarrow{\mathcal{P}}Y\)，再决定标签比较可被解释为何种效应。名义标签解释只有在规范证据、实现守卫与时钟、实际轨迹、结局窗口暴露、精确溯源和推断单位全部支持时才保留；任一环节不支持时，比较降级为分配标签及其实际暴露分布之间的描述性差异。没有名义目标的指标标记为“不适用”，缺少规范或记录字段的指标标记为“不可获得”；二者都不能转换为保真度通过。

# 3. 回顾性遥操作案例研究

## 3.1 人机系统、参与者与实验结构

实验平台由人类操作者、Force Dimension Omega.7主端触觉设备、监督控制器、Intel RealSense D435i视觉通道、Franka Emika Panda机器人与Franka Hand夹爪以及物理对象组成。Omega.7增量平移输入经3倍缩放和符号映射形成机器人笛卡尔位置目标；机器人状态估计的外部力/力矩同时用于接触检测、触觉反馈和结局计算。该力通道为Panda内部估计\(`O_F_ext_hat_K`\)，不是独立外部力/力矩传感器。记录的刚度是软件指令参数，未被独立验证为物理闭环阻抗。

5名参与者完成了存档实验。清理后数据具有参与者内重复测量结构：5名参与者×3种材料类别×3个重复区组×4种配置（A/G/E/F），共180次分析试次。每名参与者在每种配置下贡献9次试次，每种配置共45次。重复试次提高参与者内表征精度，但独立人体实验单位仍是参与者（\(n=5\)），不是180次试次或45个匹配区组。

任务日志表示接近、阈值定义的接触、抓取、搬运、释放和完成序列。`task_start`在力基线准备就绪且控制器无转换活动时自动发出，表示**系统就绪**，而非首次人体运动。原始CSV虽包含Omega.7位置，但存档没有经外部验证的人体运动起点；本文不新增human motion onset终点，也不把`contact − task_start`解释为操作者接近时长或移动速度。

参与者人口学、惯用手、经验、招募、补偿和训练方案仍需从同期记录核实。对象几何、物理实例、起始与目标位置、放置容差以及前瞻性随机化/平衡顺序方案未从当前血缘中恢复。最重要的是：`[ETHICS RECORD REQUIRED—DO NOT SUBMIT：审批/豁免机构、编号、日期、知情同意及存档数据使用范围]`。

## 3.2 名义配置与实际干预重建

四个存档标签表示捆绑的监督配置，而非可直接分解的单一因子。A为固定记录配置，名义平移刚度200 N/m；G使用无视觉的原始力相关刚度自适应，但其可执行更新器不要求基线就绪或接触，且现有血缘没有恢复一项独立、同期的“接触后G”名义规范；E由首次有效视觉锁定选择材料相关预设，并同时改变平移/旋转刚度、阻尼、触觉反馈和夹爪力；F在E的视觉预设基础上加入有源代码说明支持的名义接触后+0.20 s力相关细化。由于E/F同时改变多个参数，E-A不能解释为视觉或刚度的孤立效应。

视觉通道使用424×240、名义15帧/s彩色流和`yolo11n.pt`模型；首次有效语义映射锁定soft、medium、hard或unknown配置。监督循环名义频率为200 Hz，但实测控制周期不规则，因此所有时域分析使用记录时间戳。

每次采集产生原始CSV、事件JSON和摘要JSON。CSV包含单调相对时间、主端输入、机器人目标和状态、力/力矩、控制器参数、视觉状态、激活标志、接触阈值和控制周期。名义配置及预期守卫实例化\(N_m\)，源代码守卫、更新和时钟操作实例化\(C_m\)，行级事件、激活和参数轨迹实例化\(R_i\)，事件对齐结局实例化\(Y_i\)。

![案例人机系统、异步事件通道与采集溯源。](../19_publication_figures/figures/Fig02_system_and_lineage.png)

**图2.** 案例系统将人体主端输入\(H_i(t)\)、视觉感知、监督控制和机器人—环境交互置于异步闭环中；\(H_i(t)\)用于描述耦合系统背景，不被定义为控制器实际干预\(R_i\)。事件与轨迹仅通过逻辑试次键和带时间戳的精确采集身份连接。该溯源路径是\(R_i\rightarrow Y_i\)连接的数据完整性前提；试次级保真度使用180次入选采集，人体结局推断在5名参与者层面完成。

## 3.3 溯源、事件与结局

存档包含186条采集记录，对应180个逻辑试次键。174条为唯一记录，另有6个键各包含一条20260729初始记录和一条20260730替代记录。冻结清单以不读取结局字段的固定身份规则选择174条唯一记录和6条替代记录；所有初始和替代记录均只读保留。现有材料未保留同期技术故障说明，也不能确定最初认定错误时是否已查看结局，因此替换不被描述为前瞻性盲态排除。

事件和CSV `system_time`来自相对于`time.perf_counter()`原点的单调时间线。G更新器使用原始滤波力且不检查基线或接触。F延迟逻辑把`time.time()`墙上时钟值与`time.perf_counter()`原点混合比较，使名义+0.20 s门控不能被视为可靠实现。G首次激活定义为`force_adapt_active>0`首行，F首次激活定义为`fusion_active>0`首行。

接触阈值为\(T_i=\max(1.0\,\mathrm{N},\mu_{0,i}+3\sigma_{0,i})\)，并要求连续越阈0.050 s。回顾性主要安全相关结局为接触后0.20–1.00 s的阈值参照超额力冲量：

\[
I_{excess,i}^{0.2:1.0}=\int_{0.20}^{1.00}\max[F_i(t_c+\tau)-T_i,0]d\tau.
\]

该窗口未前瞻性预注册，因此结局分析属于探索性。为检验E-A方向是否依赖0.20–1.00 s这一单一回顾性边界，本轮在查看敏感性结果前固定四个相邻窗口：保持终点1.00 s并把起点改为0.10或0.30 s，以及保持起点0.20 s并把终点改为0.80或1.20 s。所有窗口使用相同阈值、梯形积分、参与者内聚合和E-A配对方向评价。它们不被视为四个新增主要终点，也不用于选择最有利窗口或增加显著性声明。次要指标包括接触后0–0.20 s初始峰值力、任务开始至接触间隔、总任务时间和软件日志成功。软件成功不是独立视频或物理裁决。

## 3.4 统计分析

先在每名参与者、每种配置内对9次试次求平均，再形成E-A、G-A、F-E和F-G参与者层面配对差。报告均值差、自由度4的\(t\)分布95%置信区间、双侧配对\(t\)检验、全部\(2^5\)种符号分配的精确双侧符号翻转检验及精确Wilcoxon符号秩敏感性检验。对每项结局的4项对比分别进行Holm校正，并进行留一参与者分析。窗口敏感性强调效应方向、幅度范围和参与者一致性，不把相邻窗口当作独立假设族追求显著性。统计方法不会根据最小\(p\)值选择。5名独立参与者的双侧穷举符号翻转检验具有内在离散分辨率：即使5个差值方向完全一致，最小双侧\(p\)值仍为0.0625。因此，本文优先报告估计值、参与者一致性和预先固定的敏感性，而非阈值化显著性结论。

# 4. 结果

## 4.1 RQ1：本案例中的一致与偏离模式

A提供记录指令通过型对照。45/45次A试次在审计标志时间及结局窗口保持200 N/m记录平移刚度，观测指令偏差为零；这不构成物理阻抗测量。

G显示“符合可执行代码”不等于“符合名义实验语义”。45/45次G试次均按实现的1 N死区原始力规则激活，但42/45早于任务开始，42/45早于基线就绪，43/45早于记录接触；仅2/45满足接触后顺序。相对任务开始和接触的首次激活中位数分别为−0.379 s和−1.214 s。因此，G实际实现以接触前预激活为主，不是纯接触后力干预。

F显示名义规范与源代码实现不一致所产生的实际时序偏离。没有F试次在接触前激活，但仅3/45满足名义接触后+0.20 s门控；42/45早于名义门控。接触到激活中位时延为+0.0533 s，时序误差中位数为−0.1467 s。该模式与延迟路径混用墙上时钟和单调时钟的实现检查一致；现有分析没有把它另行归为\(C\neq R\)，因为尚未证明日志违背了混合时钟代码实际会产生的判断。

结局窗口暴露进一步表明同一标签内部并非均匀干预。在接触后0.20–1.00 s窗口中，E视觉暴露为39次完全、2次部分、4次零暴露；F视觉暴露为42次完全、0次部分、3次零暴露；F自适应及视觉+自适应联合暴露均为35次完全、7次部分、3次零暴露。暴露类别未用于删除试次。

正交的溯源完整性检查显示，全部180条清理后采集均具有同源CSV、事件JSON和摘要JSON，180条干预—结局连接全部有效，540个入选文件的SHA-256哈希全部通过，6条被替代记录仍可追溯。血缘修复前后4项主要冲量对比方向不变：E-A由−0.3416变为−0.3489 N·s，G-A保持−0.0742 N·s，F-E由−0.0469变为−0.0212 N·s，F-G由−0.3143变为−0.2958 N·s。该检查建立\(R_i\rightarrow Y_i\)连接的数据完整性，不构成干预交付保真度；该敏感性也不验证控制器时序。

![试次层面的实际干预保真度。](../19_publication_figures/figures/Fig03_realized_intervention_fidelity.png)

**图3.** 试次层面的实际干预保真度。（A）45次G试次的首次激活、任务开始、基线就绪与接触；可执行原始力规则45/45合规，但43/45在接触前激活。（B）45次F试次相对接触的首次激活；仅3/45满足名义+0.20 s门控，中位激活时间+0.0533 s，中位时序误差−0.1467 s。（C）E视觉、F视觉、F自适应及F联合暴露在结局窗口内的完全、部分和零暴露分布。试次级结果用于保真度描述；人体结局推断使用参与者\(n=5\)。

## 4.2 RQ2：偏离如何约束证据可容许解释

保真度分析没有根据结局删除或重分类试次，而是把名义比较改写为实际证据支持的最窄解释（表III）。

**表III. 名义主张、关键保真度证据与证据可容许解释。**

| 比较 | 名义或标签主张 | 关键保真度证据 | 允许表述 | 禁止表述 |
|---|---|---|---|---|
| G-A | 接触后力相关细化相对固定配置 | G缺少可恢复的独立接触后名义规范；代码无接触守卫；43/45接触前激活 | 以预激活为主的原始力自适应G分配相对固定A的描述性差异 | 纯接触后力自适应效应 |
| E-A | 视觉或刚度单因素效应 | E同时改变多个指令参数；视觉暴露39次完全、2次部分和4次零暴露 | E分配及其异质实际视觉暴露分布相对固定A的描述性差异 | 单独视觉、刚度或另一参数的因果效应 |
| F-E | 正确执行+0.20 s门控的增量力细化 | 混合时钟实现与名义门控不一致；仅3/45满足名义时序；窗口暴露异质 | 实际早期激活且暴露异质的F分配相对E分配的描述性差异 | 正确执行+0.20 s策略的增量效应 |
| F-G | 视觉×力交互或孤立视觉增量 | 两种配置的视觉、力规则、参数捆绑和实现时序均不同 | 两种实际捆绑及暴露分布之间的描述性差异 | 视觉主效应、力主效应或视觉×力交互 |

因此，A/G/E/F不能作为清晰的2×2析因设计解释。名义标签只组织分配；有文档支持的规范、源代码实现、实际轨迹和窗口暴露共同决定存档能够支持何种描述性统计比较与科学措辞。这些比较不因被称为“可容许估计目标”而自动获得因果含义。

## 4.3 RQ3：保真度重建后仍可解释的结局模式

主要阈值参照超额力冲量的参与者层面均值在A、G、E、F中分别为0.8073、0.7330、0.4584和0.4372 N·s。以下结果描述实际记录配置，不用于验证框架，也不构成单个控制成分的因果效应。

E-A冲量均值差为−0.3489 N·s（95% CI，−0.6080至−0.0898；\(t(4)=-3.739\)，配对\(t\)检验\(p=0.0201\)）。5名参与者差值均为负，范围−0.6006至−0.1331 N·s。精确符号翻转和Wilcoxon检验均为\(p=0.0625\)；4项对比Holm校正后，配对\(t\)检验\(p=0.0633\)，两种精确检验均为0.2500。因此，方向一致的估计不构成确认性证据。

固定相邻窗口敏感性显示，E-A差值没有依赖0.20–1.00 s这一单一边界（补充表S5）。将起点单独提前或推后0.10 s，或将终点单独缩短/延长0.20 s，参与者层面均值差均保持为负（−0.2438至−0.4307 N·s），且每个窗口内5名参与者方向均一致。所有窗口的双侧精确符号翻转\(p\)值均为0.0625，反映\(n=5\)下的离散分辨率；这些结果用于评价方向和幅度稳定性，而不是构造多个替代主要终点。

既有留一参与者敏感性提供了另一种稳定性检查：依次省略一名参与者后，5个E-A冲量均值差仍全部为负，范围−0.4028至−0.2860 N·s；5个子集的95%区间中有1个跨越零。该结果说明差值方向并非由单一参与者决定，但不会增加独立人体样本量，也不把探索性结果转化为确认性证据。

任务开始至接触间隔在A和E中的参与者层面均值分别为0.8974 s和2.6779 s，E-A差1.7805 s（95% CI，1.5084至2.0527；\(t(4)=18.165\)，配对\(t\)检验\(p=5.40\times10^{-5}\)）。5名参与者均为正；精确检验均为\(p=0.0625\)，Holm校正配对\(t\)检验\(p=0.000162\)，校正精确检验均为0.2500。该指标只表示从系统就绪到接触的记录间隔，不能证明操作者移动更慢或机器人接近时间更长。

总任务时间在A和E中的均值分别为16.2631 s和17.4758 s，E-A差1.2128 s（95% CI，0.5741至1.8514；\(t(4)=5.272\)，配对\(t\)检验\(p=0.00620\)）。5名参与者均为正；精确检验均为\(p=0.0625\)，Holm校正配对\(t\)检验\(p=0.0186\)，校正精确检验均为0.2500。较低的早期力暴露与较长的时间指标共同构成观测到的力—时间模式，但不能证明一般性的安全—效率机制。

G-A冲量差为−0.0742 N·s（95% CI，−0.1978至0.0494；\(p=0.1708\)），描述的是以预激活为主的实际G配置。F-E差为−0.0212 N·s（95% CI，−0.1433至0.1010；\(p=0.6556\)），5名参与者中3负2正，未显示稳定的实际配置增量差异。F-G差为−0.2958 N·s（95% CI，−0.5000至−0.0917；\(p=0.0158\)），但精确检验均为0.0625、Holm校正配对\(t\)检验为0.0633；该比较不是视觉×力交互证据。

![参与者层面的探索性E-A配对差。](../19_publication_figures/figures/Fig04_participant_EA_outcomes.png)

**图4.** 参与者层面的探索性E-A配对差。（A）阈值参照超额力冲量；（B）系统就绪至接触间隔；（C）总任务时间。空心点表示5名独立参与者的配对差，菱形及横线表示均值差及基于\(t\)的95%置信区间。E表示具有异质实际视觉暴露的捆绑配置分配；结果不代表单一视觉或刚度效应，系统就绪至接触间隔也不代表人体运动起点后的接近时间。

# 5. 讨论

## 5.1 对三个研究问题的回答

**RQ1：本案例同时存在一致与多种偏离模式。** A呈现记录指令一致；G呈现标签语义不足与接触前实际激活，但由于缺少独立同期规范，不把“接触后G”反推为已证实的\(N_m\)；F呈现名义+0.20 s要求与混合时钟实现不一致及其实际时序后果；E/F呈现窗口暴露异质性。G在45/45次试次中遵循其实际代码，却不能支持标签所暗示的接触后解释；F的源代码包含名义延迟说明，但实际时钟操作不能可靠实现该目标。这些是单一回顾性系统中的观察模式，不用于估计类似偏离在其他异步人机系统中的发生率。

**RQ2：不同干预断点产生不同推断后果。** \(N\neq C\)要求收窄干预语义，并包括名义守卫由不相容时钟实现的情况；\(C\neq R\)只在实际记录未再现代码及其输入所预测的状态时成立；实际暴露与结局窗口不匹配意味着标签对应暴露分布而非均匀状态。溯源完整性在另一正交维度上决定\(R_i\)能否可信连接到\(Y_i\)，但它不是干预交付本身。因而，框架的主要产出不是“通过率”，而是名义统计比较目标是否仍受支持以及科学措辞应如何改写；该改写本身不建立因果识别。

**RQ3：案例只支持有边界的实际配置模式。** E-A显示方向一致的较低早期力暴露估计，并伴随更长的系统就绪至接触间隔和总任务时间；四个固定相邻窗口中的E-A冲量差均为负，说明方向不依赖单一0.20–1.00 s边界。与此同时，5名独立参与者使双侧精确推断具有内在有限分辨率：5个差值方向全部一致时，最小穷举符号翻转\(p\)值仍为0.0625。因此，本文强调估计值、参与者一致性和敏感性，而非为\(p=0.0625\)增加bootstrap、Bayesian或混合模型以追求阈值显著性。多重性校正同样不支持确认性结论。G-A、F-E和F-G只能按实际捆绑和时序配置描述，不能回答正确接触门控策略、正确+0.20 s细化或视觉×力交互的效果。

## 5.2 对人机系统实验设计的启示

**采集前。** 研究者应冻结名义干预规范，明确哪些事件允许激活、使用何种时钟、干预应覆盖哪个结局窗口，以及谁或什么是独立实验单位。控制器标签不应代替可执行规范。

**采集中。** 系统应同时记录人体输入、感知事件、激活状态、指令参数、机器/环境事件、时钟域和精确采集身份。人体输入的存在并不自动提供有效行为指标；例如，本案例记录了Omega.7位置，却没有外部验证的人体运动起点，因此不能在分析阶段任意选择阈值把`task_start`改写为人体行为时间。

**推断前。** 应在不查看结局方向的前提下检查\(N\rightarrow C\)、\(C\rightarrow R\)，并通过正交的溯源完整性验证\(R\xleftrightarrow{\mathcal{P}}Y\)。试次级保真度观察与人体推断单位必须分开报告。只有完成这些检查后，才能使用“条件F改善了某结局”一类陈述；若证据只支持实际捆绑配置，则结论也必须停留在该层级。

最低证据包并不要求所有人机实验采用相同传感器或控制架构。它要求每个科学比较都能回答三个基本问题：计划交付什么、实际记录了什么、结局由同一次采集的哪些样本构成。该原则可迁移到共享控制、驾驶自动化、辅助机器人、可穿戴交互和其他异步人机系统，但框架的外部适用性仍需前瞻性验证。

## 5.3 案例解释与局限

E在接触附近的记录平移刚度低于A（补充图S1），为较低力暴露提供物理上相容的背景，但记录刚度不是物理闭环阻抗，E还同时改变旋转刚度、阻尼、触觉反馈和夹爪力。人的等待、停顿或对反馈的适应也可能参与形成结果，但存档没有直接测量注意、谨慎程度、意图或经验证的人体运动起点。因此，E-A只能解释为E分配及其异质实际视觉暴露分布与固定配置之间的差异。

框架仅在一个存档遥操作系统中得到回顾性操作化，不能恢复未记录的软件状态，也未在其他人机系统中外部验证。案例只有5名参与者；180次试次不是180个独立人体样本。0.20–1.00 s冲量窗口为回顾性选择；相邻窗口的方向稳定降低了结论依赖单一边界的担忧，但不能把终点转化为前瞻性预注册结局。E/F为多参数捆绑配置，随机化或平衡顺序未恢复，因而不能排除学习、疲劳和顺序影响。

力信号来自机器人内部外部力估计，而非独立传感器；物体身份、姿态、放置和容差不完整，软件成功没有视频或人工复核。参与者人口学、经验和训练信息应尽力依据同期记录恢复，否则必须作为代表性局限保留。6组记录替换遵循固定身份规则并有敏感性分析，但同期故障依据和最初判断是否发生于结局查看前仍未知。伦理审批/豁免和知情同意信息则不能仅作为局限：必须在投稿前得到机构记录支持。

# 6. 结论

异步人机实验中的名义条件分配不能独立证明相应干预已经由耦合人—机器系统实际经历。本文提出的\(N_m\rightarrow C_m\rightarrow R_i\rightarrow Y_i\)框架，将名义语义、可执行守卫、实际事件与参数轨迹和结局窗口连接起来，并以正交的采集溯源完整性保证\(R_i\)与\(Y_i\)属于同一次采集。回顾性案例表明，实际干预保真度的主要作用不是排除试次，而是在语义、运行时或暴露发生偏离时重新界定证据可容许的统计比较与科学解释；这种界定不自动赋予因果含义。对人机系统评价而言，只有重建实际干预并验证干预—结局连接，模式标签才能从实验组织工具转化为有证据支持的推断对象。

# 参考文献

1. Hannaford, B. (1989). A design framework for teleoperators with kinesthetic feedback. *IEEE Transactions on Robotics and Automation, 5*(4), 426–434. https://doi.org/10.1109/70.88057
2. Lawrence, D. A. (1993). Stability and transparency in bilateral teleoperation. *IEEE Transactions on Robotics and Automation, 9*(5), 624–637. https://doi.org/10.1109/70.258054
3. Hokayem, P. F., & Spong, M. W. (2006). Bilateral teleoperation: An historical survey. *Automatica, 42*(12), 2035–2057. https://doi.org/10.1016/j.automatica.2006.06.027
4. Passenberg, C., Peer, A., & Buss, M. (2010). A survey of environment-, operator-, and task-adapted controllers for teleoperation systems. *Mechatronics, 20*(7), 787–801. https://doi.org/10.1016/j.mechatronics.2010.04.005
5. Huang, K., Chitrakar, D., Rydén, F., & Chizeck, H. J. (2019). Evaluation of haptic guidance virtual fixtures and 3D visualization methods in telemanipulation—A user study. *Intelligent Service Robotics, 12*, 289–301. https://doi.org/10.1007/s11370-019-00283-w
6. Rakita, D., Mutlu, B., & Gleicher, M. (2020). Effects of onset latency and robot speed delays on mimicry-control teleoperation. In *Proceedings of the 2020 ACM/IEEE International Conference on Human-Robot Interaction*. https://doi.org/10.1145/3319502.3374838
7. Louca, J., Eder, K., Vrublevskis, J., & Tzemanaki, A. (2024). Impact of haptic feedback in high latency teleoperation for space applications. *ACM Transactions on Human-Robot Interaction, 13*(2), Article 16, 1–21. https://doi.org/10.1145/3651993
8. Gong, Y., Mat Husin, H., Erol, E., Ortenzi, V., & Kuchenbecher, K. J. (2024). AiroTouch: Enhancing telerobotic assembly through naturalistic haptic feedback of tool vibrations. *Frontiers in Robotics and AI, 11*, 1355205. https://doi.org/10.3389/frobt.2024.1355205
9. Hogan, N. (1985). Impedance control: An approach to manipulation: Part I—Theory. *Journal of Dynamic Systems, Measurement, and Control, 107*(1), 1–7. https://doi.org/10.1115/1.3140702
10. Walker, D. S., Wilson, R. P., & Niemeyer, G. (2010). User-controlled variable impedance teleoperation. In *2010 IEEE International Conference on Robotics and Automation*. https://doi.org/10.1109/ROBOT.2010.5509811
11. Buchli, J., Stulp, F., Theodorou, E., & Schaal, S. (2011). Learning variable impedance control. *The International Journal of Robotics Research, 30*(7), 820–833. https://doi.org/10.1177/0278364911402527
12. Ajoudani, A., Tsagarakis, N. G., & Bicchi, A. (2012). Tele-impedance: Teleoperation with impedance regulation using a body–machine interface. *The International Journal of Robotics Research, 31*(13), 1642–1656. https://doi.org/10.1177/0278364912464668
13. Peternel, L., Petrič, T., & Babič, J. (2018). Robotic assembly solution by human-in-the-loop teaching method based on real-time stiffness modulation. *Autonomous Robots, 42*, 1–17. https://doi.org/10.1007/s10514-017-9635-z
14. Abu-Dakka, F. J., Rozo, L., & Caldwell, D. G. (2018). Force-based variable impedance learning for robotic manipulation. *Robotics and Autonomous Systems, 109*, 156–167. https://doi.org/10.1016/j.robot.2018.07.008
15. Abu-Dakka, F. J., & Saveriano, M. (2020). Variable impedance control and learning—A review. *Frontiers in Robotics and AI, 7*, 590681. https://doi.org/10.3389/frobt.2020.590681
16. Michel, Y., Rahal, R., Pacchierotti, C., Robuffo Giordano, P., & Lee, D. (2021). Bilateral teleoperation with adaptive impedance control for contact tasks. *IEEE Robotics and Automation Letters, 6*(3), 5429–5436. https://doi.org/10.1109/LRA.2021.3066974
17. Peternel, L., & Ajoudani, A. (2023). After a decade of teleimpedance: A survey. *IEEE Transactions on Human-Machine Systems, 53*(2), 401–416. https://doi.org/10.1109/THMS.2022.3231703
18. Michel, Y., Li, Z., & Lee, D. (2023). A learning-based shared control approach for contact tasks. *IEEE Robotics and Automation Letters, 8*(12), 8002–8009. https://doi.org/10.1109/LRA.2023.3322332
19. Huang, Y.-C., Abbink, D. A., & Peternel, L. (2021). A semi-autonomous tele-impedance method based on vision and voice interfaces. In *2021 20th International Conference on Advanced Robotics*, 180–186. https://doi.org/10.1109/ICAR53236.2021.9659427
20. Siegemund, G., Díaz Rosales, A., Glodde, A., Dietrich, F., & Peternel, L. (2024). Semi-autonomous teleimpedance based on visual detection of object geometry and material and its relation to environment. In *2024 IEEE-RAS 23rd International Conference on Humanoid Robots*, 779–786. https://doi.org/10.1109/Humanoids58906.2024.10769858
21. Jekel, H. H. A., Díaz Rosales, A., & Peternel, L. (2026). Visio-verbal teleimpedance interface: Enabling semi-autonomous control of physical interaction via eye tracking and speech. *Frontiers in Robotics and AI, 13*, 1749105. https://doi.org/10.3389/frobt.2026.1749105
22. Vogels, I. M. L. C. (2004). Detection of temporal delays in visual-haptic interfaces. *Human Factors, 46*(1), 118–134. https://doi.org/10.1518/hfes.46.1.118.30394
23. Bonsignorio, F., & del Pobil, A. P. (2015). Toward replicable and measurable robotics research [From the Guest Editors]. *IEEE Robotics & Automation Magazine, 22*(3), 32–35. https://doi.org/10.1109/MRA.2015.2452073
24. Bonsignorio, F. (2017). A new kind of article for reproducible research in intelligent robotics [From the Field]. *IEEE Robotics & Automation Magazine, 24*(3), 178–182. https://doi.org/10.1109/MRA.2017.2722918
25. Gunes, H., Broz, F., Crawford, C. S., Rosenthal-von der Pütten, A., Strait, M., & Riek, L. (2022). Reproducibility in human-robot interaction: Furthering the science of HRI. *Current Robotics Reports, 3*(4), 281–292. https://doi.org/10.1007/s43154-022-00094-5
26. Aldana-López, R., Aragüés, R., & Sagüés, C. (2023). Latency vs precision: Stability preserving perception scheduling. *Automatica, 155*, 111123. https://doi.org/10.1016/j.automatica.2023.111123
27. Bagchi, S., Holthaus, P., Beraldo, G., Senft, E., Hernandez, D., Han, Z., Jayaraman, S. K., Rossi, A., Esterwood, C., Andriella, A., & Pridham, P. S. (2023). Towards improved replicability of human studies in human-robot interaction. In *Companion of the 2023 ACM/IEEE International Conference on Human-Robot Interaction*. https://doi.org/10.1145/3568294.3580162
28. Marchesi, S., De Tommaso, D., Kompatsiari, K., Wu, Y., & Wykowska, A. (2024). Tools and methods to study and replicate experiments addressing human social cognition in interactive scenarios. *Behavior Research Methods, 56*(7), 7543–7560. https://doi.org/10.3758/s13428-024-02434-z
29. Huang, J., Erdogan, C., Zhang, Y., Moore, B., Luo, Q., Sundaresan, A., & Roşu, G. (2014). ROSRV: Runtime verification for robots. In *Runtime Verification* (Lecture Notes in Computer Science, Vol. 8734, pp. 247–254). Springer. https://fsl.cs.illinois.edu/publications/huang-erdogan-zhang-moore-luo-sundaresan-rosu-2014-rvtool.html
30. Carroll, C., Patterson, M., Wood, S., Booth, A., Rick, J., & Balain, S. (2007). A conceptual framework for implementation fidelity. *Implementation Science, 2*, 40. https://doi.org/10.1186/1748-5908-2-40
31. Lundberg, I., Johnson, R., & Stewart, B. M. (2021). What is your estimand? Defining the target quantity connects statistical evidence to theory. *American Sociological Review, 86*(3), 532–565. https://doi.org/10.1177/00031224211004187
