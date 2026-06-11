# 📖 adaptive_admittance.py 逐行代码解释（小白版）

> 这个文件实现的是一个"视觉驱动的自适应导纳/阻抗控制器"。
> 简单说：**机器人的爪子（末端）摸到不同东西时，会自动调整"软硬程度"**。
> 摸软的物体（如海绵）就变得柔软顺从，摸硬的物体（如金属）就变得坚硬。

---

## 一、文件头部注释（第 1-37 行）

```python
#!/usr/bin/env python3
```
- **"Shebang"** 行，告诉系统用 Python3 来运行这个脚本。Linux 环境下双击文件时有用。

```python
"""
adaptive_admittance.py — 视觉驱动的自适应导纳/阻抗控制
============================================================

核心功能:
    1. 根据 PhysicsProfile 运行时切换 CartesianImpedance 刚度矩阵
    2. 阻尼比保持 ζ = 1.0 (临界阻尼)，阻尼矩阵自动计算 D = 2·√(M·K)
    3. 通过 set_impedance() 安全切换（**平滑过渡，避免手感突变**）
...
"""
```
- **多行注释（docstring）**，描述了整个文件是干嘛的。
- **核心功能三句话**：
  1. 根据视觉检测到的物体（比如"苹果"还是"铁块"），切换机器人的软硬程度
  2. 阻尼比 ζ = 1.0 表示"临界阻尼"——既不会震荡也不会太慢，是最舒服的响应
  3. 切换不是"咔"一下跳变，而是平滑过渡，防止手感突变

```python
"""
原理:
    ┌──────────┐    K(c)     ┌──────────────────┐
    │ 视觉检测  │ ────────→  │ 刚度调度器        │
    │ YOLO+查表 │            │ 软→50N/m, 硬→300  │
    └──────────┘            └──────────────────┘
                             │ set_impedance()
                             ▼
                      ┌──────────────────┐
                      │ CartesianImpedance│
                      │   控制器          │
                      └──────────────────┘
"""
```
- 一个**ASCII 流程图**，展示整体流程：
  - 左边：视觉检测（YOLO 算法 + 查表）→ 识别物体类别
  - 中间：刚度调度器 → 软的给 50 N/m，硬的给 300 N/m
  - 右边：把刚度值设给机器人的"笛卡尔阻抗控制器"

```python
"""
参数映射:
    PhysicsProfile.admittance_K → 笛卡尔平移刚度 K_x, K_y (Z 轴按 label 打折)
    阻尼自动: D = 2 * sqrt(M * K), 其中 M 取固定质量假设

平滑过渡:
    刚度切换采用后台线程 + EMA 插值，约 200~300ms 完成过渡，
    避免瞬间跳变导致的操作手感突变。
"""
```
- **参数映射**：视觉系统传来的"导纳刚度值"会映射到机器人 X、Y、Z 方向的刚度，Z 轴会按物体类型打折
- **阻尼自动计算**：阻尼是根据质量 M 和刚度 K 算出来的，保证响应不震荡
- **平滑过渡**：在后台开个线程慢慢变，大约 0.2-0.3 秒完成，手感不会突然变化

---

## 二、导入模块（第 39-44 行）

```python
import threading
import time
from typing import Optional
```
- **导入标准库**：
  - `threading`：多线程，用来在后台执行平滑过渡
  - `time`：睡眠等待，控制每一步的时间间隔
  - `Optional`：告诉 Python 某个变量可以是 None（没有值）

```python
import numpy as np
from panda_py import controllers
```
- **导入第三方库**：
  - `numpy as np`：强大的数值计算库，处理矩阵运算
  - `panda_py.controllers`：Franka Panda 机器人的 Python 控制器接口

---

## 三、全局常量（第 46-48 行）

