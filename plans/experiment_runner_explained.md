# 📖 experiment_runner.py 逐行代码解释（小白版）

> 这个文件实现的是一个 **"实验运行器"**，用来**自动执行一组机器人对比实验**。
> 简单说：让机器人用 **3 种不同的控制模式**，分别去**抓/碰 5 种不同的物体**，然后**记录数据、做对比分析**。

---

## 一、文件头部与文档注释（第 1-22 行）

```python
#!/usr/bin/env python3
```
- **Shebang 行**：告诉系统用 Python3 解释器运行这个脚本。

```python
from __future__ import annotations
```
- **未来特性导入**：让 Python 3.7+ 支持在类型注解中使用字符串形式的类名（如 `List[dict]`），避免运行时出错。

```python
"""实验运行器 — 自动化执行三模式 × 5物体对比实验

使用方法:
  python3 experiment_runner.py                    # 运行全部实验（需要3次硬件启动）
  python3 experiment_runner.py --mode a --obj book  # 单次指定实验
  python3 experiment_runner.py --dry-run            # 仅打印实验计划
```
- **多行注释（docstring）**，也是脚本的使用说明书。
- 三种运行方式：
  1. 不传参数：跑全部实验（18 轮，需要多次换物体）
  2. `--mode a --obj book`：只跑"A 模式"下摸"书"这一个实验
  3. `--dry-run`：不真的跑，只列出计划

```python
输出:
  data/experiment_YYYYMMDD_HHMMSS/
    ├── config.yaml              # 实验配置
    ├── summary.md               # 人工阅读总结
    ├── mode_a_book.csv          # 每周期数据
    ├── mode_a_book_metadata.yaml
    ├── mode_b_banana.csv
    ├── ...
    └── plots/                   # 可视化
        ├── force_comparison.png
        ├── grip_comparison.png
        └── trajectory.png
"""
```
- **输出目录结构**：每次实验会创建一个带时间戳的文件夹。
  - `config.yaml`：这次实验的配置记录
  - `summary.md`：数据分析总结（可直接阅读）
  - `mode_a_book.csv`：模式A+书 的原始数据
  - `plots/`：生成的对比图表

---

## 二、导入模块（第 24-31 行）

```python
import argparse
import csv
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
```
| 模块 | 作用 |
|------|------|
| `argparse` | 解析命令行参数（`--mode`, `--obj` 等） |
| `csv` | 读写 CSV 格式数据文件 |
| `os` | 操作系统接口（路径操作等） |
| `subprocess` | 启动和管理**子进程**（运行另一个 Python 脚本） |
| `sys` | Python 解释器相关（如 `sys.executable` 获取当前 Python 路径） |
| `time` | 时间相关（休眠、计时） |
| `datetime` | 获取当前日期时间 |
| `pathlib.Path` | 面向对象的文件路径操作（比 `os.path` 更现代） |

---

## 三、实验配置（第 34-61 行）

```python
# 三种模式
MODES = ["a", "b", "c"]
```
- 三种控制模式：
  - **A 模式**：零力模式（传统遥操作，不给力反馈）
  - **B 模式**：固定增益（力反馈强度固定）
  - **C 模式**：自适应（力反馈强度自动调节）

```python
# 5种物体（按 YOLO 检测顺序放置；N/A 为无物体基线）
OBJECTS = [
    ("无物体",    "N/A"),       # baseline（无物体放置）
    ("瓶子",      "bottle"),    # 中等硬度
    ("香蕉",      "banana"),    # 软质
    ("书",        "book"),      # 硬质
    ("杯子",      "cup"),       # 软质
    ("钟",        "clock"),     # 未知硬度
]
```
- **6 种实验条件**（实际上 5 种物体 + 1 个空载基线）。
- 每个元组是 `("显示用的中文名", "YOLO 检测用的英文名")`。
- 注释标明了每种物体的软硬属性。

```python
# 每轮采集周期数
CYCLES_PER_RUN = 500
```
- 每个实验采集 **500 个控制周期**的数据。每个周期大约几毫秒到几十毫秒。

