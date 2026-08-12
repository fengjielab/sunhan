# THMS 定向重构与投稿级审查

## 审查范围与结论

本报告以三篇已发表 IEEE Transactions on Human-Machine Systems（THMS）论文为主要结构参照：Amirshirzad et al.（2019）、Gottardi et al.（2022）和 De Pace et al.（2024）。分析关注 section organization、argument flow、information density、实验与统计的衔接以及 Figure/Table 的科学功能，不复制具体句子、视觉样式或结论。Beraldo et al.（2022）仅作辅助核对，未据其个别写法推导期刊硬性模板。

总体判断：当前稿件已经具备清楚且谨慎的科学边界，RQ1–RQ3 也能被 Results 逐项回答。最需要的不是增加控制器技术、人体指标或统计模型，而是把稿件从“审计说明书式完整”重构为“THMS regular paper 式论证”：Introduction 更快落到人机系统问题和方法学缺口；Framework 保留定义但减少程序性重复；Case Demonstration 明确承担复现而非概念贡献；Results 以 RQ 为主线并把原因解释留给 Discussion；Discussion 增强与既有研究路线的关系和可迁移的人机系统意义。

---

# A. 三篇参考 THMS 论文结构拆解

## A1. Amirshirzad et al. (2019), “Human Adaptation to Human–Robot Shared Control”

### A1.1 全文结构与科学功能

| 层级 | 标题 | 科学功能 |
|---|---|---|
| I | Introduction | 从人—机器人协同潜力进入 shared control，回顾意图推断与人适应研究，明确“人与非平稳机器人伙伴共同学习”的缺口和研究问题。Related work 融入本节。 |
| II | Methods | 将控制框架、任务、机器人平台、实验设计、性能指标和统计方法置于同一方法章节。 |
| II-A | Shared Control Framework | 定义人、机器人命令以及融合权重，先交代概念和控制关系。 |
| II-B | Designed Task | 说明球平衡任务、目标和成功要求。 |
| II-C | Robotic Setup | 说明机器人、视觉跟踪、teleoperation、autonomous controller 与 human intention inference。 |
| II-D | Experiments | 说明两种条件、20 名参与者、4 天/64 次试次、程序和性能测量。 |
| II-E | Analysis | 预先说明 MANOVA/ANOVA、回归与命令相关性分析。 |
| III | Results | 依研究问题/分析对象组织，而不是按方法步骤复述。 |
| III-A | Group and Day-by-Day Performance | 比较 shared control 与 human control 的逐日表现。 |
| III-B | Learning Rate | 用回归模型量化学习率。 |
| III-C | Compatibility of Human and Robot Commands | 分析人和机器人命令相关性随天数变化。 |
| IV | Conclusion | 先给研究级总结。该文把 Conclusion 放在 Discussion 前，是个别写法，不宜视为 THMS 模板。 |
| V | Discussion | 解释人如何适应机器人、共享权重与接口设计意义、个体差异和未来研究。 |
| Appendix | Regression model comparison | 放置逐参与者模型选择细节，避免打断主论证。 |

### A1.2 Introduction 逐段功能

按跨栏连续语义可分为约 8 个功能段：

1. 建立人—机器人协同愿景，说明人和机器能力互补。
2. 引入 human-in-the-loop/shared control，说明双方适应的重要性并给出已有例子。
3. 从任务目标参数进入 human intention inference，指出目标通常被预知或显式给定的局限。
4. 明确 gap：shared control 中人的适应尚缺乏系统研究。
5. 回顾 direct control 和 human-in-the-loop robot control，建立任务与控制背景。
6. 区分辅助式 shared control 和真正的协同/协同增益目标。
7. 将研究缺口转为具体问题：无显式共同目标时如何协作、人如何适应非平稳机器人伙伴。
8. 说明球平衡实例、human control 与 shared control 对照以及长期学习关注点。

结构特征：Introduction 约占研究正文 18%–20%；无独立 Related Work；不使用编号 RQ 或 Hypothesis；贡献在末段以研究目标和问题隐式提出，没有 contribution bullets；后续 Results 通过“group/day performance → learning rate → command compatibility”回答引言中的问题。

### A1.3 Methods / Framework 顺序

顺序为：shared-control conceptual framework → designed task → robotic setup 与控制实现 → experimental conditions/participants/procedure → performance measure → statistical analysis。方法创新和实验验证没有拆为两个一级章节，但通过 II-A–C 与 II-D–E 的二级标题清楚分隔。这样适合“一个控制系统 + 一个主实验”的文章；若方法本身需要独立抽象和跨系统主张，这种合并方式未必适用。

### A1.4 Results 组织逻辑

Results 按研究问题和分析层次组织：总体表现及随天变化、学习率、人机命令兼容性。结果段报告统计量后做有限解释，较深入的行为机制、控制权分配与接口意义主要留给 Discussion。该文没有把 objective/subjective 指标作为 Results 的一级分组。

### A1.5 Discussion 逻辑

Discussion 从共享控制权分配问题进入，继而解释“为什么共享组学得更快”，结合问卷反馈推断参与者逐步理解机器人行为，然后讨论可能的人类策略、个体差异、双向适应、multimodal interfaces 与未来任务。它的人机系统定位体现在：不只问机器人是否更快，还问人如何建模并利用机器伙伴、控制权怎样分配、接口和反馈如何改变协同。

