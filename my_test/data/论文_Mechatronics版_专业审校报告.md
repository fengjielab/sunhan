# 《Mechatronics》稿件专业审校报告

审校对象：`论文_Mechatronics版_最终术语与图文一致性检查稿.md`  
审校日期：2026-07-13  
审校结论：**Major revision（目前不建议直接投稿）**

> 本报告为独立审校文件，未修改原稿、图片、代码或实验数据。行号均指审校时的目标 Markdown 文件。

## 1. 执行摘要

稿件的主线是成立的：异质对象语义在接触前触发一组离散、可解释的阻抗—触觉接口—夹爪参数，并通过 A–E 五模式区分固定参数、人工选择、仅视觉提示、完整调度和仅阻抗调度。C–E 比较也确实是全文最有说服力的系统级消融。

但目前存在四类会被审稿人直接抓住的问题：

1. **论文描述与实际实现不完全一致**：视觉流、采样频率、触觉死区公式、夹爪力反馈叠加、策略锁定和参数更新方式均存在差异。
2. **图文和数据版本未完全锁定**：Fig. 2 缺少正文所述面板；Table 4 多个中位数/IQR 与当前数据不一致；Fig. 7 正文取整错误。
3. **统计推断边界仍偏强**：27 个 task block 嵌套于 3 名操作者，不能等同于 27 名独立参与者；block-level bootstrap 也没有处理操作者聚类。
4. **投稿合规尚未闭环**：伦理豁免缺少机构依据，参考文献 [14–23] 未引用，且若图形由生成式 AI 创建或修改，将触发 Elsevier 明确的禁用政策。

建议先解决第 2 节的投稿阻断项，再做语言润色。否则，语言越精致，方法—实现不一致越容易被审稿人识别为实质性问题。

## 2. 致命问题 / 投稿阻断项

### F1. “RGB-D、约 20 Hz”与当前实现不一致

- **位置**：第 9、49、59、63、79、86、141、282 行及 Fig. 2。
- **原文要点**：D435i 以约 20 Hz 采集 RGB-D 图像，并由异步 RGB-D 感知进程完成识别。
- **核查证据**：`interactive_teleop.py:1009` 仅启用了 `rs.stream.color, 424×240@15 fps`；未启用 depth stream。第 1016–1017 行建立的是彩色帧队列与结果队列。
- **问题**：硬件是 RGB-D 相机，不等于实验实际使用了深度信息；15 fps 采集也不能写成约 20 Hz 感知。48.19 ms/帧是推理处理时间，不代表新图像输入频率为 20 Hz。
- **风险**：方法不可复现，审稿人会质疑是否夸大了感知模态和实时性能。
- **建议改法**：全文统一改为“D435i 的 RGB stream / color stream”；将“约 20 Hz”改为“相机输入 15 fps，单帧推理平均 48.19 ms，推理进程异步运行”。若确实使用过深度流，需提供对应版本代码、深度用途和实验日志后才能保留 RGB-D。

### F2. 触觉接口公式与代码实现不等价

- **位置**：第 124–135 行，式（触觉反馈）；第 57、81、135、392 行。
- **原文要点**：先按外力向量范数与死区 `d` 比较，再按向量方向输出 `K_f(||F_ext||-d)`。
- **核查证据**：`interactive_teleop.py:1931–1938` 实际先逐轴计算 `F_scaled = K_f F_ext`，再对每个分量应用死区：`sign(F_scaled)(|F_scaled|-d)`；第 1940–1944 行还额外在 Z 方向叠加夹爪闭合程度对应的触觉力。
- **问题**：范数死区与逐轴死区不同；“先乘增益再减死区”与论文公式“先减原始力死区再乘增益”也不同。当前公式还遗漏夹爪力反馈叠加通道。
- **风险**：核心方法公式与实际实验实现不一致，属于可复现性硬伤。
- **建议改法**：不要改代码追论文；应按实际实验代码重写方法。推荐公式：

  \[
  u_{h,i}=\operatorname{sgn}(K_fF_{\mathrm{ext},i})
  \max\!\left(|K_fF_{\mathrm{ext},i}|-d,0\right),\quad i\in\{x,y,z\},
  \]

  并另写 `u_{h,z} ← u_{h,z}+u_g`，说明 `u_g` 是由主端夹爪输入/闭合程度生成并限幅的附加提示。如果实验期间实际关闭了该叠加项，则须用实验配置或日志证明，而不能仅依据当前代码推断。

### F3. “接触前原子锁定并保持不变”与实现存在差异

