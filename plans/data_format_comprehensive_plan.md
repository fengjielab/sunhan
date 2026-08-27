# 实验数据格式综合分析 + 标准化方案

## 一、现有数据文件概览

### hard_date/第一组实验 (11 files)

| 文件 | 格式版本 | CSV列数 | JSON结构 | 说明 |
|------|---------|---------|---------|------|
| `default.csv` / `default.json` | v1 | 12 | 基础字段 | 模式A(固定参数) |
| `hard_obj.csv` / `hard_obj.json` | v1 | 12 | 基础+preset | 模式B(硬物体预设) |
| `vision_observe.csv` / `vision_observe.json` | v1 | 12 | 基础字段 | 模式C(视觉消融) |
| `vision.csv` / `vision.json` | v1 | 12 | 基础字段 | 模式E(视觉前馈) |
| `vision_stiffness_20260702_105245.csv` | **v2** | **49** | **完整含事件** | 模式D(视觉调阻抗) |
| `vision_stiffness_20260702_105245_summary.json` | **v2** | - | 含`experiment`块 | 模式D汇总 |
| `vision_stiffness_20260702_105245_events.json` | **v2** | - | 仅事件 | 独立事件文件 |

### soft_date/第一组实验 (11 files)
同样的文件结构，其中:
- `vision_stiffness_20260702_093613.csv` — v2格式 (49列)
- `vision_stiffness_20260702_093613_summary.json` — v2格式
- `vision_stiffness_20260702_093613_events.json` — v2格式

## 二、CSV格式差异对比

### v1 (旧版) — 12列
```csv
time,x,y,z,gripper_deg,button,K_trans,K_rot,damping_ratio,K_fb,deadband,scale
```

### v2 (新版, vision_stiffness) — 49列
```csv
schema_version,system_time,operation_time,phase,event,mode,controller_mode,
subject_id,object_id,trial_id,omega_x,omega_y,omega_z,omega_valid,gripper_deg,
button,target_x,target_y,target_z,robot_x,robot_y,robot_z,F_ext_x,F_ext_y,F_ext_z,
T_ext_x,T_ext_y,T_ext_z,F_ext_mag,K_trans,K_rot,damping_ratio,K_fb,deadband,scale,
gripper_state,gripper_cmd_width,gripper_width,gripper_width_valid,gripper_speed,
gripper_force,grasp_success,vision_class,vision_label,vision_confidence,vision_locked,
fusion_delta_K,fusion_active,control_dt,force_baseline_mean,force_baseline_std,force_threshold
```

### 关键缺失
| 数据 | v1 CSV | v2 CSV | 重要性 |
|------|--------|--------|--------|
| 外力 F_ext_mag | ❌ | ✅ (48列) | 论文核心指标 |
| 阶段 phase | ❌ | ✅ (4列) | 按阶段分析 |
| 夹爪状态 | ✅ gripper_deg | ✅ 更丰富 | - |
| 视觉信息 | ❌ | ✅ vision_class/label | 模式C/D/E/F必需 |
| 融合信息 | ❌ | ✅ fusion_delta_K/active | 模式F必需 |

## 三、JSON格式差异

### v1 (旧版) — 结构
```json
{
  "timestamp": "20260613_175709",
  "saved_at": "...",
  "mode": { "mode": "default", "vision_enabled": false },
  "runtime": { "duration_s": 21.99, "traj_length_m": 0.6332, ... },
  "trajectory": { "n_samples": 4324, "pos_x_range_m": [...], ... },
  "final_params": { "K_trans": 150.0, ... }
}
```