```python
DEFAULT_STIFFNESS = np.diag([200.0, 200.0, 200.0, 10.0, 10.0, 10.0])
```
- **默认刚度矩阵**：`np.diag()` 创建对角矩阵（只有对角线有值）。
- 6 个值对应机器人的 **6 个自由度**：
  - 前三个 200.0：X、Y、Z 方向的**平移刚度**（单位 N/m，牛顿/米）—— 中等硬度
  - 后三个 10.0：绕 X、Y、Z 轴的**旋转刚度**（单位 Nm/rad）—— 旋转比较软，方便调整姿态

```python
DEFAULT_DAMPING_RATIO = 1.0
```
- **默认阻尼比** = 1.0，即"临界阻尼"。
- 想象弹簧：阻尼比 <1 会来回晃，>1 回位很慢，=1 最快回位且不晃。

```python
NULLSPACE_STIFFNESS_DEFAULT = 0.5
```
- **零空间刚度默认值**：机器人有"多余"的自由度（比如 7 个关节做 6 个自由度的运动），这个控制那些"多余"的关节的硬度，默认 0.5 表示比较松。

---

## 四、类定义与类属性（第 51-71 行）

```python
class AdaptiveAdmittance:
```
- **定义一个类**：可以理解为一个"模板"，用来创建"自适应导纳控制器"对象。

```python
    """
    视觉驱动的自适应导纳控制器

    职责:
        - 维护当前阻抗矩阵
        - 根据 PhysicsProfile.admittance_K 计算新的阻抗矩阵
        - 通过 set_impedance() 安全切换

    注意:
        切换刚度时不要过于频繁（建议 > 0.5s 间隔），以免引起控制不连续。
    """
```
- 类的说明文档。

### 类属性（所有实例共享的变量）

```python
    K_TRANS_MIN = 50.0
    K_TRANS_MAX = 400.0
```
- **平移刚度**的取值范围：最小 50 N/m（很软），最大 400 N/m（很硬）。

```python
    K_ROT_FIXED = np.array([10.0, 10.0, 10.0])
```
- **旋转刚度固定为 10.0**：三个旋转方向（Rx, Ry, Rz）的刚度保持不变，不随物体改变。

```python
    M_EFF = 3.0  # 假设末端等效质量 (kg)
```
- **假设的末端等效质量** = 3 公斤。机器人末端（抓东西的部分）的"虚拟质量"。
- 计算阻尼时要用到这个值。

```python
    # 平滑过渡配置
    TRANSITION_DURATION = 0.25       # 总过渡时间 (s)
    TRANSITION_STEP_INTERVAL = 0.01  # 每步间隔 (s) → 约 25 步完成过渡
```
- **平滑过渡配置**：
  - 整个过渡持续 **0.25 秒**
  - 每隔 **0.01 秒** 更新一次 → 总共约 25 步完成

---

## 五、初始化方法 `__init__`（第 73-94 行）

```python
    def __init__(
        self,
        ctrl: controllers.CartesianImpedance,
        damping_ratio: float = DEFAULT_DAMPING_RATIO,
    ):
```
- **构造函数**：创建对象时自动调用。
- 参数：
  - `ctrl`：机器人的"笛卡尔阻抗控制器"对象，用来下发刚度命令
  - `damping_ratio`：阻尼比，默认 1.0

```python
        self.ctrl = ctrl
        self.damping_ratio = damping_ratio
```
- 把传入的参数存到对象自己身上。

```python
        self._K_current = DEFAULT_STIFFNESS.copy()
        self._D_current = self._compute_damping(self._K_current)
```
- `_K_current`：**当前刚度矩阵**，初始为默认刚度。`copy()` 复制一份，防止意外修改原值。
- `_D_current`：**当前阻尼矩阵**，用当前刚度计算出来。

```python
        self._K_target = DEFAULT_STIFFNESS.copy()
```
- `_K_target`：**目标刚度矩阵**（最终要达到的值），也初始为默认。

```python
        self._current_class = "unknown"
        self._current_label = "unknown"
```
- 记录当前识别的物体**类别**（如 apple/bottle）和**标签**（如 soft/hard），初始都为"unknown"。