```python
# 物体更换间隔（秒）
OBJECT_CHANGE_DELAY = 5.0
```
- 换下一个物体之前，等待 **5 秒**，给操作者换物体的时间。

```python
# 实验数据目录
DATA_DIR = Path("data")
```
- 所有实验数据都保存在项目根目录下的 `data/` 文件夹里。

```python
# 共享控制节点脚本路径
SHARED_CONTROL_SCRIPT = str(Path(__file__).resolve().parent / "shared_control_node.py")
```
- **关键路径**：找到跟本脚本**同目录**下的 `shared_control_node.py` 文件。
- `__file__`：当前脚本的完整路径
- `.resolve()`：解析成绝对路径
- `.parent`：取父目录
- 最终效果：这个脚本要启动另一个脚本 `shared_control_node.py` 来实际控制机器人。

---

## 四、辅助函数（第 64-74 行）

```python
def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
```
- **生成时间戳字符串**：比如 `20260607_125430`。
- `strftime` = "string format time"。

```python
def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
```
- **确保目录存在**：
  - `mkdir`：创建目录
  - `parents=True`：如果父目录也不存在，一起创建（类似 `mkdir -p`）
  - `exist_ok=True`：如果目录已存在，不要报错
- 返回路径本身，方便链式调用。

---

## 五、实验计划生成（第 77-108 行）

### `build_experiment_plan`（第 81-92 行）

```python
def build_experiment_plan(cycles_per_run: int = CYCLES_PER_RUN) -> List[dict]:
    """生成完整实验计划"""
    plan = []
    for mode in MODES:
        for obj_display, obj_yolo in OBJECTS:
            plan.append({
                "mode": mode,
                "obj_display": obj_display,
                "obj_yolo": obj_yolo,
                "cycles": cycles_per_run,
            })
    return plan
```
- **构建完整实验计划**：双重循环。
- 外层循环 3 种模式，内层循环 6 种条件 → 总共 **3 × 6 = 18 个实验**。
- 每个实验是一个字典，包含：模式、物体中文名、物体 YOLO 名、周期数。

### `print_plan`（第 95-108 行）

```python
def print_plan(plan: List[dict]):
    """打印实验计划"""
    print("=" * 60)
    print("实验计划")
    print("=" * 60)
    print(f"模式: {', '.join(MODES)}")
    print(f"物体: {', '.join(o[0] for o in OBJECTS)}")
    print(f"每轮周期: {CYCLES_PER_RUN}")
    print(f"总实验数: {len(plan)}")
    print("-" * 60)
    for i, exp in enumerate(plan, 1):
        print(f"  [{i:2d}] 模式{exp['mode']} — {exp['obj_display']:4s} (YOLO: {exp['obj_yolo']})"
              f"  {exp['cycles']} cycles")
    print("=" * 60)
```
- **打印实验计划表格**：
  - 显示模式列表、物体列表、周期数、总实验数
  - `enumerate(plan, 1)`：从 1 开始编号
  - `:2d`：数字占 2 位宽度右对齐
  - `:4s`：字符串占 4 位宽度
- 典型输出效果：
  ```
  ============================================================
  实验计划
  ============================================================
  模式: a, b, c
  物体: 无物体, 瓶子, 香蕉, 书, 杯子, 钟
  每轮周期: 500
  总实验数: 18
  ------------------------------------------------------------
    [ 1] 模式a — 无物体 (YOLO: N/A)  500 cycles
    [ 2] 模式a — 瓶子  (YOLO: bottle)  500 cycles
    ...
  ```

---

## 六、DataCollector 类（第 115-248 行）

这个类是**整个脚本的核心**，负责从另一个程序（`shared_control_node.py`）的输出中**提取数据**并**保存成 CSV 文件**。

### 6.1 初始化 `__init__`（第 118-135 行）

```python
class DataCollector:
    """从 shared_control_node 的 stdout 中提取结构化数据"""

    def __init__(self, output_dir: Path, mode: str, obj_name: str):
        self.output_dir = output_dir
        self.mode = mode
        self.obj_name = obj_name
        self.rows: List[dict] = []
        self.start_time = time.time()
```
- **构造函数**，创建数据收集器时需要：
  - `output_dir`：数据输出目录
  - `mode`：当前实验的模式（a/b/c）
  - `obj_name`：物体 YOLO 名字
