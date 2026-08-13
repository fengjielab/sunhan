# K_fb 真实参与者试验运行表（v7）

状态：**仅在完整工程验收通过，并完成伦理审批、知情同意和实验室安全审查后使用。**

## 每天开始前

```bash
cd ~/sunhan/my_test
python3 verify_kfb_timing_setup.py --schedule-dir paper2_sci/23_kfb_timing_pilot/frozen_schedule_v7 --start-pose-file paper2_sci/23_kfb_timing_pilot/start_pose_v1.json
```

校验必须显示 `"overall_pass": true`。现场表只显示匿名条件码，不显示真实 C0–C4。

下面每行都使用最短启动格式：

```bash
bash run_kfb_trial.sh TRIAL_ID SUBJECT_ID
```

程序会先把本次的4个文件统一保存到 `data/kfb_timing_pilot_v7/`。每次结束后，按 Trial ID 将 `.csv`、`_events.json`、`_summary.json` 和 `_manifest.json` 四个文件一起移动到表中对应的参与者目录，再运行下一行。不要只移动 CSV，也不要改文件名。

- 训练试次 `PXX_T...` → `participants/PXX/training/`
- 正式第1区组 `PXX_M01...` → `participants/PXX/measured/block_01/`
- 正式第2区组 `PXX_M02...` → `participants/PXX/measured/block_02/`
- 正式第3区组 `PXX_M03...` → `participants/PXX/measured/block_03/`

## P01

数据根目录：`data/kfb_timing_pilot_v7/participants/P01/`

| 顺序 | 阶段 | 区组 | 序位 | Trial ID | 匿名码 | 完成 | 最短运行命令 |
|---:|---|---:|---:|---|---|:---:|---|
| 1 | 训练（不分析） | 1 | 1 | `P01_T01_01` | `M26F5767` | ☐ | `bash run_kfb_trial.sh P01_T01_01 P01` |
| 2 | 训练（不分析） | 1 | 2 | `P01_T01_02` | `MFA8F504` | ☐ | `bash run_kfb_trial.sh P01_T01_02 P01` |
| 3 | 训练（不分析） | 1 | 3 | `P01_T01_03` | `M3140C01` | ☐ | `bash run_kfb_trial.sh P01_T01_03 P01` |
| 4 | 训练（不分析） | 1 | 4 | `P01_T01_04` | `M79631BA` | ☐ | `bash run_kfb_trial.sh P01_T01_04 P01` |
| 5 | 训练（不分析） | 1 | 5 | `P01_T01_05` | `M87FBFEE` | ☐ | `bash run_kfb_trial.sh P01_T01_05 P01` |
| 1 | 正式 | 1 | 1 | `P01_M01_01` | `M127D2BF` | ☐ | `bash run_kfb_trial.sh P01_M01_01 P01` |
| 2 | 正式 | 1 | 2 | `P01_M01_02` | `M8923879` | ☐ | `bash run_kfb_trial.sh P01_M01_02 P01` |
| 3 | 正式 | 1 | 3 | `P01_M01_03` | `MF0F61F6` | ☐ | `bash run_kfb_trial.sh P01_M01_03 P01` |
| 4 | 正式 | 1 | 4 | `P01_M01_04` | `M4BF245C` | ☐ | `bash run_kfb_trial.sh P01_M01_04 P01` |
| 5 | 正式 | 1 | 5 | `P01_M01_05` | `MB51ECC0` | ☐ | `bash run_kfb_trial.sh P01_M01_05 P01` |
|  | **休息2–3分钟** |  |  |  |  |  | 完成本区组后休息，确认设备状态正常再继续 |
| 6 | 正式 | 2 | 1 | `P01_M02_01` | `MBCD29EA` | ☐ | `bash run_kfb_trial.sh P01_M02_01 P01` |
| 7 | 正式 | 2 | 2 | `P01_M02_02` | `M982A5AA` | ☐ | `bash run_kfb_trial.sh P01_M02_02 P01` |
| 8 | 正式 | 2 | 3 | `P01_M02_03` | `M97EADC5` | ☐ | `bash run_kfb_trial.sh P01_M02_03 P01` |
| 9 | 正式 | 2 | 4 | `P01_M02_04` | `MA987852` | ☐ | `bash run_kfb_trial.sh P01_M02_04 P01` |
| 10 | 正式 | 2 | 5 | `P01_M02_05` | `MFAED338` | ☐ | `bash run_kfb_trial.sh P01_M02_05 P01` |
|  | **休息2–3分钟** |  |  |  |  |  | 完成本区组后休息，确认设备状态正常再继续 |
| 11 | 正式 | 3 | 1 | `P01_M03_01` | `M5EA214B` | ☐ | `bash run_kfb_trial.sh P01_M03_01 P01` |
| 12 | 正式 | 3 | 2 | `P01_M03_02` | `M400319B` | ☐ | `bash run_kfb_trial.sh P01_M03_02 P01` |
| 13 | 正式 | 3 | 3 | `P01_M03_03` | `M81FFD2A` | ☐ | `bash run_kfb_trial.sh P01_M03_03 P01` |
| 14 | 正式 | 3 | 4 | `P01_M03_04` | `M9CC0260` | ☐ | `bash run_kfb_trial.sh P01_M03_04 P01` |
| 15 | 正式 | 3 | 5 | `P01_M03_05` | `M0C77635` | ☐ | `bash run_kfb_trial.sh P01_M03_05 P01` |