### A1.6 Figure/Table 功能

| 编号 | 类型与位置 | 科学问题/功能 | 核心性 |
|---|---|---|---|
| Fig. 1 | 概念框架图，Methods II-A | 人和机器人命令如何融合，反馈/前馈信息如何闭环 | 核心 |
| Fig. 2 | 任务与机器人设置图，II-B/C | 球平衡任务、机器人自由度、目标位置是什么 | 核心复现图 |
| Fig. 3 | 轨迹与命令实例，II-D | 低/高表现试次如何体现轨迹和人机命令差异 | 核心桥接图 |
| Fig. 4 | 逐日组均值结果，III-A | 两条件表现如何随 4 天变化 | 核心结果图 |
| Fig. 5 | 两名参与者的拟合示例，III-B | 学习曲线模型如何拟合单人试次 | 辅助/机制图 |
| Fig. 6 | 学习率组比较，III-B | shared control 是否具有更高学习率 | 核心结果图 |
| Table I | 第 1 天 block 统计，III-A | 首日各 block 是否已有组差异 | 辅助 |
| Table II | shared-control 逐日 post hoc，III-A | 哪些天之间发生变化 | 核心支持表 |
| Table III | human-control 逐日 post hoc，III-A | 对照条件的学习变化 | 辅助支持表 |
| Table IV | 人—机器人 roll/pitch 相关统计，III-C | 命令兼容性是否随天数增加 | 核心支持表 |
| Table V | Appendix 模型拟合比较 | 为什么选择 power model 量化学习率 | 辅助，适合附录 |

### A1.7 篇幅特点

粗略按研究正文页面估计：Introduction 19%，Methods 36%，Results 27%，Conclusion 7%，Discussion 11%。全文 6 幅图、5 张表（其中 1 张在 Appendix）。其特点是 Methods 和 Results 占主体，Discussion 只承接人机适应意义，不重复大量统计细节。

---

## A2. Gottardi et al. (2022), “Shared Control in Robot Teleoperation With Improved Potential Fields”

### A2.1 全文结构与科学功能

| 层级 | 标题 | 科学功能 |
|---|---|---|
| I | Introduction | 从 teleoperation 局限导出 intent recognition、safe motion、seamless interaction 三项需求，随后列出贡献和文章结构。 |
| I-A | Contribution | 把方法、系统兼容性和实验比较作为三项贡献。 |
| II | Related Work | 分别梳理意图推断和碰撞避免，再指出两者缺少统一框架。 |
| III | Our Framework | 独立呈现方法创新。 |
| III-A | Goal Prediction | 定义用户目标概率估计。 |
| III-B | Artificial Potential Fields | 给出基线 APF。 |
| III-C | Improved APF With Escape Points | 给出 escape point 与约束优化。 |
| III-D | Shared Control Framework | 汇总算法和在线流程。 |
| IV | Experiments | 将方法验证与方法本体分离。 |
| IV-A | Evaluation Setups | 说明静态/动态场景、机器人、接口与对象。 |
| IV-B | Evaluation Metrics | 分 objective 和 subjective 指标。 |
| IV-C | Evaluation Procedure | 参与者、条件顺序、重复、成功/失败定义和培训。 |
| IV-D | Statistical Analysis | 正态性检查、Friedman/Kruskal–Wallis、post hoc 和校正。 |
| V | Results Obtained in the Static Setup | 按静态实验组织结果，内部分 Objective/Subjective Metrics。 |
| VI | Results Obtained in the Dynamic Setup | 按第二实验场景组织 objective/subjective 结果。 |
| VII | Conclusion | 合并主要结果、用户体验、局限和未来研究。无独立 Discussion。 |

### A2.2 Introduction 逐段功能

1. 定义 teleoperation、应用和 direct teleoperation 的局限。
2. 引入 shared control，说明辅助的目标与应用价值。
3. 以编号列表提出设计需求：intent recognition、safe motion、seamless interaction。
4. 在 Contribution 小节提出方法并列出三项贡献。
5. 给出文章结构路线图。

结构特征：Introduction 约占正文 11%–13%；Related Work 独立；贡献在 Introduction 末部的专门小节中提出；无显式 RQ/Hypothesis，但三项需求和三项贡献直接决定 Framework、Experiments 和 Results；Results 不是按贡献编号，而是按两个实验环境组织。

### A2.3 Methods / Framework 顺序

顺序为：related work → goal prediction → conventional APF → improved APF → integrated shared-control algorithm → evaluation setups → objective/subjective metrics → procedure → statistics。方法创新与实验验证明确分成两个一级 section，原因是理论与算法本身篇幅较大、可独立复用，而人类实验承担比较与评价功能。

### A2.4 Results 组织逻辑

Results 首先按 Experiment/Environment（static 与 dynamic）分开，静态场景内部再分 objective metrics 和 subjective metrics；objective 段又按 failure rate、time、inputs、direction changes、trajectory 逐项推进。解释在 Results 中相对较多，因为文章没有独立 Discussion；作者直接用轨迹和用户感受解释为何 improved-APF 更优或为何 APF 令人失去控制感。

