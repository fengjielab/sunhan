# RAL 论文实验数据格式规范 + 自动化分析方案

## 一、你需要跑哪些实验

6种模式 × 3类物体 × 5+个操作者 × 5次重复 = **最少 450 次实验**

| 模式 | 名称 | 启动命令 | 谁做 |
|------|------|---------|------|
| A | 固定参数 | `interactive_teleop.py --mode experiment_fixed_a` | 所有人 |
| B | 人工选择 | `interactive_teleop.py --mode experiment_fixed_a` + 手动按预设键 | 所有人 |
| C | 视觉前馈 | `interactive_teleop.py --mode vision` | 所有人 |
| D | 视觉消融 | `interactive_teleop.py --mode vision_observe` | 所有人 |
| E | 力反馈自适应 | `force_adaptive_teleop.py` | 所有人 |
| F | **视觉-力融合** | `interactive_teleop.py --mode vision_force` | 所有人 |

## 二、你的数据存什么

### 每个 trial 产生 2 个文件

**文件1: 轨迹 CSV**（模式A-F共用统一格式）

```csv
time,x,y,z,gripper_deg,button,K_trans,K_rot,damping_ratio,K_fb,deadband,scale,F_ext_mag,fusion_delta_K,fusion_active,vision_label,alpha,F_sat
```

| 列 | 来源 | 含义 |
|----|------|------|
| time | 共同 | 时间戳(s) |
| x,y,z | 共同 | 末端位置(m) |
| gripper_deg | 共同 | 夹爪开度(deg) |
| button | 共同 | 按钮状态 |
| K_trans | 共同 | 平移刚度(N/m) |
| K_rot | 共同 | 旋转刚度(Nm/rad) |
| F_ext_mag | 共同 | 末端外力幅值(N) |
| fusion_delta_K | 模式F特有 | 融合修正量，其他模式=0 |
| fusion_active | 模式F特有 | 融合是否激活，其他模式=0 |
| vision_label | 模式C/D/F | 视觉标签，其他=unknown |
| alpha | 模式E特有 | 自适应缩放系数，其他=0 |
| F_sat | 模式E特有 | 力饱和阈值，其他=0 |

**文件2: 汇总 JSON**

```json
{
  "operator": "01",
  "mode": "F",
  "object": "soft",
  "repeat": 1,
  "object_name": "sponge",
  "timestamp": "20260629_143000",
  "duration_s": 12.5,
  "traj_length_m": 0.42,
  "mean_speed_ms": 0.035,
  "F_ext_peak_N": 4.2,
  "F_ext_mean_N": 2.1,
  "F_ext_std_N": 1.5,
  "F_ext_p95_N": 5.8,
  "K_trans_mean": 75.0,
  "K_trans_min": 30.0,
  "fusion_delta_K_final": -35.0,
  "vision_label": "soft",
  "success": 1,
  "nasa_tlx": 25,
  "damage_score": 0,
  "human_score": 4
}
```

## 三、文件命名规范

```
data/ral_experiment/
└── operator_{编号}/
    ├── A_fixed/
    │   ├── trial_A_soft_01.csv
    │   ├── trial_A_soft_01.json
    │   ├── trial_A_soft_02.csv
    │   ├── trial_A_soft_02.json
    │   ├── trial_A_medium_01.csv
    │   ├── trial_A_hard_01.csv
    │   └── ...
    ├── B_human/
    ├── C_vision/
    ├── D_vision_observe/
    ├── E_force_adaptive/
    └── F_fusion/
        ├── trial_F_soft_01.csv
        ├── trial_F_soft_01.json
        ├── trial_F_medium_01.csv
        └── ...
```

## 四、实验时要注意记录的数据

### 自动记录（脚本已做）
- ✅ 轨迹数据（CSV）
- ✅ 外力峰值/均值
- ✅ 完成时间
- ✅ 轨迹长度

### 需要人工记录（建议做个小表格打勾）
- ✅ 成功/失败（success=1/0）
- ✅ NASA-TLX 六维度评分（做完一组模式填一次，不是每次trial都填）
- ✅ 物体损伤评分（1-5）
- ✅ 抓取品质评分（1-5）

## 五、分析脚本出图清单

写好脚本后，一次 `python3` 命令输出：

| 图号 | 内容 | 数据来源 |
|------|------|---------|
| 图1 | **完成时间分组柱状图**（6模式×3物体） | JSON中的duration_s |
| 图2 | **末端外力峰值对比**（6模式×3物体） | JSON中的F_ext_peak_N |
| 图3 | **F模式过程曲线**（F_ext_mag, K_trans, fusion_delta_K vs time） | F模式的CSV |
| 图4 | **NASA-TLX雷达图**（6模式×6维度） | 手动填写的TLX数据 |
| 图5 | **成功率和损伤评分** | JSON中的success/damage_score |
| 图6 | **六模式外力峰值折线图**（按操作者分组） | JSON汇总 |
| 图7 | **F模式 vs E模式 外力时序对比** | CSV文件直接对比 |
| 图8 | **刚度-力散点图**（K_trans vs F_ext_mag，所有模式） | CSV汇总 |

## 六、生成论文表格

| 表号 | 内容 |
|------|------|
| 表1 | 策略库参数表 |
| 表2 | 完成时间+外力峰值+成功率 汇总表 |
| 表3 | NASA-TLX 汇总表 |