### v2 (新版) — 结构
```json
{
  // 基础字段（同v1）
  "timestamp": "...", "saved_at": "...",
  "mode": { "mode": "vision_stiffness", "vision_enabled": true, ... },
  "runtime": { ... },
  "trajectory": { ... },
  "external_force": {        // 🆕 新增
    "source": "Franka estimated external wrench",
    "F_ext_peak_N": 6.515, "F_ext_peak_time_s": 23.293,
    "F_ext_mean_N": 2.679, "n_samples": 2955
  },
  "final_params": {           // 🆕 新增 vision_base_*, fusion_delta_K_final
    "vision_base_K_trans": 200.0, "vision_base_K_rot": 13.0,
    "fusion_delta_K_final": 0.0
  },
  "fusion_config": null,      // 🆕 新增
  "experiment": {             // 🆕 全新 events 块
    "schema_version": 2,
    "mode": "D",
    "subject_id": "unknown", "object_id": "unknown", "trial_id": "unknown",
    "started_at_unix": ...,
    "phase": "COMPLETE",
    "completed": true, "incomplete": false,
    "recognition_time_s": 1.7386, "operation_time_s": 19.3594,
    "force_baseline_mean_N": 1.4689, "force_baseline_std_N": 0.0617,
    "force_threshold_N": 1.6538,
    "events": [ ...11个事件... ]
  }
}
```

## 四、模式映射不一致问题 ⚠️

| 内部模式名 | `interactive_teleop.py` 映射 | `ral_paper_plots.py` 映射 | 正确论文标号 |
|-----------|----------------------------|--------------------------|------------|
| `default` / `experiment_fixed_a` | A | A | A(固定参数) |
| `soft_obj` / `hard_obj` | B | B | B(人工选择) |
| `vision_observe` | **C** | **D** ❌ | C(视觉消融) |
| `vision_stiffness` | **D** | ❌未明确处理 | D(视觉仅调阻抗) |
| `vision` | **E** | **C** ❌ | E(视觉多参数前馈) |
| `vision_force` | F | F | F(视觉-力融合) |

**`ral_paper_plots.py` 中模式解析存在错误：**
- 第103行: `"vision_observe" → "D"` 应为 `C`
- 第107行: `"vision" → "C"` 应为 `E`
- 未处理 `"vision_stiffness"` 映射到 D

## 五、待办事项清单

### 第一阶段：格式标准化

- [ ] **1.1 创建统一数据加载器** — 支持同时读取 v1 和 v2 格式的 CSV/JSON
  - v1 缺少 `F_ext_mag` → 标记为 NaN
  - v1 缺少实验事件 → 标记为 None
  - v2 的49列CSV头 + v2 JSON events 优先使用

- [ ] **1.2 修复 ral_paper_plots.py 的模式映射**
  - `vision_observe` → C (不是D)
  - `vision` → E (不是C)  
  - 新增 `vision_stiffness` → D

- [ ] **1.3 统一 CSV 产出格式** — 修改 `interactive_teleop.py`
  - 所有模式都输出 v2 格式 (49列CSV)
  - 所有模式都输出含 `experiment` 块的 JSON
  - 新增：`F_ext_mag` 列到所有模式CSV

### 第二阶段：数据分析能力

- [ ] **2.1 按模式+物体分组的批量分析**
  - 从 `data/hard_date/` 和 `data/soft_date/` 自动发现所有 trial
  - 支持 v1/v2 混合数据集的统一分析

- [ ] **2.2 生成论文所需图表**
  - 完成时间、外力峰值、NASA-TLX、成功率等
  - 确保 v1 数据也能参与分析（标记缺失列）

### 第三阶段：与新数据目录结构对齐

- [ ] **3.1 启用新目录结构** (ral_experiment/operator_{id}/)
  - 添加 `--operator-id` 参数
  - 保存时自动使用新结构

## 六、技术决策

1. **v1→v2 数据桥接**：分析脚本中通过 `has_col("F_ext_mag")` 判断数据完整性，缺失则在该指标分析中排除该 trial
2. **CSV列定义**：定义 `TRAJECTORY_CSV_HEADER_V2` 常量，所有模式统一使用
3. **JSON版本识别**：通过 `"experiment" in summary` 判断 v1/v2
