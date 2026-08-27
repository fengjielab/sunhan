# 超越实验条件标签：异步人机实验的运行时暴露保真度框架

> **稿件状态。** THMS定向中文审批稿v3。伦理审批或豁免机构、编号、日期、知情同意程序及存档数据再使用范围必须依据真实同期记录补齐：`[ETHICS RECORD REQUIRED—DO NOT SUBMIT]`。作者、单位、基金、利益冲突、作者贡献、致谢及数据代码可用性声明也须在投稿前由作者据实完成。

## 摘要

异步人机实验常用“固定”“自适应”或“视觉使能”等标签定义条件，但标签不能证明耦合系统在结局窗口内经历了相应状态，更不能证明软件命令已按预期转化为物理刺激。本文提出五层运行时暴露保真度框架，将名义规范、代码实现、记录运行状态、独立测得的物理传递和人体结果表示为 (N_m\rightarrow C_m\rightarrow R_i^{rec}\rightarrow D_i^{phys}\rightarrow Y_i)，并将采集身份与哈希溯源作为贯穿各层的正交证据。框架用激活时序误差 \(\epsilon_i\) 和结局窗口暴露比例 \(\Phi_i\)限定证据可容许比较，而不把多维保真度压缩为单一分数。证据包括两个互补案例。5人回顾性案例在180个清理后试次中定位了名义语义、可执行逻辑和记录状态的断点。随后，20名彼此独立参与者完成300个计划试次，五个冻结条件系统改变激活时刻和持续时间；294次完整试次进入记录层判据分析，6次安全中止保留在流程与安全分母中。独立离线分析在294/294次中恢复正确条件，准确率100%，精确95%置信区间98.75%–100%。激活时刻绝对误差的MAE、P95和最大值为2.381、4.957和5.408 ms；暴露比例绝对误差为0.001798、0.005996和0.006760。20名参与者的平均接近时长为1.3033–2.8360 s，记录层准确性在轨迹长度、时长和限幅率四分位中保持稳定。65/294次在试次任意时刻出现命令限幅，47/294次在结局窗口内出现；C4虽有11次全试次限幅，窗口内为0次，说明窗口绑定会改变可解释的暴露证据。记录向量是限幅后发送给API的软件命令，API返回不是物理确认；本研究没有独立输出传感器，因此物理传递层保持未观测。人体力结果仅作参与者层面的探索性描述。结果支持单平台内部的记录层判据有效性，并明确指出它不能替代端到端物理测量或人体因果证据。

**关键词：** 人机系统评价；运行时暴露；干预保真度；异步遥操作；结果窗口；判据有效性；数据溯源

# 1. 引言

人机闭环遥操作把人的感知和适应、主端触觉接口、监督控制器、远端机器人及环境耦合在同一动态系统中。接触结果不是某个控制器的孤立输出，而是各组成部分在不同频率、线程和时钟域中持续作用的结果（Hannaford, 1989; Lawrence, 1993; Hokayem and Spong, 2006）。近年来，触觉引导、共享控制和可变阻抗继续扩展人机协作能力，但也增加了实验条件在运行时被改变、延迟或限幅的机会（Rakita et al., 2020; Michel et al., 2021; Peternel and Ajoudani, 2023; Louca et al., 2024）。

一个具体例子说明标签为何不够。假设协议把某条件描述为“接触后200 ms提高反馈增益”，分析窗口为接触后200–1000 ms。代码可能因接触事件线程和控制线程异步而在203 ms写入新状态；发送前，2 N安全上限又可能截断命令。日志能支持“记录状态从203 ms起激活”和“发送软件命令发生限幅”，却不能在没有独立传感器时支持“操作者端物理力从203 ms起按比例增加”。如果分析只保留一个条件标签，这三个不同命题会被错误合并。

