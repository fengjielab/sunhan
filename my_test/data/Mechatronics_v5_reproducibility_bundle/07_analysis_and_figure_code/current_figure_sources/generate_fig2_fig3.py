from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reproduced_figures"

BLUE = "#1F5AA6"
LIGHT_BLUE = "#EAF2FB"
GREEN = "#238B45"
LIGHT_GREEN = "#EAF6EE"
PURPLE = "#7043A5"
LIGHT_PURPLE = "#F1ECF7"
ORANGE = "#E56B1F"
LIGHT_ORANGE = "#FFF1E8"
RED = "#C73E3A"
GRAY = "#4E5968"
LIGHT_GRAY = "#F4F6F8"


def setup_ax(ax, xlim=(0, 100), ylim=(0, 100)):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")


def box(ax, x, y, w, h, text, edge=BLUE, face="white", size=9.2,
        weight="normal", radius=0.8, text_color="#17212B", lw=1.3):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.28",
        linewidth=lw, edgecolor=edge, facecolor=face,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2, y + h / 2, text,
        ha="center", va="center", fontsize=size, fontweight=weight,
        color=text_color, linespacing=1.18,
    )
    return patch


def arrow(ax, p1, p2, color=BLUE, lw=1.3, style="-", mutation=9,
          connectionstyle="arc3"):
    patch = FancyArrowPatch(
        p1, p2, arrowstyle="-|>", mutation_scale=mutation,
        linewidth=lw, color=color, linestyle=style,
        connectionstyle=connectionstyle, shrinkA=2, shrinkB=2,
    )
    ax.add_patch(patch)
    return patch


def save(fig, stem):
    OUT.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf", "svg"):
        kwargs = {"dpi": 600} if suffix == "png" else {}
        fig.savefig(OUT / f"{stem}.{suffix}", bbox_inches="tight", facecolor="white", **kwargs)
    plt.close(fig)


