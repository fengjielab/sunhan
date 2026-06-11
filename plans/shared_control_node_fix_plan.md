# shared_control_node.py 错误修复计划

## 背景

`biaoding/vision_physics_mapper.py` 中的 `PhysicsProfile` 数据类经过了重构：
- `K_grip` → 重命名为 `K_fb`
- `F_target` → 已删除（不再使用）
- 新增了 `K_rot`, `D_trans`, `D_rot`, `M`, `gripper_speed`, `gripper_force_limit`, `description` 等字段

但 `shared_control_node.py` 中的构造调用未同步更新，导致运行时 **TypeError**。

---

## 错误清单及修复方案（共 4 处）

### 🐛 Bug 1: `__init__` — 默认 profile 构造 (line 359-363)

**问题：** 使用了已删除的 `K_grip` 和 `F_target` 参数

```python
# ❌ 旧代码
self._default_profile = PhysicsProfile(
    K_trans=0.4, K_grip=0.3, F_target=10.0,   # ← K_grip 已不存在, F_target 已删除
    deadband=0.3, admittance_K=100.0,
    approach_speed=0.03, label="unknown",
)
```

**修复：** `K_grip=0.3` → `K_fb=0.3`，删除 `F_target=10.0`

```python
# ✅ 新代码
self._default_profile = PhysicsProfile(
    K_trans=0.4, K_fb=0.3,
    deadband=0.3, admittance_K=100.0,
    approach_speed=0.03, label="unknown",
)
```

---

### 🐛 Bug 2: `run()` — 模式 B profile 构造 (line 694-698)

**问题：** 同上，使用了 `K_grip` 和 `F_target`

```python
# ❌ 旧代码
profile = PhysicsProfile(
    K_trans=0.6, K_grip=0.5, F_target=15.0,   # ← 同上
    deadband=0.4, admittance_K=150.0,
    approach_speed=0.03, label="medium",
)
```

**修复：** `K_grip=0.5` → `K_fb=0.5`，删除 `F_target=15.0`

```python
# ✅ 新代码
profile = PhysicsProfile(
    K_trans=0.6, K_fb=0.5,
    deadband=0.4, admittance_K=150.0,
    approach_speed=0.03, label="medium",
)
```

---

### 🐛 Bug 3: `main()` — force-label profile 构造 (line 1002-1011)

**问题：** 使用了 `K_grip` 和 `F_target`

```python
# ❌ 旧代码
fake = PhysicsProfile(
    admittance_K=params["admittance_K"],
    K_trans=params["K_trans"],
    deadband=params["deadband"],
    K_grip=30.0,              # ← 已不存在
    F_target=10.0,            # ← 已删除
    approach_speed=0.1,
    label=args.force_label,
    description=f"manual_{args.force_label}",
)
```

**修复：** `K_grip=30.0` → `K_fb=30.0`，删除 `F_target=10.0`

```python
# ✅ 新代码
fake = PhysicsProfile(
    admittance_K=params["admittance_K"],
    K_trans=params["K_trans"],
    deadband=params["deadband"],
    K_fb=30.0,
    approach_speed=0.1,
    label=args.force_label,
    description=f"manual_{args.force_label}",
)
```

---

### 🐛 Bug 4: `main()` — 属性名错误 (line 1016)

**问题：** 实例属性名为 `self.admittance`，但在 `main()` 中引用了 `node.admittance_ctrl`

```python
# ❌ 旧代码
if hasattr(node, 'admittance_ctrl') and node.admittance_ctrl:
    node.admittance_ctrl.apply_profile(fake)
```

**修复：** `admittance_ctrl` → `admittance`

```python
# ✅ 新代码
if hasattr(node, 'admittance') and node.admittance:
    node.admittance.apply_profile(fake)
```

---

## 影响范围

| 错误 | 触发条件 | 严重程度 |
|------|----------|----------|
| Bug 1 | 任何模式启动时 | ⚠️ **致命** — 初始化直接崩溃 |
| Bug 2 | 模式 B 运行时 | ⚠️ **致命** — run() 中构造 profile 崩溃 |
| Bug 3 | `--force-label` 参数使用时 | ⚠️ **致命** — main() 中构造 profile 崩溃 |
| Bug 4 | `--force-label` 参数使用时 | ⚠️ **致命** — main() 中引用不存在的属性 |

所有 4 个 bug 都会导致 **TypeError 崩溃**，必须全部修复。

---

## 修复步骤（Code 模式执行）

1. 修复 `__init__` 中 `_default_profile` 构造参数（Bug 1）
2. 修复 `run()` 中模式 B profile 构造参数（Bug 2）
3. 修复 `main()` 中 force-label profile 构造参数（Bug 3）
4. 修复 `main()` 中 `admittance_ctrl` → `admittance` 属性名（Bug 4）