时延与透明性研究量化了通信和控制延迟（Vogels, 2004; Rakita et al., 2020; Aldana-López et al., 2023）；机器人运行时验证关注执行轨迹是否满足形式属性（Huang et al., 2014）；实施保真度研究关注方案是否按设计实施（Carroll et al., 2007）；HRI可重复性研究要求更完整地报告装置、流程和分析（Gunes et al., 2022; Bagchi et al., 2023; Marchesi et al., 2024）。触觉装置研究进一步表明，命令输入与实际输出精度必须通过附加力传感器区分（Liu et al., 2022）。这些工作尚未形成一条直接服务于异步人机实验推断的联合规则：应如何把标签追踪到结果窗口内的记录暴露，怎样显式保留软件记录与物理传递之间的缺口，以及证据缺口出现后还能进行何种比较。

本文回答三个研究问题：

- **RQ1：** 五层框架能否定位名义标签、代码实现、记录状态、物理传递和人体结果之间的断点？
- **RQ2：** 在人体产生的异质运动轨迹下，能否准确恢复记录层激活时序、结果窗口暴露和条件类别？
- **RQ3：** 不同证据缺口如何限制证据可容许比较与科学措辞？

本文贡献有三点。第一，提出 (N\rightarrow C\rightarrow R^{rec}\rightarrow D^{phys}\rightarrow Y) 五层证据链，并把结果窗口暴露作为连接运行状态和结果的核心量。第二，提出向量化保真度报告：语义、实现、记录时序、窗口暴露、发送命令、物理传递和溯源分别给出状态，不计算掩盖断点的总分。第三，以5人回顾性诊断和20人记录层判据实验建立互补证据；后者使用人体轨迹变异进行压力测试，但不以参与者数量替代独立硬件测量。

# 2. 五层运行时暴露保真度框架

## 2.1 证据链与正交溯源

模式 \(m\) 下试次 \(i\) 的证据链表示为

\[
N_m\rightarrow C_m\rightarrow R_i^{rec}\rightarrow D_i^{phys}\rightarrow Y_i.
\]

其中，\(N_m\) 是有同期规范支持的目标参数、守卫、事件顺序和预期暴露；\(C_m\) 是采集软件实际实现的状态机、初始化、更新与限幅逻辑；\(R_i^{rec}=\{\mathcal E_i,a_i(t),\boldsymbol\theta_i^{log}(t),\mathbf u_i^{cmd}(t)\}\) 是事件、记录激活状态、参数轨迹及限幅后发送命令；\(D_i^{phys}\) 是由独立传感器测得的端到端物理刺激；\(Y_i\) 是明确窗口内的人体或系统结果。

精确采集溯源 \(\mathcal P_i\) 与五层链正交。它证明事件、逐样本记录、摘要和结果属于同一采集，并记录软件与配置身份。哈希一致只能支持文件身份，不能证明命令被物理装置准确实现。同样，API成功返回只能支持软件调用完成，不能代替输出传感器。

## 2.2 记录时序、窗口暴露与发送命令

若计划激活时刻为 \(t^N_{act,i}\)，记录激活时刻为 \(t^{rec}_{act,i}\)，则

\[
\epsilon_i=t^{rec}_{act,i}-t^N_{act,i}.
\]

对结局窗口 \(W=[t_0,t_1]\) 和记录激活状态 \(a_i(t)\)，记录层暴露比例为

\[
\Phi_i^{rec}=\frac{1}{t_1-t_0}\int_{t_0}^{t_1}a_i(t)\,dt.
\]

发送命令层可另行描述为

\[
Q_i^{cmd}=\int_{t_0}^{t_1}\lVert\mathbf u_i^{cmd}(t)\rVert\,dt,
\]

并同时报告窗口限幅持续比例。\(Q_i^{cmd}\) 的单位可写为软件命令N·s，但它不是独立测得的物理冲量。本文的记录层判据针对 \(\epsilon_i\) 和 \(\Phi_i^{rec}\)，不以 \(Q_i^{cmd}\) 通过与否替代物理层。

## 2.3 向量化保真度与证据可容许比较

保真度状态写为向量