- `self.rows`：用来保存所有解析到的数据行（列表里每个元素是一个字典）
- `self.start_time`：记录开始时间，用于计算相对时间戳

```python
        # CSV 文件
        csv_name = f"mode_{mode}_{obj_name}.csv"
        self.csv_path = output_dir / csv_name
        self.csv_file = open(self.csv_path, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow([
            "timestamp", "cycle", "object", "label",
            "F_ext_x", "F_ext_y", "F_ext_z",
            "F_fb_x", "F_fb_y", "F_fb_z",
            "grip",
        ])
```
- **创建 CSV 文件**，文件名如 `mode_a_book.csv`。
- `open(path, "w", newline="")`：以写入模式打开文件，`newline=""` 防止 CSV 出现多余空行。
- `csv.writer()`：创建一个 CSV 写入器。
- `writerow(...)`：写入**表头**（CSV 的第一行），包含：
  - `timestamp`：时间戳（秒，从实验开始算起）
  - `cycle`：控制周期编号
  - `object` / `label`：物体名称和软硬标签
  - `F_ext_x/y/z`：外部力（机器人受到的外力）
  - `F_fb_x/y/z`：反馈力（力反馈设备给操作者的力）
  - `grip`：夹爪开合度

### 6.2 `feed_line` 方法（第 137-194 行）

这是**最核心的数据解析方法**。

```python
    def feed_line(self, line: str):
        """解析 shared_control_node 的一行输出"""
        try:
            # 示例: [  123] 物体=book         label=hard     F_ext=(-1.23,+0.45,+2.34) F_fb=(-0.50,+0.10,+1.00) grip=0.15
            if "F_ext=" not in line or "F_fb=" not in line:
                return
```
- `feed_line`：每次从子进程读取一行，调用此方法。
- 注释给出了要解析的**示例行格式**。
- 快速检查：如果行里没有 `F_ext=` 和 `F_fb=`，直接跳过（不处理无关输出）。

```python
            # 解析 cycle
            parts = line.strip().split("]")
            if len(parts) < 2:
                return
            cycle_str = parts[0].strip("[ ")
            cycle = int(cycle_str)
```
- **解析周期编号**：用 `]` 分割行。
  - 行如 `[ 123] ...` → 分割成 `[" 123", " ..."]`
  - `strip("[ ")`：去掉 `[` 和空格 → `"123"`
  - `int(...)`：转成整数 123

```python
            # 解析物体
            obj_part = parts[1] if len(parts) > 1 else ""
            obj = "N/A"
            if "物体=" in obj_part:
                obj = obj_part.split("物体=")[1].split()[0].strip()
```
- **解析物体名字**：在 `"物体="` 后面找，取第一个空白字符前的单词。
  - 比如 `"... 物体=book  label=hard ..."` → 取到 `"book"`

```python
            # 解析 label
            label = "unknown"
            if "label=" in obj_part:
                label = obj_part.split("label=")[1].split()[0].strip()
```
- **解析软硬标签**：同理，在 `"label="` 后面找。

```python
            # 解析 F_ext
            fext = self._parse_vector(line, "F_ext=")
            # 解析 F_fb
            ffb = self._parse_vector(line, "F_fb=")
```
- **解析力向量**：调用内部方法 `_parse_vector` 来解析 `(x, y, z)` 格式的向量。

```python
            # 解析 grip
            grip = 0.0
            if "grip=" in line:
                grip_str = line.split("grip=")[-1].split()[0].strip()
                if grip_str != "N/A":
                    grip = float(grip_str)
```
- **解析夹爪开合度**：
  - 在 `"grip="` 后面找数值
  - 如果值是 `"N/A"`（无物体时），保持 0.0
  - 否则转成浮点数

