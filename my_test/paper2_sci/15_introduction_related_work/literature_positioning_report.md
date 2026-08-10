# Introduction and Related Work positioning report

## A. 真实文献路线图

### Route 1 — Human-in-the-loop bilateral and haptic teleoperation

**核心思想。** 遥操作不是孤立的机器人控制器，而是operator–master–communication/control–slave–environment耦合系统。稳定性、透明度、反馈质量、延迟和人的适应策略共同决定任务表现。

**代表工作。** Hannaford (1989)；Lawrence (1993)；Hokayem and Spong (2006)；Passenberg et al. (2010)；Huang et al. (2019)；Rakita et al. (2020)；Louca et al. (2024)；Gong et al. (2024)。

**该路线支持本文的内容。**

- 人是闭环组成部分，不能只用robot-side controller指标解释全部结果。
- 延迟类型不同，人采用的补偿策略也可能不同。
- 接触力、任务完成、速度/时间、碰撞、信任和工作负荷等指标应按科学问题联合评价。

**该路线不直接支持的内容。** 它不能证明E-A是视觉效应，也不能证明其他研究普遍存在mode实现错误。

### Route 2 — Variable impedance, teleimpedance, and adaptive impedance

**核心思想。** 阻抗控制塑造运动与交互力之间的动态关系；variable impedance进一步根据任务状态、力、学习策略或人的命令更新stiffness/damping等参数。

**代表工作。** Hogan (1985)；Walker et al. (2010)；Buchli et al. (2011)；Ajoudani et al. (2012)；Peternel et al. (2018)；Abu-Dakka et al. (2018)；Abu-Dakka and Saveriano (2020)；Michel et al. (2021, 2023)；Peternel and Ajoudani (2023)。

**该路线支持本文的内容。**

- stiffness/damping/force-dependent updates是成熟研究方向。
- teleimpedance condition通常是一个controller/interface bundle，人的行为会和阻抗命令相互作用。
- force/stiffness trajectory可以用于说明controller execution，但不能自动证明nominal gate被逐trial正确执行。

**定位结论。** 本文不能把“变刚度”“力相关刚度更新”或“teleimpedance”本身作为新颖性。

### Route 3 — Vision-informed and object-property-aware impedance

**核心思想。** 在接触前利用视觉获得对象/环境信息，并据此选择或生成阻抗；人仍负责运动或监督控制。

**代表工作。** Huang et al. (2021)明确实现了vision → object/material property → pre-contact impedance，并加入voice confirmation/override；Siegemund et al. (2024)进一步使用RGB-D估计geometry、material和object–environment relation；Jekel et al. (2026)使用gaze、speech和VLM生成3D stiffness command。

**定位结论。** “用视觉识别材料并选择阻抗”已经存在，且有与本文系统概念上非常接近的公开工作。本文不能写成novel vision-informed impedance controller，也不能声称视觉材料映射为首次提出。本文可以研究的是：视觉锁定和参数bundle在每个trial中何时真正被logged command应用，以及这对已有数据的解释有什么影响。

### Route 4 — Timing, logging, experiment fidelity, and reproducibility

**核心思想。** 该路线分成三类：

1. teleoperation delay和operator adaptation：Vogels (2004)、Rakita et al. (2020)、Louca et al. (2024)；
2. perception-to-control latency：Aldana-López et al. (2023)；
3. robotics/HRI reproducibility与reporting：Bonsignorio and del Pobil (2015)、Bonsignorio (2017)、Gunes et al. (2022)、Bagchi et al. (2023)、Marchesi et al. (2024)。

**检索后能够回答的问题。**

- 已有研究明确重视通信延迟、perception latency、human adaptation和可复现报告。
- 一些实验会验证其人为设置的delay、报告采集频率，或展示force/stiffness trajectories。
- Marchesi et al. (2024)还明确测量event of interest与realized robot response time，说明“protocol说何时发生”和“机器人实际何时响应”可以被区分。
- 但本次是定向检索而非系统综述，因此不能声称“机器人研究通常不检查时序”，也不能估计有多少比例的论文未检查。
- 在本次筛选的human-in-the-loop contact teleoperation近邻文献中，没有发现一篇以“legacy repeated-measures dataset的逐trial perception lock/contact/adaptation/command trajectory/record provenance联合重建”为中心贡献的论文。这个结论必须限定为“the literature reviewed here”，不能写成全球首创声明。

## B. related_work_matrix

完整28篇核心文献比较表见 [related_work_matrix.csv](related_work_matrix.csv)。表中对“Timing explicitly logged?”和“Realized controller parameters verified?”使用了`Yes / Partial / No / not a focus`等保守分类；`Partial`不能在正文中改写为“未记录”。

## C. 最接近本文的9篇论文

| 接近度 | 文献 | 接近原因 |
|---:|---|---|
| 1 | Huang et al. (2021) | 已实现视觉识别对象/材料属性并在接触前选择阻抗，是对视觉主张约束最强的prior art |
| 2 | Siegemund et al. (2024) | human-in-loop、RGB-D、geometry/material/object relation、自动stiffness选择、接触任务均与本文相近 |
| 3 | Michel et al. (2021) | bilateral teleoperation、contact task、force-informed adaptive impedance和安全/跟踪评价均接近G/F的nominal意图 |
| 4 | Michel et al. (2023) | human user study、contact task、force/stiffness profile和shared control均接近系统级比较 |
| 5 | Peternel and Ajoudani (2023) | 系统整理teleimpedance接口、反馈和控制器，决定本文不能把teleimpedance本身写成创新 |
| 6 | Rakita et al. (2020) | 直接区分不同delay类型并研究operator adaptation，支持“timing changes interpretation” |
| 7 | Louca et al. (2024) | human-in-loop接触遥操作、haptic feedback、明确延迟条件、多维performance metrics |
| 8 | Marchesi et al. (2024) | 方法学上明确测量事件与realized robot response timing，是“实际实现时序”最接近的HRI工作 |
| 9 | Gunes et al. (2022) | 对HRI reproducibility、技术artifact、sample/reporting问题提供直接背景 |

