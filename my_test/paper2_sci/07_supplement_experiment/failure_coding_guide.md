# 失败与成功率编码规则

成功率必须按首测、端到端口径统计，不能删除视觉误识别、抓取失败或安全停止试次。

`failure_stage` 只使用：`vision`、`approach`、`initial_contact`、`grasp`、`transport`、`release`、`system`。`failure_reason` 采用可观察事实，例如 `no_detection`、`wrong_raw_class`、`excess_force`、`grasp_not_secured`、`object_drop`、`collision`、`communication_error`，不要写主观推测。

判定规则：

- `task_completed=1`：事件日志存在 `task_end`。
- `grasp_success=1`：存在 `grasp_success`，且物体确已被稳定提起；程序字段与人工观察冲突时必须备注。
- `software_safety_stop=1`：存在 `safety_stop` 事件。
- `raw_vision_correct=1`：原始检测类别与实际物体一致；这不改变 C/W 条件身份。
- `include_end_to_end_success=1`：所有首测固定为 1，包括失败；该列表示纳入成功率分母，不表示成功。
- 任何补测使用新的 trial_id，`attempt_number≥2`，`primary_first_attempt=0`，并链接到首测。补测不能覆盖或替换主分析首测。