- **位置**：第 65、67、84、88、141、188–191、196–198 行；Fig. 2–3。
- **原文要点**：首次有效检测后原子更新七个参数；锁定发生在 approach 前；整个 episode 参数固定。
- **核查证据**：
  - `interactive_teleop.py:1982–2017` 在首次有效检测时触发；未见以 approach phase 为硬门限、禁止迟到检测的判断。
  - `interactive_teleop.py:757–814` 的阻抗参数由后台线程做 smoothstep 过渡，并非瞬时原子更新；触觉、映射比例和夹爪参数则在启动过渡后立即写入。
  - 完整模式虽然 `scale=3.0`，但代码仍把 `scale` 作为 preset 成员写入；“七维参数原子更新”不能准确描述执行顺序。
  - 无有效检测时启动的是 `standard` preset，其中 `deadband=0.3`；表 2 的“折中策略”为 `d=0.4`，两者并不完全相同。
- **问题**：锁定事件、参数到达最终值的时刻、fallback 参数和“原子”概念均未准确描述。
- **风险**：Fig. 2–3 的核心创新图与实际软件状态机不一致。
- **建议改法**：
  1. 将“原子更新”改为“首次有效检测触发一次性策略选择；阻抗参数平滑过渡到目标值，其他接口参数按当前实现写入”。
  2. 明确检测窗口：若实验协议保证 approach 前等待视觉锁定，写出等待条件和超时；否则改为“目标接触前完成锁定”，并报告迟到/未锁定次数。
  3. 明确 fallback 的真实数值，尤其是 `d=0.3` 还是 `0.4`。
  4. 不要声称七个参数原子同步，除非代码和日志能证明同一控制周期生效。

### F4. Fig. 2 文件、正文与 caption 三者不一致

- **位置**：第 45、51–53、88 行。
- **当前文件**：`图二.png` 只包含标为 (a) 的总体架构。
- **补充文件**：`图二b.png` 包含 (b)，但没有 caption 所称的“5-ms update interval”和“48.19-ms processing time”数值。
- **问题**：把 `图二b.png` 简单拼接进去仍不能满足现有 caption。
- **风险**：属于投稿前技术检查即可发现的明显错误。
- **建议改法**：组合 (a)+(b)，并采用本报告第 8 节的新 caption；或者重新绘制 (b)，显式放入 15 fps 输入、48.19 ms 平均推理时间、名义 5 ms supervisor target、锁定事件和任务阶段。二者选其一，不可继续使用当前 caption。

### F5. Table 4 多个 median [IQR] 与当前数据不一致

- **位置**：第 303–311 行；摘要第 12 行；Fig. 5。
- **核查基准**：`all_trials_135.csv`（135 行）和 `nasa_tlx_results/nasa.md`（45 条，即每模式 9 条）。
- **问题**：完成时间统计正确，但 A/B/D 的轨迹长度中位数及 A/B/D 的 Raw NASA-TLX 中位数与当前源数据不一致。均值±SD反而与源数据一致，说明表中混入了旧版本或不同筛选口径。
- **正确汇总**（Pandas 默认线性分位数；mean±sample SD）：

| 模式 | 完成时间 (s) | 轨迹长度 (m) | Raw NASA-TLX |
|:---:|:---|:---|:---|
| A | 21.18 [20.62, 22.08] (21.42±1.58) | **0.757 [0.693, 0.816]** (0.763±0.098) | **62.50 [59.67, 64.50]** (62.59±3.95) |
| B | 20.89 [20.12, 21.83] (21.01±1.61) | **0.787 [0.721, 0.861]** (0.799±0.115) | **56.17 [55.00, 59.33]** (57.15±3.68) |
| C | 19.57 [18.41, 20.05] (19.28±1.30) | 0.697 [0.660, 0.769] (0.715±0.092) | 48.67 [47.67, 51.83] (49.67±3.63) |
| D | 20.79 [20.32, 21.16] (20.91±1.10) | **0.722 [0.678, 0.768]** (0.734±0.085) | **60.33 [57.33, 62.50]** (60.22±3.85) |
| E | 20.73 [19.95, 22.25] (21.07±1.56) | 0.732 [0.678, 0.799] (0.739±0.084) | 53.67 [51.83, 57.83] (54.54±4.09) |

- **建议改法**：锁定唯一分析脚本、分位数算法和纳入规则；重生 Table 4、Fig. 5 与全文数字表。不要手工抄写统计量。

### F6. 伦理“自行豁免”表述不可直接保留

- **位置**：第 217、445–446 行。
- **原文**：“不收集可识别个人身份的信息，因此免于正式伦理审查。”
- **问题**：是否豁免通常由机构伦理委员会或本机构适用规则决定，不由作者依据“非医学/去标识”自行宣告。研究还记录了年龄、性别、手别和人在环表现。
- **风险**：伦理合规质疑可直接导致编辑部要求说明，严重时退稿。
- **建议改法**：
  - 若有机构批准/豁免：写明机构全称、批准或豁免编号和日期。
  - 若确无审查机制：如实写明研究所在机构的适用规定及为何不要求审查，并保留书面知情同意证据；投稿前由单位科研/伦理管理部门确认。
  - 不能仅写“作者认为免审”。

