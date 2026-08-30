"""Generate the deterministic, balanced 384-trial formal schedule."""

from __future__ import annotations

import csv
import random
from collections import Counter, defaultdict
from pathlib import Path


SEED = 260641
CONDITIONS = ["I", "I_H", "I_G", "I_H_G"]
OBJECTS = ["apple", "banana", "bottle", "cup", "mouse", "scissors"]
LATIN = [
    ["I", "I_H", "I_H_G", "I_G"],
    ["I_H", "I_G", "I", "I_H_G"],
    ["I_G", "I_H_G", "I_H", "I"],
    ["I_H_G", "I", "I_G", "I_H"],
]


def build_rows():
    rows = []
    for subject_number in range(1, 9):
        subject = f"P{subject_number:02d}"
        rng = random.Random(SEED + subject_number)
        objects = OBJECTS.copy()
        rng.shuffle(objects)
        trial_order = 0
        for object_position, object_id in enumerate(objects):
            session = 1 if object_position < 3 else 2
            base = LATIN[(subject_number - 1 + object_position) % len(LATIN)]
            for repetition, sequence in ((1, base), (2, list(reversed(base)))):
                for condition_position, condition in enumerate(sequence, start=1):
                    trial_order += 1
                    rows.append({
                        "schedule_id": "MECH-D-26-00641-ABLATION-v1-seed260641",
                        "seed": SEED,
                        "subject_id": subject,
                        "session_id": f"{subject}_S{session}",
                        "trial_order": trial_order,
                        "object_order": object_position + 1,
                        "object_id": object_id,
                        "repetition": repetition,
                        "condition_position": condition_position,
                        "condition": condition,
                        "trial_id": f"{subject}_T{trial_order:02d}",
                    })
    return rows


def validate(rows):
    assert len(rows) == 384
    by_subject = defaultdict(list)
    for row in rows:
        by_subject[row["subject_id"]].append(row)
    assert set(by_subject) == {f"P{i:02d}" for i in range(1, 9)}
    for subject, subject_rows in by_subject.items():
        assert len(subject_rows) == 48
        assert Counter(row["condition"] for row in subject_rows) == Counter({key: 12 for key in CONDITIONS})
        assert Counter(row["object_id"] for row in subject_rows) == Counter({key: 8 for key in OBJECTS})
        assert set(Counter(row["session_id"] for row in subject_rows).values()) == {24}
        assert [row["trial_order"] for row in subject_rows] == list(range(1, 49))


def main():
    rows = build_rows()
    validate(rows)
    output = Path(__file__).with_name("randomization_schedule.csv")
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote and validated {len(rows)} trials to {output}")


if __name__ == "__main__":
    main()