```python
            row = {
                "timestamp": time.time() - self.start_time,
                "cycle": cycle,
                "object": obj,
                "label": label,
                "F_ext_x": fext[0], "F_ext_y": fext[1], "F_ext_z": fext[2],
                "F_fb_x": ffb[0], "F_fb_y": ffb[1], "F_fb_z": ffb[2],
                "grip": grip,
            }
            self.rows.append(row)
```
- **组装成字典**：把所有解析结果放在一个字典里。
- `timestamp`：当前时间 - 开始时间 = 相对时间（秒）。
- 存入 `self.rows` 列表。

```python
            self.csv_writer.writerow([
                f"{row['timestamp']:.3f}", row["cycle"], row["object"], row["label"],
                *[f"{v:.4f}" for v in [row["F_ext_x"], row["F_ext_y"], row["F_ext_z"],
                                        row["F_fb_x"], row["F_fb_y"], row["F_fb_z"]]],
                f"{row['grip']:.4f}",
            ])
```
- **写入 CSV 行**：把字典转成 CSV 的一行数据。
- `f"{value:.3f}"`：格式化浮点数保留 3 位小数。
- `*[...]`：星号是**解包操作符**，把列表展开成单独的参数。
- 这样 CSV 文件里每一行的列顺序和表头一致。

```python
        except Exception as e:
            # 日志记录但继续
            pass
```
- **异常捕获**：如果某一行解析失败，就**静默跳过**，不中断整个实验。
- 注释说"日志记录但继续"，但实际上只是 `pass`（啥也不做），设计者可能是打算加日志但还没加。

### 6.3 `_parse_vector` 方法（第 196-211 行）

```python
    def _parse_vector(self, line: str, prefix: str) -> tuple:
        """解析 (x, y, z) 格式向量"""
        try:
            if prefix not in line:
                return (0.0, 0.0, 0.0)
```
- 解析格式如 `F_ext=(-1.23, +0.45, +2.34)` 的向量。
- 如果前缀不存在，返回三个 0。
- 参数 `prefix` 可以是 `"F_ext="` 或 `"F_fb="`。

```python
            after = line.split(prefix)[1].strip()
            if after[0] != "(":
                return (0.0, 0.0, 0.0)
```
- 找到前缀后面的内容，去掉首尾空格。
- 检查第一个字符是不是 `(`，不是就返回零向量。

```python
            end = after.find(")")
            vec_str = after[1:end]
            parts = [float(p.strip()) for p in vec_str.split(",")]
            if len(parts) == 3:
                return tuple(parts)
            return (0.0, 0.0, 0.0)
```
- `find(")")`：找到右括号的位置。
- `after[1:end]`：截取括号里面的内容，比如 `"-1.23, +0.45, +2.34"`。
- `split(",")`：按逗号分割 → `["-1.23", " +0.45", " +2.34"]`
- `float(p.strip())`：去空格后转成浮点数。
- 列表推导式 `[... for p in ...]` 简洁地创建列表。
- 如果正好 3 个值，返回元组；否则返回零向量。

### 6.4 `close` 方法（第 213-214 行）

```python
    def close(self):
        self.csv_file.close()
```
- **关闭 CSV 文件**，确保数据写盘。

### 6.5 `summary` 方法（第 216-248 行）

```python
    def summary(self) -> dict:
        """计算本轮统计数据"""
        if not self.rows:
            return {"cycles": 0, "error": "no data"}
```
- 如果一条数据都没有，返回错误信息。

```python
        fext_x = [r["F_ext_x"] for r in self.rows]
        fext_y = [r["F_ext_y"] for r in self.rows]
        fext_z = [r["F_ext_z"] for r in self.rows]
        ffb_x = [r["F_fb_x"] for r in self.rows]
        ffb_y = [r["F_fb_y"] for r in self.rows]
        ffb_z = [r["F_fb_z"] for r in self.rows]
        grips = [r["grip"] for r in self.rows]
```
- **提取各列数据**：从所有行中分别提取每个维度的数据，组成 7 个列表。

```python
        def stats(vals):
            return {
                "mean": sum(vals) / len(vals),
                "std": (sum((v - sum(vals)/len(vals))**2 for v in vals) / len(vals))**0.5,
                "min": min(vals),
                "max": max(vals),
            }
```
- **内部函数 `stats`**：计算一组数据的统计量。
  - `mean`：平均值 = 总和 ÷ 数量
  - `std`：**标准差**，衡量数据波动大小的指标。
    - 公式：√( Σ(每个值 - 平均值)² ÷ 数量 )
    - 标准差越大，说明数据越"散"、波动越大
  - `min`：最小值
  - `max`：最大值