```python
        self._switch_count = 0
        self._last_switch_class = ""
        self._min_switch_interval = 1.0
```
- `_switch_count`：刚度切换了多少次（计数器）
- `_last_switch_class`：上次切换的类别
- `_min_switch_interval`：最小切换间隔 1 秒，防止切得太频繁

```python
        # ── 平滑过渡线程控制 ──
        self._transition_thread: Optional[threading.Thread] = None
        self._transition_stop_event = threading.Event()
        self._transition_active = False
```
- **线程控制相关**：
  - `_transition_thread`：后台执行平滑过渡的线程，一开始是 None
  - `_transition_stop_event`：**停止事件**，用来通知后台线程"别干了，停下来"
  - `_transition_active`：标记当前是否正在过渡中

```python
        print(f"[AdaptiveAdmittance] 就绪 | 初始刚度={np.diag(self._K_current)} | 平滑过渡={self.TRANSITION_DURATION}s")
```
- 打印初始化信息：刚度对角线的值和过渡时长。

---

## 六、公共接口方法（第 96-129 行）

这些是**外部调用者**可以调用的方法。

### 6.1 `apply_admittance_K`（第 100-103 行）

```python
    def apply_admittance_K(self, admittance_K: float) -> None:
        """根据导纳刚度值直接设置阻抗矩阵"""
        K_new = self._build_stiffness_matrix(admittance_K)
        self._apply(K_new)
```
- **直接给一个刚度数值**，构建刚度矩阵并应用。
- 比如调用 `apply_admittance_K(200.0)` 就把刚度设为 200 N/m。

### 6.2 `apply_profile`（第 105-116 行）

```python
    def apply_profile(self, profile) -> None:
        """根据 PhysicsProfile 切换阻抗"""
        self._current_label = profile.label
        K_val = profile.admittance_K
```
- 接收一个 **PhysicsProfile 对象**（视觉检测的结果）。
- `profile.label`：物体的标签（soft/hard/medium）
- `profile.admittance_K`：推荐使用的刚度值

```python
        if profile.label == "soft":
            K_z = K_val * 0.5
        elif profile.label == "hard":
            K_z = K_val
        else:
            K_z = K_val * 0.8
```
- **Z 轴刚度打折**（因为 Z 轴是垂直方向，夹取时希望更柔顺一些）：
  - 软的物体：Z 轴刚度减半（*0.5）
  - 硬的物体：Z 轴保持原值
  - 其他情况：Z 轴打 8 折

```python
        K_new = self._build_stiffness_matrix(K_val, K_z=K_z)
        self._apply(K_new)
```
- 构建新的刚度矩阵并应用。

### 6.3 `apply_class`（第 118-124 行）

```python
    def apply_class(self, class_name: str, label: str = "unknown") -> None:
        """根据类别名称直接切换 (不依赖 PhysicsProfile)"""
        K_val = self._label_to_stiffness(label)
        K_new = self._build_stiffness_matrix(K_val)
        self._apply(K_new)
        self._current_class = class_name
        self._current_label = label
```
- 不依赖 PhysicsProfile 对象，直接给**类别名**和**标签**来切换。
- `_label_to_stiffness` 会把 label 转成具体的刚度值。

### 6.4 `set_custom_stiffness`（第 126-129 行）

```python
    def set_custom_stiffness(self, K_trans: float, K_rot: float = 10.0) -> None:
        """直接设置自定义刚度"""
        K_new = np.diag([K_trans, K_trans, K_trans, K_rot, K_rot, K_rot])
        self._apply(K_new)
```
- **终极手动模式**：直接指定平移刚度和旋转刚度。
- 比如 `set_custom_stiffness(100.0, 5.0)` → X/Y/Z 刚度 100，Rx/Ry/Rz 刚度 5。

---

## 七、内部方法（第 131-227 行）

这些方法以下划线 `_` 开头，意思是"**不要直接在外面调用**"，是内部使用的。

### 7.1 `_build_stiffness_matrix`（第 135-142 行）