### A2.5 Discussion 逻辑

无独立 Discussion。其解释分布在 Results 与 Conclusion：objective performance → trajectory/mechanism → subjective control/workload → static/dynamic robustness → limitations/future work。人机系统定位特别体现在把效率、失败率、用户输入、方向改变、控制感、负荷和满意度放在同一评价体系中，而不是只报告路径规划性能。

### A2.6 Figure/Table 功能

| 编号 | 类型与位置 | 科学问题/功能 | 核心性 |
|---|---|---|---|
| Fig. 1 | 2-D 仿真案例，Framework | escape points 是否克服 APF 局部极小/绕障问题 | 核心机制图 |
| Algorithm 1 | SharedControl 伪代码，Framework | 在线推断、避障和运动更新如何组合 | 核心复现信息 |
| Algorithm 2 | FindEscapePoint 伪代码，Framework | escape point 如何生成和选择 | 核心复现信息 |
| Fig. 2 | 静态实验场景照片，Experiments | 目标、障碍与机器人视野如何布置 | 核心设置图 |
| Fig. 3 | Myo—机器人方向映射，Experiments | 人体手臂动作如何映射机器人 3-D 速度 | 核心接口图 |
| Fig. 4 | 静态 objective 指标及逐人连线，Results V | 三种控制方法对时间、输入、方向改变的影响 | 核心结果图 |
| Fig. 5 | 2-D/3-D 平均轨迹，Results V | 性能差异通过何种运动路径产生 | 核心机制结果图 |
| Fig. 6 | 静态 Likert/NASA-TLX，Results V | 控制感、可用性和工作负荷如何变化 | 核心人因结果图 |
| Fig. 7 | 动态 objective 指标，Results VI | 动态干扰下效率和用户干预是否保持改善 | 核心结果图 |
| Fig. 8 | 动态 subjective 指标，Results VI | 动态环境中的信心、工作负荷和满意度 | 核心人因结果图 |
| Table I | Likert 问卷条目，Experiments | subjective constructs 如何操作化 | 复现/辅助 |
| Table II | 静态失败率，Results V | 不同接口和目标下的失败分布 | 核心支持表 |
| Table III | 动态失败率，Results VI | 动态环境中的失败率 | 核心支持表 |

### A2.7 篇幅特点

粗略估计：Introduction 12%，Related Work 10%，Framework 22%，Experiments 18%，Results（静态+动态）28%，Conclusion/局限 10%。全文 8 幅图、3 张表、2 个算法框。信息密度高，但每幅图都对应明确的机制、设置、objective 或 subjective 问题。

---

## A3. De Pace et al. (2024), “Supporting Human–Robot Interaction by Projected Augmented Reality and a Brain Interface”

### A3.1 全文结构与科学功能

| 层级 | 标题 | 科学功能 |
|---|---|---|
| I | Introduction | 从 HRI 分类和 mobility-impaired users 的需求进入 BCI+projected AR 系统，提出两种定位方法、RQ 和评价策略。 |
| II | State of the Art | 独立、分主题地建立技术背景与 gap。 |
| II-A | BCI Interfaces | BCI 类型、处理流程和适用性。 |
| II-B | Remote Interfaces for Telerobotics | 眼动/VR 等远程机器人接口。 |
| II-C | BCI and AR Interfaces for HRI | 混合 BCI–AR 研究。 |
| II-D | Label Placement in AR | AR 标签放置算法。 |
| II-E | Contribution | 在 related work 之后明确本文与前述工作的差异。 |
| III | Proposed System | 说明系统、架构、算法和系统级 benchmark。 |
| III-A | Brain–AR Interface | 用户如何通过 NeuroTag 选择对象。 |
| III-B | Hardware and Software Architecture | 设备、ROS/Unity、数据流与机器人执行。 |
| III-C | Adaptive Positioning Approach | APA 算法。 |
| III-D | Nonadaptive Positioning Approach | NAPA 算法。 |
| III-E | Evaluation of NeuroTag Positioning and Robot Movement | 在用户研究前先评估算法时间、失败与机器人动作时间。 |
| IV | User Study | 人体评价，包含任务、参与者、程序、统计、结果、讨论和局限。 |
| IV-A | Results | 按 SUS、NASA-TLX、SEQ、time、error 报告。 |
| IV-B | Discussion | 显式逐项回答 R1a/R1b、R2、R3。 |
| IV-C | Limitations | 目标人群外推、安全性和 head tracking 等局限。 |
| V | Conclusion and Future Works | 研究总结及下一步系统与目标人群验证。 |

### A3.2 Introduction 逐段功能

1. 用 HRI 四类任务定位论文所属的 assistive HRI 场景。
2. 说明 mobility-impaired users 的意图表达困难。
3. 引入 BCI、SSVEP 和 AR 作为技术桥梁。
4. 提出 projected AR + BCI 系统并以编号步骤描述应用场景。
5. 指出视觉刺激位置的重要性，提出 adaptive 与 nonadaptive 两种方案。
6. 解释为什么先用健康参与者模拟目标用户条件，并限定该策略的目的。
7. 说明 NextMind/NeuroTag 的具体作用。
8. 明确提出 R1a、R1b、R2、R3。
9. 将 RQ 映射到 22 人用户研究、SUS/NASA-TLX、完成时间和选择错误，并预告主要结果。
10. 给出全文结构。