## P02

数据根目录：`data/kfb_timing_pilot_v7/participants/P02/`

| 顺序 | 阶段 | 区组 | 序位 | Trial ID | 匿名码 | 完成 | 最短运行命令 |
|---:|---|---:|---:|---|---|:---:|---|
| 1 | 训练（不分析） | 1 | 1 | `P02_T01_01` | `M821FA2C` | ☐ | `bash run_kfb_trial.sh P02_T01_01 P02` |
| 2 | 训练（不分析） | 1 | 2 | `P02_T01_02` | `M00AA5F3` | ☐ | `bash run_kfb_trial.sh P02_T01_02 P02` |
| 3 | 训练（不分析） | 1 | 3 | `P02_T01_03` | `M1315BE5` | ☐ | `bash run_kfb_trial.sh P02_T01_03 P02` |
| 4 | 训练（不分析） | 1 | 4 | `P02_T01_04` | `M6429A81` | ☐ | `bash run_kfb_trial.sh P02_T01_04 P02` |
| 5 | 训练（不分析） | 1 | 5 | `P02_T01_05` | `M15BF43F` | ☐ | `bash run_kfb_trial.sh P02_T01_05 P02` |
| 1 | 正式 | 1 | 1 | `P02_M01_01` | `M662D33B` | ☐ | `bash run_kfb_trial.sh P02_M01_01 P02` |
| 2 | 正式 | 1 | 2 | `P02_M01_02` | `MBFF9E05` | ☐ | `bash run_kfb_trial.sh P02_M01_02 P02` |
| 3 | 正式 | 1 | 3 | `P02_M01_03` | `M10918AB` | ☐ | `bash run_kfb_trial.sh P02_M01_03 P02` |
| 4 | 正式 | 1 | 4 | `P02_M01_04` | `M3A4474E` | ☐ | `bash run_kfb_trial.sh P02_M01_04 P02` |
| 5 | 正式 | 1 | 5 | `P02_M01_05` | `M776CD15` | ☐ | `bash run_kfb_trial.sh P02_M01_05 P02` |
|  | **休息2–3分钟** |  |  |  |  |  | 完成本区组后休息，确认设备状态正常再继续 |
| 6 | 正式 | 2 | 1 | `P02_M02_01` | `M69C3585` | ☐ | `bash run_kfb_trial.sh P02_M02_01 P02` |
| 7 | 正式 | 2 | 2 | `P02_M02_02` | `M5C2EFD2` | ☐ | `bash run_kfb_trial.sh P02_M02_02 P02` |
| 8 | 正式 | 2 | 3 | `P02_M02_03` | `MA4D07E4` | ☐ | `bash run_kfb_trial.sh P02_M02_03 P02` |
| 9 | 正式 | 2 | 4 | `P02_M02_04` | `M1E4E9B4` | ☐ | `bash run_kfb_trial.sh P02_M02_04 P02` |
| 10 | 正式 | 2 | 5 | `P02_M02_05` | `MA830893` | ☐ | `bash run_kfb_trial.sh P02_M02_05 P02` |
|  | **休息2–3分钟** |  |  |  |  |  | 完成本区组后休息，确认设备状态正常再继续 |
| 11 | 正式 | 3 | 1 | `P02_M03_01` | `M12879D9` | ☐ | `bash run_kfb_trial.sh P02_M03_01 P02` |
| 12 | 正式 | 3 | 2 | `P02_M03_02` | `M47BD4FA` | ☐ | `bash run_kfb_trial.sh P02_M03_02 P02` |
| 13 | 正式 | 3 | 3 | `P02_M03_03` | `M9F3C1F8` | ☐ | `bash run_kfb_trial.sh P02_M03_03 P02` |
| 14 | 正式 | 3 | 4 | `P02_M03_04` | `MB00DFA1` | ☐ | `bash run_kfb_trial.sh P02_M03_04 P02` |
| 15 | 正式 | 3 | 5 | `P02_M03_05` | `M50570E8` | ☐ | `bash run_kfb_trial.sh P02_M03_05 P02` |