```python
    def _build_stiffness_matrix(
        self, K_xy: float, K_z: float = None, K_rot: float = 10.0
    ) -> np.ndarray:
```
- **构建刚度矩阵**。
- 参数：
  - `K_xy`：X 和 Y 方向的平移刚度
  - `K_z`：Z 方向平移刚度（可选，不传就和 K_xy 一样）
  - `K_rot`：旋转刚度，默认 10.0

```python
        if K_z is None:
            K_z = K_xy
```
- 如果没给 Z 轴刚度，就用 X/Y 的值。

```python
        K_xy = np.clip(K_xy, self.K_TRANS_MIN, self.K_TRANS_MAX)
        K_z = np.clip(K_z, self.K_TRANS_MIN, self.K_TRANS_MAX)
```
- **夹紧（clip）**：确保值在 [50, 400] 范围内。不能太软（<50）也不能太硬（>400）。

```python
        return np.diag([K_xy, K_xy, K_z, K_rot, K_rot, K_rot])
```
- 返回 6×6 的对角矩阵，对角线为 [X刚度, Y刚度, Z刚度, Rx刚度, Ry刚度, Rz刚度]。

### 7.2 `_compute_damping`（第 144-148 行）

```python
    def _compute_damping(self, K: np.ndarray) -> np.ndarray:
        """临界阻尼: D = 2 * ζ * sqrt(M * K)"""
```
- **计算阻尼矩阵**，公式：D = 2 × 阻尼比 × √(质量 × 刚度)

```python
        M_assumed = np.diag([self.M_EFF] * 3 + [0.1] * 3)
```
- 构建"虚拟质量矩阵"：
  - 前三个自由度（平移）：质量 = 3.0 kg
  - 后三个自由度（旋转）：惯性 = 0.1

```python
        sqrt_MK = np.sqrt(np.maximum(np.diag(M_assumed) * np.diag(K), 0))
```
- `np.diag(M_assumed) * np.diag(K)`：质量 × 刚度（对应元素相乘）
- `np.maximum(..., 0)`：防止负数（安全保护）
- `np.sqrt(...)`：开平方根

```python
        return np.diag(2.0 * self.damping_ratio * sqrt_MK)
```
- 乘以 2 × 阻尼比，得到最终阻尼矩阵。

### 7.3 `_apply`（第 150-155 行）

```python
    def _apply(self, K_new: np.ndarray) -> None:
        """触发刚度平滑过渡（后台线程执行插值）"""
        if np.allclose(K_new, self._K_current) and not self._transition_active:
            return
```
- **应用新刚度**的入口。
- `np.allclose(A, B)`：检查 A 和 B 是否差不多相等（考虑浮点误差）。
- 如果新刚度≈当前刚度，且不在过渡中 → 什么都不做。

```python
        self._K_target = K_new.copy()
        self._start_smooth_transition()
```
- 更新目标刚度，启动平滑过渡。

### 7.4 `_start_smooth_transition`（第 157-166 行）

```python
    def _start_smooth_transition(self) -> None:
        """停止旧过渡并启动新的平滑过渡线程"""
        self._stop_transition()
```
- 先停止可能正在运行的旧过渡。

```python
        self._transition_stop_event.clear()
        self._transition_active = True
        self._transition_thread = threading.Thread(
            target=self._transition_worker,
            daemon=True,
        )
        self._transition_thread.start()
```
- `clear()`：重置停止标志（允许新线程运行）
- 设置 `_transition_active = True` 标记正在过渡
- 创建新线程，目标函数是 `_transition_worker`
- `daemon=True`：设为**守护线程**，主程序退出时自动结束
- 启动线程！

### 7.5 `_transition_worker`（第 168-213 行）

这是最核心的方法，在**后台线程**中执行。

```python
    def _transition_worker(self) -> None:
        """后台线程：从当前刚度线性插值到目标刚度"""
        K_start = self._K_current.copy()
        K_end = self._K_target.copy()
```
- 记录起始刚度和目标刚度（复制一份，防止中途被改）。