结构特征：Introduction 约占正文 14%–16%；Related Work 独立；RQ 明确且在 User Study Discussion 中逐项回收；贡献列表不在 Introduction，而是在 State of the Art 末尾提出；RQ 同时决定 metrics 和 Results/Discussion 顺序。

### A3.3 Methods / Framework 顺序

顺序为：technical background → contribution → proposed interface → hardware/software architecture → adaptive algorithm → nonadaptive baseline → system performance benchmark → user study procedure → participants/ethics → distribution checks/statistics → results。方法创新和实验验证分开：Proposed System 证明系统如何工作并进行机器/算法层 benchmark，User Study 检验可用性、负荷和鲁棒性。

### A3.4 Results 组织逻辑

Results 按指标组织：SUS/SEQ → NASA-TLX → time → error/precision；统计分布检查与检验选择紧接数据说明。原因解释和 RQ 回答主要置于 IV-B Discussion，Results 仅保留必要的统计含义。

### A3.5 Discussion 逻辑

Discussion 直接以 R1a/R1b、R2、R3 回答：可用性与两定位方案比较 → workload → time/error/robustness → 用户评论；随后独立 Limitations，再由 Conclusion and Future Works 给出目标人群验证、安全与技术升级。其 THMS 定位体现为把用户能力限制、接口可用性、认知负荷、系统鲁棒性与机器人任务性能共同评价。

### A3.6 Figure/Table 功能

| 编号 | 类型与位置 | 科学问题/功能 | 核心性 |
|---|---|---|---|
| Fig. 1 | 当前测试与目标应用场景，Introduction | 健康参与者实验如何映射到 mobility-impaired use case | 核心概念/边界图 |
| Fig. 2 | 工作区与 NeuroTag，Proposed System | 实物、投影、可操作区与标签如何共置 | 核心设置图 |
| Fig. 3 | 系统架构，III-B | 摄像头、Windows/Unity、Linux/ROS、BCI 用户和机器人如何连接 | 核心架构图 |
| Fig. 4 | 可用/占用 cell，III-C | APA 的搜索空间和遮挡约束如何表示 | 核心算法图 |
| Fig. 5 | APA/NAPA 输出示例，III-C/D | 两种标签布局及碰撞路径有何差别 | 核心实现结果图 |
| Fig. 6 | SUS 与 SEQ，IV-A | 可用性和单任务易用性是否不同 | 核心主观结果图 |
| Fig. 7 | 时间结果，IV-A | 方法与任务复杂度如何影响完成时间 | 核心客观结果图 |
| Fig. 8 | 错误结果，IV-A | 方法与任务复杂度如何影响误选 | 核心鲁棒性结果图 |
| Table I | APA/NAPA 计算性能，III-E | 算法耗时和失败率是否支持实时使用 | 核心系统 benchmark |
| Table II | 机器人动作时间分解，III-E | 算法、BCI 选择与机器人运动各占多少时间 | 核心系统时间链 |

### A3.7 篇幅特点

粗略估计：Introduction 15%，State of the Art 22%，Proposed System 32%，User Study（含 Results/Discussion/Limitations）24%，Conclusion/Future Works 7%。全文 8 幅图、2 张表。其显著特征是 Framework/System 与 User Study 清楚分离，并把每个 RQ 映射到具体主观或客观指标。

---

# B. 三篇论文共同体现的 THMS 写作规律

以下是共同规律，而非期刊硬性格式：

1. **先建立人机系统问题，再介绍算法或装置。** 三篇论文都先说明人的能力、限制、负荷、适应或控制感为何与机器行为共同决定结果。
2. **Introduction 末端形成清楚的逻辑契约。** 契约可以是 RQ、设计需求或研究问题，不要求统一采用 Hypothesis，但必须能在 Methods 和 Results 中找到对应项。
3. **方法创新与实验评价的边界清楚。** 即使放在同一 Methods 一级节，也会通过小节把 framework/system 与 participants/procedure/metrics/statistics 分开；方法较复杂时直接拆为独立一级 section。
4. **复现信息按执行顺序组织。** system/task → conditions → participants/procedure → metrics → statistics 是常见走向；公式和算法只在支撑理解或复现时保留。
5. **Results 有单一主轴。** 可以按 RQ、experiment/environment 或 metric 组织，但不会同时用多个互相竞争的结构。小节标题应让读者知道正在回答什么。
6. **解释位置可以不同，但职责必须明确。** 有独立 Discussion 的论文把机制、人与机器关系、局限放在 Discussion；没有 Discussion 的论文会在 Results/Conclusion 中承担这些功能。不能在 Results 和 Discussion 完整重复同一套解释。
7. **Figure 是论证节点，不是装饰。** 核心图通常依次承担：概念/架构、任务与设置、方法机制、objective results、subjective/human results。每张图都回答一个科学或复现问题。
8. **participant-level 信息优于只有组均值。** Gottardi 用逐人连线，Amirshirzad 以个体学习曲线示例补充组结果；这支持当前稿件保留参与者层面的 E-A 图。
9. **人机系统意义不等于强行增加人体指标。** 参考论文的人因变量来自明确协议和有效量表。当前存档没有经验证的 human motion onset，因此不应为了“像 THMS”制造反应时或 approach-speed 指标。
10. **局限具体指向可解释性与推广边界。** 目标人群代理、控制接口、测量来源、样本量、场景复杂度和实现限制会被明确写出，而非用泛化句收尾。

