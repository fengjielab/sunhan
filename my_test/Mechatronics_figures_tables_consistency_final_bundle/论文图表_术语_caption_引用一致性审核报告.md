# 论文图表、术语、caption 与正文引用一致性审核报告

## 1. Supplementary Table S1 的放置方式

- Supplementary Table S1 不作为正文中的普通表格插入，也不需要转换成图片。
- 正文在实验设计部分引用 “Supplementary Table S1”；完整表格作为单独的补充材料文件提交。
- 表中的 A–E 为分析展示顺序，不声称是实际时间执行顺序。

## 2. 术语统一结果

### 三类操作策略（不是三种实验模式）

| 中文 | 英文 | 对象 |
|---|---|---|
| 易损优先策略 | fragility-priority strategy | 苹果、香蕉 |
| 折中策略 | balanced strategy | 纸杯、瓶子 |
| 稳定优先策略 | stability-priority strategy | 鼠标、剪刀 |

### 五种实验模式

| 模式 | 中文标准名称 | 英文标准名称 |
|---|---|---|
| A | 固定参数 | fixed parameters |
| B | 操作者选择完整参数策略 | operator-selected full-parameter strategy |
| C | 视觉语义完整多通道调度 | vision-semantic full multi-channel scheduling |
| D | 仅视觉提示 | visual cue only without parameter updates |
| E | 视觉语义仅阻抗调度 | vision-semantic impedance-only scheduling |

## 3. 差值方向统一

- 全文、Fig. 6、Fig. 7 和 Supplementary Table S1 统一定义 $\Delta T=T_E-T_C$。
- 正值表示模式 C 更快。完成时间改善为 1.79 s，95% CI [1.10, 2.51] s。
- 主端轨迹缩短量为 0.024 m，95% CI [−0.014, 0.059] m。
- Raw NASA-TLX 改善量为 4.87，95% CI [4.39, 5.35]。

## 4. Caption 与图内容审核

| 图 | 审核结果 | 正文作用 |
|---|---|---|
| Fig. 1 | caption 描述实验平台和设备组成；需确保最终平台照片确实标出 Omega.7、Panda、Franka Hand、D435i 和控制计算机。 | 支撑系统硬件组成。 |
| Fig. 2 | caption 与方法中的异步感知、200 Hz 上层循环、5 ms 周期及 48.19 ms 视觉处理时间一致。 | 支撑感知—控制解耦和接触前锁定。 |
| Fig. 3 | caption 与三面板流程图对应；最终图内已统一为 Fixed、Operator-selected、Full multi-channel、Visual cue only、Impedance-only，并将 manual selection 改为 operator selection。 | 支撑五模式定义与参数锁定范围。 |
| Fig. 4 | 三个子图分别对应混淆矩阵、置信度和处理时间；48.19 ms 已统一。 | 支撑视觉模块在受控条件下的识别和时延结果。 |
| Fig. 5 | (a)–(d) 与完成时间、轨迹长度、Raw NASA-TLX、成功率完全对应。 | 支撑五模式总体描述性比较。 |
| Fig. 6 | 最终正文版仅保留 (a) 配对散点和 (b) 配对改善分布。 | 支撑核心 C–E 系统级消融。 |
| Fig. 7 | (a) 操作者分层、(b) 对象分层；小点、均值菱形和 ±1 SD 与 caption 对应。 | 回答 RQ4，支撑跨操作者和对象的一致方向。 |

## 5. 结果与讨论对图的引用关系

- §4.1 直接引用 Fig. 4。
- §4.2 直接引用 Fig. 5。
- §4.3 直接引用 Fig. 6，并将分层结果引向 Fig. 7。
- §4.6 直接引用 Fig. 7。
- §5.1 将系统机制与 Fig. 5 的时间和工作负荷结果联系。
- §5.2 将核心解释与 Fig. 6、Fig. 5(b) 和停顿分析联系。
- §5.5 直接引用 Fig. 7(b) 解释不同对象收益幅度。
- 结论引用 Fig. 6–7 作为核心消融和一致性证据。

## 6. 尚需作者确认的事项

- Fig. 1 和 Fig. 2 的最终图像未在本次文件集中完整核对；提交前按 caption 逐项检查设备标签和两子图结构。
- Supplementary Table S1 不包含实际 chronological order；若实验日志能够恢复真实顺序，可另增 Supplementary Table S2。