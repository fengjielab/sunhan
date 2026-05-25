#!/usr/bin/env python3
"""
Step 4a — 零力透明模式
========================
目的: 验证 Omega.7 力输出功能正常，在零力模式下手柄自由顺滑。

操作:
    1. 连接 Omega.7
    2. 启动 DRD 高频伺服
    3. 开启力输出（dhd.enableForce(True)）
    4. 输出零力 10 秒，让操作员感受"透明模式"
    5. 然后输出小阻尼力模拟"坏了"的感觉，对比差异

用法:
    python3 plans/step_4a_force_zero.py

预期:
    前 10 秒: 手柄非常轻，几乎无阻尼
    后 5 秒: 手柄有明显阻尼，对比明显

注意:
    确保 Omega.7 USB 已连接，dhd 驱动已加载。

作者: mfj
日期: 2026-05
"""

import sys
import time
import ctypes
import numpy as np
import forcedimension_core.dhd as dhd
import forcedimension_core.drd as drd


def wait_for_user(prompt: str):
    """打印提示并等待用户按 Enter"""
    print(f"  {prompt}")
    input("  按 Enter 继续...")


def main():
    print("=" * 60)
    print("  Step 4a: 零力透明模式测试")
    print("=" * 60)

    # ── 连接 Omega.7 ──
    print("\n[1/2] 连接 Omega.7 ...")
    if dhd.open() < 0:
        print("   ❌ Omega.7 连接失败。检查 USB 线和驱动。")
        print("   提示: 用 lsusb 检查是否识别到设备")
        sys.exit(1)
    sysname = dhd.getSystemName()
    if isinstance(sysname, bytes):
        sysname = sysname.decode('utf-8', errors='replace')
    print(f"   ✓ 已连接: {sysname}")

    # 启动 DRD
    if drd.start() < 0:
        print("   ⚠️  DRD 启动失败，部分功能可能不可用")
    else:
        print("   ✓ DRD 高频伺服已启动")

    dhd.enableForce(True)
    print("   ✓ 力输出已使能\n")

    # ── 阶段 1: 零力透明模式 ──
    print("=" * 60)
    print("  阶段 1: 零力透明模式 (10 秒)")
    print("=" * 60)
    print("  手柄应非常轻、顺滑，几乎感觉不到任何阻力")
    print("  请握着但不要用力，感受最小阻尼状态\n")

    wait_for_user("准备好后开始零力测试")

    start = time.time()
    zero_force = (ctypes.c_double * 3)(0.0, 0.0, 0.0)
    while time.time() - start < 10.0:
        elapsed = time.time() - start
        dhd.setForce(zero_force)
        time.sleep(0.01)  # 100Hz 更新
        if int(elapsed) != int(time.time() - start):
            print(f"  零力模式: {int(elapsed)}/10s ... 手柄应很轻")

    print("\n   ✅ 零力透明模式测试完成")
    print("   [ ] 确认: 手柄非常轻、顺滑，几乎无阻力")

    # ── 阶段 2: 对比测试（故意加阻尼） ──
    print("\n" + "=" * 60)
    print("  阶段 2: 对比测试 — 加阻尼力 (5 秒)")
    print("=" * 60)
    print("  接下来会施加一个小阻尼力，手感应明显变重")
    print("  这是为了让你对比感受 '有力反馈' 和 '无' 的区别\n")

    wait_for_user("准备好后开始阻尼测试")

    # 读取当前位置，施加与位移成正比的虚拟弹簧力
    pos = (ctypes.c_double * 3)(0.0, 0.0, 0.0)
    start = time.time()
    while time.time() - start < 5.0:
        dhd.getPosition(pos)
        # 虚拟弹簧: F = -K * pos (把手柄拉回零点)
        K_virtual = 50.0  # 50 N/m 虚拟弹簧
        damp_force = (ctypes.c_double * 3)(
            -K_virtual * pos[0],
            -K_virtual * pos[1],
            -K_virtual * pos[2],
        )
        dhd.setForce(damp_force)
        time.sleep(0.01)

        elapsed = time.time() - start
        if int(elapsed) != int(time.time() - start):
            f_mag = np.sqrt(damp_force[0]**2 + damp_force[1]**2 + damp_force[2]**2)
            print(f"  阻尼模式: {int(elapsed)}/5s ... 手柄回拉力={f_mag:.1f}N")

    # ── 恢复零力 ──
    dhd.setForce(zero_force)

    print("\n   ✅ 阻尼力测试完成")
    print("   [ ] 确认: 阻尼模式下手柄有明显回拉感，与零力模式区别明显")

    # ── 总结 ──
    print("\n" + "=" * 60)
    print("  测试总结")
    print("=" * 60)
    print("  验证清单:")
    print("  [ ] Omega.7 连接正常，drd.start() 成功")
    print("  [ ] dhd.enableForce(True) 正常生效")
    print("  [ ] 零力模式: 手柄轻、顺滑、无阻力")
    print("  [ ] 阻尼模式: 手柄有回拉感，与零力模式明显不同")
    print("  [ ] 切回零力后手柄恢复顺滑")

    dhd.setForce(zero_force)
    dhd.close()
    print("\nOmega.7 已断开。\n")


if __name__ == "__main__":
    main()