\[
\mathbf F_i=(F_N,F_C,F_{R,t},F_{R,\Phi},F_{R,cmd},F_D,F_P),
\]

各分量可为“支持”“受限”“不可获得”或“未独立观测”。不定义加权总分，因为不同缺口限制不同命题。例如，记录时序恢复准确而物理层未观测时，可以比较记录暴露，但不能把命令积分解释为实际触觉剂量。

本文用“证据可容许比较”指现有层级证据允许表达的最窄比较。只有名义、实现、记录和物理层均支持时，条件差异才可按完整物理干预语义解释；若仅记录层支持，则比较必须限定为记录状态或软件命令分布。观察到的实际状态不会因事后分组自动获得因果含义。

![五层框架及本研究证据边界。](analysis/figures/fig1_five_layer_framework.png)

**图1.** 五层运行时暴露证据链。红色物理层在本研究中未独立观测；溯源是贯穿各层的正交证据。

# 3. 研究一：5人回顾性诊断

## 3.1 平台与档案

存档平台包含Omega.7主端、Intel RealSense D435i视觉通道、监督控制器、Franka Emika Panda机械臂及夹爪。5名参与者在3种材料、3个区组和A/G/E/F四种配置下形成180个清理后试次。人体结果的独立单位是参与者 \(n=5\)，不是180个试次。力通道为Panda内部估计外力 `O_F_ext_hat_K`，记录刚度为软件指令参数。

配置A为固定参照；G包含原始力规则；E同时改变视觉和若干指令参数；F捆绑视觉与自适应路径。主要回顾性结果窗口为接触后0.20–1.00 s。该研究的作用是检验五层框架能否改变对档案比较的解释，而不是重新证明原控制器效果。

## 3.2 重建与断点

重建联合名义说明、采集代码、事件JSON、逐样本CSV和摘要文件。186条采集记录经冻结身份规则选出180条分析采集；同源文件的采集身份与SHA-256用于连接记录状态和结果。

G的45/45次遵循可执行原始力规则，但43/45次在记录接触前激活，因而不能解释为纯接触后干预。F没有接触前激活，但仅3/45次实现名义接触后+0.20 s门控；接触至激活中位数为+0.0533 s。E视觉暴露为39次完整、2次部分、4次零暴露；F联合暴露为35次完整、7次部分、3次零暴露。因此A/G/E/F不构成清晰的2×2析因设计：E−A只能描述捆绑配置及其异质视觉暴露；G−A不能代表孤立接触后力效应；F−E不能代表正确+0.20 s门控的增量效应；F−G不能代表视觉×力交互。

# 4. 研究二：20人记录层判据实验

## 4.1 设计与已知计划模式

正式实验使用同一Omega.7—Panda平台的隔离 `kfb_timing` 模式，关闭视觉、夹爪动作及其他自适应策略，仅操纵 \(K_{fb}=0.5\rightarrow0.7\) 的记录激活时刻和持续时间。F01–F20为20名彼此独立的参与者。每人3个区组、每区组五条件各一次，共15个计划试次；固定队列为300个试次。冻结顺序曾预留F01–F24位置，本分析仅使用已完成的F01–F20。

控制循环目标为200 Hz。接触由基线校正力超过阈值并持续0.050 s确认；结果窗口为接触后0.20–1.00 s。Panda估计外力超过5 N触发安全中止，触觉命令范数在发送前限制为2 N。

| 条件 | 计划模式 | 激活区间，接触后s | 预期 \(\epsilon\)，s | 预期 \(\Phi^{rec}\) |
|---|---|---:|---:|---:|
| C0 | Correct | 0.20–1.20 | 0.00 | 1.000 |
| C1 | Early | 0.05–1.20 | −0.15 | 1.000 |
| C2 | Late | 0.50–1.20 | +0.30 | 0.625 |
| C3 | Short | 0.20–0.60 | 0.00 | 0.500 |
| C4 | Outside window | 1.10–1.30 | +0.90 | 0.000 |