```python
        return {
            "mode": self.mode,
            "object": self.obj_name,
            "cycles": len(self.rows),
            "F_ext_x": stats(fext_x),
            "F_ext_y": stats(fext_y),
            "F_ext_z": stats(fext_z),
            "F_fb_x": stats(ffb_x),
            "F_fb_y": stats(ffb_y),
            "F_fb_z": stats(ffb_z),
            "grip": stats(grips),
        }
```
- 返回一个**嵌套字典**，每个力维度下面还有 `mean`/`std`/`min`/`max`。
- 比如：`{"mode": "a", "object": "book", "F_fb_x": {"mean": 1.23, "std": 0.45, ...}}`

---

## 七、单次实验执行（第 255-346 行）

### `run_single_experiment`（第 255-341 行）

这是**执行单个实验**的核心函数。

```python
def run_single_experiment(exp: dict, data_dir: Path) -> dict:
    """启动 shared_control_node 子进程，实时采集 stdout 数据

    工作流程:
      1. 启动 shared_control_node --mode X 作为子进程
      2. 逐行读取 stdout，喂给 DataCollector 解析
      3. 达到目标周期数后自动停止（或 Ctrl+C 中断）
      4. 保存 CSV 和元数据
    """
```
- 函数注释清晰说明了**工作流程**。

```python
    mode = exp["mode"]
    obj_yolo = exp["obj_yolo"]
    obj_display = exp["obj_display"]
    cycles = exp["cycles"]
```
- 从实验计划字典中提取参数。

```python
    print(f"\n{'=' * 60}")
    print(f"实验: 模式{modes_desc(mode)} | 物体: {obj_display} (YOLO: {obj_yolo})")
    print(f"周期: {cycles}")
    print(f"{'=' * 60}")
```
- 打印实验信息，`modes_desc()` 把 `"a"` 转成 `"A-零力(传统遥操作)"`。

```python
    # 准备输出目录
    ensure_dir(data_dir / f"mode_{mode}_{obj_yolo}")

    # 创建数据收集器
    collector = DataCollector(data_dir, mode, obj_yolo)
```
- 确保输出目录存在，创建数据收集器。

```python
    # 元数据
    metadata = {
        "mode": mode,
        "object_display": obj_display,
        "object_yolo": obj_yolo,
        "requested_cycles": cycles,
        "timestamp": timestamp(),
        "status": "running",
    }
```
- 创建一个字典记录**元数据**（关于数据的数据），初始状态为 `"running"`。

```python
    # 启动 shared_control_node 子进程（自动继承当前环境）
    cmd = [
        sys.executable, SHARED_CONTROL_SCRIPT,
        "--mode", mode,
    ]
```
- **构造命令**：用当前 Python 解释器执行 `shared_control_node.py`，传入 `--mode` 参数。
- `sys.executable`：当前 Python 的路径，确保使用同一个 Python 环境。

```python
    print(f"\n启动: {' '.join(cmd)}")
    print(f"将物体「{obj_display}」放在相机前")
    print(f"操作 Omega.7 进行遥操作，{cycles} 周期后自动停止")
    print(f"或按 Ctrl+C 提前中断\n")
```
- 打印操作提示：把物体放好，操作 Omega.7（力反馈设备），等待自动完成。

```python
    # 启动子进程并实时读取 stdout
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,          # 行缓冲
    )
```
- **启动子进程**：`subprocess.Popen` 在不阻塞主进程的情况下启动一个新进程。
  - `stdout=subprocess.PIPE`：捕获子进程的标准输出
  - `stderr=subprocess.STDOUT`：错误输出也合并到标准输出
  - `text=True`：以文本模式（而非二进制）读取
  - `bufsize=1`：**行缓冲**，每输出一行就刷新，实现实时读取

