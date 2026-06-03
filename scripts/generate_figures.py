#!/usr/bin/env python3
"""
生成论文图表：图1(方法对比)、图2(系统架构)、图4(阻抗响应)
输出目录: paper_figures/
"""

import os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines
from scipy.integrate import odeint

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'paper_figures')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════
# 配色方案
# ═══════════════════════════════════════════════════════════
BLUE   = '#2196F3'   # 运动流
RED    = '#F44336'   # 力觉流
GREEN  = '#4CAF50'   # 视觉语义流
ORANGE = '#FF9800'
GRAY   = '#9E9E9E'
LIGHT_GRAY = '#F5F5F5'
DARK   = '#333333'

# ── 中文字体设置 ──
import matplotlib.font_manager as fm
fm.fontManager.addfont('/usr/share/fonts/truetype/arphic/uming.ttc')
fm._load_fontmanager(try_read_cache=False)
_FONT = 'AR PL UMing CN'
plt.rcParams['font.sans-serif'] = [_FONT, 'DejaVu Sans']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False


# ═══════════════════════════════════════════════════════════
# 图4：阻抗响应对比曲线（可仿真生成）
# ═══════════════════════════════════════════════════════════
def generate_fig4():
    print("[图4] 生成阻抗响应对比曲线...")

    M = 3.0
    configs = [
        (50,  2*np.sqrt(3*50),   GREEN,  'K=50 N/m (软)',  '4.0 cm'),
        (150, 2*np.sqrt(3*150), ORANGE, 'K=150 N/m (中)', '1.3 cm'),
        (300, 2*np.sqrt(3*300), RED,    'K=300 N/m (硬)', '0.67 cm'),
    ]

    def system(y, t, K, D):
        x, v = y
        F = 2.0 if t >= 0.1 else 0.0
        return [v, (F - K*x - D*v) / M]

    t = np.linspace(0, 2.0, 2000)
    fig, ax = plt.subplots(figsize=(5.5, 3.8))

    for K, D, color, label, steady_text in configs:
        sol = odeint(system, [0, 0], t, args=(K, D))
        ax.plot(t, sol[:, 0], color=color, label=label, linewidth=2.0)
        steady = 2.0 / K
        ax.axhline(y=steady, color=color, linestyle='--', alpha=0.4, linewidth=1.0)
        # 标注稳态值
        ax.text(1.75, steady + 0.001, steady_text, color=color, fontsize=8,
                ha='right', va='bottom')

    ax.set_xlabel('时间 (s)', fontsize=11)
    ax.set_ylabel('位移 (m)', fontsize=11)
    ax.set_xlim(0, 2.0)
    ax.set_ylim(0, 0.05)
    ax.legend(fontsize=9, loc='lower right', framealpha=0.9)
    ax.grid(alpha=0.3)
    ax.set_title('阶跃外力 F=2N 下的阻抗响应', fontsize=11, fontweight='bold')
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'fig4_impedance_response.png')
    fig.savefig(path, dpi=300)
    plt.close(fig)
    print(f"  ✓ 已保存: {path}")


