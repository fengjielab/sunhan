#!/usr/bin/env python3
"""
夹爪单独测试 V2：Omega.7 平移+夹持是两个独立设备，需分别 open
"""
import sys
import time
import ctypes
import numpy as np
import forcedimension_core.dhd as dhd
import panda_py

# ============================================================
robot_ip = "192.168.1.51"
GRIPPER_SPEED = 0.1
GRIPPER_FORCE = 20.0
GRIPPER_MAX = 0.08
GRIPPER_EPS_INNER = 0.005
GRIPPER_EPS_OUTER = 0.005
# ============================================================

print("=" * 60)
print("步骤 1: 枚举设备数量")
device_count = dhd.getDeviceCount()
print(f"   getDeviceCount() → {device_count}")

print("\n步骤 2: 打开主设备（平移）")
ret = dhd.open()
print(f"   dhd.open() → {ret}")

print("\n步骤 3: 检查是否有夹持设备")
has_grip = dhd.hasGripper()
has_active = dhd.hasActiveGripper()
print(f"   hasGripper() → {has_grip}")
print(f"   hasActiveGripper() → {has_active}")

print("\n步骤 4: 尝试打开第二个设备（夹持）")
grip_id = dhd.openID(1)
print(f"   dhd.openID(1) → {grip_id}")

print("\n步骤 5: 尝试启用夹持力（让夹持机构上电）")
ret_force = dhd.enableGripperForce(True)
print(f"   dhd.enableGripperForce(True) → {ret_force}")

print("\n步骤 6: 实时读取 Omega.7 夹爪角度")
print("  反复捏合/松开 Omega 夹爪，观察角度变化")
print("  Ctrl+C 退出\n")

try:
    while True:
        # 用默认 ID 读（主设备）
        angle_def = ctypes.c_double()
        ret_def = dhd.getGripperAngleDeg(angle_def)

        # 用夹持设备 ID 读
        angle_grip = ctypes.c_double()
        ret_grip = dhd.getGripperAngleDeg(angle_grip, grip_id)

        # 用 getDeviceAngleDeg 试试
        angle_dev = ctypes.c_double()
        ret_dev = dhd.getDeviceAngleDeg(angle_dev, grip_id)

        print(
            f"\r  [主设备] ret={ret_def:2d} angle={angle_def.value:7.3f}°  |  "
            f"[夹持ID] ret={ret_grip:2d} angle={angle_grip.value:7.3f}°  |  "
            f"[DeviceAngle] ret={ret_dev:2d} angle={angle_dev.value:7.3f}°  ",
            end="", flush=True,
        )
        time.sleep(0.05)
except KeyboardInterrupt:
    print("\n\n结束测试")
finally:
    dhd.close()
    print("✅ 已断开 Omega.7")