## 3. 主要问题

### M1. RQ3 没有被结果部分真正回答

- **位置**：第 210、280–299、408、426 行。
- **问题**：RQ3 问“实时性和基础可靠性”，4.1 只报告识别准确率和推理时间。现有 `control_loop_jitter_results.md` 显示 591,554 周期的平均周期 5.80 ms、中位数 5.07 ms、1.77% 周期超过 10 ms、最大 99.96 ms。这支持“名义 200 Hz、非硬实时”，但不支持笼统的“满足实时性”。
- **建议**：二选一：
  1. 将 RQ3 改为“异步感知是否能在不把推理放入控制关键路径的情况下完成接触前策略初始化”，并仅作架构可行性回答；
  2. 正式加入 jitter 结果，分 vision-on/off 比较，并明确 supervisor loop 不是硬实时控制环。

### M2. 27 个 block 不能当作 27 名独立参与者

- **位置**：第 244、274、315、323–339、416–418 行。
- **问题**：task block 在同一操作者内重复，block-level bootstrap 假定的独立性并不充分。只有 3 名操作者时，面向总体人群的显著性推断很弱。
- **建议**：
  - 将 Friedman/Wilcoxon 和 bootstrap 明确标注为“task-block-level exploratory paired analysis”。
  - 主要结论限定于当前平台、操作者和任务块；保留操作者分层方向作为重复测量证据。
  - 不写“证明方法对操作者泛化”；写“the direction was consistent across the three tested operators”。
  - 若重分析，优先使用能体现 operator clustering 的层级模型或按操作者聚合的敏感性分析；3 个 cluster 下不要夸大渐近 p 值。

### M3. Fig. 4 的 100% 准确率缺少数据隔离说明

- **位置**：第 280–299、420 行。
- **缺失信息**：180 张图像是否来自训练集之外；是否为连续视频抽帧；每个对象是否只有一个实例；采集日期、视角和背景；YOLO11n 是 COCO 预训练直接使用还是再次训练；策略触发如何处理多目标和漏检。
- **风险**：同一对象实例、相邻帧和受控背景下的 180/180 很容易被质疑为非独立样本或数据泄漏。
- **建议**：将其定位为“controlled bench validation”，补充独立性和采样协议；不要用“识别性能验证”暗示开放场景泛化。

### M4. Fig. 4(b)/(c) 图例声称显示 individual samples，但图中未显示

- **位置**：Fig. 4b、Fig. 4c、caption 第 299 行。
- **问题**：两图图例都有“Individual detections/frames”的空心圆符号，但实际只画了柱/方块和误差条。
- **建议**：要么真正叠加 30 个 jittered points/类，要么删除 individual-sample 图例。本报告第 8 节 caption 按“当前未显示散点”的版本撰写。

### M5. 模式 B “策略误选”解释与数据冲突

- **位置**：第 352、357 行。
- **核查证据**：`all_trials_135.csv` 中 B 模式 27 次的 `b_subtype` 与 `object_attr` 全部一致（soft 9/9、medium 9/9、hard 9/9）。
- **问题**：不能把 B 的 6 次失败归因于“操作者策略误选”，除非另有逐试验记录证明。
- **建议改法**：改为“人工选择与切换增加了工作流步骤；现有任务级记录不足以把失败归因于具体选择错误”。

### M6. 指标定义与结果报告不闭环

- **位置**：第 268 行定义了方向反转和运动平滑性，但第 4 节未报告；第 213 行把轨迹长度写成预期改善，但 C–E CI 跨零。
- **建议**：未作为预注册终点且未完整报告的方向反转/平滑性应从“评价指标”删除，或补齐算法、结果和统计口径。假设应区分主要终点和探索性次要终点。

### M7. “停顿减少导致时间收益”的机制解释仍偏强

- **位置**：第 12、213、335、343、386、390、431 行。
- **问题**：C 与 E 同时改变 `K_f`、`d`、`v_g`、`F_g`，无法识别哪个通道导致停顿变化；停顿中位数两组同为 3，当前只报告描述性均值差，没有阶段级或因果分析。
- **建议**：统一使用“consistent with / 与……一致”“may be associated with / 可能相关”，不要使用“主要来自”“从而减少”等因果措辞。

### M8. Fig. 7 正文取整错误

- **位置**：第 333、374 行。
- **当前数据**：P01=1.662678→1.66 s；P02=2.564933→**2.56 s**；P03=1.157100→**1.16 s**。
- **原文**：1.66、2.57、1.15 s。
- **建议**：统一采用常规四舍五入后的 1.66、2.56、1.16 s；Fig. 7 当前图内数值是正确的。

