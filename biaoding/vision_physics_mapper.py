#!/usr/bin/env python3
"""
VisionPhysicsMapper —— 视觉语义 → 物理属性查表映射
========================================================

综合版本：融合简洁 API 与完整物理参数

功能:
    1. 封装 YOLO 推理 + 查表映射为单步调用 detect_and_map()
    2. 每个 class_name 映射到完整的力控/阻抗/导纳参数
    3. 支持 JSON 文件持久化自定义表
    4. 与现有 ROS 节点（yolo_object_detector_node + grasp_controller_node）无缝集成

参数说明:
    K_trans        : 笛卡尔平移刚度比例/系数 (可理解为阻抗控制中的 K 增益)
    K_grip         : 夹爪刚度系数 (0~1 比例，或 N/m)
    F_target       : 目标夹持力 (N)
    deadband       : 力控死带 (m)
    admittance_K   : 导纳控制刚度 (N/m)
    approach_speed : 接近速度 (m/s)
    label          : 语义标签 soft / hard / medium / unknown

用法:
    # 方式1: 纯视觉映射（自带 YOLO）
    mapper = VisionPhysicsMapper(model_path="yolo11n.pt")
    det = mapper.detect_and_map(rgb_image)
    profile = mapper.get_current_profile()

    # 方式2: 仅查表（ROS 节点里 YOLO 已跑完）
    mapper = VisionPhysicsMapper()  # 不加载模型
    profile = mapper.lookup("bottle")
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List, Any
import numpy as np


@dataclass
class PhysicsProfile:
    """物体物理-控制参数配置"""
    K_trans: float         # 平移刚度比例 (N/m 或 0~1 增益)
    K_grip: float          # 夹爪刚度系数
    F_target: float        # 目标夹持力 N
    deadband: float        # 力控死带 m
    admittance_K: float    # 导纳刚度 N/m
    approach_speed: float  # 接近速度 m/s
    label: str = "unknown" # 语义标签: soft/hard/medium/unknown
    description: str = ""  # 人类可读描述

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PhysicsProfile":
        return cls(
            K_trans=d["K_trans"],
            K_grip=d["K_grip"],
            F_target=d["F_target"],
            deadband=d["deadband"],
            admittance_K=d["admittance_K"],
            approach_speed=d["approach_speed"],
            label=d.get("label", "unknown"),
            description=d.get("description", ""),
        )

    def to_grasp_strategy(self) -> dict:
        """
        转换为 grasp_controller_node 所需的策略字典格式
        兼容 GraspControllerNode.select_grasp_strategy() 的返回结构
        """
        # 将标量 K_trans 展开为 [K, K, Kz] 列表（Z 方向略软）
        K_val = self.K_trans * 1000  # 比例 → 绝对刚度 (示例)
        Kz = K_val * 0.5 if self.label == "soft" else K_val
        return {
            "stiffness": [K_val, K_val, Kz, 10, 10, 10],
            "force": self.F_target,
            "approach_speed": self.approach_speed,
            "admittance_K": self.admittance_K,
            "deadband": self.deadband,
            "K_grip": self.K_grip,
            "label": self.label,
            "description": self.description,
        }


class VisionPhysicsMapper:
    """
    视觉语义 → 物理属性 查表器

    两种使用模式:
        A) 端到端: 加载 YOLO 模型，调用 detect_and_map(image)
        B) 纯查表: 不加载模型，调用 lookup(class_name)
    """

    # ── 内建默认查表（基于经验值，可 JSON 覆盖）──
    DEFAULT_TABLE: Dict[str, dict] = {
        # ===== soft =====
        "apple": {
            "K_trans": 0.3, "K_grip": 0.2, "F_target": 8.0,
            "deadband": 0.3, "admittance_K": 50.0,
            "approach_speed": 0.02, "label": "soft",
            "description": "软物体-苹果: 低刚度、小力",
        },
        "banana": {
            "K_trans": 0.3, "K_grip": 0.2, "F_target": 6.0,
            "deadband": 0.3, "admittance_K": 50.0,
            "approach_speed": 0.015, "label": "soft",
            "description": "软物体-香蕉: 极低刚度、极小力、超慢速",
        },
        "orange": {
            "K_trans": 0.35, "K_grip": 0.25, "F_target": 7.0,
            "deadband": 0.25, "admittance_K": 60.0,
            "approach_speed": 0.02, "label": "soft",
            "description": "软物体-橙子: 低刚度",
        },
        "teddy bear": {
            "K_trans": 0.2, "K_grip": 0.1, "F_target": 3.0,
            "deadband": 0.5, "admittance_K": 30.0,
            "approach_speed": 0.01, "label": "soft",
            "description": "软物体-毛绒玩具: 极柔策略",
        },
        # ===== medium =====
        "bottle": {
            "K_trans": 0.5, "K_grip": 0.4, "F_target": 15.0,
            "deadband": 0.4, "admittance_K": 150.0,
            "approach_speed": 0.03, "label": "medium",
            "description": "中硬-瓶子: 中等刚度",
        },
        "cup": {
            "K_trans": 0.5, "K_grip": 0.4, "F_target": 12.0,
            "deadband": 0.4, "admittance_K": 150.0,
            "approach_speed": 0.025, "label": "medium",
            "description": "中硬-杯子: 中等刚度、略低力",
        },
        "bowl": {
            "K_trans": 0.45, "K_grip": 0.35, "F_target": 10.0,
            "deadband": 0.35, "admittance_K": 120.0,
            "approach_speed": 0.025, "label": "medium",
            "description": "中硬-碗: 中等刚度",
        },
        # ===== hard =====
        "book": {
            "K_trans": 1.0, "K_grip": 0.8, "F_target": 25.0,
            "deadband": 0.5, "admittance_K": 300.0,
            "approach_speed": 0.05, "label": "hard",
            "description": "硬物体-书本: 正常刚度、正常力",
        },
        "cell phone": {
            "K_trans": 1.0, "K_grip": 0.8, "F_target": 20.0,
            "deadband": 0.5, "admittance_K": 300.0,
            "approach_speed": 0.04, "label": "hard",
            "description": "硬物体-手机: 中高刚度、谨慎夹持",
        },
        "keyboard": {
            "K_trans": 1.0, "K_grip": 0.8, "F_target": 22.0,
            "deadband": 0.5, "admittance_K": 300.0,
            "approach_speed": 0.05, "label": "hard",
            "description": "硬物体-键盘: 正常刚度",
        },
        "mouse": {
            "K_trans": 0.9, "K_grip": 0.7, "F_target": 18.0,
            "deadband": 0.45, "admittance_K": 250.0,
            "approach_speed": 0.04, "label": "hard",
            "description": "硬物体-鼠标: 中等刚度",
        },
        "scissors": {
            "K_trans": 1.2, "K_grip": 1.0, "F_target": 30.0,
            "deadband": 0.6, "admittance_K": 400.0,
            "approach_speed": 0.06, "label": "hard",
            "description": "硬物体-剪刀: 高刚度、大力",
        },
        # ===== unknown / default =====
        "__default__": {
            "K_trans": 0.4, "K_grip": 0.3, "F_target": 10.0,
            "deadband": 0.3, "admittance_K": 100.0,
            "approach_speed": 0.03, "label": "unknown",
            "description": "默认策略: 中等保守参数",
        },
    }

    def __init__(
        self,
        model_path: Optional[str] = None,
        json_path: Optional[str] = None,
        conf_threshold: float = 0.5,
    ):
        """
        初始化

        Args:
            model_path: YOLO 模型路径，如 "yolo11n.pt"。None 则不加载模型（纯查表模式）
            json_path:  自定义查表 JSON 文件路径，None 则只用内建表
            conf_threshold: YOLO 置信度阈值
        """
        self.conf_threshold = conf_threshold
        self._table: Dict[str, PhysicsProfile] = {}
        self.current_profile: PhysicsProfile = None
        self._model = None

        # ── 加载内建表 ──
        for cls_name, params_dict in self.DEFAULT_TABLE.items():
            self._table[cls_name] = PhysicsProfile.from_dict(params_dict)

        # ── 加载用户自定义表（覆盖内建）──
        if json_path is not None and os.path.exists(json_path):
            self.load_json(json_path)

        # ── 加载 YOLO 模型（端到端模式）──
        if model_path is not None:
            from ultralytics import YOLO
            self._model = YOLO(model_path)
            print(f"[VisionPhysicsMapper] YOLO 模型加载完成: {model_path}")

        # 初始化为默认值
        self.current_profile = self.get_default()
        print(f"[VisionPhysicsMapper] 查表器就绪，共 {len(self._table)-1} 条映射")

    # ═══════════════════════════════════════
    # 模式 A: 端到端（YOLO + 查表）
    # ═══════════════════════════════════════
    def detect_and_map(self, rgb_image: np.ndarray) -> Optional[dict]:
        """
        单步完成：YOLO 检测 → 取最佳目标 → 查表 → 更新 current_profile

        Args:
            rgb_image: BGR 格式图像 (OpenCV 默认)

        Returns:
            dict: {class, bbox, profile, conf} 或 None（无有效检测）
        """
        if self._model is None:
            raise RuntimeError("未加载 YOLO 模型，请构造时传入 model_path，或改用 lookup()")

        results = self._model(rgb_image, verbose=False)[0]

        best_det = None
        for box in results.boxes:
            conf = float(box.conf[0])
            if conf < self.conf_threshold:
                continue
            cls_name = results.names[int(box.cls[0])]

            # 优先匹配查表中的类别
            if cls_name in self._table and not cls_name.startswith("__"):
                best_det = {
                    "class": cls_name,
                    "bbox": box.xyxy[0].cpu().numpy(),
                    "profile": self._table[cls_name],
                    "conf": conf,
                }
                break  # 取第一个高置信度已知物体

        if best_det is None and len(results.boxes) > 0:
            # 没有匹配到已知类别，取置信度最高的，用默认参数
            best_box = max(results.boxes, key=lambda b: float(b.conf[0]))
            conf = float(best_box.conf[0])
            if conf >= self.conf_threshold:
                cls_name = results.names[int(best_box.cls[0])]
                best_det = {
                    "class": cls_name,
                    "bbox": best_box.xyxy[0].cpu().numpy(),
                    "profile": self._table["__default__"],
                    "conf": conf,
                }

        if best_det:
            self.current_profile = best_det["profile"]
            return best_det
        return None

    # ═══════════════════════════════════════
    # 模式 B: 纯查表（YOLO 外部已跑完）
    # ═══════════════════════════════════════
    def lookup(self, class_name: str) -> PhysicsProfile:
        """
        仅查表，不跑 YOLO

        Args:
            class_name: YOLO 检测到的类别名称

        Returns:
            PhysicsProfile: 对应的物理参数，未找到则返回默认参数
        """
        if class_name in self._table:
            profile = self._table[class_name]
        elif class_name.lower() in self._table:
            profile = self._table[class_name.lower()]
        else:
            print(f"[VisionPhysicsMapper] 未找到 '{class_name}'，使用默认参数")
            profile = self._table["__default__"]

        self.current_profile = profile
        return profile

    def get_current_profile(self) -> PhysicsProfile:
        """获取当前/最近一次查表得到的物理参数"""
        return self.current_profile

    # ═══════════════════════════════════════
    # 查表管理
    # ═══════════════════════════════════════
    def update(self, class_name: str, profile: PhysicsProfile):
        """运行时动态更新/添加映射"""
        self._table[class_name] = profile

    def load_json(self, path: str):
        """从 JSON 文件加载/覆盖查表"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for cls_name, params_dict in data.items():
            self._table[cls_name] = PhysicsProfile.from_dict(params_dict)
        print(f"[VisionPhysicsMapper] 已从 {path} 加载 {len(data)} 条映射")

    def save_json(self, path: str):
        """将当前查表保存为 JSON"""
        dump = {k: v.to_dict() for k, v in self._table.items()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dump, f, ensure_ascii=False, indent=2)
        print(f"[VisionPhysicsMapper] 已保存到 {path}")

    def list_classes(self) -> List[str]:
        """返回当前所有已知的类别名（不含 __default__）"""
        return [k for k in self._table.keys() if not k.startswith("__")]

    def get_default(self) -> PhysicsProfile:
        """获取默认参数副本"""
        # dataclass 没有 copy()，用 from_dict 重建
        return PhysicsProfile.from_dict(self._table["__default__"].to_dict())