```python
        # 计算步数（至少 3 步，最多 50 步）
        steps = max(
            3,
            min(50, int(self.TRANSITION_DURATION / self.TRANSITION_STEP_INTERVAL))
        )
```
- 0.25 秒 ÷ 0.01 秒 = 25 步。但限制在 [3, 50] 之间。
- `int(...)` 取整（去掉小数部分）。

```python
        for i in range(1, steps + 1):
            if self._transition_stop_event.is_set():
                break
```
- 循环 `steps` 次（1 到 steps）。
- **检查停止标志**，如果外部要求停止就跳出循环。

```python
            # 平滑步进函数：smoothstep 3-5-1（起始缓、中间快、末尾缓）
            t = i / steps
            alpha = t * t * (3.0 - 2.0 * t)  # smoothstep
```
- `t = i / steps`：进度从 0 到 1。
- **smoothstep 函数**：`t²(3-2t)`。效果是：
  - 刚开始变化慢（起步柔和）
  - 中间变化快
  - 末尾又变慢（精确到达）
- 这比直接线性变化更平滑，手感更好。

```python
            K_interp = K_start + alpha * (K_end - K_start)
            self._K_current = K_interp.copy()
            self._D_current = self._compute_damping(K_interp)
```
- **插值公式**：当前值 = 起点 + 进度 × (终点 - 起点)
- 更新当前刚度和阻尼。

```python
            try:
                self.ctrl.set_impedance(K_interp)
            except Exception as e:
                print(f"[AdaptiveAdmittance] ⚠️ 过渡中 set_impedance 失败: {e}")
                break
```
- `try-except`：尝试设置阻抗，如果失败（比如网络断了）就打印错误并退出循环。
- **异常处理**，防止程序崩溃。

```python
            time.sleep(self.TRANSITION_STEP_INTERVAL)
```
- 休眠 0.01 秒，控制节奏。

```python
        # 确保最终到达目标（未被中断时）
        if not self._transition_stop_event.is_set():
            self._K_current = K_end.copy()
            self._D_current = self._compute_damping(K_end)
            try:
                self.ctrl.set_impedance(K_end)
            except Exception:
                pass
```
- 如果没被中断，确保最终刚度精确等于目标值（尽管已经接近了，但再确保一下）。

```python
            self._switch_count += 1
            print(
                f"[AdaptiveAdmittance] 平滑切换完成 → diag={np.round(np.diag(K_end), 1)} "
                f"({steps}步/{self.TRANSITION_DURATION*1000:.0f}ms)"
            )
```
- 切换计数加 1，打印完成信息：最终刚度对角线和耗时。

```python
        self._transition_active = False
```
- 标记过渡结束。

### 7.6 `_stop_transition`（第 215-219 行）

```python
    def _stop_transition(self) -> None:
        """安全停止当前过渡线程"""
        if self._transition_thread is not None and self._transition_thread.is_alive():
            self._transition_stop_event.set()
            self._transition_thread.join(timeout=0.15)
```
- 如果线程存在且存活：
  - `set()`：设置停止标志 → 线程下次循环时会退出
  - `join(timeout=0.15)`：等待线程结束，最多等 0.15 秒

### 7.7 `_label_to_stiffness`（第 221-227 行）

```python
    @staticmethod
    def _label_to_stiffness(label: str) -> float:
        mapping = {
            "soft": 50.0, "medium": 150.0,
            "hard": 300.0, "unknown": 100.0,
        }
        return mapping.get(label, 100.0)
```
- **静态方法**（不需要访问对象里的数据），就是个工具函数。
- 把文字标签转成刚度数值：
  - soft（软）→ 50 N/m
  - medium（中等）→ 150 N/m
  - hard（硬）→ 300 N/m
  - unknown（未知）→ 100 N/m
- `mapping.get(label, 100.0)`：如果标签不在字典里，默认返回 100。

---

## 八、查询属性（第 229-255 行）

```python
    @property
    def current_stiffness(self) -> np.ndarray:
        return self._K_current.copy()
```
- `@property`：**属性装饰器**，可以像访问变量一样调用：`adapter.current_stiffness`。
- 返回当前刚度（复制品，防止外部修改内部数据）。