### M9. 参考文献双向对应失败，且有一次错引

- **位置**：全文和第 453–477 行。
- **核查结果**：正文仅覆盖 [1–13]；[14–23] 均未出现。第 398 行把 visual-impedance framework 指向 [9]，但 [9] 是 variable impedance review，真正对应的是当前 [12]。
- **建议**：
  - [14] 可用于机电系统集成定位；[15–17] 用于视觉伺服背景；[18] 用于抓取/接触背景；[19–20] 用于轻量机械臂/Franka 平台；[21] 用于 Raw NASA-TLX；[22–23] 用于 haptic shared control/virtual fixtures。
  - 添加后必须按首次出现顺序整体重编号，不能保留当前编号硬插。
  - 按期刊格式补 DOI，并使用期刊名标准缩写。

### M10. 标题使用“协同合成”超出实际方法

- **位置**：第 1 行及全文创新性表述。
- **问题**：方法是从三组预定义参数中查表、锁定和调度，没有在线优化或参数 synthesis 算法。“合成”容易让审稿人期待优化目标、约束求解或稳定性证明。
- **建议**：标题和主线统一用“接触前协同调度/初始化”。推荐标题见第 7 节。

### M11. Mode 字母与软件内部标签存在版本冲突

- **核查证据**：当前论文定义 C=完整多通道、D=仅视觉提示、E=仅阻抗；`interactive_teleop.py:476–481` 的内部 `_experiment_condition` 却把 `vision_observe→C`、`vision_stiffness→D`、`vision→E`。`extract_all_trials.py` 又使用论文的新映射。
- **风险**：共享代码、日志或补充材料时会出现 C/D/E 含义冲突。
- **建议**：论文中保留当前 A–E，但在数据字典中给出唯一映射；投稿前冻结代码版本并改内部标签，或明确说明原始软件标签已在分析阶段重映射。

### M12. 图像分辨率/格式不完全符合投稿建议

- **现状**：Fig. 2a/2b 为 1672×941，Fig. 3 为 1448×1086；Fig. 4b/c 为 2104×1063。它们属于线图/文本图，作为位图低于 Elsevier 对单栏 bitmapped line drawing 的推荐 3543 px。
- **建议**：Fig. 2–7 优先导出 PDF/EPS 矢量图并嵌入字体；不要只提交 PNG。Fig. 1 照片 3000×2250 足够作为照片类图像，但应保留原始未标注照片。

### M13. 性别/手别信息需要说明其分析用途

- **位置**：第 217、416 行。
- **问题**：报告了 2 男 1 女，却没有讨论性别分析；样本也不足以进行性别比较。
- **建议**：保留为参与者描述，并在局限性写明没有设计或统计功效进行 sex/gender subgroup analysis；不要暗示代表性。

### M14. 数据可用性表述偏弱

- **位置**：第 449 行。
- **问题**：文中大量结果依赖 135-trial 数据、NASA-TLX、视觉验证和绘图脚本，仅写“合理请求”会削弱可复现性。
- **建议**：在隐私允许下，将去标识数据、分析脚本、图源和数据字典存入有版本号的仓库；至少随稿提交完整 Supplementary Table S1 和统计脚本。

## 4. 一般问题与语言问题

1. **第 8–15 行结构化摘要**：Mechatronics 要求英文摘要不超过 250 词，但未要求结构化小标题。最终英文稿建议改成单段，避免 Purpose/Design/Results/Originality 的管理学期刊风格。
2. **第 17 行关键词**：当前 6 个，数量合规；最终必须为英文，尽量避免过长复合短语。
3. **第 45、71、88 等行**：中文内部稿统一写“图 1”“表 1”；最终英文稿统一为“Fig. 1”“Table 1”。不要在同一语言版本混用。
4. **episode / block / trial**：建议定义为：trial=一次模式任务；matched task block=同一 operator-object-repeat 下的五个 matched trials；episode 不再使用，统一改为 trial。
5. **wall-clock、bootstrap、mixed**：中文稿分别改为“墙钟处理时间”“Bootstrap（自助法）”“方向不一致”；英文稿再恢复标准英文术语。
6. **第 57 行“基础触觉接口”**：含义不清，改为“主端力反馈渲染通道”。
7. **第 59、63 行“视觉线程/子进程”混用**：实际为采集线程加 YOLO 子进程，应分别描述，不能都叫视觉线程。
8. **第 84 行“每个 5 ms 周期开始时”**：代码只表明主循环读取共享状态，不宜写成经实测的严格周期起点行为；改为“在主循环迭代中非阻塞读取”。
9. **第 120 行“改进”**：改为“本文贡献”，避免暗示对经典阻抗方程作了数学改进。
10. **第 161–177 行参数依据**：诸如“Omega.7 舒适范围”“Panda 稳定范围”缺少具体边界和测量。改成“本平台预实验确认的可用工作点”，除非能给出硬件手册或稳定性试验。
11. **第 217 行左手操作**：所有人右利手却统一左手操作可能显著影响绝对表现，应提前解释选择左手的工程原因，并在局限性中保留。
12. **第 244 行 block**：使用 `matched task block`，避免裸写英文 `block`。
13. **第 268 行 Raw NASA-TLX**：首次出现应写全称“unweighted Raw NASA Task Load Index (Raw NASA-TLX)”并引用原始文献。
14. **第 303 行 mean±SD**：数学排版统一为 `mean ± SD`，运算符两侧留空格。
15. **第 315 行“极显著/显著优于”**：英文科技写作不使用“extremely significant”。写“a global difference was detected”及准确 p 值。
16. **第 357、392 行抓取稳定性解释**：没有接触力、滑移量或损伤量标定，改为“与……解释一致”，不要写成已证明机制。
17. **第 433 行“低成本”**：未报告成本比较，改为“low computational overhead”或“无需在线优化”。