三篇论文之间存在的差异同样重要：Related Work 可独立也可融入 Introduction；Contribution 可置于 Introduction 或 Related Work 末端；Results 可按 RQ、指标或实验组织；Discussion 可以独立，也可以并入 Results/Conclusion。因此，不应把任一篇的标题顺序当成 THMS 统一模板。

---

# C. 当前稿件与参考论文的差距表

| 我们当前部分 | 当前功能 | 参考论文中的对应做法 | 当前问题 | 决策 | 建议 |
|---|---|---|---|---|---|
| 标题与摘要 | 提出 fidelity framework 并概述案例 | 三篇均采用 problem→method→study→main results→meaning | v1 摘要信息完整但过密，provenance、G/F、E-A、统计边界竞争注意力 | 修改 | 压缩背景和血缘细节，保留 G/F 核心偏离、E-A 估计及探索性边界 |
| Introduction 第 1–2 段 | 人机系统背景和异步错位 | 均先建立人的角色和系统问题 | 引用密度偏高，但科学动机清楚 | 修改 | 减少列举式技术清单，强化“标签不能证明实际经历”的主问题 |
| Introduction 文献 gap | 用表 I 连接五条方法学路线 | Gottardi/De Pace 独立 Related Work；Amirshirzad 融合 | gap 已明确，但正文只用一句引入表格，容易像综述清单 | 修改 | 在表前增加综合段，说明各路线为何仍不能完成联合推断 |
| RQ1–RQ3 | 串联实现、解释和结局 | De Pace 显式 RQ 并在 Discussion 回收 | 三个 RQ 与 Results 对应良好；RQ3“案例示范”可更精确 | 保留并微调 | 改为“有边界的案例结果”，避免暗示 validation |
| Contributions | 两项方法贡献，案例不作第三项 | 参考论文贡献通常置于引言末部 | 边界非常清楚，是稿件强项 | 保留 | 继续只保留两项；增加文章结构路线图 |
| Framework 2.1 | 定义 N→C→R→Y、H 与 provenance | 参考论文先图/概念再公式 | 定义完整，略像规范文件 | 修改 | 缩短限定语重复；保留 H 与 R 分离、provenance 正交性 |
| Framework 2.2 | 时序误差、暴露、admissible estimand | 参考论文公式紧邻所支持的机制 | 必要，但 causal 限制重复多次 | 修改 | 核心定义只在此处完整说明，后文使用短提醒 |
| Framework 2.3 与表 II | 断点类型和最低证据包 | Gottardi 的算法框、De Pace 的架构/benchmark 同属复现核心 | 表 II 是核心贡献，不宜移补充；三阶段说明与 Discussion 重复 | 保留并压缩 | 主文保留表 II，缩短三阶段流程；详细 metric dictionary 留 Supplement S1 |
| Case 3.1 | 系统、参与者与设计 | 均说明 platform、participants、task/procedure | 参与者元数据、训练、顺序和伦理未恢复；这是投稿阻断项 | 修改/待核实 | 保留显式占位，不填补未知；将 section 名改为 Case Demonstration |
| Case 3.2 | 名义配置和实现 | 方法与条件在实验前交代 | G/F 实现事实清楚；事件定义原放 3.3，略晚 | 修改 | 把 G/F 时钟和 activation definition 前移到“名义配置与可执行实现” |
| Case 3.3 | 溯源、结局、窗口 | 参考论文常按 procedure→metrics 排列 | v1 先 lineage 再 outcome，读者较晚知道每次采集如何实例化 R/Y | 修改 | 先试次文件与 R/Y 重建，再 lineage selection，再 outcome |
| Statistics | 参与者内聚合、精确推断、Holm、LOPO、窗口敏感性 | 均独列 statistical analysis | 与 n=5 边界匹配；不应增加模型追显著性 | 保留 | 保留当前方法，突出 estimand、单位和固定敏感性，不新增 bootstrap/Bayesian/mixed model |
| Results 4.1 | 回答 RQ1 | 参考论文按 RQ 或指标报告事实 | 事实充分；局部含较多解释 | 修改 | 标题直接写“名义标签、可执行逻辑与实际干预”，深层原因留 Discussion |
| Results 4.2/表 III | 回答 RQ2 | De Pace 用 Discussion 回答 RQ；Gottardi 在 Results 解释 | 表 III 是论文的科学后果核心 | 保留 | 继续主文保留；不改为 fidelity score，不删除/重分类试次 |
| Results 4.3 | 回答 RQ3，报告 E-A 及其他对比 | 参考论文强调主要比较并用个体图支持 | 核心结果略被多重 p 值淹没，但 n=5 离散性必须说明 | 修改 | 先 effect estimate 和 participant consistency，再 exact/Holm；详细全对比表放 Supplement |
| Discussion 5.1 | 按 RQ 再述全部结果 | 参考论文 Discussion 回答 RQ，但避免逐句重报数值 | 与 Results 重复较多 | 修改 | 合并为“主要发现与人机系统意义”，不重列全部统计值 |
| Discussion 5.2 | 采集前/中/推断前启示 | 参考论文将 design implications 连到具体系统 | 符合 THMS，内容重要 | 保留并加强 | 增加“报告时”的措辞约束和捆绑配置示例 |
| Discussion 5.3 | 案例解释和局限 | 三篇均具体说明样本、接口、目标人群和场景边界 | 缺少与既有时延/验证/复现路线的显式比较，future validation 不够独立 | 修改 | 新增相关工作关系段；加入前瞻性验证需求 |
| Conclusion | 概括框架和推断意义 | 均很短，回到系统层意义 | v1 已合格 | 微调 | 保持一段，不重报数值，不声称 external validation |
| References | 支撑背景和框架 | IEEE 编号制 | 当前为作者—年份正文和 APA 风格列表，尚非 IEEE 最终格式 | 投稿排版时修改 | 英文稿阶段统一成 IEEE 编号引用；本轮不改变事实性文献内容 |
| Supplement | metric dictionary、全对比、窗口和 lineage | 参考论文把模型选择/次级证据移 Appendix/Supplement | 当前分配总体合理 | 保留 | 继续放详细 metric dictionary、全对比、lineage trace、trajectory 与 LOPO |

