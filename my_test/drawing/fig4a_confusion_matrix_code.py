import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.patches import Rectangle

# ============================================================
# Fig. 4(a): Class confusion matrix (simplified)
# ============================================================

# 1. Input and output
CSV_PATH = Path("../data/vision_validation/results/vision_validation_per_image.csv")

# 2. Class order and display labels
CLASS_ORDER = ["apple", "banana", "cup", "bottle", "mouse", "scissors"]
DISPLAY_NAMES = ["Apple", "Banana", "Paper cup", "Bottle", "Mouse", "Scissors"]

# 3. Figure size and export setting
MM_TO_INCH = 1 / 25.4
FIG_SIZE = (180 * MM_TO_INCH, 126 * MM_TO_INCH)
DPI = 300

# 4. Color and font style
BLUE = "#0B3D91"
MID_BLUE = "#1F4E79"
LIGHT_BLUE = "#E8F1FF"
GRID_GRAY = "#D9D9D9"
TEXT_BLACK = "#111111"
LIGHT_GRAY = "#F5F7FA"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 9,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "axes.linewidth": 0.8,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
})


def check_required_columns(df, required_cols):
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def compute_confusion_matrix(df, class_order):
    class_to_idx = {c: i for i, c in enumerate(class_order)}
    cm = np.zeros((len(class_order), len(class_order)), dtype=int)

    for _, row in df.iterrows():
        true_label = row["expected_coco"]
        pred_label = row["predicted_coco"]

        if true_label not in class_to_idx:
            raise ValueError(f"Unknown expected_coco value: {true_label}")
        if pred_label not in class_to_idx:
            raise ValueError(f"Unknown predicted_coco value: {pred_label}")

        i = class_to_idx[true_label]
        j = class_to_idx[pred_label]
        cm[i, j] += 1

    return cm


def plot_fig4a_confusion_matrix(df):
    cm = compute_confusion_matrix(df, CLASS_ORDER)
    n = len(CLASS_ORDER)

    row_totals = cm.sum(axis=1)
    col_totals = cm.sum(axis=0)

    fig, ax = plt.subplots(figsize=FIG_SIZE, dpi=DPI)
    ax.set_axis_off()

    # Compact layout: remove the extra space previously used for text boxes
    ax.set_xlim(-1.85, n + 1.05)
    ax.set_ylim(n + 1.25, -1.65)

    # Sub-figure label (a), centered above matrix
    ax.text(
        (n - 1) / 2, -1.25,
        "(a)",
        ha="center", va="center", fontsize=11, fontweight="bold", color=TEXT_BLACK,
    )
    ax.text(
        (n - 1) / 2, -0.75,
        "Predicted class",
        ha="center", va="center", fontsize=10, color=TEXT_BLACK,
    )
    ax.text(
        -1.47, (n - 1) / 2,
        "True class",
        ha="center", va="center", rotation=90, fontsize=10, color=TEXT_BLACK,
    )

    # Column headers (including "Row total")
    for j, label in enumerate(DISPLAY_NAMES):
        ax.text(j + 0.5, -0.18, label, ha="center", va="center", fontsize=8.5, color=TEXT_BLACK)
    ax.text(n + 0.5, -0.35, "Row\ntotal", ha="center", va="center", fontsize=8.5, color=TEXT_BLACK)

    # Row headers (including "Column total")
    for i, label in enumerate(DISPLAY_NAMES):
        ax.text(-0.20, i + 0.5, label, ha="right", va="center", fontsize=8.5, color=TEXT_BLACK)
    ax.text(-0.20, n + 0.5, "Column total", ha="right", va="center", fontsize=8.5, color=TEXT_BLACK)

    # Draw matrix cells (6×6 + margin row/col)
    for i in range(n + 1):
        for j in range(n + 1):
            if i < n and j < n:
                value = int(cm[i, j])
                facecolor = LIGHT_BLUE if (i == j and value > 0) else "white"
            elif i < n and j == n:
                value = int(row_totals[i])
                facecolor = LIGHT_GRAY
            elif i == n and j < n:
                value = int(col_totals[j])
                facecolor = LIGHT_GRAY
            else:
                value = int(cm.sum())
                facecolor = "#EAEAEA"

            rect = Rectangle((j, i), 1, 1, facecolor=facecolor, edgecolor=GRID_GRAY, linewidth=0.8)
            ax.add_patch(rect)
            ax.text(j + 0.5, i + 0.5, str(value), ha="center", va="center", fontsize=9.5,
                    color=TEXT_BLACK, fontweight="bold" if (i == n or j == n) else "normal")

    ax.add_patch(Rectangle((0, 0), n + 1, n + 1, fill=False, edgecolor=MID_BLUE, linewidth=1.0))

    # Bottom annotation: n=30 per class
    ax.text(
        (n - 1) / 2, n + 0.85,
        "Confusion matrix (n = 30 / class, 180 / 180 correct)",
        ha="center", va="center", fontsize=8.5, color=TEXT_BLACK,
        fontstyle="italic",
    )

    fig.savefig("Fig4_a_confusion_matrix.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    total = int(cm.sum())
    correct = int(np.trace(cm))
    print(f"Total samples: {total}")
    print(f"Correct classifications: {correct}/{total}")
    print(f"Class recognition accuracy: {correct/total:.1%}")
    print("Fig4(a) saved: Fig4_a_confusion_matrix.png")


if __name__ == "__main__":
    df = pd.read_csv(CSV_PATH)
    check_required_columns(df, ["expected_coco", "predicted_coco"])
    plot_fig4a_confusion_matrix(df)