## 5. 逐图审查

| 图 | 判定 | 主要问题 | 必须动作 |
|:---:|:---:|:---|:---|
| Fig. 1 | 可用但需整理 | 图内标题字号过大；背景人员虽模糊仍较杂；Host PC 指向不够明确；图内用红色虚线而全文图形多用蓝/紫/绿 | 裁剪背景、统一标注样式；保留匿名化；caption 说明平台，不重复所有软件功能 |
| Fig. 2 | 不可投稿 | 主文件只有 (a)；(b) 独立存在但与现 caption 数值不匹配；图内还写 ~20 Hz | 组合并重绘/改字为 15 fps；caption 与实际面板逐项一致；导出矢量 |
| Fig. 3 | 基本可用 | 图内模式定义清楚，但 Mode E 的“others default”应说明具体 baseline；“lock before contact”需与实际协议一致 | 先修方法状态机描述，再同步图内文字；导出矢量 |
| Fig. 4 | 需大修 | b/c 图例声称显示 individual samples，实际无散点；100% 结果缺少 hold-out 说明；三个独立文件投稿时易被误当三张图 | 添加原始点或删图例；最好合成统一 Fig. 4；补数据采样说明 |
| Fig. 5 | 可用但数据表需重生 | 图本身表达清楚；Table 4 与图/数据不一致；组合图在双栏缩放后字体需实测 | 用同一数据脚本重生表图；在 190 mm 宽度检查最小字体 |
| Fig. 6 | 可用 | 直观支持 C–E；violin 在 n=27 时应明确仅描述性；文件名 `AB` 容易造成版本误解 | caption 保留重复测量限制；投稿文件重命名为 `Figure_6` |
| Fig. 7 | 可用但正文数字需改 | 图内 P02=2.56、P03=1.16 正确，正文错误；对象层每组仅 n=4/5 | 修改正文；caption 强调描述性，不对对象总体作推断 |

## 6. 数据与统计复核结果

### 6.1 已复核正确

- 135 次试验 = 27 matched task blocks × 5 modes。
- 每名操作者每模式 9 次。
- C–E 完成时间平均配对改善：1.7949 s；22/27 blocks 中 C 更快。
- C–E 操作者分层均值：P01 1.6627 s（7/9）、P02 2.5649 s（9/9）、P03 1.1571 s（6/9）。
- 对象分层均值：剪刀 2.8548、纸杯 2.4815、鼠标 1.8903、苹果 1.6958、香蕉 1.1448、瓶子 0.6693 s。
- Raw NASA-TLX 的 C–E 平均差为 4.8704 分。
- 成功率汇总 A/B/C/D/E = 22/21/26/24/24（每模式 n=27）。

### 6.2 尚需作者确认

- 失败试验是否确实未提前截断，并与成功试验共享同一计时终点。
- 180 张视觉图像与训练/调参数据的独立关系。
- 预实验两名研究人员是否与正式三名操作者重叠；若重叠，是否可能形成熟练度偏倚。
- 参数表和停顿阈值是否在查看正式结果前冻结；“预先定义”需要实验协议、代码提交或时间戳支持。
- Fig. 1–3 是否使用了任何生成式 AI 创建或修改；若是，按当前 Elsevier 政策不能作为投稿图直接使用。

## 7. 推荐标题与关键结论替换稿

### 7.1 标题

**中文推荐：**

> 面向异质对象触觉遥操作的视觉语义驱动接触前多通道机电参数调度

**英文推荐：**

> Pre-contact vision-semantic scheduling of coupled mechatronic parameters for haptic teleoperation of heterogeneous objects

该标题准确体现“接触前、视觉语义、多通道、调度”，同时避免“synthesis”带来的优化/控制综合预期。