## P03

数据根目录：`data/kfb_timing_pilot_v7/participants/P03/`

| 顺序 | 阶段 | 区组 | 序位 | Trial ID | 匿名码 | 完成 | 最短运行命令 |
|---:|---|---:|---:|---|---|:---:|---|
| 1 | 训练（不分析） | 1 | 1 | `P03_T01_01` | `MFC6FF0E` | ☐ | `bash run_kfb_trial.sh P03_T01_01 P03` |
| 2 | 训练（不分析） | 1 | 2 | `P03_T01_02` | `ME3EF173` | ☐ | `bash run_kfb_trial.sh P03_T01_02 P03` |
| 3 | 训练（不分析） | 1 | 3 | `P03_T01_03` | `M03AE55C` | ☐ | `bash run_kfb_trial.sh P03_T01_03 P03` |
| 4 | 训练（不分析） | 1 | 4 | `P03_T01_04` | `M9072726` | ☐ | `bash run_kfb_trial.sh P03_T01_04 P03` |
| 5 | 训练（不分析） | 1 | 5 | `P03_T01_05` | `M17EA603` | ☐ | `bash run_kfb_trial.sh P03_T01_05 P03` |
| 1 | 正式 | 1 | 1 | `P03_M01_01` | `MC25F147` | ☐ | `bash run_kfb_trial.sh P03_M01_01 P03` |
| 2 | 正式 | 1 | 2 | `P03_M01_02` | `MD90B3D4` | ☐ | `bash run_kfb_trial.sh P03_M01_02 P03` |
| 3 | 正式 | 1 | 3 | `P03_M01_03` | `MA5D7C00` | ☐ | `bash run_kfb_trial.sh P03_M01_03 P03` |
| 4 | 正式 | 1 | 4 | `P03_M01_04` | `MCCA0590` | ☐ | `bash run_kfb_trial.sh P03_M01_04 P03` |
| 5 | 正式 | 1 | 5 | `P03_M01_05` | `M6CD876F` | ☐ | `bash run_kfb_trial.sh P03_M01_05 P03` |
|  | **休息2–3分钟** |  |  |  |  |  | 完成本区组后休息，确认设备状态正常再继续 |
| 6 | 正式 | 2 | 1 | `P03_M02_01` | `M9FB3DB6` | ☐ | `bash run_kfb_trial.sh P03_M02_01 P03` |
| 7 | 正式 | 2 | 2 | `P03_M02_02` | `M1C54AC4` | ☐ | `bash run_kfb_trial.sh P03_M02_02 P03` |
| 8 | 正式 | 2 | 3 | `P03_M02_03` | `M84575A0` | ☐ | `bash run_kfb_trial.sh P03_M02_03 P03` |
| 9 | 正式 | 2 | 4 | `P03_M02_04` | `M0E4E80F` | ☐ | `bash run_kfb_trial.sh P03_M02_04 P03` |
| 10 | 正式 | 2 | 5 | `P03_M02_05` | `M6D2A39C` | ☐ | `bash run_kfb_trial.sh P03_M02_05 P03` |
|  | **休息2–3分钟** |  |  |  |  |  | 完成本区组后休息，确认设备状态正常再继续 |
| 11 | 正式 | 3 | 1 | `P03_M03_01` | `MF7E25DF` | ☐ | `bash run_kfb_trial.sh P03_M03_01 P03` |
| 12 | 正式 | 3 | 2 | `P03_M03_02` | `M5499B8A` | ☐ | `bash run_kfb_trial.sh P03_M03_02 P03` |
| 13 | 正式 | 3 | 3 | `P03_M03_03` | `M693973F` | ☐ | `bash run_kfb_trial.sh P03_M03_03 P03` |
| 14 | 正式 | 3 | 4 | `P03_M03_04` | `M05564F7` | ☐ | `bash run_kfb_trial.sh P03_M03_04 P03` |
| 15 | 正式 | 3 | 5 | `P03_M03_05` | `M89108D3` | ☐ | `bash run_kfb_trial.sh P03_M03_05 P03` |

## P04

数据根目录：`data/kfb_timing_pilot_v7/participants/P04/`