这些值是冻结调度模式的真值。它们为计划状态到记录状态的重建提供判据，但不构成物理输出真值。

## 4.2 独立分析、队列与溯源

离线程序不导入在线控制器条件常量，只读取冻结协议JSON、oracle及正式采集文件。程序只接受F01–F20，要求每人恰有15个逻辑试次，并核验300组CSV、事件、摘要和manifest。缺失、重复、额外参与者、身份错配、掩码错配或配置哈希错配都会立即失败。历史同名F01–F05不在输入根目录中，未被扫描或合并。

CSV要求原始字节SHA-256一致。事件和摘要JSON同时计算原始字节哈希与规范化文本哈希；规范化只处理UTF-8 BOM和换行。300个CSV均字节一致；事件和摘要因换行表示不同而字节不同，但300/300规范化内容一致。原始文件没有被修改。

## 4.3 终点、界限与人体轨迹压力测试

主要记录层终点为条件识别准确率及精确二项95%置信区间、激活时刻绝对误差MAE/P95/最大值、暴露比例绝对误差MAE/P95/最大值。界限为识别率≥95%，时序MAE和P95≤20 ms、最大值≤50 ms，\(\Phi\) MAE≤0.02。20 ms对应200 Hz下4个周期；50 ms对应10个周期且等于接触确认保持间隔；\(\Phi=0.02\)对应0.8 s窗口中的16 ms暴露误差。这些界限早于当前正式数据形成，但未在公共登记平台登记。

控制周期、Omega有效率、发送失败、安全中止和命令限幅分别报告。结果窗口限幅用左保持积分；限幅后命令范数用梯形积分。`haptic_send_ok`仅表示API返回。

20人用于检验人在环运动差异是否破坏记录层恢复。每个试次计算任务开始至接触时长、机器人与Omega路径、机器人峰值速度、内部力冲量和限幅比例；再以参与者为单位，按接近时长、机器人路径和全试次限幅率四分位汇总识别率、时序MAE和暴露MAE，不进行显著性筛选。

人体结果仅在补充材料中报告参与者级C1–C4相对C0配对差和排除限幅试次的敏感性分析。

# 5. 结果

## 5.1 试次流程与记录层恢复

300个计划试次中294次完整并可评估，6次因5 N规则安全中止。294次均恢复为正确条件，准确率100%，精确95%置信区间98.75%–100%。

| 条件 | 可评估/计划 | 识别率（精确95% CI） | 目标启动，s | 记录启动参与者均值，s | 时序MAE，ms | 目标 \(\Phi\) | 记录 \(\Phi\) 参与者均值 | \(\Phi\) MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| C0 | 60/60 | 100% [94.04%, 100%] | 0.200 | 0.20291 | 2.932 | 1.000 | 0.99635 | 0.003653 |
| C1 | 59/60 | 100% [93.94%, 100%] | 0.050 | 0.05109 | 1.095 | 1.000 | 1.00000 | 0.000000 |
| C2 | 58/60 | 100% [93.83%, 100%] | 0.500 | 0.50251 | 2.528 | 0.625 | 0.62186 | 0.003160 |
| C3 | 60/60 | 100% [94.04%, 100%] | 0.200 | 0.20282 | 2.826 | 0.500 | 0.49977 | 0.002100 |
| C4 | 57/60 | 100% [93.73%, 100%] | 1.100 | 1.10248 | 2.513 | 0.000 | 0.00000 | 0.000000 |

总体时序绝对误差MAE、P95和最大值为2.381、4.957和5.408 ms；暴露绝对误差为0.001798、0.005996和0.006760，均满足既定界限。

![计划模式到记录状态的恢复。](analysis/figures/fig2_record_layer_recovery.png)

**图2.** 黑线为冻结计划模式，蓝点为试次记录值，红点为均值。该图验证记录层恢复，不表示物理输出或人体效果。

## 5.2 命令层与窗口绑定