# ═══════════════════════════════════════════════════════════
# 图1：方法对比示意图
# ═══════════════════════════════════════════════════════════
def generate_fig1():
    print("[图1] 生成方法对比示意图...")

    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(10, 4.5))
    for ax in [ax_left, ax_right]:
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.set_aspect('equal')
        ax.axis('off')

    # ── 左侧：传统方法 ──
    ax = ax_left
    ax.text(5, 9.2, '传统方法', fontsize=13, fontweight='bold', ha='center', color=DARK)

    # 视觉模块
    rect1 = FancyBboxPatch((2, 6.5), 6, 1.5, boxstyle="round,pad=0.15",
                           facecolor='#E8F5E9', edgecolor=GREEN, linewidth=2)
    ax.add_patch(rect1)
    ax.text(5, 7.6, '视觉模块', fontsize=11, ha='center', fontweight='bold', color=GREEN)
    ax.text(5, 7.0, '仅定位 → 目标位置', fontsize=8, ha='center', color=GRAY)

    # 力反馈模块
    rect2 = FancyBboxPatch((2, 3.8), 6, 1.5, boxstyle="round,pad=0.15",
                           facecolor='#FFEBEE', edgecolor=RED, linewidth=2)
    ax.add_patch(rect2)
    ax.text(5, 4.9, '力反馈', fontsize=11, ha='center', fontweight='bold', color=RED)
    ax.text(5, 4.3, 'K_trans = 固定值', fontsize=8, ha='center', color=GRAY)

    # 阻抗控制模块
    rect3 = FancyBboxPatch((2, 1.1), 6, 1.5, boxstyle="round,pad=0.15",
                           facecolor='#E3F2FD', edgecolor=BLUE, linewidth=2)
    ax.add_patch(rect3)
    ax.text(5, 2.2, '阻抗控制', fontsize=11, ha='center', fontweight='bold', color=BLUE)
    ax.text(5, 1.6, 'K = 200 N/m 固定', fontsize=8, ha='center', color=GRAY)

    # 独立运行标注
    ax.text(5, 0.3, '各模块独立运行，参数固定', fontsize=8, ha='center', color=GRAY, fontstyle='italic')

    # 红色 X 标记
    ax.text(9.2, 2.5, '✗', fontsize=16, ha='center', color=RED, alpha=0.6)
    ax.text(9.2, 5.2, '✗', fontsize=16, ha='center', color=RED, alpha=0.6)


    # ── 右侧：本文方法 ──
    ax = ax_right
    ax.text(5, 9.2, '本文方法', fontsize=13, fontweight='bold', ha='center', color=DARK)

    # YOLO视觉语义模块（顶部，绿色）
    rect_v = FancyBboxPatch((2.5, 6.5), 5, 1.5, boxstyle="round,pad=0.15",
                            facecolor='#E8F5E9', edgecolor=GREEN, linewidth=2.5)
    ax.add_patch(rect_v)
    ax.text(5, 7.6, 'YOLOv11n 视觉语义', fontsize=10, ha='center', fontweight='bold', color=GREEN)
    ax.text(5, 7.0, '识别 → 物体类别 c', fontsize=8, ha='center', color=GRAY)

    # 力反馈调度器（左下，红色）
    rect_f = FancyBboxPatch((1, 3.0), 4, 1.5, boxstyle="round,pad=0.15",
                            facecolor='#FFEBEE', edgecolor=RED, linewidth=2.5)
    ax.add_patch(rect_f)
    ax.text(3, 4.1, '力反馈调度器', fontsize=10, ha='center', fontweight='bold', color=RED)
    ax.text(3, 3.5, 'K_trans(c) 自适应', fontsize=8, ha='center', color=GRAY)

    # 阻抗调度器（右下，蓝色）
    rect_i = FancyBboxPatch((5, 3.0), 4, 1.5, boxstyle="round,pad=0.15",
                            facecolor='#E3F2FD', edgecolor=BLUE, linewidth=2.5)
    ax.add_patch(rect_i)
    ax.text(7, 4.1, '阻抗调度器', fontsize=10, ha='center', fontweight='bold', color=BLUE)
    ax.text(7, 3.5, 'K(c), D(c) 自适应', fontsize=8, ha='center', color=GRAY)

    # Omega.7 和 Franka 模块（底部）
    rect_o = FancyBboxPatch((1, 0.8), 4, 1.5, boxstyle="round,pad=0.15",
                            facecolor='#F3E5F5', edgecolor='#9C27B0', linewidth=2)
    ax.add_patch(rect_o)
    ax.text(3, 1.7, 'Omega.7 主手', fontsize=9, ha='center', fontweight='bold', color='#9C27B0')
    ax.text(3, 1.2, '力反馈渲染', fontsize=8, ha='center', color=GRAY)

    rect_p = FancyBboxPatch((5, 0.8), 4, 1.5, boxstyle="round,pad=0.15",
                            facecolor='#FFF3E0', edgecolor='#FF5722', linewidth=2)
    ax.add_patch(rect_p)
    ax.text(7, 1.7, 'Franka Panda', fontsize=9, ha='center', fontweight='bold', color='#FF5722')
    ax.text(7, 1.2, '阻抗伺服控制', fontsize=8, ha='center', color=GRAY)

    # 添加箭头：视觉→力反馈（绿色）
    ax.annotate('', xy=(3, 4.5), xytext=(4.2, 6.3),
                arrowprops=dict(arrowstyle='->', color=GREEN, lw=2.5))
    ax.text(2.5, 5.4, 'K_trans(c)', fontsize=8, color=GREEN, fontweight='bold', rotation=-45)

    # 添加箭头：视觉→阻抗（绿色）
    ax.annotate('', xy=(7, 4.5), xytext=(5.8, 6.3),
                arrowprops=dict(arrowstyle='->', color=GREEN, lw=2.5))
    ax.text(7.5, 5.4, 'K(c), D(c)', fontsize=8, color=GREEN, fontweight='bold', rotation=45)

    # 底部标注
    ax.text(5, 0.2, '视觉语义驱动双调度 → 识别即适配', fontsize=8, ha='center', color=GREEN, fontweight='bold')

    # 绿色对勾
    ax.text(9.2, 2.5, '✓', fontsize=18, ha='center', color=GREEN, fontweight='bold')
    ax.text(9.2, 5.5, '✓', fontsize=18, ha='center', color=GREEN, fontweight='bold')

    fig.tight_layout(pad=1.5)
    path = os.path.join(OUTPUT_DIR, 'fig1_method_comparison.png')
    fig.savefig(path, dpi=300)
    plt.close(fig)
    print(f"  ✓ 已保存: {path}")


