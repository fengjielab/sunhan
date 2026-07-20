"""Generate Fig. 3: object-conditioned cross-channel system architecture."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


NAVY = "#174A7E"
BLUE_FILL = "#EAF2F8"
GREEN = "#2E8B57"
GREEN_FILL = "#EAF7EF"
GREY = "#5C6873"


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Generate Fig. 3 system architecture.")
    parser.add_argument("--output-dir", type=Path, default=here / "outputs" / "fig3_system_workflow")
    parser.add_argument("--dpi", type=int, default=600)
    return parser.parse_args()


def box(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    edge: str = NAVY,
    fill: str = BLUE_FILL,
    fontsize: float = 8.0,
    weight: str = "normal",
    lw: float = 1.1,
) -> None:
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.25,rounding_size=0.72",
            linewidth=lw,
            edgecolor=edge,
            facecolor=fill,
            zorder=2,
        )
    )
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color="#17232D",
            fontsize=fontsize, fontweight=weight, linespacing=1.08, zorder=3)


def frame(ax: plt.Axes, x: float, y: float, w: float, h: float, label: str) -> None:
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.34,rounding_size=1.0",
            linewidth=1.15,
            edgecolor=NAVY,
            facecolor="none",
            zorder=0,
        )
    )
    ax.text(x + 1.5, y + h - 2.1, label, ha="left", va="center", color=NAVY,
            fontsize=9.3, fontweight="bold", fontstyle="italic", zorder=1)


def arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = NAVY,
    dashed: bool = False,
    lw: float = 1.15,
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start, end,
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=lw,
            linestyle=(0, (3, 2)) if dashed else "solid",
            color=color,
            connectionstyle="arc3,rad=0",
            shrinkA=1.5,
            shrinkB=1.5,
            zorder=1,
        )
    )


def elbow_arrow(
    ax: plt.Axes,
    points: list[tuple[float, float]],
    *,
    color: str = NAVY,
    dashed: bool = False,
    lw: float = 1.1,
) -> None:
    """Draw an orthogonal connector with an arrowhead on its final segment."""
    xs, ys = zip(*points)
    ax.plot(xs, ys, color=color, linewidth=lw,
            linestyle=(0, (3, 2)) if dashed else "solid", zorder=1)
    arrow(ax, points[-2], points[-1], color=color, dashed=dashed, lw=lw)


def main() -> None:
    args = parse_args()
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )

    fig, ax = plt.subplots(figsize=(7.2, 4.05))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 77)
    ax.axis("off")

    ax.text(3, 75.0, "Object-conditioned cross-channel reconfiguration architecture",
            ha="left", va="center", fontsize=11.0, fontweight="bold", color="#111820")

    # Low-rate visual path.  Bounded queues expose exactly how inference is
    # decoupled from the supervisory control loop.
    frame(ax, 3, 55, 94, 17.5, "Asynchronous perception thread (15 fps)")
    box(ax, 5, 58.2, 13, 8.1, "D435i camera\nRGB frames", fontsize=7.6, weight="bold")
    box(ax, 22, 58.2, 13, 8.1, "Single-slot\nframe queue", fontsize=7.5, weight="bold")
    box(ax, 39, 58.2, 13, 8.1, "Independent\nYOLO11n worker", fontsize=7.4, weight="bold")
    box(ax, 56, 58.2, 13, 8.1, "Class +\nconfidence", fontsize=7.6, weight="bold")
    box(ax, 73, 58.2, 19, 8.1, "Two-slot latest-result queue\n(class, confidence)", fontsize=6.9, weight="bold")
    for start, end in [((18, 62.25), (22, 62.25)), ((35, 62.25), (39, 62.25)), ((52, 62.25), (56, 62.25)), ((69, 62.25), (73, 62.25))]:
        arrow(ax, start, end, color=NAVY, dashed=True)

    # The scheduler differentiates valid mappings from the two documented
    # fallback cases.  It deliberately makes no pre-contact timing claim.
    box(ax, 30, 43.2, 39, 7.3,
        "One-shot parameter scheduler\nfirst valid result: $p \\geq 0.25$; class $\\rightarrow$ strategy $\\rightarrow \\Theta(c)$; lock for trial",
        edge=GREEN, fill=GREEN_FILL, fontsize=7.0, weight="bold")
    elbow_arrow(ax, [(82.5, 58.2), (82.5, 53.2), (49.5, 53.2), (49.5, 50.5)],
                color=GREEN, dashed=True)
    ax.text(68.5, 54.0, "non-blocking poll every 5 ms", ha="center", va="bottom",
            fontsize=6.1, color=GREEN,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.2})
    box(ax, 73, 45.5, 21, 4.3, "No result or $p<0.25$:\nretain initial $\\Theta_0$",
        edge=GREY, fill="#F7F9FA", fontsize=6.0)
    box(ax, 73, 39.6, 21, 4.3, "Detected but unmapped:\nbalanced default strategy",
        edge=GREY, fill="#F7F9FA", fontsize=6.0)
    elbow_arrow(ax, [(82.5, 58.2), (82.5, 49.8), (73, 49.8)], color=GREY, dashed=True, lw=0.9)
    elbow_arrow(ax, [(82.5, 58.2), (82.5, 43.9), (73, 43.9)], color=GREY, dashed=True, lw=0.9)

    # The coordinated parameter bundle fans out to the three physical channels.
    box(ax, 12, 31.0, 20, 6.2, "Haptic-interface channel\n$K_f, d$", edge=GREEN,
        fill=GREEN_FILL, fontsize=7.4, weight="bold")
    box(ax, 40, 31.0, 20, 6.2, "Slave-side impedance channel\n$K_t, K_r, \\zeta$", edge=GREEN,
        fill=GREEN_FILL, fontsize=7.2, weight="bold")
    box(ax, 68, 31.0, 20, 6.2, "Gripper-execution channel\n$v_g, F_g$", edge=GREEN,
        fill=GREEN_FILL, fontsize=7.4, weight="bold")
    ax.text(50, 40.8, "enabled channels only (Table 3)", ha="center", va="center", fontsize=6.3, color=GREEN,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.15})
    elbow_arrow(ax, [(49.5, 43.2), (49.5, 39.5), (22, 39.5), (22, 37.2)], color=GREEN, dashed=True, lw=1.0)
    elbow_arrow(ax, [(49.5, 43.2), (49.5, 37.2)], color=GREEN, dashed=True, lw=1.0)
    elbow_arrow(ax, [(49.5, 43.2), (49.5, 39.5), (78, 39.5), (78, 37.2)], color=GREEN, dashed=True, lw=1.0)

    # Continuous human loop remains independent of inference completion.
    frame(ax, 3, 4, 94, 23.4, "Human-in-the-loop teleoperation supervisor (nominal 200 Hz)")
    box(ax, 6, 10.2, 12, 8.0, "Operator", fontsize=8.2, weight="bold")
    box(ax, 24, 10.2, 18, 8.0, "Omega.7 master\nmotion + gripper input", fontsize=7.4, weight="bold")
    box(ax, 50, 10.2, 20, 8.0, "Panda + Franka Hand\nimpedance / grasp / transport", fontsize=7.2, weight="bold")
    box(ax, 79, 10.2, 15, 8.0, "Object\nworkspace", fontsize=8.0, weight="bold")
    arrow(ax, (18, 14.2), (24, 14.2), color=NAVY, lw=1.3)
    arrow(ax, (42, 14.2), (50, 14.2), color=NAVY, lw=1.3)
    arrow(ax, (70, 14.2), (79, 14.2), color=NAVY, lw=1.3)
    ax.text(21, 20.0, "operator command", ha="center", va="bottom", fontsize=6.4, color=NAVY)
    ax.text(46, 20.0, "robot command", ha="center", va="bottom", fontsize=6.4, color=NAVY)
    ax.plot([86.5, 86.5, 12, 12], [10.2, 6.8, 6.8, 10.2], color=NAVY, linewidth=1.1, zorder=1)
    arrow(ax, (12, 6.8), (12, 10.2), color=NAVY, lw=1.1)
    ax.text(49, 5.6, "continuous force and robot/hand-state feedback", ha="center", va="center",
            fontsize=7.0, color=NAVY)

    # Parameter injections reach their enabled subsystems without stopping control.
    elbow_arrow(ax, [(22, 31.0), (22, 24.7), (33, 24.7), (33, 18.2)], color=GREEN, dashed=True, lw=1.0)
    elbow_arrow(ax, [(50, 31.0), (50, 24.7), (60, 24.7), (60, 18.2)], color=GREEN, dashed=True, lw=1.0)
    elbow_arrow(ax, [(78, 31.0), (78, 24.7), (64, 24.7), (64, 18.2)], color=GREEN, dashed=True, lw=1.0)
    ax.text(95.5, 23.7, "Visual inference does not\ngate operator motion.", ha="right", va="center",
            fontsize=6.8, color=GREY, linespacing=1.1)
    ax.text(50, 1.2, "Dashed green: asynchronous perception and one-shot updates; solid blue: continuous teleoperation.",
            ha="center", va="bottom", fontsize=6.6, color=GREY)

    fig.subplots_adjust(left=0.02, right=0.985, bottom=0.02, top=0.98)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.output_dir / "Fig3_system_workflow"
    fig.savefig(stem.with_suffix(".png"), dpi=args.dpi, facecolor="white")
    fig.savefig(stem.with_suffix(".pdf"), facecolor="white")
    fig.savefig(stem.with_suffix(".svg"), facecolor="white")
    plt.close(fig)
    print(f"Saved Fig. 3 to: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