294个可评估试次中，65次在试次任意时刻发生至少一次限幅，47次在结果窗口内发生限幅。C0–C4窗口限幅试次数分别为14、13、11、9和0；窗口限幅平均比例分别为0.1103、0.1021、0.0610、0.0230和0。C4有11次全试次限幅，但由于计划激活位于结果窗口之后，窗口内为0次。这一差异说明，不绑定时间窗口的“是否限幅”不能代表结果所对应的命令暴露。

参与者均值的限幅后发送命令积分在C0–C4分别为0.9773、1.0224、0.8394、0.7891和0.5917软件命令N·s。它描述发送给触觉API的记录向量，不是操作者端实际力冲量。

![记录命令层限幅与命令积分。](analysis/figures/fig3_command_layer.png)

**图3.** 左图区分全试次和结果窗口限幅；右图是限幅后发送命令积分。两者均属于记录软件命令层。

## 5.3 人体轨迹变异压力测试

参与者平均任务开始至接触时长为1.3033–2.8360 s，全部完整试次范围为0.6145–5.3001 s；参与者平均接近机器人路径为0.00954–0.02444 m，内部力冲量为0.2492–1.1881 N·s，全试次限幅率为6.67%–78.57%。

尽管轨迹差异明显，每名参与者记录层识别率均为100%。参与者时序MAE范围为1.386–3.052 ms，暴露MAE为0.000771–0.002521。按接近时长、机器人路径和限幅率划分的12个描述性四分位组中，平均识别率均为100%，时序MAE为2.23–2.62 ms，暴露MAE为0.00143–0.00203。

![20人轨迹变异与逐参与者恢复。](analysis/figures/fig4_variability_stress_test.png)

**图4.** 参与者平均接近时长以及逐参与者时序和暴露误差。该分析是人在环轨迹变异压力测试，不替代物理传感器验证。

## 5.4 系统质量与探索性结果

安全中止按C0–C4为0、1、2、0和3次。所有完整试次的Omega窗口有效率不低于99%；没有控制周期P99超过20 ms或最大值超过50 ms，也没有触觉API发送失败。

探索性人体配对差、参与者方向及排除限幅试次结果置于补充材料。正文不以任何人体差异支持框架成功；主要成功标准仅为冻结计划模式到记录状态的 \(\epsilon\)、\(\Phi\) 和条件类别恢复。

# 6. 讨论

## 6.1 框架的新意在结果窗口绑定

五层链的重点不是增加检查项，而是把动态干预绑定到结果窗口。回顾性案例表明，名义相同或看似析因的配置可能产生提前、部分或零记录暴露；正式实验进一步表明，全试次限幅与窗口限幅可以得出不同结论。C4的11次全试次限幅和0次窗口限幅是最直接例子。因而，异步系统的实验条件应表示为带时序、状态和窗口的运行对象，而不是静态标签。

向量化报告避免“某层通过”掩盖其他层缺口。本研究的记录时序和暴露恢复达到既定界限，同时触觉命令频繁限幅且物理层未观测。正确表述是记录层判据得到单平台内部支持，而不是整条端到端链已被证明。

## 6.2 两个案例的不同证据角色

5人案例证明框架能够发现真实档案中的解释断点，并把原A/G/E/F比较收窄到证据允许的内容。20人实验则在冻结计划模式下检验记录层测量和分类。后者不依赖原人体结果是否理想，因此回应“仅继续利用不理想旧数据”的质疑；但它也不会反过来证明原控制器有效。

20人的作用不是扩大试次数，而是让相同计划模式经历不同的人体接近时间、轨迹、速度、力和限幅背景。四分位结果表明这些变化没有破坏记录恢复。该证据仍来自同一平台和日志生态，无法排除共同模式错误。

## 6.3 有效性边界与下一步

