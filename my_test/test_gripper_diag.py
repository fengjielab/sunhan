#!/usr/bin/env python3
"""
Omega.7 夹爪诊断脚本：用所有可能的 API 逐项排查
"""
import time
import ctypes
import forcedimension_core.dhd as dhd

print("=" * 60)
print("Omega.7 夹爪诊断工具")
print("=" * 60)

# 1. 枚举设备
print("\n[1] 枚举设备")
cnt = dhd.getDeviceCount()
print(f"   getDeviceCount() = {cnt}")

# 2. 用 open() 打开默认设备
print("\n[2] 打开默认设备")
ret = dhd.open()
print(f"   dhd.open() = {ret}")

# 3. 检查设备属性
print("\n[3] 设备属性")
print(f"   hasGripper()      = {dhd.hasGripper()}")
print(f"   hasActiveGripper()= {dhd.hasActiveGripper()}")

# 4. 尝试打开第二个设备（如果 getDeviceCount() >= 2）
grip_id = -1
if cnt >= 2:
    print(f"\n[4] 尝试打开第二个设备 (index=1)")
    grip_id = dhd.openID(1)
    print(f"   dhd.openID(1) = {grip_id}")
    if grip_id >= 0:
        print(f"   夹持设备 ID = {grip_id}")
        # 启用夹持力
        ret_f = dhd.enableGripperForce(True)
        print(f"   enableGripperForce(True) = {ret_f}")
else:
    print(f"\n[4] 设备数 < 2，跳过 openID(1)")

print("\n[5] 读取夹爪角度（捏合/松开夹爪看数值是否变化）")
print("   Ctrl+C 退出\n")

try:
    while True:
        # 方法1：默认设备，getGripperAngleDeg
        a1 = ctypes.c_double()
        r1 = dhd.getGripperAngleDeg(a1)

        # 方法2：如果 grip_id 有效，用指定设备 ID
        a2 = ctypes.c_double()
        r2 = -99
        if grip_id >= 0:
            r2 = dhd.getGripperAngleDeg(a2, grip_id)

        # 方法3：getGripperAngleRad
        a3 = ctypes.c_double()
        r3 = dhd.getGripperAngleRad(a3)

        # 方法4：getGripperGap
        a4 = ctypes.c_double()
        r4 = dhd.getGripperGap(a4)

        print(
            f"\r"
            f"[def]ret={r1:2d} angle={a1.value:+7.3f}°  |  "
            + (f"[id{grip_id}]ret={r2:2d} angle={a2.value:+7.3f}°  |  " if grip_id >= 0 else "")
            + f"[rad]ret={r3:2d} angle={a3.value:+7.3f}rad  |  "
            f"[gap]ret={r4:2d} gap={a4.value:+7.4f}m  ",
            end="", flush=True,
        )
        time.sleep(0.05)
except KeyboardInterrupt:
    print("\n\n结束诊断")
finally:
    dhd.close()
    print("✅ 已关闭设备")
