"""Generate the separate 24-trial pilot schedule (12 trials per pilot operator)."""

from __future__ import annotations

import csv
import random
from collections import Counter
from pathlib import Path


SEED = 260642
CONDITIONS = ["I", "I_H", "I_G", "I_H_G"]
OBJECTS = ["apple", "cup", "mouse"]  # soft, medium, hard representatives
LATIN = [
    ["I", "I_H", "I_H_G", "I_G"],
    ["I_H", "I_G", "I", "I_H_G"],
    ["I_G", "I_H_G", "I_H", "I"],
    ["I_H_G", "I", "I_G", "I_H"],
]


def build_rows():
    rows = []
    for pilot_number in (1, 2):
        subject = f"PILOT{pilot_number:02d}"
        objects = OBJECTS.copy()
        random.Random(SEED + pilot_number).shuffle(objects)
        order = 0
        for object_position, object_id in enumerate(objects):
            sequence = LATIN[(pilot_number - 1 + object_position) % len(LATIN)]
            for condition_position, condition in enumerate(sequence, start=1):
                order += 1
                rows.append({
                    "schedule_id": "MECH-D-26-00641-PILOT-v1-seed260642",
                    "seed": SEED,
                    "subject_id": subject,
                    "session_id": f"{subject}_S1",
                    "trial_order": order,
                    "object_order": object_position + 1,
                    "object_id": object_id,
                    "repetition": 1,
                    "condition_position": condition_position,
                    "condition": condition,
                    "trial_id": f"{subject}_T{order:02d}",
                })
    return rows


def validate(rows):
    assert len(rows) == 24
    for subject in ("PILOT01", "PILOT02"):
        selected = [row for row in rows if row["subject_id"] == subject]
        assert len(selected) == 12
        assert Counter(row["condition"] for row in selected) == Counter({key: 3 for key in CONDITIONS})
        assert Counter(row["object_id"] for row in selected) == Counter({key: 4 for key in OBJECTS})
        assert [row["trial_order"] for row in selected] == list(range(1, 13))


def main():
    rows = build_rows()
    validate(rows)
    output = Path(__file__).with_name("pilot_schedule.csv")
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote and validated {len(rows)} pilot trials to {output}")


if __name__ == "__main__":
    main()