def figure_2():
    """Create a single integrated multi-rate, bounded-queue architecture."""
    fig = plt.figure(figsize=(7.2, 4.55), facecolor="white")
    fig.subplots_adjust(left=0.02, right=0.99, bottom=0.025, top=0.97)
    ax = fig.add_subplot(111)
    setup_ax(ax)

    ax.text(50, 97, "Multi-rate bounded-queue software architecture",
            ha="center", va="top", fontsize=10.1, fontweight="bold", color="#173D73")

    lanes = [
        (65, 26, "Perception process", "15 fps", LIGHT_BLUE, BLUE),
        (36, 24, "Bounded event\ncommunication", "asynchronous", LIGHT_GRAY, GRAY),
        (5, 26, "Supervisory loop", "nominal 200 Hz", LIGHT_GREEN, GREEN),
    ]
    for y, h, title, rate, face, edge in lanes:
        ax.add_patch(FancyBboxPatch(
            (1.5, y), 97, h, boxstyle="round,pad=0.25",
            linewidth=1.15, edgecolor=edge, facecolor=face,
        ))
        ax.add_patch(FancyBboxPatch(
            (1.5, y), 14, h, boxstyle="round,pad=0.25",
            linewidth=1.15, edgecolor=edge, facecolor="white",
        ))
        ax.text(8.5, y + h * 0.62, title, ha="center", va="center",
                fontsize=7.2, fontweight="bold", color="#173D73")
        ax.text(8.5, y + h * 0.27, rate, ha="center", va="center",
                fontsize=6.8, fontweight="bold", color=edge)

    # Perception lane.
    box(ax, 19, 72, 19, 11, "RGB camera\n424 × 240", BLUE, "white", 7.3, "bold")
    ax.add_patch(FancyBboxPatch(
        (44, 72), 14, 11, boxstyle="round,pad=0.28",
        linewidth=1.3, edgecolor=BLUE, facecolor="white",
    ))
    ax.text(51, 80.0, "Frame queue · capacity 1", ha="center", va="center",
            fontsize=6.35, fontweight="bold", color="#17212B")
    ax.add_patch(Rectangle((49.3, 73.3), 3.4, 3.8, linewidth=1.1,
                           edgecolor=BLUE, facecolor=LIGHT_BLUE))
    box(ax, 64, 72, 23, 11, "YOLO11n visual processing\n48.19 ms/image (mean)",
        BLUE, "white", 7.0, "bold")
    arrow(ax, (38, 77.5), (44, 77.5), BLUE, lw=1.3, mutation=8)
    arrow(ax, (58, 77.5), (64, 77.5), BLUE, lw=1.3, mutation=8)
    ax.text(51, 68.2, "single-slot queue limits stale-frame accumulation",
            ha="center", va="center", fontsize=6.3, color=GRAY)

    # Communication lane.
    ax.add_patch(FancyBboxPatch(
        (50, 42), 16, 11, boxstyle="round,pad=0.28",
        linewidth=1.3, edgecolor=GRAY, facecolor="white",
    ))
    ax.text(58, 50.0, "Result queue · capacity 2", ha="center", va="center",
            fontsize=6.35, fontweight="bold", color="#17212B")
    for i in range(2):
        ax.add_patch(Rectangle((54.3 + i * 3.8, 43.3), 3.1, 3.8, linewidth=1.0,
                               edgecolor=GRAY, facecolor=LIGHT_GRAY))
        ax.text(55.85 + i * 3.8, 45.2, str(i + 1), ha="center", va="center",
                fontsize=5.8, color=GRAY)
    box(ax, 72, 42, 18, 11, "Class + confidence", GRAY, "white", 7.1, "bold")
    arrow(ax, (75.5, 72), (59, 53), BLUE, lw=1.15, style="--", mutation=8,
          connectionstyle="arc3,rad=0.16")
    arrow(ax, (66, 47.5), (72, 47.5), GRAY, lw=1.15, mutation=8)

    # Supervisory lane.
    box(ax, 38, 14, 18, 11, "Non-blocking poll", GREEN, "white", 7.1, "bold")
    diamond = Polygon([(66, 26), (75, 19.5), (66, 13), (57, 19.5)], closed=True,
                      linewidth=1.2, edgecolor=GREEN, facecolor="white")
    ax.add_patch(diamond)
    ax.text(66, 19.5, "First valid\nmapped result?", ha="center", va="center",
            fontsize=6.8, fontweight="bold", color="#17212B")
    box(ax, 78, 17, 19, 10, "One-shot strategy event\n$\\Theta(c)$",
        GREEN, LIGHT_GREEN, 6.7, "bold")
    box(ax, 78, 7, 18, 7, "Keep mode initialization",
        GRAY, "white", 6.5, "bold")
    arrow(ax, (58, 42), (47, 25), BLUE, lw=1.1, style="--", mutation=8)
    arrow(ax, (56, 19.5), (57, 19.5), GREEN, lw=1.2, mutation=8)
    arrow(ax, (75, 20.5), (78, 22), GREEN, lw=1.3, mutation=8)
    arrow(ax, (69, 14.8), (78, 10.5), GRAY, lw=1.05, mutation=7)
    ax.text(76.5, 24.3, "valid", ha="center", fontsize=6.2, color=GREEN)
    ax.text(73.5, 12.3, "no result", ha="center", fontsize=6.2, color=GRAY)
    save(fig, "Figure_2")