第一，计划模式、在线状态机和记录架构来自同一系统；虽然离线程序独立读取冻结配置且不导入控制器常量，共同代码或共同时间源错误仍可能存在。第二，`haptic_send_ok`是API返回，限幅后向量是软件记录；没有负载传感器、手柄力传感器或独立F/T通道，因此 \(D^{phys}\) 保持未独立观测。触觉输出准确性研究采用附加力传感器形成独立测量链（Liu et al., 2022），这正是未来端到端验证所需的证据。第三，Panda外力为内部估计，人体力结果只用于探索。第四，本研究是单平台固定接触任务，不能代表复杂抓取、视觉感知、长时延网络或第二团队的软件生态。

伦理治理是投稿硬条件。人口统计、训练、风险告知、知情同意和伦理机构信息必须从真实记录补齐；数据文件与哈希不能替代研究治理证据。Son et al. (2025)在THMS形式方法验证研究中以明确的人体实验和伦理流程建立证据，这也说明“方法验证”不能降低人体研究报告要求。

# 7. 结论

本文提出五层运行时暴露保真度框架，将名义规范、代码、记录状态、物理传递和人体结果明确分开，并以结果窗口暴露连接动态干预和可解释结果。5人回顾性案例展示框架如何发现语义与运行断点；20人正式实验在294个完整试次中实现294/294记录条件识别，时序误差P95为4.957 ms，暴露误差P95为0.005996，并在显著的人体轨迹差异下保持稳定。命令限幅、API返回、内部力估计和未观测物理层被单独保留。由此，研究支持的是计划模式到记录运行状态的单平台内部判据有效性，而不是控制器疗效、人体因果效果或端到端物理传递。

# 参考文献