```python
    try:
        for line in iter(proc.stdout.readline, ""):
            print(line, end="")                    # 回显到终端
            collector.feed_line(line)              # 解析并写入 CSV

            # 达到目标周期数 → 自动停止
            if len(collector.rows) >= cycles:
                print(f"\n✅ 已采集 {cycles} 周期，停止...")
                break
```
- **实时读取循环**：
  - `iter(proc.stdout.readline, "")`：不断读取子进程的输出行，直到读到空字符串（进程结束）
  - `print(line, end="")`：回显到终端，让操作者看到实时输出
  - `collector.feed_line(line)`：交给 DataCollector 解析和保存
  - **自动停止条件**：采集到的行数 ≥ 目标周期数

```python
    except KeyboardInterrupt:
        print(f"\n⏹ 用户中断")
```
- **捕获 Ctrl+C**：用户按 Ctrl+C 可以手动中断实验。

```python
    finally:
        # 清理子进程
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        collector.close()
```
- **`finally` 块**：无论正常结束还是异常中断，**一定会执行**这里的清理工作。
  - `terminate()`：温柔地请求子进程结束
  - `wait(timeout=5)`：等最多 5 秒
  - 如果 5 秒还没结束 → `kill()`：强制杀掉
  - `collector.close()`：关闭 CSV 文件

```python
    # 计算统计
    stats = collector.summary()

    # 保存元数据
    import yaml
    meta_path = data_dir / f"mode_{mode}_{obj_yolo}_metadata.yaml"
    with open(meta_path, "w") as f:
        yaml.dump({**metadata, "status": "completed", "stats": stats}, f)
```
- `collector.summary()`：计算统计数据。
- `import yaml`：**延迟导入**（用到时才导入）YAML 库。
- 更新元数据状态为 `"completed"`，加上统计信息，保存为 YAML 文件。

```python
    print(f"\n✅ 完成: {meta_path}")
    print(f"   数据文件: {collector.csv_path}")

    return stats
```
- 打印完成信息，返回统计数据。

### `modes_desc`（第 344-346 行）

```python
def modes_desc(mode: str) -> str:
    desc = {"a": "A-零力(传统遥操作)", "b": "B-固定增益", "c": "C-自适应"}
    return desc.get(mode, mode)
```
- **模式编号转中文描述**的字典映射。
- `desc.get(mode, mode)`：如果字典里有就返回，没有就返回原值。

---

## 八、完整实验运行（第 353-404 行）

```python
def run_all_experiments():
    """按顺序运行所有实验"""

    plan = build_experiment_plan()
    print_plan(plan)
```
- 生成并打印全部 18 个实验的计划。

```python
    # 创建实验目录
    exp_ts = timestamp()
    data_dir = ensure_dir(DATA_DIR / f"experiment_{exp_ts}")

    # 保存实验计划
    import yaml
    plan_path = data_dir / "config.yaml"
    with open(plan_path, "w") as f:
        yaml.dump({
            "timestamp": exp_ts,
            "modes": MODES,
            "objects": [{"display": d, "yolo": y} for d, y in OBJECTS],
            "cycles_per_run": CYCLES_PER_RUN,
            "plan": [{
                "mode": e["mode"],
                "object_display": e["obj_display"],
                "object_yolo": e["obj_yolo"],
                "cycles": e["cycles"],
            } for e in plan],
        }, f)
```
- 创建带时间戳的实验目录（如 `data/experiment_20260607_125430/`）。
- 把实验配置保存为 `config.yaml`，包括时间戳、模式列表、物体列表、每个实验的细节。

```python
    all_results = []

    for i, exp in enumerate(plan, 1):
        print(f"\n{'#' * 60}")
        print(f"# 实验 [{i}/{len(plan)}]")
        print(f"{'#' * 60}")

        input(f"按 Enter 开始实验 [{i}/{len(plan)}]（或 Ctrl+C 停止）...")

        result = run_single_experiment(exp, data_dir)
        all_results.append(result)

        if i < len(plan):
            print(f"\n等待 {OBJECT_CHANGE_DELAY}s 更换物体...")
            time.sleep(OBJECT_CHANGE_DELAY)
```
- **主循环**：逐个执行 18 个实验。
  - `input(...)`：**等待用户按 Enter**，给操作者时间准备（摆好物体、握好手柄）
  - 执行单个实验
  - 收集结果
  - 如果不是最后一个实验，等待 5 秒换物体

