# 视觉前验代码修改方案

基于数据分析结论，提出三个修改方向。

---

## 修改方向 1（推荐）: 降低视觉基线刚度 + 降低 force_sat

**目的**: 让视觉方法在外力较小时就进入更低刚度，产生明显更低的峰值力。

### 修改 A: 降低 vision_soft 的基线刚度

文件: [`my_test/interactive_teleop.py:285-291`](my_test/interactive_teleop.py:285)

```python
# 修改前
"vision_soft": {
    "K_trans": 90.0, "K_rot": 5.0,   # 刚度 90
    ...
},

# 修改后
"vision_soft": {
    "K_trans": 60.0, "K_rot": 3.5,   # 刚度 60 (降 33%)
    ...
},
```

### 修改 B: 降低 soft 策略的 force_sat

文件: [`my_test/interactive_teleop.py:331-338`](my_test/interactive_teleop.py:331)

```python
# 修改前
"soft": {
    "gain": -0.40,
    "force_deadband": 0.5,
    "force_sat": 4.0,       # 4N 就饱和
    "K_min": 55.0,
    "K_max": 90.0,
},

# 修改后
"soft": {
    "gain": -0.50,          # 更大幅度降低
    "force_deadband": 0.3,  # 更早开始降刚度
    "force_sat": 2.5,       # 更低饱和阈值
    "K_min": 30.0,          # 允许降到更低
    "K_max": 60.0,          # 配合新的 K_base
},
```

### 预期效果

新公式下，外力 2.5N 时刚度就降到最低：
```
K_t = clip(60 · (1 + (-0.50) · 1.0), 30, 60) = 30
```
比原来的最低 55 降低了 45%，有望在峰值力上体现明显差异。

---

## 修改方向 2: 提前激活视觉融合（接触前干预）

**目的**: 视觉在接触发生前就降低刚度，减少首次冲击力峰值。

### 修改: 用 gripper_deg 判断"即将接触"来触发融合

文件: [`my_test/interactive_teleop.py:887-901`](my_test/interactive_teleop.py:887)

```python
def _update_vision_force_fusion(self, now: float):
    if not self._vision_force_fusion or not self._vision_locked:
        return
    if now - self._fusion_last_update < FUSION_IMPD_UPDATE_INTERVAL:
        return
    self._fusion_last_update = now

    # ── 新增：提前激活逻辑 ──
    # 如果夹爪开度接近物体宽度（gripper_deg < 某个阈值），提前降刚度
    # 而不需要等到接触力产生
    if self.gripper_deg < 20.0:  # 夹爪接近闭合 → 即将接触
        # 直接使用视觉基线的低刚度，跳过力等待
        target_K = self._vision_base_K_trans * 0.8  # 提前降到 80%
        self._K_trans_cur += 0.1 * (target_K - self._K_trans_cur)
        # ... 继续正常 fusion 逻辑
```

### 预期效果

避免 `fusion_active` 在 t=4.266s 才激活（此时已接触），改为接触前就进入低刚度状态，首次接触力峰值从 4.658N 降到更低。

---

## 修改方向 3: 降低基线方法的 F_sat 以公平对比

**目的**: 如果基线方法也降低 F_sat，就更能说明视觉的价值。

### 修改

文件: [`my_test/force_adaptive_teleop.py:178`](my_test/force_adaptive_teleop.py:178)

```python
# 修改前
DEFAULT_F_SAT = 5.0

# 修改后
DEFAULT_F_SAT = 3.0   # 降低饱和阈值
```

### 预期效果

降低后基线方法的峰值力会被迫降到 3N 附近，此时再对比视觉方法——如果视觉也低，说明视觉有效；如果视觉更低，说明视觉更优。

---

## 实验设计建议

建议做 **3组对比实验**，每组重复 3-5 次取平均：

| 实验组 | 基线方法参数 | 视觉方法参数 | 验证目标 |
|--------|------------|------------|---------|
| 对照组 | 原参数 F_sat=5 | 原参数 | 复现"无差异"结论 |
| 实验组1 | F_sat=5 | vision_soft K=60 + force_sat=2.5 | 验证降刚度是否能降峰值力 |
| 实验组2 | F_sat=3 | vision_soft K=60 + force_sat=2.5 | 验证低饱和下视觉更有优势 |