### 7.2 摘要结果段（中文安全版）

> 在当前平台、三名操作者和六种测试对象范围内，完整多通道模式取得最短的任务完成时间中位数（19.57 s，IQR 18.41–20.05 s）、最高的描述性成功率（26/27，96.3%）和最低的 Raw NASA-TLX 中位数（48.67，IQR 47.67–51.83）。相较于视觉语义仅阻抗调度，完整多通道模式的平均配对完成时间缩短 1.79 s（task-block-level Bootstrap 95% CI 1.10–2.51 s），三名操作者和六种对象的分层均值均呈相同方向。主端轨迹长度差异较小（平均配对差 0.024 m，95% CI −0.014–0.059 m）。停顿次数的描述性变化与完成时间改善方向一致，但现有实验不能将该差异归因于某一独立参数通道。

### 7.3 Abstract results paragraph (English)

> On the tested platform and within the three-operator, six-object task set, the full multi-channel mode yielded the shortest median task duration (19.57 s, IQR 18.41–20.05 s), the highest descriptive success rate (26/27, 96.3%), and the lowest median Raw NASA-TLX score (48.67, IQR 47.67–51.83). Relative to vision-semantic impedance-only scheduling, the full mode reduced task duration by a mean paired difference of 1.79 s (task-block-level bootstrap 95% CI, 1.10–2.51 s). The stratum means had the same direction for all three operators and all six objects. The paired difference in master-side trajectory length was smaller (0.024 m; 95% CI, −0.014 to 0.059 m). The descriptive pause-count results were consistent with the duration difference, but the present design does not identify the contribution of any individual parameter channel.

### 7.4 结论段（中文安全版）

> 本文实现并评估了一种面向异质对象触觉遥操作的接触前视觉语义参数调度框架。该框架将受控对象类别映射为三种面向操作的策略，并一次性选择从端阻抗、主端触觉接口和夹爪执行参数。五模式实验表明，在当前平台和任务集内，完整多通道模式相较仅阻抗调度具有一致的任务完成时间优势，同时保持较高的描述性成功率和较低的主观工作负荷。由于研究仅包含三名操作者，且未对各附加参数通道进行独立消融，结果支持的是当前系统级参数包的有效性，而不是人群层面的统计泛化或单一通道的因果贡献。

### 7.5 Conclusion paragraph (English)

> This study implemented and evaluated a pre-contact vision-semantic parameter-scheduling framework for haptic teleoperation of heterogeneous objects. The framework maps controlled object classes to three operation-oriented strategies and selects a coupled set of slave-side impedance, master-side haptic-interface, and gripper-execution parameters. In the five-mode experiment, the full multi-channel mode consistently reduced task duration relative to impedance-only scheduling within the tested platform and task set, while showing a higher descriptive success rate and lower perceived workload. Because the study included only three operators and did not independently ablate the additional parameter channels, the results support the system-level parameter package under the tested conditions rather than population-level generalization or a causal contribution from any single channel.

## 8. Fig. 1–7 可直接替换的 captions

以下 captions 以“先修正实现描述和图片内容”为前提；Fig. 2 采用组合现有 (a)+(b)、不虚构 5 ms/48.19 ms 图内标注的版本。

### Fig. 1

**中文：**

> **图 1.** 异质对象触觉遥操作实验平台。操作者使用 Force Dimension omega.7 主端设备生成运动输入并接收力提示；从端由 Franka Emika Panda 机械臂和 Franka Hand 夹爪组成。Intel RealSense D435i 的彩色图像流用于观察对象工作区，主机负责视觉推理、监督式遥操作、参数选择、机器人命令和数据记录。

**English:**

> **Fig. 1.** Experimental platform for haptic teleoperation of heterogeneous objects. The operator uses a Force Dimension omega.7 device to provide motion input and receive force cues. The slave side comprises a Franka Emika Panda manipulator and a Franka Hand gripper. The color stream from an Intel RealSense D435i observes the object workspace, while the host computer performs visual inference, supervisory teleoperation, parameter selection, robot command generation, and data logging.

### Fig. 2

**中文：**

> **图 2.** 接触前视觉语义参数调度框架及其异步执行逻辑。(a) 彩色图像感知、三级语义映射、参数调度、从端阻抗、主端触觉接口、夹爪执行和安全回退之间的信息流。(b) 感知结果经有界队列传递，并由监督式遥操作循环非阻塞读取；首次有效类别触发一次性策略选择，随后参数在试验执行期间不再因后续检测结果切换。无有效类别时使用预设回退参数。图示为软件架构与事件顺序，不表示硬实时保证。

**English:**

