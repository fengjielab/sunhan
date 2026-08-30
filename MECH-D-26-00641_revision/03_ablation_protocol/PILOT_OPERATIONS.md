# 预实验现场操作说明

原始预实验部分使用 `PILOT01`、`PILOT02`，每人12次，测试 cup（medium）、
apple（soft）、mouse（hard）三个代表物体。为在正式锁定前覆盖全部六种物体，
`PILOT02` 增加第二会话12次：banana、scissors、bottle 各完成 `I`、`I_H`、
`I_G`、`I_H_G` 四个条件。`PILOT01` 为1-12次；`PILOT02` 为1-24次。
顺序只能来自 `pilot_schedule.csv`。

## 一、实验前一次性准备

1. 将整个 `MECH-D-26-00641_revision` 文件夹复制到机器人实验计算机。
2. 确认实验计算机仍能运行原来的 Omega.7、Franka、RealSense 和 YOLO 环境。
3. 找到本次实际使用的训练权重，记下绝对路径。不要使用不确定的
   `yolo11n.pt` 代替训练权重。
4. 固定机器人、Omega.7、相机、物体起点和目标区；使用优势手操作 Omega.7。
5. 确认物理急停可触及，实验员全程站在急停旁；第一次只放置较安全的 cup。
6. 不得把预实验目录改成 `06_formal_data`，不得修改四条件参数。

## 二、先做软件检查

进入：

```text
MECH-D-26-00641_revision/04_experiment_code/working/my_test
```

运行：

```text
python -m unittest test_ablation_design.py
python simulate_ablation.py --output ../../../07_analysis/ablation_mapping_check.json
python -m py_compile interactive_teleop.py experiment_protocol.py run_scheduled_trial.py
```

必须看到消融设计9项测试、分析工具2项测试通过，并看到模拟结果 `PASS`。

修复版还必须先完成一次硬件冒烟试验。冒烟试验的 validation JSON 中不得有
`errors`，并应确认物体锁定、H/G操纵检查和严格JSON均通过。控制周期若仍有
warning，应记录实测频率并在正式锁定前决定降低主张或锁定较低目标频率。

## 三、检查下一条试验，但不启动硬件

PILOT01第1次的物体是 cup、条件是 `I`。将模型路径替换为真实路径：

```text
python run_scheduled_trial.py \
  --schedule ../../../03_ablation_protocol/pilot_schedule.csv \
  --subject-id PILOT01 --trial-order 1 --run-kind pilot \
  --data-root ../../../05_pilot_data \
  --yolo-model /absolute/path/to/locked_model.pt
```

不加 `--execute` 时只打印计划行和完整命令。核对屏幕中的
`object_id=cup`、`condition=I`、`trial_id=PILOT01_T01` 后才能继续。

Windows命令行不使用反斜杠续行时，可把上述命令写成同一行。

## 四、正式启动一条预实验

在完全相同的命令末尾增加：

```text
--execute
```

程序将依次：

1. 在 `05_pilot_data/PILOT01/PILOT01_S1/G##_object_R1` 写入不可覆盖的运行配置；
2. 连接 Omega.7、Franka、夹爪和 RealSense；
3. 采集静止外力基线；
4. 识别 cup、锁定策略并完成平滑参数切换；
5. 显示“实验开始”后才允许操作者移动；
6. 自动记录接近、抓取、搬运和释放阶段；
7. 释放并稳定0.5 s后自动结束、保存；
8. 自动调用试次校验器并显示 `PASS` 或具体错误。

“实验开始”出现前，操作者必须保持 Omega.7 和机器人不动。10 s内没有有效
视觉锁定时程序会中止该次试验，不会静默使用默认策略。

## 五、操作者动作

1. 用优势手握住 Omega.7，另一只手不得接触实验装置。
2. 听到/看到“实验开始”后接近物体。
3. 通过 Omega.7夹钳闭合触发 Franka抓取。
4. 将物体搬运到固定目标区。
5. 使用灰色按钮或规定的张开动作释放；不要用手扶正物体。
6. 任务结束前不要按键调参。四个正式条件会锁定参数。

## 六、每次结束后的检查

只有校验显示 `PASS`，才能继续下一条。打开生成的 validation JSON，确认：

- 条件和H/G标志一致；
- 存在 `vision_lock`、`task_start`，成功试验还应有 `task_end`；
- 视觉、推理和参数更新时间戳不为0；
- 触觉命令没有超过3.0 N软件限制；
- 控制周期、超时率和饱和率已生成。

随后在 `outcome_record_template.csv` 的副本中记录掉落、滑移、碰撞、重试、
干预和中断原因；每完成一个物体的四个条件，记录六维Raw NASA-TLX。

## 七、继续下一条

把 `--trial-order 1` 逐次递增。每次都先不加 `--execute`核对物体和条件，
确认后再执行。`PILOT01` 到12；`PILOT02` 到24，其中T13-T24位于第二会话。

新采集数据自动按四条件物体组归档。例如PILOT02补充香蕉四条件均进入：

```text
05_pilot_data/PILOT02/PILOT02_S2/G04_banana_R1/
```

剪刀进入 `G05_scissors_R1`，瓶子进入 `G06_bottle_R1`。已有平铺原始数据不移动、
不改名；分析脚本会递归读取新旧两种结构。

## 八、立即停止条件

出现机械臂异常运动、持续振荡、不可预期的大力、夹爪损伤物体、Omega.7异常
输出、频繁USB失联或人员进入机器人危险范围时，立即按现场物理安全流程停机，
然后用 `Ctrl+C` 让程序尽可能保存中断记录。不得删除失败文件；同一计划行可以
重新运行，系统会使用新的run UUID保存，原文件不会被覆盖。

## 九、预实验通过标准

- `PILOT01` 12条与 `PILOT02` 24条计划行均有记录；中断有明确原因。
- 六种物体均能在10 s内稳定识别并完成参数切换。
- 四条件映射全部正确，日志字段完整，无命令越过软件力上限。
- 阶段顺序正确，成功终点无误判。
- 无危险振荡或异常运动，PILOT02完成24次没有不可接受的疲劳。

预实验通过后仍不能直接采集正式数据。应先把模型哈希、伦理信息、安全评估和
最终参数写入 `FORMAL_LOCK.md`，将状态改为正式锁定。

当前 `PILOT01` 属于 pilot_v0，不与修复后的 pilot_v1 合并。完成修复版硬件
冒烟试验并通过上述门槛后，才可开始 `PILOT02`。
