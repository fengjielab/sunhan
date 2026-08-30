"""Generate the pilot schedule plus PILOT02's 12-trial shape supplement."""

from __future__ import annotations

import csv
import random
from collections import Counter
from pathlib import Path


SEED = 260642
SUPPLEMENT_SEED = 260643
CONDITIONS = ["I", "I_H", "I_G", "I_H_G"]
OBJECTS = ["apple", "cup", "mouse"]  # soft, medium, hard representatives
SUPPLEMENTAL_OBJECTS = ["banana", "scissors", "bottle"]
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

    # Preserve the original PILOT01/PILOT02 rows above exactly.  The supplement
    # uses the same repaired code but a distinct schedule ID and second session.
    subject = "PILOT02"
    order = 12
    for supplemental_position, object_id in enumerate(SUPPLEMENTAL_OBJECTS):
        object_position = supplemental_position + 3
        sequence = LATIN[(1 + object_position) % len(LATIN)]
        for condition_position, condition in enumerate(sequence, start=1):
            order += 1
            rows.append({
                "schedule_id": "MECH-D-26-00641-PILOT-SUP-v1-seed260643",
                "seed": SUPPLEMENT_SEED,
                "subject_id": subject,
                "session_id": f"{subject}_S2",
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
    assert len(rows) == 36
    pilot01 = [row for row in rows if row["subject_id"] == "PILOT01"]
    pilot02 = [row for row in rows if row["subject_id"] == "PILOT02"]
    assert len(pilot01) == 12
    assert len(pilot02) == 24
    assert Counter(row["condition"] for row in pilot01) == Counter({key: 3 for key in CONDITIONS})
    assert Counter(row["condition"] for row in pilot02) == Counter({key: 6 for key in CONDITIONS})
    assert Counter(row["object_id"] for row in pilot01) == Counter({key: 4 for key in OBJECTS})
    assert Counter(row["object_id"] for row in pilot02) == Counter({
        key: 4 for key in OBJECTS + SUPPLEMENTAL_OBJECTS
    })
    assert [row["trial_order"] for row in pilot01] == list(range(1, 13))
    assert [row["trial_order"] for row in pilot02] == list(range(1, 25))
    assert Counter(row["session_id"] for row in pilot02) == Counter({
        "PILOT02_S1": 12,
        "PILOT02_S2": 12,
    })


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