> **Fig. 2.** Pre-contact vision-semantic parameter-scheduling framework and asynchronous execution logic. (a) Information flow among color-image perception, three-level semantic mapping, parameter scheduling, slave-side impedance, the master-side haptic interface, gripper execution, and safety fallback. (b) Perception results are transferred through bounded queues and read non-blockingly by the supervisory teleoperation loop. The first valid class triggers a one-time strategy selection, after which subsequent detections do not cause intra-trial switching. Preset fallback parameters are retained when no valid class is available. The diagram describes the software architecture and event sequence and does not imply hard-real-time operation.

### Fig. 3

**中文：**

> **图 3.** 实验流程、五种模式及策略选择后的参数范围。(a) 每次试验依次经历复位、模式相关策略输入、接近、抓取、转运、释放和结束；视觉模式的策略选择目标是在对象接触前完成。(b) 五种模式为固定参数（A）、操作者选择完整策略（B）、视觉语义完整多通道调度（C）、仅视觉提示且参数固定（D）和视觉语义仅阻抗调度（E）。(c) 完整策略包含从端阻抗参数 \(K_t,K_r,\zeta\)、主端触觉接口参数 \(K_f,d\) 和夹爪执行参数 \(v_g,F_g\)；模式 E 仅改变阻抗相关参数。

**English:**

> **Fig. 3.** Experimental workflow, five operating modes, and the parameter scope following strategy selection. (a) Each trial proceeds through reset, mode-specific strategy input, approach, grasp, transport, release, and task completion; in the vision-based modes, strategy selection is intended to be completed before object contact. (b) The five modes are fixed parameters (A), operator-selected full strategy (B), vision-semantic full multi-channel scheduling (C), visual cue only with fixed parameters (D), and vision-semantic impedance-only scheduling (E). (c) The full strategy comprises slave-side impedance parameters \(K_t,K_r,\zeta\), master-side haptic-interface parameters \(K_f,d\), and gripper-execution parameters \(v_g,F_g\); mode E changes only the impedance-related parameters.

### Fig. 4

**中文：**

> **图 4.** 受控台架条件下的对象类别检测与策略触发结果。(a) 六类对象的混淆矩阵，每类 30 张图像。(b) 各类别检测置信度的均值±SD；虚线表示总体均值 0.853，点线表示检测阈值 0.25。(c) 各类别单帧墙钟处理时间的均值±SD；虚线表示总体均值 48.19 ms。共评估 180 张图像，当前受控数据集中所有图像均被正确分类并映射到预定义策略。该结果不代表开放场景鲁棒性或硬实时保证。

**English:**

> **Fig. 4.** Object detection and strategy-trigger results under controlled bench conditions. (a) Confusion matrix for six object classes, with 30 images per class. (b) Class-wise detection confidence, reported as mean ± SD; the dashed line denotes the overall mean of 0.853 and the dotted line denotes the detection threshold of 0.25. (c) Class-wise per-frame wall-clock processing time, reported as mean ± SD; the dashed line denotes the overall mean of 48.19 ms. All 180 images in the controlled dataset were correctly classified and mapped to the predefined strategies. These results do not establish robustness in open environments or hard-real-time performance.

### Fig. 5

**中文：**

> **图 5.** 五种实验模式下任务表现和主观工作负荷的描述性比较。(a) 任务完成时间；(b) 主端轨迹长度；(c) 未加权 Raw NASA-TLX；(d) 任务成功率。面板 (a) 和 (b) 每种模式包含来自 27 个匹配任务块的试验，圆、三角和方形分别表示 P01–P03；箱体、中心线和须分别表示 IQR、中位数和 1.5×IQR。面板 (c) 的小符号表示每模式 9 个“操作者×策略”评分单元，大符号及连线表示按三种策略等权平均的操作者均值。面板 (d) 报告每模式 27 次尝试中的成功次数，仅作描述性解释。

**English:**

> **Fig. 5.** Descriptive comparison of task performance and perceived workload across the five experimental modes. The panels show (a) task duration, (b) master-side trajectory length, (c) unweighted Raw NASA-TLX, and (d) task success rate. Panels (a) and (b) contain 27 matched task-block observations per mode; circles, triangles, and squares denote P01–P03, respectively. Boxes, center lines, and whiskers denote the interquartile range, median, and 1.5 times the interquartile range. In panel (c), small symbols denote the nine operator-by-strategy ratings per mode, whereas the larger connected symbols denote operator means obtained by equally averaging the three strategies. Panel (d) reports successful trials among 27 attempts per mode and is interpreted descriptively.

### Fig. 6

**中文：**

> **图 6.** 视觉语义完整多通道调度（模式 C）与视觉语义仅阻抗调度（模式 E）的系统级消融。(a) 27 个匹配任务块的配对完成时间；恒等线下方的点表示模式 C 更快。(b) 配对改善量 \(\Delta T=T_E-T_C\) 的描述性分布；正值表示模式 C 的完成时间更短。符号区分 P01–P03，小提琴形状仅用于描述分布，水平线和菱形分别表示中位数和均值。这些任务块嵌套于三名操作者内，不代表 27 名独立参与者。