```python
    @property
    def current_damping(self) -> np.ndarray:
        return self._D_current.copy()
```
- 返回当前阻尼矩阵。

```python
    @property
    def current_label(self) -> str:
        return self._current_label
```
- 返回当前物体的标签。

```python
    def get_info(self) -> dict:
        return {
            "class": self._current_class,
            "label": self._current_label,
            "K_diag": np.diag(self._K_current),
            "K_target_diag": np.diag(self._K_target),
            "D_diag": np.diag(self._D_current),
            "switches": self._switch_count,
            "damping_ratio": self.damping_ratio,
            "transition_active": self._transition_active,
        }
```
- **汇总信息**，返回一个字典包含当前所有状态：
  - 物体类别和标签
  - 当前刚度和目标刚度的对角线
  - 当前阻尼对角线
  - 切换次数
  - 阻尼比
  - 是否正在过渡

---

## 九、自测代码（第 258-280 行）

```python
if __name__ == "__main__":
```
- **Python 特殊机制**：只有直接运行这个文件时（`python adaptive_admittance.py`），里面的代码才会执行。
- 如果被别的文件导入（`import`），这段不执行。

```python
    print("=" * 50)
    print("AdaptiveAdmittance 自测")
    print("=" * 50)
```
- 打印分隔线和标题。

```python
    adapter = AdaptiveAdmittance(ctrl=None)  # type: ignore
```
- 创建一个测试用的控制器对象，**没有实际机器人**（ctrl=None）。
- `# type: ignore`：告诉类型检查器"我知道这里类型不匹配，别报错"。

```python
    test_cases = [
        ("apple", 50.0, "soft"), ("banana", 50.0, "soft"),
        ("bottle", 150.0, "medium"), ("book", 300.0, "hard"),
        ("cell phone", 300.0, "hard"), ("unknown", 100.0, "unknown"),
    ]
```
- **测试用例表**：6 种物体，每个有（类别名，刚度值，标签）。

```python
    print(f"\n{'类别':<12} {'label':<10} {'admittance_K':>10} → K_diag  [X, Y, Z, Rx, Ry, Rz]")
    print("-" * 70)
```
- 打印表格表头，`:12` 和 `:10` 控制列宽。

```python
    for name, K_val, label in test_cases:
        K = adapter._build_stiffness_matrix(K_val)
        D = adapter._compute_damping(K)
        diag_str = np.array2string(np.diag(K), precision=1, separator=", ")
        print(f"{name:<12} {label:<10} {K_val:>8.1f} N/m  → {diag_str}")
```
- 循环每个测试用例：
  - 构建刚度矩阵
  - 计算阻尼
  - 把对角线转成字符串显示
  - 打印一行结果

```python
    print("\n✅ 自适应导纳控制模块验证通过")
```
- 完成提示。

---

## 十、总结：这段代码到底干了啥？

想象你有一台 Franka Panda 机器人，前面有个摄像头（YOLO 算法）。

**流程是这样的：**

```
摄像头看到"苹果" → 查表知道苹果是"软的"(soft) → 刚度设为 50 N/m
摄像头看到"金属杯" → 查表知道是"硬的"(hard) → 刚度设为 300 N/m
```

**关键设计点：**

| 设计 | 说明 |
|------|------|
| 🎯 **自适应** | 根据视觉结果自动调刚度 |
| 🌀 **临界阻尼** | ζ=1.0，不震荡不迟缓 |
| 🔄 **平滑过渡** | 0.25 秒渐变，手感不突变 |
| 📐 **smoothstep** | 缓起缓停，中间快速 |
| 🧵 **后台线程** | 不阻塞主控制循环 |
| 🛡 **异常处理** | set_impedance 失败不崩溃 |
| 📊 **查询接口** | 随时查看当前状态 |

**总体评价**：这是一个设计得很专业的机器人控制器接口代码，考虑到了安全性（clip限制范围、异常处理）、用户体验（平滑过渡、critical damping）和可维护性（清晰的接口分离）。
