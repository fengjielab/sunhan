from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

BUNDLE_ROOT = Path(__file__).resolve().parents[2]

from Fig5_combined_final_helper import (
    draw_nasa_panel,
    draw_success_panel,
    load_nasa_data,
    operator_legend_handles,
    save_figure,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Fig. 7: workload and observed task success across five modes."
    )
    parser.add_argument("--nasa-file", type=Path, default=BUNDLE_ROOT / "04_nasa_tlx" / "nasa_tlx_results" / "nasa.md")
    parser.add_argument("--output-dir", type=Path, default=BUNDLE_ROOT / "reproduced_figures")
    parser.add_argument("--dpi", type=int, default=600)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    nasa = load_nasa_data(args.nasa_file)

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.25))
    draw_nasa_panel(axes[0], nasa, panel_tag="(a)")
    draw_success_panel(axes[1], panel_tag="(b)")

    fig.legend(
        handles=operator_legend_handles(),
        loc="upper center",
        ncol=3,
        frameon=False,
        fontsize=8,
        handletextpad=0.45,
        columnspacing=1.6,
        bbox_to_anchor=(0.5, 0.995),
    )
    fig.subplots_adjust(left=0.095, right=0.985, bottom=0.17, top=0.84, wspace=0.30)

    save_figure(fig, args.output_dir, "Fig7_workload_success_final", args.dpi)
    plt.close(fig)
    print(f"Saved Fig. 7 to: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