# ═══════════════════════════════════════════
# 与现有 ROS 节点的集成辅助函数
# ═══════════════════════════════════════════

def map_profile_to_ros_message(profile: PhysicsProfile) -> dict:
    """
    将 PhysicsProfile 转换为可在 ROS topic 上发布的字典格式
    方便序列化为 JSON string 发布到 /object_physics_profile
    """
    return profile.to_dict()


def profile_to_grasp_controller_dict(profile: PhysicsProfile) -> dict:
    """
    转换为 grasp_controller_node 直接可用的策略字典
    兼容现有 GraspControllerNode.select_grasp_strategy() 返回结构
    """
    return profile.to_grasp_strategy()


if __name__ == "__main__":
    # ── 自测 ──
    print("=" * 50)
    print("VisionPhysicsMapper 自测")
    print("=" * 50)

    mapper = VisionPhysicsMapper()  # 纯查表模式，不加载 YOLO

    test_classes = ["banana", "book", "cell phone", "bottle", "未知类别"]
    for cls in test_classes:
        p = mapper.lookup(cls)
        strategy = p.to_grasp_strategy()
        print(f"\n[{cls}] label={p.label}")
        print(f"  K_trans={p.K_trans}, F_target={p.F_target}N, speed={p.approach_speed}m/s")
        print(f"  → strategy: stiffness={strategy['stiffness'][:3]}, force={strategy['force']}N")
        print(f"  → {p.description}")

    # 保存默认表为 JSON 模板
    mapper.save_json("biaoding/physics_table_template.json")