按中文主文字符数粗略估计（包含主文表格和公式，不含摘要、参考文献），v1 的分配为 Introduction 15.8%、Framework 19.6%、Case 21.1%、Results 26.5%、Discussion 14.7%、Conclusion 2.3%；v2 为 16.3%、17.3%、21.0%、27.2%、16.1%、2.2%。因此 Introduction 并不过长，Framework 也没有失控；本轮主要把 Framework 的程序性说明压缩约 2.3 个百分点，并把篇幅转给文献定位和 THMS-oriented Discussion。Results 仍是最长部分，这是由 RQ1 的 fidelity evidence、RQ2 的 interpretation map 和 RQ3 的小样本边界共同决定的，属于可辩护的信息分配。

## 必须在投稿前解决的阻断项

1. 伦理审批或豁免机构、编号、日期、知情同意及存档数据使用范围。
2. 作者、单位、基金、利益冲突、作者贡献、致谢、数据和代码可用性声明。
3. 尽力恢复参与者人口学、惯用手、经验、招募、补偿和训练信息；无法恢复则明确报告缺失。
4. 尽力恢复任务对象、起始/目标位置、容差和条件顺序；无法恢复则不能声称随机化或平衡。
5. 最终英文稿采用 IEEE 引用与图表编号格式，并核对 2026 年文献的正式出版状态与卷期页码。

---

# D. 推荐的新论文目录

1. Introduction
2. Realized-Intervention Fidelity Framework
   - A. Nominal–Executable–Realized–Outcome Evidence Chain
   - B. Timing, Outcome-Window Exposure, and Admissible Statistical Comparisons
   - C. Fidelity Breaks and the Orthogonal Provenance Prerequisite
3. Retrospective Teleoperation Case Demonstration
   - A. Human–Machine System, Participants, and Experimental Structure
   - B. Nominal Configurations and Executable Implementations
   - C. Trial Reconstruction, Outcomes, and Data Integrity
   - D. Statistical Analysis
4. Results
   - A. RQ1: Nominal Labels, Executable Logic, and Realized Interventions
   - B. RQ2: Constraints on Evidence-Admissible Interpretation
   - C. RQ3: Outcome Patterns Remaining After Reconstruction
5. Discussion
   - A. Principal Findings and Human–Machine Systems Significance
   - B. Implications for Experimental Design, Acquisition, and Reporting
   - C. Case Limitations and Prospective Validation Needs
6. Conclusion

不建议为了模仿 Gottardi 或 De Pace 强行新增独立 Related Work。当前稿件的文献任务是界定方法学缺口，不是全面综述 teleoperation 技术；在 Introduction 内保留一个综合段和表 I 更紧凑。若英文排版后 Introduction 超过约 1.5–2 个双栏页，再考虑把表 I 与扩展说明独立成 Section II。

---

# E. Figure/Table 规划

## E1. 最小正文图体系

| 图 | 应回答的科学问题 | 当前状态 | 决策 |
|---|---|---|---|
| Figure 1 | 为什么名义标签不足，以及 N→C→R→Y 如何限制解释？ | 已同时展示证据链和简化异步时间线；provenance 只用一句指向 Fig. 2 | **保留，核心概念图。** 信息密度符合参考论文的框架图功能。英文终稿可减少框内句子，确保双栏宽度可读。 |
| Figure 2 | 案例系统如何闭环、异步事件如何发生、R 与 Y 如何由同一次采集连接？ | 当前包含 system、event channels、provenance/inference level 三个 panel | **保留，核心系统/复现图。** 与 De Pace Fig. 3、Gottardi Fig. 2–3 类似地承担架构和设置功能。若版面拥挤，可把 panel B 的示意时间线与 Fig. 1 合并后删除重复。 |
| Figure 3 | G、F 和 E/F 的实际干预证据是什么？ | G/F timing + window exposure，直接回答 RQ1 | **保留，核心证据图。** 是全文最不可替代的案例结果图。 |
| Figure 4 | 保真度证据如何把名义解释收窄为可容许解释，并留下何种 E-A 结果？ | 当前只有 E-A 三项 participant-level outcome，回答 RQ3，但没有可视化 RQ2 的“科学后果” | **建议重设计。** 最优方案为两层组合：上层用四条简洁映射展示 nominal claim→fidelity evidence→admissible interpretation；下层只保留最核心的 E-A excess-force impulse participant plot。任务开始至接触与总任务时间移 Supplement 或主文表。 |