```python
    # 生成总结
    summary_path = generate_summary(all_results, data_dir)

    print(f"\n{'=' * 60}")
    print(f"所有实验完成！")
    print(f"数据目录: {data_dir}")
    print(f"总结: {summary_path}")
    print(f"{'=' * 60}")
```
- 生成总结报告，打印完成信息。

---

## 九、总结生成（第 410-456 行）

```python
def generate_summary(results: List[dict], output_dir: Path) -> Path:
    """生成 Markdown 总结"""
    path = output_dir / "summary.md"

    with open(path, "w") as f:
        f.write("# 实验总结\n\n")
        f.write(f"生成时间: {timestamp()}\n\n")
        f.write("## 对比表\n\n")
        f.write("| 模式 | 物体 | 周期 | F_fb_x均值 | F_fb_y均值 | F_fb_z均值 | grip均值 |\n")
        f.write("|------|------|------|-----------|-----------|-----------|---------|\n")
```
- **生成 Markdown 文件**（`.md` 格式），可以直接在 GitHub 或 VSCode 中预览。
- 写入表格表头，包含模式、物体、周期、各方向反馈力均值、夹爪开合度均值。

```python
        for r in results:
            mode = modes_desc(r.get("mode", "?"))
            obj = r.get("object", "?")
            cycles = r.get("cycles", 0)
            ffx = f"{r.get('F_fb_x', {}).get('mean', 0):.3f}"
            ffy = f"{r.get('F_fb_y', {}).get('mean', 0):.3f}"
            ffz = f"{r.get('F_fb_z', {}).get('mean', 0):.3f}"
            grip = f"{r.get('grip', {}).get('mean', 0):.3f}"
            f.write(f"| {mode} | {obj} | {cycles} | {ffx} | {ffy} | {ffz} | {grip} |\n")
```
- **循环每个结果**，提取需要的统计值。
- `r.get("F_fb_x", {}).get("mean", 0)`：两层 `.get()` 安全取值。
  - 第一层：从结果字典取 `F_fb_x`，如果没有返回空字典 `{}`
  - 第二层：从 `F_fb_x` 字典里取 `mean`，如果没有返回 0

```python
        f.write("\n## 关键对比指标\n\n")

        # 计算三种模式的 F_fb 总体均值和 grip 均值
        for m in ["a", "b", "c"]:
            mode_results = [r for r in results if r.get("mode") == m]
            if not mode_results:
                continue
```
- **按模式分组**：对 a/b/c 三种模式分别汇总。

```python
            total_fb_x = sum(
                abs(r.get("F_fb_x", {}).get("mean", 0)) for r in mode_results
            )
            total_fb_y = sum(
                abs(r.get("F_fb_y", {}).get("mean", 0)) for r in mode_results
            )
            total_fb_z = sum(
                abs(r.get("F_fb_z", {}).get("mean", 0)) for r in mode_results
            )
```
- 对当前模式的所有结果，将每个物体的**反馈力均值**取**绝对值**后求和。
- `abs(...)`：取绝对值。因为力有方向（正负），取绝对值后才代表"力的大小"。
- 这个合计值可以用来比较不同模式的**总反馈强度**。

```python
            avg_grip = sum(
                abs(r.get("grip", {}).get("mean", 0)) for r in mode_results
            ) / len(mode_results)
```
- **平均夹爪开合度**：所有物体夹爪开合度的均值。

```python
            f.write(f"- **模式{modes_desc(m).split('-')[0]}**: "
                    f"Σ|F_fb| = ({total_fb_x:.3f}, {total_fb_y:.3f}, {total_fb_z:.3f}) N, "
                    f"avg grip = {avg_grip:.3f}\n")

    return path
```
- 写入一行汇总对比数据。
- `modes_desc(m).split("-")[0]`：比如 `"A-零力(传统遥操作)"` 只取 `"A"` 这部分。
- `Σ|F_fb|`：西格玛（求和符号）表示"绝对值的总和"。