**English:**

> **Fig. 6.** System-level ablation of vision-semantic full multi-channel scheduling (mode C) against vision-semantic impedance-only scheduling (mode E). (a) Paired task durations for 27 matched task blocks; points below the identity line indicate a shorter duration in mode C. (b) Descriptive distribution of the paired improvement, \(\Delta T=T_E-T_C\); positive values indicate a shorter duration in mode C. Symbols identify P01–P03, the violin summarizes the empirical distribution, and the horizontal line and diamond denote the median and mean, respectively. The task blocks are nested within three operators and do not represent 27 independent participants.

### Fig. 7

**中文：**

> **图 7.** 模式 C 相对于模式 E 的完成时间配对改善在操作者和对象层面的描述性一致性，\(\Delta T=T_E-T_C\)。(a) P01–P03 的操作者分层结果，每名操作者 9 个匹配任务块。(b) 六种对象的分层结果，每种对象 4 或 5 个匹配任务块，并按平均改善量递减排序。小符号表示任务块配对差，菱形表示分层均值，水平线表示重复任务块差值的均值±SD。右侧给出分层均值和模式 C 更快的任务块数。该图用于描述当前样本内的一致性，不作操作者或对象总体推断。

**English:**

> **Fig. 7.** Descriptive operator- and object-stratified consistency of the paired task-duration improvement of mode C over mode E, \(\Delta T=T_E-T_C\). (a) Operator-stratified results for P01–P03, with nine matched task blocks per operator. (b) Object-stratified results for the six objects, with four or five matched task blocks per object and strata ordered by decreasing mean improvement. Small symbols denote task-block paired differences, diamonds denote stratum means, and horizontal lines denote mean ± SD across the repeated task-block differences. Labels on the right report the stratum mean and the number of blocks in which mode C was faster. The figure describes consistency within the tested sample and is not used for population-level inference across operators or objects.

## 9. 投稿合规检查

依据 [Mechatronics 官方 Guide for Authors](https://www.sciencedirect.com/journal/mechatronics/publish/guide-for-authors)：

1. 期刊目前仅接受使用 LaTeX、双栏格式的投稿；建议使用 `elsarticle` 的 `5p,times` 选项。
2. Regular Article 通常不超过 10,000 词和 15 个印刷页；最终英文稿需在双栏版式下实测。
3. 摘要不超过 250 词；关键词 1–6 个；需另交 3–5 条 highlights，每条不超过 85 个字符。
4. 图必须逐一在正文引用，caption 需包含简短标题和自解释描述，符号与缩写必须解释。
5. 参考文献必须双向匹配，并按正文首次出现顺序编号。
6. 需要 CRediT author contribution statement、funding statement、competing-interest declaration 和 data statement。
7. 使用生成式 AI 辅助稿件准备必须按指南声明。本次若采纳 AI 生成的审校或改写内容，应由作者全面核实并在投稿时按政策作相应声明。
8. Elsevier 当前明确不允许使用生成式 AI 创建或修改投稿图像/图形（除非其本身是研究方法且可复现说明）。若 Fig. 1–3 或其他图使用过生成式 AI，必须以作者可控的原始照片、数据绘图或矢量工具重新制作，不能仅作声明后继续提交。

## 10. 四轮终检结果

| 回查项 | 当前状态 | 判定依据 |
|:---|:---:|:---|
| 所有图表均被引用且面板存在 | **失败** | Fig. 2(b) 未包含在正文引用的主图文件中；现有 (b) 与 caption 数值仍不匹配 |
| 数值跨摘要/正文/表图一致 | **失败** | Table 4 多个 median/IQR 错误；Fig. 7 正文取整错误 |
| 参考文献双向匹配 | **失败** | [14–23] 未引用；第 398 行 visual-impedance 错引 [9] |
| 摘要、讨论和结论不超过证据 | **失败** | RGB-D/20 Hz、原子锁定、触觉公式、机制因果和实时性表述需收缩或更正 |

## 11. 推荐修订顺序

1. 冻结唯一代码、数据和模式映射版本。
2. 依据真实实现重写视觉流、触觉公式、fallback 和锁定机制。
3. 用单一脚本重生 Table 4、Fig. 5–7 及所有统计文字。
4. 重制 Fig. 2，修正 Fig. 4 图例并导出矢量图。
5. 收缩统计与机制结论，修正 RQ3、模式 B 失败解释和未报告指标。
6. 补齐伦理依据、参考文献、CRediT、AI 使用声明和数据可用性。
7. 最后再进行全文英文润色和 LaTeX 双栏排版；不要在方法事实尚未锁定前做终稿级语言抛光。

