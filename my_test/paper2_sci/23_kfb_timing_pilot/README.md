# K_fb 时序扰动最小可试实验执行包

状态：软件与冻结协议已实现；尚未运行实体机器人、工程验收或人体采集。

本实验沿用 `my_test/interactive_teleop.py` 的 Omega.7、Panda、200 Hz控制循环和原始数据保存，仅新增隔离的 `kfb_timing` 模式。该模式关闭 RealSense、视觉策略、Franka Hand动作和夹爪附加力反馈，只改变 `K_fb=0.5→0.7` 的启动与关闭时刻。

## 研究边界

- 阶段A为25次工程验收，不进入人体结果。
- 阶段B为4名审批后志愿者的可行性预试，每人5次训练和15次正式试次。
- 不计算确认性p值。
- 接触和力结局仍来自Panda内部外力估计，不是独立物理安全终点。
- 未通过机构伦理审批、知情同意或实验室机器人安全审查时，不得开始阶段B。

## 冻结配置

五条件均以 `contact_confirmed` 为零点，结局窗口为 `[+0.20,+1.00] s`：

| 条件 | `K_fb=0.7`区间 | 预期epsilon | 预期Phi |
|---|---:|---:|---:|
| C0 | +0.20至+1.20 s | 0.00 s | 1.000 |
| C1 | +0.05至+1.20 s | -0.15 s | 1.000 |
| C2 | +0.50至+1.20 s | +0.30 s | 0.625 |
| C3 | +0.20至+0.60 s | 0.00 s | 0.500 |
| C4 | +1.10至+1.30 s | +0.90 s | 0.000 |

公共参数、接触检测、5 N中止、2 N反馈限幅、0.03 m/s目标速度限制和分析阈值均在 `my_test/kfb_timing_protocol.py` 中定义，并序列化到 `protocol_config_v1.json`。

## 1. 固定目标和起始位姿

使用至少60 × 60 × 10 mm的平面弹性垫并刚性固定。先由有资质的实验人员通过实验室既有安全流程把末端置于垫面法向外30±2 mm；程序不会在未知工作空间内自动移动机器人。

确认垫在5 N内不触底、不移动后冻结当前位置：

```bash
python3 my_test/capture_kfb_start_pose.py \
  --output my_test/paper2_sci/23_kfb_timing_pilot/start_pose_v1.json \
  --pad-width-mm 60 --pad-height-mm 60 --pad-thickness-mm 10 \
  --pad-distance-mm 30 --fixed-target-checked
```

每次试次启动时，程序只要求当前位置大致回到冻结起点，容差为15 mm、5°；超出时才在控制器启动前拒绝采集并安全关闭设备。若夹具、垫、机器人基座或起始方向发生明显改变，必须生成新位姿文件并重新完成25次工程验收。

## 2. 顺序表和oracle

当前冻结顺序位于 `frozen_schedule_v7/`。`frozen_schedule_v1/` 至
`frozen_schedule_v6/` 已被取代。v7保留跨平台规范文本哈希，并把现场起始位姿
容差放宽为相对冻结位置15 mm、姿态5°；名义起点仍为垫面法向外约30 mm。
实体采集产生的CSV/events/summary仍使用严格原始字节哈希。不得用v1至v6开展采集。

- `engineering_run_sheet.csv`：25次工程顺序，不含真实条件；
- `participant_run_sheet.csv`：4人训练和正式顺序，不含真实条件；
- `private_oracle/oracle.csv`：真实条件、预定时刻及配置/采集代码哈希，应限制访问；
- `schedule_metadata.json`：种子、数量及冻结哈希。

只有在采集代码有意修改并决定重新开始完整验收时，才可在新的空目录重新生成：

```bash
python3 my_test/generate_kfb_timing_schedule.py \
  --output-dir my_test/paper2_sci/23_kfb_timing_pilot/frozen_schedule_v8
```

程序会拒绝非空输出目录；代码哈希变化后，旧oracle也会被现场入口拒绝。

采集前验证冻结文件；起始位姿生成后同时传入该文件：

```bash
python3 my_test/verify_kfb_timing_setup.py \
  --schedule-dir my_test/paper2_sci/23_kfb_timing_pilot/frozen_schedule_v7 \
  --start-pose-file my_test/paper2_sci/23_kfb_timing_pilot/start_pose_v1.json
```

## 3. 运行一次试次

按现场运行表中的匿名顺序执行。示例：

```bash
python3 my_test/interactive_teleop.py \
  --mode kfb_timing \
  --subject-id ENGINEER \
  --trial-id ENG_E01_01 \
  --object-id FIXED_PAD \
  --kfb-oracle my_test/paper2_sci/23_kfb_timing_pilot/frozen_schedule_v7/private_oracle/oracle.csv \
  --kfb-start-pose-file my_test/paper2_sci/23_kfb_timing_pilot/start_pose_v1.json \
  --trajectory-dir data/kfb_timing_pilot_v7
```

程序行为：

1. 核对 trial、participant、配置哈希、采集代码哈希和起始位姿；
2. 采集2 s静止基线，以median/MAD冻结接触阈值；
3. 显示可以接近目标；连续满足接触条件50 ms后显示 `HOLD`；
4. 按私有oracle施加匿名时序，接触后1.5 s自动撤去反馈并结束；
5. 保存不可覆盖的CSV、events、summary和SHA-256 manifest四个文件。

高/低力、运动量异常或结果方向不是补测理由。技术中止必须保留原文件，使用预先登记的新trial ID补测并记录关联关系。

## 4. 盲态重建和揭盲顺序

先由不接触oracle的分析者运行：

```bash
python3 my_test/analyze_kfb_timing.py reconstruct \
  --data-dir data/kfb_timing_pilot_v7 \
  --output analysis/kfb_timing/fidelity_blinded.csv
```

保存 `fidelity_blinded.csv` 和自动生成的 `fidelity_blinded.freeze.json`，锁定其SHA-256后再揭盲：

```bash
python3 my_test/analyze_kfb_timing.py unblind \
  --fidelity analysis/kfb_timing/fidelity_blinded.csv \
  --oracle my_test/paper2_sci/23_kfb_timing_pilot/frozen_schedule_v7/private_oracle/oracle.csv \
  --output analysis/kfb_timing/fidelity_unblinded.csv
```

最后才计算Omega路径长度和Panda操作性力指标：

```bash
python3 my_test/analyze_kfb_timing.py analyze \
  --data-dir data/kfb_timing_pilot_v7 \
  --fidelity analysis/kfb_timing/fidelity_unblinded.csv \
  --oracle my_test/paper2_sci/23_kfb_timing_pilot/frozen_schedule_v7/private_oracle/oracle.csv \
  --output-dir analysis/kfb_timing/results
```

输出包括试次指标、参与者×条件描述统计、`C1-C0`/`C3-C0`配对差、工程或人体通过报告和分析溯源。分析程序不计算p值。

## 5. 硬性停止规则

- 阶段A任一硬指标失败，不得招募志愿者；修复后升级版本并重新完成全部25次。
- 阶段B至少57/60次技术有效且每人至少14/15次有效；否则仅报告未通过可行性。
- 任何安全事件、反馈发送失败、命令限幅、系统性掉帧或条件相关数据缺失均不得以删除试次解决。
- 正式20–24人实验前必须增加独立F/T传感器；本预试不能替代该步骤。