当前 Figure 4 不是无效图；它有很强的 participant-level 证据价值。但它没有完全实现用户给定的“scientific consequence”任务。若短期不重画，应保留当前 Fig. 4，并让表 III 承担 RQ2 的科学后果；若重画，则不要把表 III 全文塞入图，而只放四项比较的最短映射。

## E2. 正文表体系

| 表 | 任务 | 决策 |
|---|---|---|
| Table I | 证明方法学 gap 来自多个分散路线之间缺少连接 | 保留正文；它是 Introduction 的证据，不是普通综述表 |
| Table II | 给出框架最低证据包 | 保留正文；是框架可操作化的核心，不移 Supplement |
| Table III | 把名义主张、证据与允许/禁止措辞直接连接 | 保留正文；是 RQ2 的核心论证表 |

## E3. 建议继续放 Supplement 的内容

- 全 metric dictionary 和 applicability（Table S1）。
- 配置级完整 fidelity summary（Table S2）。
- 全部 participant-level contrasts 与多种检验（Table S3）。
- lineage correction sensitivity（Table S4）。
- fixed adjacent-window sensitivity（Table S5）。
- contact-aligned trajectories/commanded stiffness（Fig. S1）。
- participant consistency 与 LOPO（Fig. S2）。
- lineage trace examples（Fig. S3）。

若 Figure 4 重设计，系统就绪至接触和总任务时间的 participant plots 可并入 Supplement Fig. S2 或新增 Fig. S4；正文仍在 RQ3 用数值描述其力—时间模式。

---

# F. 逐节修改建议

## Introduction

- 用 5 个功能块组织：human–machine problem → label/realization gap → related-method gap → RQs → two contributions + article map。
- 保留 RQ1–RQ3，因为它们已与 Results 完整对应；不要新增 Hypothesis。
- 保留表 I，但在表前增加一段真正的 synthesis，而不是只说“这些路线存在”。
- 两项贡献继续只写证据链和 evidence-to-interpretation mapping；案例只能称 retrospective case demonstration。

## Framework

- 以 Fig. 1 为入口，先定义 N/C/R/Y 和 H，再给 timing/window/estimand 公式。
- 把 provenance 始终写成正交 data-integrity prerequisite，不进入 fidelity score。
- “admissible estimand”只在 2.2 完整限定一次，后文用“可容许统计比较/解释”简写。
- 表 II 留正文；详细逐字段判定规则继续放 Supplement S1。

## Case Demonstration

- 标题从“案例研究”改为“回顾性案例示范”，防止被读成 external validation。
- 按 system/participants/design → nominal conditions/executable logic → trial reconstruction/outcomes/data integrity → statistics 排列。
- 把 G 和 F 的具体时钟/activation definition 放在 3.2，使读者在看 Results 前知道规则。
- 所有 `[待核实]` 与伦理阻断必须保留；不得猜测人口学、随机化、训练或对象信息。

## Results

- 保持 RQ1/RQ2/RQ3 结构；这是当前稿件与 De Pace 式明确 RQ 回收最契合的做法。
- RQ1 只报告 A/G/F/暴露/lineage 事实及必要的分类边界。
- RQ2 用表 III 完成“科学后果”论证；明确不删除或重分类试次。
- RQ3 先效应估计和 5 名参与者方向，再 exact/Holm/窗口/LOPO；180 trial 不可作为人体样本量。
- 不增加 bootstrap、Bayesian、mixed-effects、事后 subgroup 或新窗口。

## Discussion

- 第一小节不再逐项复制 Results 数字，而用一段回答三个 RQ，再解释为何这是 human–machine systems 问题。
- 增加与 latency、runtime verification、reproducibility/provenance、implementation fidelity、estimand 路线的互补关系。
- design implications 继续按采集前/采集中/推断前组织，并增加“报告时”约束。
- limitations 独立收束样本、回顾性 outcome、捆绑配置、顺序未知、传感器来源、缺失元数据与伦理阻断。
- future work 只提出 prospective framework validation，不暗示当前案例已完成 validation。

## Conclusion

- 保持一段，回到“名义标签不能独立成为推断对象”。
- 不重报 E-A 数值，不把 E-A 称为 vision/stiffness/safety causal effect。
- 明确证据收窄解释不自动产生因果含义。

---

# G. 修改后的完整中文稿

完整稿已另存为：`01_manuscript/manuscript_thms_v2_zh.md`。

该版本保留 v1 不动，并完成以下结构性变化：

- Introduction 按 THMS 常见的 human–machine problem→gap→RQ→contribution→roadmap 重排。
- Section 2 缩短规范式重复，保留核心定义、三个断点和最低证据包。
- Section 3 改名为 retrospective case demonstration，并按复现顺序重排 G/F 时钟和试次重建信息。
- Results 保留 RQ1–RQ3，减少解释性重复。
- Discussion 改为 principal findings/human–machine significance、design implications、limitations/prospective validation。
- 科学事实、统计值与限定语未被扩展为新因果主张。

