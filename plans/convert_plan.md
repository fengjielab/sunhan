# vision_stiffness 格式转换计划

## 转换目标

将 `vision_stiffness` 的 v2 格式转换为与其他模式一致的 v1 格式。

## 转换脚本

将要创建的 Python 脚本: `plans/convert_vision_stiffness_format.py`

### 脚本逻辑

**Step 1: 备份** → 将原始文件复制到 `_backup_vision_stiffness/` 目录

**Step 2: CSV 转换 (49列 → 12列)**

| v1列名 | 从v2映射 |
|--------|---------|
| time | system_time |
| x | robot_x |
| y | robot_y |
| z | robot_z |
| gripper_deg | gripper_deg |
| button | button |
| K_trans | K_trans |
| K_rot | K_rot |
| damping_ratio | damping_ratio |
| K_fb | K_fb |
| deadband | deadband |
| scale | scale |

**Step 3: JSON 转换**

删除这些顶层键：
- `external_force`（与力相关，不要）
- `fusion_config`（融合配置）
- `experiment`（完整事件块和实验元数据）

简化 `final_params`，删除：
- `vision_base_K_trans`
- `vision_base_K_rot`
- `fusion_delta_K_final`

简化 `mode`，只保留：
- `mode`, `vision_enabled`

**Step 4: 删除 `_events.json` 文件**
（其他模式没有这个文件）

### 目标文件

| 目录 | CSV | Summary JSON | Events JSON |
|------|-----|-------------|-------------|
| hard_date/第一组实验 | `vision_stiffness_20260702_105245.csv` | `vision_stiffness_20260702_105245_summary.json` | `vision_stiffness_20260702_105245_events.json` |
| soft_date/第一组实验 | `vision_stiffness_20260702_093613.csv` | `vision_stiffness_20260702_093613_summary.json` | `vision_stiffness_20260702_093613_events.json` |

### 验证方法

转换完成后，用 `diff` 风格检查：
1. CSV header 必须是 `time,x,y,z,gripper_deg,button,K_trans,K_rot,damping_ratio,K_fb,deadband,scale`
2. JSON 必须包含且只包含: `timestamp`, `saved_at`, `mode`, `runtime`, `trajectory`, `final_params`
3. JSON 不能包含: `external_force`, `fusion_config`, `experiment`
