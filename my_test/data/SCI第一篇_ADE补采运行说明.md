# SCI 第一篇 A/D/E 补采运行说明

## 1. 本轮目的

旧 108 次实验继续作为 A/B/C/E 四模式主体数据。本轮只补同批次的 D/E 配对数据：

- D：视觉仅阻抗，语义只调度 \(K_t,K_r,\zeta\)；
- E：视觉多参数前馈，语义调度 \(K_t,K_r,\zeta,K_f,d,v_g,F_g\)。

新 E 同时作为批次锚点，用于检查新旧 E 是否一致。A 可在预实验或发现明显批次漂移时补采。

## 2. 已冻结参数

| 类别 | \(K_t\)/(N/m) | \(K_r\)/(N·m/rad) | \(\zeta\) | \(K_f\) | \(d\)/N | 夹爪速度/(m/s) | 夹爪力/N |
|---|---:|---:|---:|---:|---:|---:|---:|
| soft | 50 | 5 | 0.8 | 0.2 | 0.3 | 0.02 | 8 |
| medium | 150 | 10 | 1.0 | 0.5 | 0.4 | 0.05 | 15 |
| hard | 200 | 13 | 1.2 | 0.7 | 0.5 | 0.10 | 20 |

D 模式只使用表中的前三列，其他参数保持固定基线；E 使用完整参数组。主从映射比例统一为 3.0，不作为本论文的语义调度变量。

## 3. 上机前九次预实验

使用一名调试操作者，每类物体分别运行 D/E，并额外运行 A 检查固定基线，共 9 次：

```text
soft:   A, D, E
medium: D, E, A
hard:   E, A, D
```

预实验数据目录必须与正式数据分开，例如 `my_test/data/sci_pilot/`。预实验不进入论文统计。

## 4. 正式运行命令

### A 固定参数（仅作锚点时使用）

```bash
python3 my_test/interactive_teleop.py \
  --mode experiment_fixed_a \
  --subject-id P01 \
  --object-id soft_01 \
  --trial-id SCI_P01_soft_01_A_R01 \
  --trajectory-dir my_test/data/sci_formal/P01
```

### D 视觉仅阻抗

```bash
python3 my_test/interactive_teleop.py \
  --mode vision_stiffness \
  --subject-id P01 \
  --object-id soft_01 \
  --trial-id SCI_P01_soft_01_D_R01 \
  --trajectory-dir my_test/data/sci_formal/P01
```

### E 视觉多参数前馈

```bash
python3 my_test/interactive_teleop.py \
  --mode vision \
  --subject-id P01 \
  --object-id soft_01 \
  --trial-id SCI_P01_soft_01_E_R01 \
  --trajectory-dir my_test/data/sci_formal/P01
```

正式实验不要添加 `--manual-stop`。程序检测到释放完成后应自动结束并保存一个独立 trial。

## 5. 正式补采数量

若沿用原 3 名操作者、每人每条件 3 次重复：

\[
3\text{名操作者}\times3\text{类物体}\times2\text{模式(D/E)}\times3\text{次}=54\text{次}
\]

每名操作者完成 18 次。D/E 顺序需要交替，不能所有人都先做 D：

```text
P01：D-E-D-E...
P02：E-D-E-D...
P03：按物体类别轮换起始模式
```

## 6. 每次结束后的立即检查

每个 trial 应生成：

- `*.csv`：逐周期原始数据；
- `*_events.json`：任务阶段与视觉锁定事件；
- `*_summary.json`：汇总结果；
- 力指标分析文件或图（生成失败不影响前三个原始文件）。

抽查 CSV 时必须满足：

- `subject_id/object_id/trial_id` 不是 `unknown`；
- D 的 `mode` 为 `D`，E 的 `mode` 为 `E`；
- D 中 `K_fb/deadband/scale/gripper_speed/gripper_force` 不随类别切换；
- D 中 `K_trans/K_rot/damping_ratio` 与识别类别一致；
- E 中阻抗、力反馈及夹爪参数均与识别类别一致；
- `vision_confidence` 有有效数值且 `vision_locked=1`；
- `task_start` 和 `task_end` 均存在；
- `completed=true`，失败任务则单独记录原因，不覆盖或删除。

## 7. 禁止中途修改

正式采集开始后，除修复会导致数据无效的明确程序错误外，不再调整参数表、视觉阈值、计时阈值、夹爪逻辑和任务流程。若必须修改，应提升实验版本号并将修改前后数据视为不同批次。