---

## 十、主入口 `main` 函数（第 463-497 行）

```python
def main():
    parser = argparse.ArgumentParser(description="三模式 × 5物体 共享控制实验运行器")
    parser.add_argument("--mode", choices=MODES, help="仅运行指定模式")
    parser.add_argument("--obj", help="仅运行指定物体 (YOLO class name)")
    parser.add_argument("--dry-run", action="store_true", help="仅打印实验计划，不执行")
    parser.add_argument("--cycles", type=int, default=CYCLES_PER_RUN, help="每轮周期数")

    args = parser.parse_args()
```
- **命令行参数解析**：
  - `--mode`：可选 `a/b/c`，只跑指定模式
  - `--obj`：物体 YOLO 名称，如 `book`
  - `--dry-run`：只打印计划不执行
  - `--cycles`：每轮周期数，默认 500

```python
    cycles = args.cycles if args.cycles else CYCLES_PER_RUN

    if args.dry_run:
        plan = build_experiment_plan(cycles_per_run=cycles)
        print_plan(plan)
        return
```
- **Dry-run 模式**：只打印计划，不执行任何实验。

```python
    if args.mode or args.obj:
        # 单次指定实验
        plan = build_experiment_plan(cycles_per_run=cycles)
        filtered = [e for e in plan
                    if (not args.mode or e["mode"] == args.mode)
                    and (not args.obj or e["obj_yolo"] == args.obj)]
        if not filtered:
            print(f"未找到匹配的实验: mode={args.mode}, obj={args.obj}")
            sys.exit(1)

        exp_ts = timestamp()
        data_dir = ensure_dir(DATA_DIR / f"experiment_{exp_ts}")
        result = run_single_experiment(filtered[0], data_dir)
```
- **单次实验模式**：
  - 生成完整计划
  - 用列表推导式过滤出匹配的实验
  - `(not args.mode or e["mode"] == args.mode)`：如果没指定 `--mode`，不过滤；如果指定了，只匹配
  - 如果没找到匹配的，报错退出
  - 创建数据目录，跑第一个匹配的实验

```python
    else:
        run_all_experiments()
```
- **默认模式**：跑全部 18 个实验。

```python
if __name__ == "__main__":
    main()
```
- **Python 标准入口惯用法**：
  - 只有直接运行此脚本时（`python experiment_runner.py`），`main()` 才执行
  - 如果被别的脚本 `import`，不会自动执行

---

## 十一、总结：这段代码到底干了啥？

**一句话**：自动化跑一组机器人控制实验，把数据存下来方便分析。

### 整体流程

```
用户运行脚本
    │
    ├── 生成实验计划（3模式 × 6条件 = 18个实验）
    │
    ├── 创建输出目录 data/experiment_时间戳/
    │
    ├── 循环每个实验：
    │   ├── 提示用户摆放物体 → 按 Enter
    │   ├── 启动 shared_control_node.py 子进程
    │   ├── 实时读取输出 → 解析数据 → 写入 CSV
    │   ├── 采集够 500 周期自动停止
    │   ├── 保存元数据 (YAML)
    │   └── 等待 5 秒换下一个物体
    │
    └── 生成 summary.md 总结报告
```

### 关键设计点

| 设计 | 说明 |
|------|------|
| 🎯 **自动化** | 一个脚本跑完全部 18 个实验，不用手动启停 |
| 📡 **实时解析** | 通过 `subprocess.PIPE` 实时读取子进程输出 |
| 📁 **结构化输出** | CSV 存原始数据，YAML 存元数据，MD 存总结 |
| 🛡 **异常安全** | `try/finally` 确保子进程和文件被正确清理 |
| ⌨️ **人机交互** | `input()` 等待用户准备好再开始 |
| 📊 **统计分析** | 自动计算均值、标准差、最大最小值 |
| 🔍 **灵活运行** | 支持全部运行、单次指定、干跑预览三种模式 |
| 🧩 **模块化设计** | 计划生成、数据采集、统计计算、总结生成各司其职 |
