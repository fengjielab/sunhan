#!/usr/bin/env python3
"""图3：实验流程图 (v4 - 无交叉箭头，双分支直落宽框)"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def main():
    fig, ax = plt.subplots(figsize=(9, 10))
    ax.set_xlim(0, 9)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # 颜色
    C0 = "#2C3E50"   # 开始/结束
    C1 = "#D35400"   # 操作
    C2 = "#8E44AD"   # 视觉
    C3 = "#C0392B"   # 判断
    C4 = "#27AE60"   # 参数
    CA = "#95A5A6"   # 箭头

    def box(cx, cy, w, h, txt, clr, fs=9):
        p = mpatches.FancyBboxPatch((cx-w/2, cy-h/2), w, h,
            boxstyle="round,pad=0.1", facecolor=clr, edgecolor='white',
            linewidth=2, alpha=0.88)
        ax.add_patch(p)
        ax.text(cx, cy, txt, ha='center', va='center', fontsize=fs,
                color='white', fontweight='bold')

    def diamond(cx, cy, s, txt, clr):
        d = mpatches.Polygon([
            [cx, cy+s], [cx+s*1.1, cy],
            [cx, cy-s], [cx-s*1.1, cy]
        ], facecolor=clr, edgecolor='white', linewidth=2, alpha=0.88)
        ax.add_patch(d)
        ax.text(cx, cy, txt, ha='center', va='center', fontsize=8,
                color='white', fontweight='bold')

    def arrow(x1, y1, x2, y2):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=CA, lw=2.2, shrinkA=3, shrinkB=3))

    # ═══ 布局坐标 ═══
    CX = 3.0       # 主流程x中心
    W = 2.6        # 框宽
    H = 0.55       # 框高
    G = 0.25       # 箭头间隙

    # 从上到下y位置
    y = [9.2, 8.0, 6.8]  # 开始、复位、视觉检测
    y_d = 5.6            # 菱形
    y_b = 4.2            # 分支（左右对称）
    y_merge = 3.0        # 宽框（合并）
    y_rem = [1.8, 0.7]   # 抓取、运输

    LX = CX - 2.2   # 左分支x
    RX = CX + 2.2   # 右分支x
    MW = 5.5        # 宽框宽度（从左分支到右分支）

    # ═══ 绘制 ═══
    # 顶部3个
    box(CX, y[0], W*0.6, H, "开始任务", C0, 10)
    box(CX, y[1], W, H, "复位至初始姿态", C1)
    box(CX, y[2], W+0.3, H, "RGB-D图像采集 + YOLO目标检测", C2, 8)

    # 菱形
    diamond(CX, y_d, 0.45, "检测到\n有效对象?", C3)

    # 左右分支
    box(LX, y_b, W, H, "锁定视觉策略\n调用参数组 Θ(c)", C4, 8)
    box(RX, y_b, W, H, "保持默认参数\nΘ(medium) 回退", C4, 8)

    # 宽框（接近目标）
    box(CX, y_merge, MW, H, "接近目标（增量位置映射）", C1, 9)

    # 底部2个
    box(CX, y_rem[0], W, H, "抓取物体（阻抗 + 夹爪控制）", C1, 8)
    box(CX, y_rem[1], W, H, "运输至目标位置（主端力反馈）", C1, 8)

    # ═══ 箭头（全垂直，无交叉） ═══
    # 开始→复位
    arrow(CX, y[0]-H/2-G, CX, y[1]+H/2+G)
    # 复位→视觉检测
    arrow(CX, y[1]-H/2-G, CX, y[2]+H/2+G)
    # 视觉检测→菱形
    arrow(CX, y[2]-H/2-G, CX, y_d+0.45+G)
    # 菱形→左分支 (菱形左侧往下)
    arrow(CX-0.5, y_d-0.45-G, LX, y_b+H/2+G)
    ax.text(CX-0.5, (y_d-0.45+y_b+H/2)/2, "是", ha='center', fontsize=7, color=C3, fontweight='bold')
    # 菱形→右分支 (菱形右侧往下)
    arrow(CX+0.5, y_d-0.45-G, RX, y_b+H/2+G)
    ax.text(CX+0.5, (y_d-0.45+y_b+H/2)/2, "否", ha='center', fontsize=7, color=C3, fontweight='bold')

    # 左分支↓→宽框（垂直）
    arrow(LX, y_b-H/2-G, LX, y_merge+H/2+G)
    # 右分支↓→宽框（垂直）
    arrow(RX, y_b-H/2-G, RX, y_merge+H/2+G)
    # 宽框→抓取
    arrow(CX, y_merge-H/2-G, CX, y_rem[0]+H/2+G)
    # 抓取→运输
    arrow(CX, y_rem[0]-H/2-G, CX, y_rem[1]+H/2+G)

    # ═══ 右侧参数说明 ═══
    RXX = 7.2
    ax.text(RXX, 9.3, "接触前调度参数组", ha='center', fontsize=10,
            fontweight='bold', color=C4)
    ax.text(RXX, 8.7, "Θ(c) = {Kt, Kr, ζ, Kf, d, vg, Fg}",
            ha='center', fontsize=7.5, color='#444', style='italic')

    info = [
        ("从端阻抗", "Kt=50~200 N/m\nKr=5~13 N·m/rad\nζ=0.8~1.2"),
        ("力反馈",   "Kf=0.2~0.7 增益\nd=0.3~0.5 N 死区"),
        ("夹爪",     "vg=0.02~0.10 m/s\nFg=8~20 N"),
    ]
    for i, (title, desc) in enumerate(info):
        yy = 7.2 - i*1.2
        box(RXX-0.8, yy+0.2, 1.5, 0.4, title, C4, 7)
        ax.text(RXX+0.3, yy-0.1, desc, ha='left', va='top', fontsize=6.5,
                color='#333', linespacing=1.4)

    # 三条水平虚线连到主流程（不参与箭头，纯标注）
    for y_pos, label_text in [(y_b, "策略锁定阶段"),
                               (y_rem[0], "抓取执行阶段"),
                               (y_rem[1], "运输阶段")]:
        ax.hlines(y=y_pos, xmin=CX+W/2+0.2, xmax=RXX-2.0,
                  colors=C4, linestyles='dotted', linewidth=1, alpha=0.4)
        ax.text(RXX-1.8, y_pos, f"→ {label_text}", fontsize=6.5,
                color=C4, va='center', ha='center')

    # ═══ 标题 ═══
    ax.text(4.5, 9.75, "图3：实验任务流程图", ha='center', fontsize=14,
            fontweight='bold', color='#222')

    # ═══ 图例 ═══
    leg = [("开始/结束", C0), ("操作动作", C1), ("视觉检测", C2), ("参数配置", C4)]
    ax.text(0.5, 0.3, "图例", fontsize=8, fontweight='bold')
    for i, (t, c) in enumerate(leg):
        p = mpatches.FancyBboxPatch((0.5, 0.0-i*0.3), 0.25, 0.13,
            boxstyle="round,pad=0.02", facecolor=c, alpha=0.88)
        ax.add_patch(p)
        ax.text(0.9, 0.0-i*0.3, t, fontsize=7, va='center')

    plt.tight_layout()
    from pathlib import Path
    out = Path(__file__).resolve().parent / "fig"
    out.mkdir(exist_ok=True)
    plt.savefig(out/"fig3_experiment_flow.png", dpi=300, bbox_inches='tight')
    plt.savefig(out/"fig3_experiment_flow.svg", bbox_inches='tight')
    plt.close()
    print(f"✅ 图3: {out/'fig3_experiment_flow.png'}")

if __name__ == "__main__":
    main()