Jekel et al. (2026)在vision/teleimpedance技术上也很接近，但其主要意义是进一步证明视觉/多模态生成阻抗已是活跃方向；它与本文的retrospective audit问题不如前九篇直接。

## D. 这些工作与本文的真正区别

| 既有工作主要做什么 | 本文真正做什么 | 不允许写成什么 |
|---|---|---|
| 设计并验证新的haptic/teleimpedance/controller architecture | 审计既有四配置实验实际logged command和event timing | “we propose a novel controller” |
| 用vision/material/geometry生成或选择impedance | 检查已有视觉bundle是否在contact前按trial实现并如何与结果关联 | “first vision-to-impedance method” |
| 人为操纵communication/perception delay并比较表现 | 从legacy logs重建vision lock、contact和adaptation activation的真实相对时序 | “we introduce latency-aware control” |
| 展示force/stiffness trajectory作为controller evaluation | 将trajectory与event、code path和exact acquisition identity连接起来核验intervention fidelity | “logged stiffness is measured physical impedance” |
| 提供HRI复现/报告规范 | 用manifest、hash和exact record identifier修复initial/replacement record lineage | “we establish a universal reproducibility standard” |
| 基于trial或participant评价proposed method | 重新以5名participant为独立单位解释既有configuration contrasts | “180 independent experiments prove…” |

最核心的区别不是硬件、控制律或视觉模型，而是**evidential reconstruction**：先确认每个trial中软件实际logged command了什么、何时发生、数据来自哪次acquisition，再决定configuration comparison允许表达什么。

## E. 最保守的research gap

### 对用户给定gap的审查

**A. 是否有文献支持？** 有部分支持。delay/operator adaptation、perception latency、visual–haptic synchrony、HRI reproducibility都说明timing和实现细节可能影响解释。但没有文献直接支持“human-in-the-loop teleoperation studies commonly only use nominal modes”这一普遍频率判断。

**B. 是否太宽泛？** 是。“commonly define”暗示对整个领域做过系统统计；“may differ”本身合理，但如果不限定asynchronous event-gated configurations，会显得空泛。

**C. 是否已有相似工作？** 有相邻但不等同的工作。Rakita/Louca研究delay；Marchesi研究realized response timing；Huang/Siegemund研究视觉阻抗；reproducibility文献研究报告完整性。它们分别覆盖gap的一部分。

**D. 应缩到哪里？** 缩到**human-in-the-loop contact teleoperation中由perception/contact/force事件触发的bundled controller configurations，以及legacy data的acquisition-level reconstruction**。

### 推荐gap statement

> Prior teleoperation research has separately examined communication delay, operator adaptation, variable impedance, perception-informed control, and experimental reproducibility. In the human-in-the-loop contact-teleoperation literature reviewed here, relatively less explicit attention is given to jointly reconstructing, at the level of each acquired trial, the timing of perception lock, contact detection, adaptation activation, time-varying commanded parameters, and exact record provenance. This reconstruction becomes important when asynchronous event-gated configurations are compared, because nominal mode labels alone may not establish the intervention represented by the recorded data.

这个gap不声称别人没有日志，也不声称所有遥操作实验都有实现偏差；它只说明在本文这种event-gated、bundled、legacy dataset中，为什么必须先重建realized logged intervention。

## F. Introduction五段逻辑

| 段落 | 功能 | 关键内容 | 禁区 |
|---|---|---|---|
| P1 | 建立大问题 | human-in-loop contact teleoperation是耦合系统；同时考虑contact loading、responsiveness、efficiency和operator behavior | 不从bug开篇；不写具体p值 |
| P2 | 交代解决路线 | haptics、variable impedance、force adaptation、vision/object-aware impedance都已有充分研究 | 不把vision→material→impedance写成创新 |
| P3 | 引出时序问题 | human command、vision inference、contact detection、adaptation和parameter update异步；nominal label不必然等于per-trial command exposure | 不把logged command说成physical impedance |
| P4 | 收紧gap | timing、controller和reproducibility文献各自存在，但joint acquisition-level audit在所审文献中较少被明确作为中心问题 | 不写“No previous work…”或“studies commonly fail…” |
| P5 | 本文动作与贡献 | retrospective reconstruction；3个RQ；方法学/解释性贡献；极简结果方向 | 不称new controller，不隔离E-A机制，不把G/F当干净ablation |

## H. 是否单独设置Related Work

**推荐方案A：单独设置Section 2 Related Work。** 原因是本文的可发表性高度依赖“不是新controller、而是realized-intervention audit”这一定位；如果把全部文献塞入Introduction，900–1300词内很难同时完成背景、prior-art边界、gap和贡献，而且容易让视觉阻抗prior art被弱化。

建议结构：

1. Introduction
2. Related Work
   - 2.1 Haptic and variable-impedance teleoperation
   - 2.2 Vision-informed contact and impedance adaptation
   - 2.3 Timing, logging, and realized-intervention fidelity
3. Methods

如果目标期刊明确偏好不设Related Work，可将2.1和2.2压缩进Introduction第2段，将2.3压缩进第3–4段，但不能删除Huang et al. (2021)和Siegemund et al. (2024)这两项最接近prior art。