---

# H. Change log

| 原位置 | 修改 | 原因 | 参考的 THMS 结构规律 |
|---|---|---|---|
| 标题页状态块 | 压缩措辞但完整保留伦理和投稿阻断 | 让阻断项清楚且不抢占摘要功能 | 参考论文把伦理/稿件信息置于正文外，但必须明确 |
| 摘要 | 重写为 problem→framework→case→G/F evidence→E-A estimate→boundary→meaning | 降低信息拥挤，形成单一结论线 | 三篇摘要均按问题、方法、实验、主要结果、意义推进 |
| 引言第 1 段 | 减少技术清单，强调耦合人机结局 | 更快建立 THMS 适配性 | 三篇均以人的角色/限制定义系统问题 |
| 引言 gap | 新增五条研究路线为何不能独立完成联合推断的综合段 | 避免表 I 成为罗列式综述 | Gottardi/De Pace 的 Related Work 都以“已有路线→仍缺连接”收束 |
| RQ3 | “案例示范”改为“有边界的案例结果” | 防止把案例写成外部验证 | De Pace 显式映射 RQ 与验证对象；贡献/验证边界明确 |
| Contributions | 保留两项并加 article map | 稳定逻辑契约和 section 预期 | Gottardi/De Pace 均在引言末明确贡献/文章结构 |
| Section 2 标题与 2.1 | 缩短名称，先证据链后限定 H/provenance | 提升概念层次和可读性 | 参考论文 framework 先总图/总关系再进入公式 |
| 2.2 | 合并 admissible estimand 的重复限定 | 把关键定义放在唯一权威位置 | 参考论文公式后立即解释科学含义 |
| 2.3 | 保留表 II，压缩三阶段操作流程 | 表 II 是核心方法，不应被补充材料化 | Gottardi 算法框、De Pace 架构表均在正文保留 |
| Section 3 标题 | “案例研究”改为“回顾性案例示范” | 保护非外部验证边界 | 方法论文常区分 framework 与 evaluation/demonstration |
| 3.2/3.3 | 把 G/F 时钟和 activation definition 前移；先 R/Y reconstruction 后 lineage/outcome | 按读者复现顺序组织 | system/conditions→procedure/metrics→statistics 的共同顺序 |
| Fig. 2 图注 | 明确 A/B/C panel 功能 | 使图成为可检索的复现节点 | 参考论文多 panel 图注逐 panel 说明科学任务 |
| 4.1 | 标题改为名义/可执行/实际三层，减少机制性解释 | Results 以事实为主 | De Pace Results 与 Discussion 分工 |
| 4.2 | 保留表 III，不引入 score 或 compliant subgroup | 维持核心方法学后果 | THMS 图表直接承担科学问题，而非装饰 |
| 4.3 | 先 estimate/participant consistency，再 exact/Holm/sensitivity | 对 n=5 更诚实，也减少 p 值主导 | 参考论文用 participant-level displays 支撑组结果 |
| 5.1 | 三个 RQ 合并为 principal findings，并新增 THMS 系统意义 | 减少与 Results 的逐项重复 | Discussion 回答 RQ 后提升到 human–machine meaning |
| 5.1 新段 | 增加与 latency/runtime/reproducibility/fidelity/estimand 的互补关系 | 强化文献定位和 novelty | 参考论文 Discussion/Related Work 明确相对既有工作的作用 |
| 5.2 | 增加“报告时”措辞约束及 E/G/F 例子 | 把框架转成可执行 design implications | THMS 重视接口、实验设计和用户/系统共同评价 |
| 5.3 | 增加前瞻性验证需求并区分 framework validation 与 controller effect | 防止案例被过度推广 | 参考论文将局限与 future work 对应 |
| Conclusion | 精简为框架、正交 provenance、解释边界和系统意义 | 避免重复结果和不当因果暗示 | 三篇结论均回到贡献与适用边界 |

## 科学边界核对

- 核心贡献仍只有两项。
- \(R_i\) 只包括控制器相关事件、激活状态和指令轨迹；\(H_i(t)\) 单列。
- provenance 仍是正交 data-integrity prerequisite，不进入 fidelity score。
- admissible estimand 仍是最窄统计比较目标，不自动具有因果含义。
- 人体独立样本量仍为 \(n=5\)，未把 180 trials 当作 180 个人体样本。
- 0.20–1.00 s outcome 仍为 retrospective exploratory outcome；四个相邻窗口只做稳定性检查。
- E-A 仍只解释为 actual visual-enabled bundled configuration versus actual fixed configuration。
- G 仍表述为 45/45 符合可执行 raw-force logic、43/45 接触前激活，不能称纯 contact-after effect。
- F 仍表述为无接触前激活但仅 3/45 满足名义 +0.20 s，不能称 correctly gated refinement。
- 未制造 human motion onset、reaction time、approach speed 或 hesitation 指标。
- 未增加 bootstrap、Bayesian、mixed-effects、新筛选、新窗口或事后 subgroup。