# ═══════════════════════════════════════════════════════════
# 图2：系统总体架构图
# ═══════════════════════════════════════════════════════════
def generate_fig2():
    print("[图2] 生成系统总体架构图...")

    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')

    # ═══ 区域划分（背景色块）═══
    # 主端区域（顶部）
    ax.add_patch(mpatches.Rectangle((0.2, 7.8), 13.6, 2.0, facecolor='#F3E5F5', alpha=0.3, edgecolor='#9C27B0', linewidth=1, linestyle='--'))
    ax.text(0.5, 9.5, '主端 (Omega.7)', fontsize=10, fontweight='bold', color='#9C27B0')

    # 视觉区域（左侧中部）
    ax.add_patch(mpatches.Rectangle((0.2, 3.5), 4.0, 3.5, facecolor='#E8F5E9', alpha=0.3, edgecolor=GREEN, linewidth=1, linestyle='--'))
    ax.text(0.5, 6.6, '视觉模块 (独立进程 30Hz)', fontsize=9, fontweight='bold', color=GREEN)

    # 控制器区域（中部）
    ax.add_patch(mpatches.Rectangle((4.5, 3.5), 5.0, 4.0, facecolor='#FFF8E1', alpha=0.3, edgecolor=ORANGE, linewidth=1, linestyle='--'))
    ax.text(4.8, 6.8, '共享控制器 (主控机)', fontsize=10, fontweight='bold', color=ORANGE)

    # 从端区域（底部）
    ax.add_patch(mpatches.Rectangle((0.2, 0.2), 13.6, 2.8, facecolor='#FFF3E0', alpha=0.3, edgecolor='#FF5722', linewidth=1, linestyle='--'))
    ax.text(0.5, 2.4, '从端 (Franka Panda)', fontsize=10, fontweight='bold', color='#FF5722')

    # ═══ 主端模块 ═══
    # Omega.7 硬件
    rect_o = FancyBboxPatch((1.0, 8.5), 3.0, 1.0, boxstyle="round,pad=0.1",
                            facecolor='#EDE7F6', edgecolor='#9C27B0', linewidth=2)
    ax.add_patch(rect_o)
    ax.text(2.5, 9.0, 'Omega.7 硬件', fontsize=9, ha='center', fontweight='bold', color='#9C27B0')

    # 位姿读取
    rect_pos = FancyBboxPatch((5.0, 8.5), 2.5, 1.0, boxstyle="round,pad=0.1",
                              facecolor='#E3F2FD', edgecolor=BLUE, linewidth=2)
    ax.add_patch(rect_pos)
    ax.text(6.25, 8.8, '位姿读取', fontsize=9, ha='center', fontweight='bold', color=BLUE)
    ax.text(6.25, 8.2, '200 Hz', fontsize=7, ha='center', color=BLUE)

    # 力反馈渲染
    rect_force = FancyBboxPatch((8.0, 8.5), 2.5, 1.0, boxstyle="round,pad=0.1",
                                facecolor='#FFEBEE', edgecolor=RED, linewidth=2)
    ax.add_patch(rect_force)
    ax.text(9.25, 8.8, '力反馈渲染', fontsize=9, ha='center', fontweight='bold', color=RED)
    ax.text(9.25, 8.2, '200 Hz', fontsize=7, ha='center', color=RED)

    # 箭头：Omega.7 → 位姿读取
    ax.annotate('', xy=(5.0, 9.0), xytext=(4.0, 9.0),
                arrowprops=dict(arrowstyle='->', color=BLUE, lw=2))
    ax.text(4.5, 9.2, '位置', fontsize=7, ha='center', color=BLUE)

    # 箭头：力反馈渲染 → Omega.7
    ax.annotate('', xy=(11.0, 9.0), xytext=(10.5, 9.0),
                arrowprops=dict(arrowstyle='->', color=RED, lw=2))

    # ═══ 视觉模块 ═══
    # RealSense
    rect_rs = FancyBboxPatch((0.5, 4.5), 1.8, 0.9, boxstyle="round,pad=0.1",
                             facecolor='#C8E6C9', edgecolor=GREEN, linewidth=2)
    ax.add_patch(rect_rs)
    ax.text(1.4, 5.0, 'RealSense', fontsize=8, ha='center', fontweight='bold', color=GREEN)
    ax.text(1.4, 4.6, 'D435', fontsize=7, ha='center', color=GREEN)

    # YOLO
    rect_y = FancyBboxPatch((0.5, 3.5), 1.8, 0.9, boxstyle="round,pad=0.1",
                            facecolor='#A5D6A7', edgecolor=GREEN, linewidth=2)
    ax.add_patch(rect_y)
    ax.text(1.4, 4.0, 'YOLOv11n', fontsize=8, ha='center', fontweight='bold', color=GREEN)

    # 映射表
    rect_map = FancyBboxPatch((2.8, 3.8), 1.5, 1.0, boxstyle="round,pad=0.1",
                              facecolor='#81C784', edgecolor=GREEN, linewidth=2)
    ax.add_patch(rect_map)
    ax.text(3.55, 4.35, '语义-物理', fontsize=7, ha='center', fontweight='bold', color='white')
    ax.text(3.55, 4.0, '映射表', fontsize=7, ha='center', fontweight='bold', color='white')

    # 箭头：RealSense → YOLO
    ax.annotate('', xy=(1.4, 4.4), xytext=(1.4, 4.5),
                arrowprops=dict(arrowstyle='->', color=GREEN, lw=1.5))
    # YOLO → 映射表
    ax.annotate('', xy=(2.8, 4.3), xytext=(2.3, 4.3),
                arrowprops=dict(arrowstyle='->', color=GREEN, lw=1.5))
    ax.text(2.55, 4.5, 'c', fontsize=8, ha='center', color=GREEN, fontweight='bold')

    # ═══ 共享控制器模块 ═══
    # 位置映射
    rect_pm = FancyBboxPatch((5.0, 4.8), 2.0, 0.9, boxstyle="round,pad=0.1",
                             facecolor='#E3F2FD', edgecolor=BLUE, linewidth=2)
    ax.add_patch(rect_pm)
    ax.text(6.0, 5.25, '位置映射', fontsize=8, ha='center', fontweight='bold', color=BLUE)
    ax.text(6.0, 4.9, 'scale × sign', fontsize=7, ha='center', color=BLUE)

    # 导纳调度
    rect_ad = FancyBboxPatch((7.5, 4.8), 2.0, 0.9, boxstyle="round,pad=0.1",
                             facecolor='#BBDEFB', edgecolor=BLUE, linewidth=2)
    ax.add_patch(rect_ad)
    ax.text(8.5, 5.25, '自适应导纳', fontsize=8, ha='center', fontweight='bold', color=BLUE)
    ax.text(8.5, 4.9, 'K(c), D(c)', fontsize=7, ha='center', color=BLUE)

    # 力反馈调度
    rect_fs = FancyBboxPatch((5.0, 3.5), 2.0, 0.9, boxstyle="round,pad=0.1",
                             facecolor='#FFCDD2', edgecolor=RED, linewidth=2)
    ax.add_patch(rect_fs)
    ax.text(6.0, 3.95, '力反馈调度', fontsize=8, ha='center', fontweight='bold', color=RED)
    ax.text(6.0, 3.6, 'K_trans·F_ext', fontsize=7, ha='center', color=RED)

    # 夹持力估计
    rect_ge = FancyBboxPatch((7.5, 3.5), 2.0, 0.9, boxstyle="round,pad=0.1",
                             facecolor='#FFCCBC', edgecolor='#FF5722', linewidth=2)
    ax.add_patch(rect_ge)
    ax.text(8.5, 3.95, '夹持力估计', fontsize=8, ha='center', fontweight='bold', color='#FF5722')
    ax.text(8.5, 3.6, '||τ_wrist||/τ_max', fontsize=7, ha='center', color='#FF5722')

    # 绿色箭头：映射表 → 力反馈调度 + 导纳调度
    ax.annotate('', xy=(5.0, 4.0), xytext=(4.3, 4.2),
                arrowprops=dict(arrowstyle='->', color=GREEN, lw=2))
    ax.text(4.6, 3.7, 'K_trans,\ndeadband', fontsize=6, ha='center', color=GREEN, fontweight='bold')

    ax.annotate('', xy=(7.5, 5.3), xytext=(4.3, 4.6),
                arrowprops=dict(arrowstyle='->', color=GREEN, lw=2, connectionstyle='arc3,rad=-0.3'))
    ax.text(5.8, 5.7, 'K(c), D(c)', fontsize=7, color=GREEN, fontweight='bold')

    # 蓝色箭头：位置映射 → 导纳调度
    ax.annotate('', xy=(7.5, 5.3), xytext=(7.0, 5.3),
                arrowprops=dict(arrowstyle='->', color=BLUE, lw=2))
    # 蓝色箭头：导纳调度 → 下方（向下发送目标位姿）
    ax.annotate('', xy=(8.5, 4.7), xytext=(8.5, 3.1),
                arrowprops=dict(arrowstyle='->', color=BLUE, lw=2.5))
    ax.text(8.8, 3.9, '目标位姿 Xd', fontsize=7, color=BLUE, fontweight='bold')

    # ═══ 从端模块 ═══
    # 笛卡尔阻抗控制
    rect_ic = FancyBboxPatch((1.0, 1.0), 2.5, 1.0, boxstyle="round,pad=0.1",
                             facecolor='#E3F2FD', edgecolor=BLUE, linewidth=2)
    ax.add_patch(rect_ic)
    ax.text(2.25, 1.5, '笛卡尔阻抗控制', fontsize=9, ha='center', fontweight='bold', color=BLUE)
    ax.text(2.25, 1.1, '200 Hz', fontsize=7, ha='center', color=BLUE)

    # Panda 硬件
    rect_panda = FancyBboxPatch((4.5, 1.0), 2.5, 1.0, boxstyle="round,pad=0.1",
                                facecolor='#FFF3E0', edgecolor='#FF5722', linewidth=2)
    ax.add_patch(rect_panda)
    ax.text(5.75, 1.5, 'Franka Panda', fontsize=9, ha='center', fontweight='bold', color='#FF5722')

    # 腕部力矩
    rect_tau = FancyBboxPatch((8.0, 1.0), 2.5, 1.0, boxstyle="round,pad=0.1",
                              facecolor='#FFEBEE', edgecolor=RED, linewidth=2)
    ax.add_patch(rect_tau)
    ax.text(9.25, 1.5, '腕部力矩传感器', fontsize=8, ha='center', fontweight='bold', color=RED)
    ax.text(9.25, 1.1, 'τ_ext_hat', fontsize=7, ha='center', color=RED)

    # 夹爪
    rect_grip = FancyBboxPatch((11.0, 1.0), 2.0, 1.0, boxstyle="round,pad=0.1",
                               facecolor='#F3E5F5', edgecolor='#9C27B0', linewidth=2)
    ax.add_patch(rect_grip)
    ax.text(12.0, 1.5, 'Franka Hand', fontsize=8, ha='center', fontweight='bold', color='#9C27B0')
    ax.text(12.0, 1.1, '夹爪', fontsize=7, ha='center', color='#9C27B0')

    # 蓝色箭头：导纳调度 → 阻抗控制
    ax.annotate('', xy=(2.25, 2.0), xytext=(8.5, 3.0),
                arrowprops=dict(arrowstyle='->', color=BLUE, lw=2, connectionstyle='arc3,rad=0.2'))
    ax.text(4.8, 2.8, 'Xd (目标)', fontsize=7, color=BLUE, fontweight='bold')

    # 蓝色箭头：阻抗控制 → Panda
    ax.annotate('', xy=(4.5, 1.5), xytext=(3.5, 1.5),
                arrowprops=dict(arrowstyle='->', color=BLUE, lw=2))

    # 红色箭头：Panda → 力矩
    ax.annotate('', xy=(8.0, 1.5), xytext=(7.0, 1.5),
                arrowprops=dict(arrowstyle='->', color=RED, lw=2))

    # 红色箭头：力矩 → 夹持力估计
    ax.annotate('', xy=(8.5, 3.5), xytext=(9.25, 2.0),
                arrowprops=dict(arrowstyle='->', color=RED, lw=2, connectionstyle='arc3,rad=-0.2'))
    ax.text(9.5, 2.7, 'τ_ext', fontsize=7, color=RED, fontweight='bold')

    # 红色箭头：力反馈调度 → 力反馈渲染
    ax.annotate('', xy=(9.25, 8.5), xytext=(7.0, 4.4),
                arrowprops=dict(arrowstyle='->', color=RED, lw=2, connectionstyle='arc3,rad=0.3'))
    ax.text(8.8, 6.3, 'F_haptic', fontsize=7, color=RED, fontweight='bold')

    # 频率标注
    ax.text(0.5, 0.5, '控制频率: 200 Hz  |  视觉频率: 30 Hz  |  夹爪频率: 10 Hz',
            fontsize=7, color=GRAY, fontstyle='italic')

    # 图例
    legend_elements = [
        mlines.Line2D([0], [0], color=BLUE, lw=3, label='[蓝] 运动流 (200 Hz)'),
        mlines.Line2D([0], [0], color=RED, lw=3, label='[红] 力觉流 (200 Hz)'),
        mlines.Line2D([0], [0], color=GREEN, lw=3, label='[绿] 视觉语义流 (30 Hz)'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=7, framealpha=0.9)

    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'fig2_system_architecture.png')
    fig.savefig(path, dpi=300)
    plt.close(fig)
    print(f"  ✓ 已保存: {path}")


