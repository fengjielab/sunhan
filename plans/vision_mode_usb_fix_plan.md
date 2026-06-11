# Vision 模式 Omega.7 控制失效诊断报告

## 📋 问题描述

运行 `python3 my_test/interactive_teleop.py --mode vision` 时：
- Omega.7 位置读取正常（终端显示坐标有变化）
- Franka 机械臂完全不动或移动极小
- **default 模式（不带 vision）运行正常**

## 🔍 数据取证分析

### 轨迹数据对比

从 `my_test/data/` 中的 CSV 轨迹文件可以清楚看到问题：

| 指标 | default 模式 (standard) | vision 模式 |
|------|------------------------|-------------|
| 运行时长 | 22.5s (4507 采样点) | 11.2s (1770 采样点) |
| Omega.7 X 变化范围 | ~6mm (0.0118→0.0181) | **<0.3mm** (0.0179→0.0181) |
| Omega.7 Y 变化范围 | ~4mm (−0.009→−0.005) | **<0.1mm** (0.0001→0.0002) |
| Omega.7 Z 变化范围 | ~5mm (0.082→0.087) | **<0.6mm** (−0.0677→−0.0671) |
| 夹爪值变化 | −28.3° (稳定抓握) | −0.63°→−28.1° (未初始抓握) |

**结论：Vision 模式下 Omega.7 手柄位置数据几乎不变化**，远小于正常操作应有的运动幅度（正常应>10mm）。

### 最终参数对比

| 参数 | default 模式 | vision 模式 |
|------|-------------|-------------|
| K_trans | 50.0 N/m | 50.0 N/m |
| K_rot | 5.0 Nm/rad | 5.0 Nm/rad |
| damping_ratio | 0.8 | 0.8 |
| K_fb | 0.2 | 0.2 |
| scale | 3.0 | 3.0 |

Vision 模式下最终参数匹配 `soft_obj` 预设，说明 YOLO 逻辑正常工作并成功切换了参数。

## 🎯 根因定位

### 根本原因：RealSense D435i 与 Omega.7 USB 带宽争用

```
Omega.7 (USB isochronous) + RealSense D435i (USB isochronous)
                            ↓
        共享同一 USB 主机控制器 (xHCI)
                            ↓
    RealSense 30fps 640×480 消耗大量 USB 等时带宽
                            ↓
    Omega.7 的 USB 等时数据包被延迟/丢弃
                            ↓
    dhd.getPosition() 返回过时或不变的位置数据
                            ↓
    Franka 接收到几乎相同的 target_pos
                            ↓
    机械臂不动或移动极小
```

**关键代码位置**：[`_vision_loop()`](my_test/interactive_teleop.py:691)

```python
# 第 747 行 — RealSense 流配置
frames = pipeline.wait_for_frames(timeout_ms=5000)  # ← 5秒超时！

# 第 709 行 — 高带宽配置
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
#                                       ↑高分辨率   ↑高帧率
```

**为什么 default 模式没问题？**
- Default 模式**不启动 RealSense**，所有 USB 带宽归 Omega.7 独占
- Vision 模式启动后，RealSense 以 **30fps 640×480 BGR8** 持续流式传输

### 间接原因：wait_for_frames 超时过长

[`wait_for_frames(timeout_ms=5000)`](my_test/interactive_teleop.py:747) 的超时设置为 5 秒。当 USB 带宽不足时，RealSense SDK 会在这个调用内阻塞重试，进一步加剧 USB 总线上的冲突。

### 已有保护措施失效的原因

代码中已有 [`drd.start()`](my_test/interactive_teleop.py:482) 调用，旨在启用高优先级 USB 通道保护 Omega.7。然而：
1. DRD (Device Real-time Driver) 保护的是 Omega.7 的 **USB 等时传输优先级**
2. 但如果 USB 主机控制器的**总带宽被 RealSense 占满**，优先级保护也于事无补
3. 许多 Linux 主板只有一个 xHCI USB 3.0 控制器，所有 USB 端口共享带宽

## 🔧 修复方案（按优先级排序）

### 方案 A（推荐⭐）：降低 RealSense 带宽占用

| 修改项 | 当前值 | 建议值 | 改动位置 |
|--------|--------|--------|----------|
| 分辨率 | 640×480 | **424×240** | [line 709](my_test/interactive_teleop.py:709) |
| 帧率 | 30 fps | **15 fps** | [line 709](my_test/interactive_teleop.py:709) |
| 像素格式 | bgr8 | **bgr8**（不变） | [line 709](my_test/interactive_teleop.py:709) |
| wait_for_frames 超时 | 5000 ms | **200 ms** | [line 747](my_test/interactive_teleop.py:747) |

带宽计算对比：
- 当前：640 × 480 × 3 × 30 = **27.6 MB/s**
- 优化后：424 × 240 × 3 × 15 = **4.6 MB/s**（↓ **83%**）

### 方案 B：分离 USB 控制器（硬件建议）

将 Omega.7 和 RealSense 插入**不同物理 USB 端口**，确保它们使用不同的 USB 主机控制器：

```
建议拓扑：
  USB 3.0 端口 (xHCI)    ← Omega.7（主 USB 控制器）
  USB 2.0 端口 (EHCI)     ← RealSense D435i（独立控制器）
```

### 方案 C：增加自愈逻辑（代码增强）

在 [`run()`](my_test/interactive_teleop.py:1167) 主循环中添加 Omega.7 位置卡死检测：

```python
# 检测 Omega.7 位置是否长期不变（说明 USB 通信异常）
if np.linalg.norm(delta_pos) < 1e-6 and self._loop_count > 10:
    self._omega_stall_count += 1
    if self._omega_stall_count > CTRL_FREQ * 2:  # 超过 2 秒不动
        print("⚠️ Omega.7 数据可能冻结，尝试重建 USB 连接...")
```

## 📝 修改清单

| # | 文件 | 行号 | 修改内容 | 类型 |
|---|------|------|----------|------|
| 1 | `interactive_teleop.py` | [709](my_test/interactive_teleop.py:709) | `640,480` → `424,240`，`30`→`15` | 性能 |
| 2 | `interactive_teleop.py` | [747](my_test/interactive_teleop.py:747) | `timeout_ms=5000` → `timeout_ms=200` | 性能 |
| 3 | `interactive_teleop.py` | [691](my_test/interactive_teleop.py:691) | 添加 USB 带宽保护注释 | 文档 |

## ✅ 验证方法

1. 运行 `python3 my_test/interactive_teleop.py --mode vision`
2. 观察终端输出：Omega.7 位置应能实时变化
3. 检查 Franka 机械臂是否能跟随 Omega.7 运动
4. 运行 `watch -n 1 cat /sys/kernel/debug/usb/usbmon/0` 检查 USB 带宽使用情况