1. Hannaford, B. (1989). A design framework for teleoperators with kinesthetic feedback. *IEEE Transactions on Robotics and Automation, 5*(4), 426–434. https://doi.org/10.1109/70.88057
2. Lawrence, D. A. (1993). Stability and transparency in bilateral teleoperation. *IEEE Transactions on Robotics and Automation, 9*(5), 624–637. https://doi.org/10.1109/70.258054
3. Hokayem, P. F., & Spong, M. W. (2006). Bilateral teleoperation: An historical survey. *Automatica, 42*(12), 2035–2057. https://doi.org/10.1016/j.automatica.2006.06.027
4. Passenberg, C., Peer, A., & Buss, M. (2010). A survey of environment-, operator-, and task-adapted controllers for teleoperation systems. *Mechatronics, 20*(7), 787–801. https://doi.org/10.1016/j.mechatronics.2010.04.005
5. Vogels, I. M. L. C. (2004). Detection of temporal delays in visual-haptic interfaces. *Human Factors, 46*(1), 118–134. https://doi.org/10.1518/hfes.46.1.118.30394
6. Hogan, N. (1985). Impedance control: An approach to manipulation: Part I—Theory. *Journal of Dynamic Systems, Measurement, and Control, 107*(1), 1–7. https://doi.org/10.1115/1.3140702
7. Walker, D. S., Wilson, R. P., & Niemeyer, G. (2010). User-controlled variable impedance teleoperation. In *IEEE ICRA*. https://doi.org/10.1109/ROBOT.2010.5509811
8. Buchli, J., Stulp, F., Theodorou, E., & Schaal, S. (2011). Learning variable impedance control. *International Journal of Robotics Research, 30*(7), 820–833. https://doi.org/10.1177/0278364911402527
9. Ajoudani, A., Tsagarakis, N. G., & Bicchi, A. (2012). Tele-impedance: Teleoperation with impedance regulation using a body–machine interface. *International Journal of Robotics Research, 31*(13), 1642–1656. https://doi.org/10.1177/0278364912464668
10. Huang, J., et al. (2014). ROSRV: Runtime verification for robots. In *Runtime Verification*, 247–254.
11. Carroll, C., Patterson, M., Wood, S., Booth, A., Rick, J., & Balain, S. (2007). A conceptual framework for implementation fidelity. *Implementation Science, 2*, 40. https://doi.org/10.1186/1748-5908-2-40
12. Bonsignorio, F., & del Pobil, A. P. (2015). Toward replicable and measurable robotics research. *IEEE Robotics & Automation Magazine, 22*(3), 32–35. https://doi.org/10.1109/MRA.2015.2452073
13. Huang, K., Chitrakar, D., Rydén, F., & Chizeck, H. J. (2019). Evaluation of haptic guidance virtual fixtures and 3D visualization methods in telemanipulation—A user study. *Intelligent Service Robotics, 12*, 289–301. https://doi.org/10.1007/s11370-019-00283-w
14. Rakita, D., Mutlu, B., & Gleicher, M. (2020). Effects of onset latency and robot speed delays on mimicry-control teleoperation. In *ACM/IEEE HRI*. https://doi.org/10.1145/3319502.3374838
15. Abu-Dakka, F. J., & Saveriano, M. (2020). Variable impedance control and learning—A review. *Frontiers in Robotics and AI, 7*, 590681. https://doi.org/10.3389/frobt.2020.590681
16. Michel, Y., Rahal, R., Pacchierotti, C., Robuffo Giordano, P., & Lee, D. (2021). Bilateral teleoperation with adaptive impedance control for contact tasks. *IEEE Robotics and Automation Letters, 6*(3), 5429–5436. https://doi.org/10.1109/LRA.2021.3066974
17. Gunes, H., et al. (2022). Reproducibility in human-robot interaction: Furthering the science of HRI. *Current Robotics Reports, 3*(4), 281–292. https://doi.org/10.1007/s43154-022-00094-5
18. Liu, G.-Y., Wang, Y., Huang, C., Guan, C., Ma, D.-T., Wei, Z., & Qiu, X. (2022). Experimental evaluation on haptic feedback accuracy by using two self-made haptic devices and one additional interface in robotic teleoperation. *Actuators, 11*(1), 24. https://doi.org/10.3390/act11010024
19. Bagchi, S., et al. (2023). Towards improved replicability of human studies in human-robot interaction: Recommendations for formalized reporting. In *HRI 2023 Companion*. https://doi.org/10.1145/3568294.3580162
20. Aldana-López, R., Aragüés, R., & Sagüés, C. (2023). Latency vs precision: Stability preserving perception scheduling. *Automatica, 155*, 111123. https://doi.org/10.1016/j.automatica.2023.111123
21. Peternel, L., & Ajoudani, A. (2023). After a decade of teleimpedance: A survey. *IEEE Transactions on Human-Machine Systems, 53*(2), 401–416. https://doi.org/10.1109/THMS.2022.3231703
22. Michel, Y., Li, Z., & Lee, D. (2023). A learning-based shared control approach for contact tasks. *IEEE Robotics and Automation Letters, 8*(12), 8002–8009. https://doi.org/10.1109/LRA.2023.3322332
23. Marchesi, S., De Tommaso, D., Kompatsiari, K., Wu, Y., & Wykowska, A. (2024). Tools and methods to study and replicate experiments addressing human social cognition in interactive scenarios. *Behavior Research Methods, 56*(7), 7543–7560. https://doi.org/10.3758/s13428-024-02434-z
24. Louca, J., Eder, K., Vrublevskis, J., & Tzemanaki, A. (2024). Impact of haptic feedback in high latency teleoperation for space applications. *ACM Transactions on Human-Robot Interaction, 13*(2), Article 16. https://doi.org/10.1145/3651993
25. Son, Y., Bolton, M. L., Crooks, E., Palmer, H., Kang, E., & Daly, C. (2025). Validation of a formal method for human error rate prediction with negative transfer. *IEEE Transactions on Human-Machine Systems, 55*(5), 844–854. https://doi.org/10.1109/THMS.2025.3593085
26. Lundberg, I., Johnson, R., & Stewart, B. M. (2021). What is your estimand? Defining the target quantity connects statistical evidence to theory. *American Sociological Review, 86*(3), 532–565. https://doi.org/10.1177/00031224211004187