# ═══════════════════════════════════════════════════════════
# 图3：夹持过程信号曲线（仿真原理图）
# ═══════════════════════════════════════════════════════════
def generate_fig3():
    """
    生成夹爪宽度与腕部力矩在接近→接触→夹持→释放过程中的变化曲线。
    使用 sigmoid 分段函数模拟典型抓取过程，无需真实实验数据。
    """
    print("[图3] 生成夹持过程信号曲线...")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(5.5, 4.5), sharex=True)
    fig.subplots_adjust(hspace=0.08)

    # ── 时间轴 ──
    fs = 200  # 采样率 (Hz)
    t = np.linspace(0, 8.0, int(8.0 * fs))

    # ── 阶段定义（秒）──
    T_APPROACH_START = 0.0
    T_CONTACT       = 2.0   # 接触时刻（宽度停滞、力矩上升）
    T_HOLD_START    = 2.5   # 夹持阶段开始
    T_RELEASE_START = 4.0   # 释放
    T_END           = 8.0

    # ── 夹爪宽度信号 ──
    width = np.ones_like(t) * 80.0  # 初始 80mm 全开

    # 接近阶段 (0→2s): 从 80mm 缓慢下降到 ~30mm
    mask_approach = (t >= T_APPROACH_START) & (t < T_CONTACT)
    progress = (t[mask_approach] - T_APPROACH_START) / (T_CONTACT - T_APPROACH_START)
    width[mask_approach] = 80.0 - 50.0 * progress  # 80→30

    # 接触后停滞 (2→2.5s): 宽度维持在 ~30mm
    mask_stall = (t >= T_CONTACT) & (t < T_HOLD_START)
    width[mask_stall] = 30.0 + 2.0 * np.sin(t[mask_stall] * 4) * 0.5  # 微小抖动

    # 夹持保持 (2.5→4.0s): 维持
    mask_hold = (t >= T_HOLD_START) & (t < T_RELEASE_START)
    width[mask_hold] = 30.0 + 1.0 * np.sin(t[mask_hold] * 2) * 0.3

    # 释放阶段 (4→8s): 快速张开回到 80mm
    mask_release = t >= T_RELEASE_START
    release_progress = np.clip((t[mask_release] - T_RELEASE_START) / 2.0, 0, 1)
    width[mask_release] = 30.0 + 50.0 * release_progress

    # ── 腕部力矩信号 ──
    torque = np.zeros_like(t)

    # 接近阶段: 低噪声 ~0.2 N·m
    torque[mask_approach] = 0.2 + 0.05 * np.random.randn(np.sum(mask_approach))

    # 接触瞬间 (2.0s): 快速上升至 ~2.5 N·m（使用 sigmoid）
    mask_contact_rise = (t >= T_CONTACT) & (t < T_CONTACT + 0.3)
    rise_progress = (t[mask_contact_rise] - T_CONTACT) / 0.3
    torque[mask_contact_rise] = 0.2 + 2.3 * (1.0 / (1.0 + np.exp(-10 * (rise_progress - 0.5))))

    # 夹持保持 (2.3→4.0s): 约 2.5 N·m 波动
    mask_hold_torque = (t >= T_CONTACT + 0.3) & (t < T_RELEASE_START)
    torque[mask_hold_torque] = 2.5 + 0.3 * np.sin(t[mask_hold_torque] * 3)

    # 释放: 快速回落
    mask_release_torque = t >= T_RELEASE_START
    release_decay = np.exp(-3 * (t[mask_release_torque] - T_RELEASE_START))
    torque[mask_release_torque] = 2.5 * release_decay + 0.15 * np.random.randn(np.sum(mask_release_torque)) * 0.1

    # ── 绘制上子图：夹爪宽度 ──
    ax1.plot(t, width, color=BLUE, linewidth=2.0)
    ax1.set_ylabel('夹爪宽度 (mm)', fontsize=10)
    ax1.set_ylim(0, 90)
    ax1.set_yticks([0, 20, 40, 60, 80])
    ax1.grid(alpha=0.3)
    ax1.axvline(x=T_CONTACT, color=RED, linestyle='--', alpha=0.6, linewidth=1.5)
    ax1.text(T_CONTACT + 0.05, 85, '接触点', fontsize=8, color=RED, fontweight='bold')

    # 三阶段标注
    ax1.axvspan(0, T_CONTACT, alpha=0.06, color=BLUE)
    ax1.axvspan(T_CONTACT, T_RELEASE_START, alpha=0.06, color=GREEN)
    ax1.axvspan(T_RELEASE_START, T_END, alpha=0.06, color=ORANGE)
    ax1.text(1.0, 5, '接近阶段', fontsize=8, ha='center', color=BLUE, fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))
    ax1.text(3.0, 5, '夹持阶段', fontsize=8, ha='center', color=GREEN, fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))
    ax1.text(6.0, 5, '释放阶段', fontsize=8, ha='center', color=ORANGE, fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))

    # ── 绘制下子图：腕部力矩 ──
    ax2.plot(t, torque, color=RED, linewidth=2.0)
    ax2.set_xlabel('时间 (s)', fontsize=10)
    ax2.set_ylabel('腕部力矩范数 (N·m)', fontsize=10)
    ax2.set_ylim(0, 4.0)
    ax2.set_yticks([0, 1, 2, 3, 4])
    ax2.grid(alpha=0.3)
    ax2.axvline(x=T_CONTACT, color=RED, linestyle='--', alpha=0.6, linewidth=1.5)

    # 阈值线
    ax2.axhline(y=1.0, color=GRAY, linestyle=':', alpha=0.7, linewidth=1.0)
    ax2.text(T_END - 0.3, 1.05, '阈值 1.0 N·m', fontsize=7, color=GRAY, ha='right')

    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'fig3_grip_signal.png')
    fig.savefig(path, dpi=300)
    plt.close(fig)
    print(f"  ✓ 已保存: {path}")


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("=" * 50)
    print("生成论文图表")
    print("=" * 50)
    generate_fig4()   # 阻抗响应曲线
    generate_fig3()   # 夹持过程信号（新增）
    generate_fig1()   # 方法对比图
    generate_fig2()   # 系统架构图
    print("=" * 50)
    print(f"全部完成！图片已保存到: {OUTPUT_DIR}/")
    print(f"  文件列表:")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        fpath = os.path.join(OUTPUT_DIR, f)
        size = os.path.getsize(fpath) / 1024
        print(f"    {f}  ({size:.1f} KB)")