def figure_3():
    """Create the human-in-the-loop control loop and compact mode ablation."""
    fig = plt.figure(figsize=(7.2, 5.45), facecolor="white")
    fig.subplots_adjust(left=0.025, right=0.985, bottom=0.035, top=0.985)
    ax = fig.add_subplot(111)
    setup_ax(ax)

    ax.text(2, 97, "(a) Human-in-the-loop teleoperation and parameter injection",
            fontsize=9.2, fontweight="bold", color="#173D73", va="top")
    box(ax, 36, 84, 28, 9, "One-shot $\\Theta(c)$ event from Fig. 2",
        GREEN, LIGHT_GREEN, 7.3, "bold")

    loop_nodes = [
        (2, 12, "Operator"),
        (20, 16, "Omega.7 master\nmotion + gripper input"),
        (43, 18, "Panda + Franka Hand\nmotion / grasp / transport"),
        (68, 14, "Object\ninteraction"),
        (88, 10, "Haptic\nrendering"),
    ]
    for x, w, label in loop_nodes:
        box(ax, x, 60, w, 12, label, BLUE, LIGHT_BLUE, 6.95, "bold")
    for (x, w, _), (nx, _, _) in zip(loop_nodes, loop_nodes[1:]):
        arrow(ax, (x + w, 66), (nx, 66), BLUE, lw=1.25, mutation=8)
    arrow(ax, (93, 60), (8, 60), BLUE, lw=1.25, mutation=8,
          connectionstyle="arc3,rad=-0.22")
    ax.text(50, 49.0, "continuous human control loop: external force + robot/hand state feedback",
            ha="center", va="center", fontsize=6.5, color=BLUE, zorder=5,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.4})

    arrow(ax, (46, 84), (52, 72), GREEN, lw=1.15, style="--", mutation=8)
    arrow(ax, (56, 84), (93, 72), PURPLE, lw=1.15, style="--", mutation=8,
          connectionstyle="arc3,rad=-0.08")
    ax.text(41.5, 76.5, r"$K_t,K_r,\zeta;\ v_g,F_g$", fontsize=6.7, color=GREEN)
    ax.text(76, 78.3, "$K_f,d$", fontsize=6.7, color=PURPLE)
    ax.text(50, 45.5, "The visual event does not gate operator motion.",
            ha="center", fontsize=6.3, color=GRAY)

    ax.text(2, 40.5, "(b) Five-mode ablation matrix", fontsize=9.2,
            fontweight="bold", color="#173D73")
    columns = [
        (2, 8, "Mode"),
        (10, 24, "Information / selection"),
        (34, 21, "Slave impedance\n$K_t,K_r,\\zeta$"),
        (55, 21, "Haptic interface\n$K_f,d$"),
        (76, 22, "Gripper execution\n$v_g,F_g$"),
    ]
    row_h = 5.2
    header_y = 32.7
    for x, w, label in columns:
        ax.add_patch(Rectangle((x, header_y), w, 6.5, linewidth=1.0,
                               edgecolor=BLUE, facecolor="#E4EDF8"))
        ax.text(x + w / 2, header_y + 3.25, label, ha="center", va="center",
                fontsize=6.45, fontweight="bold", color="#173D73")

    rows = [
        ("A", "Fixed parameters", "—", "—", "—", LIGHT_BLUE, BLUE),
        ("B", "Operator-selected", "✓", "✓", "✓", LIGHT_PURPLE, PURPLE),
        ("C", "Vision-semantic", "✓", "✓", "✓", LIGHT_GREEN, GREEN),
        ("D", "Visual cue only", "—", "—", "—", LIGHT_ORANGE, ORANGE),
        ("E", "Vision-semantic", "✓", "—", "—", "#FDEEEE", RED),
    ]
    for r, (mode, source, imp, hap, grip, face, edge) in enumerate(rows):
        y = header_y - (r + 1) * row_h
        values = [mode, source, imp, hap, grip]
        for (x, w, _), value in zip(columns, values):
            fill = face if x in (2, 10) else "white"
            ax.add_patch(Rectangle((x, y), w, row_h, linewidth=0.9,
                                   edgecolor=edge, facecolor=fill))
            ax.text(x + w / 2, y + row_h / 2, value, ha="center", va="center",
                    fontsize=6.7 if x != 10 else 6.45,
                    fontweight="bold" if x == 2 or value == "✓" else "normal",
                    color="#17212B")
    ax.text(66, 3.1,
            "Checks denote strategy-dependent parameter updates; Table 3 gives initialization and fallback details.",
            ha="center", va="center", fontsize=6.25, color=GRAY)
    save(fig, "Figure_3")


if __name__ == "__main__":
    figure_2()
    figure_3()