| 顺序 | 阶段 | 区组 | 序位 | Trial ID | 匿名码 | 完成 | 最短运行命令 |
|---:|---|---:|---:|---|---|:---:|---|
| 1 | 训练（不分析） | 1 | 1 | `P04_T01_01` | `M5851FF8` | ☐ | `bash run_kfb_trial.sh P04_T01_01 P04` |
| 2 | 训练（不分析） | 1 | 2 | `P04_T01_02` | `M44DE2F5` | ☐ | `bash run_kfb_trial.sh P04_T01_02 P04` |
| 3 | 训练（不分析） | 1 | 3 | `P04_T01_03` | `M430679F` | ☐ | `bash run_kfb_trial.sh P04_T01_03 P04` |
| 4 | 训练（不分析） | 1 | 4 | `P04_T01_04` | `M3B2E68D` | ☐ | `bash run_kfb_trial.sh P04_T01_04 P04` |
| 5 | 训练（不分析） | 1 | 5 | `P04_T01_05` | `MB068EC9` | ☐ | `bash run_kfb_trial.sh P04_T01_05 P04` |
| 1 | 正式 | 1 | 1 | `P04_M01_01` | `M20341E5` | ☐ | `bash run_kfb_trial.sh P04_M01_01 P04` |
| 2 | 正式 | 1 | 2 | `P04_M01_02` | `M1BE9766` | ☐ | `bash run_kfb_trial.sh P04_M01_02 P04` |
| 3 | 正式 | 1 | 3 | `P04_M01_03` | `M993C42D` | ☐ | `bash run_kfb_trial.sh P04_M01_03 P04` |
| 4 | 正式 | 1 | 4 | `P04_M01_04` | `M6C750F7` | ☐ | `bash run_kfb_trial.sh P04_M01_04 P04` |
| 5 | 正式 | 1 | 5 | `P04_M01_05` | `MB0FD0C9` | ☐ | `bash run_kfb_trial.sh P04_M01_05 P04` |
|  | **休息2–3分钟** |  |  |  |  |  | 完成本区组后休息，确认设备状态正常再继续 |
| 6 | 正式 | 2 | 1 | `P04_M02_01` | `M682EF88` | ☐ | `bash run_kfb_trial.sh P04_M02_01 P04` |
| 7 | 正式 | 2 | 2 | `P04_M02_02` | `MBAA5539` | ☐ | `bash run_kfb_trial.sh P04_M02_02 P04` |
| 8 | 正式 | 2 | 3 | `P04_M02_03` | `M6AED780` | ☐ | `bash run_kfb_trial.sh P04_M02_03 P04` |
| 9 | 正式 | 2 | 4 | `P04_M02_04` | `M5018AE8` | ☐ | `bash run_kfb_trial.sh P04_M02_04 P04` |
| 10 | 正式 | 2 | 5 | `P04_M02_05` | `MF274072` | ☐ | `bash run_kfb_trial.sh P04_M02_05 P04` |
|  | **休息2–3分钟** |  |  |  |  |  | 完成本区组后休息，确认设备状态正常再继续 |
| 11 | 正式 | 3 | 1 | `P04_M03_01` | `M2DE2832` | ☐ | `bash run_kfb_trial.sh P04_M03_01 P04` |
| 12 | 正式 | 3 | 2 | `P04_M03_02` | `M9C5A167` | ☐ | `bash run_kfb_trial.sh P04_M03_02 P04` |
| 13 | 正式 | 3 | 3 | `P04_M03_03` | `M6FCAB73` | ☐ | `bash run_kfb_trial.sh P04_M03_03 P04` |
| 14 | 正式 | 3 | 4 | `P04_M03_04` | `M9CB9938` | ☐ | `bash run_kfb_trial.sh P04_M03_04 P04` |
| 15 | 正式 | 3 | 5 | `P04_M03_05` | `M5DB4CE8` | ☐ | `bash run_kfb_trial.sh P04_M03_05 P04` |

## 现场规则

- 每位参与者先完成5次训练，再完成3个正式区组，每区组5次。
- 参与者只知道反馈可能变化，不告知条件名称、真实条件或研究方向。
- `HOLD` 后停止主动推进，保持轻触；不要故意回拉、横向摆动或追踪某个力值。
- 仅因崩溃、急停、文件损坏、错误目标或交付超容差补测；不能根据力值、运动量或结果方向补测。
- 失败试次不得删除或覆盖。补测必须使用新的预登记 trial ID，并保留原 incomplete 记录。
- 每次应生成 CSV、events、summary 和 manifest 四个文件。
