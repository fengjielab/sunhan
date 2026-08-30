"""Create participant-level and phase-wise figures from the frozen trial table."""

from __future__ import annotations

import argparse
from pathlib import Path


ORDER = ["I", "I_H", "I_G", "I_H_G"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trial_table", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    frame = pd.read_csv(args.trial_table)
    if frame.empty:
        raise SystemExit("Trial table is empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    participant = frame.groupby(
        ["subject_id", "condition"], as_index=False
    )["penalized_time_s"].mean()
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for subject, group in participant.groupby("subject_id"):
        values = group.set_index("condition")["penalized_time_s"].reindex(ORDER)
        ax.plot(ORDER, values, marker="o", alpha=0.65, linewidth=1, label=subject)
    ax.set_ylabel("Participant mean penalized time (s)")
    ax.set_xlabel("Ablation condition")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(ncol=2, fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(args.output_dir / "participant_condition_times.pdf")
    fig.savefig(args.output_dir / "participant_condition_times.png", dpi=300)
    plt.close(fig)

    phases = ["approach_time_s", "grasp_time_s", "transport_time_s", "release_time_s"]
    completed = frame[frame["success"] == 1]
    subject_phase = completed.groupby(
        ["subject_id", "condition"], as_index=False
    )[phases].mean()
    means = subject_phase.groupby("condition")[phases].mean().reindex(ORDER)
    sems = subject_phase.groupby("condition")[phases].sem().reindex(ORDER)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    x = np.arange(len(ORDER))
    width = 0.19
    for index, phase in enumerate(phases):
        ax.bar(
            x + (index - 1.5) * width, means[phase], width,
            yerr=sems[phase], capsize=2, label=phase.replace("_time_s", ""),
        )
    ax.set_xticks(x, ORDER)
    ax.set_ylabel("Mean phase duration (s)")
    ax.set_xlabel("Ablation condition")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(args.output_dir / "phase_times.pdf")
    fig.savefig(args.output_dir / "phase_times.png", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    main()
