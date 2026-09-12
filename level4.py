"""Level 4 baseline using Level 3's shared helpers."""

import argparse
import json
from collections import Counter
from pathlib import Path

from level3 import HOST, SPECIES, prepare, validate


def generate(level):
    dimensions = (
        level["rows"],
        level["cols"],
        level["ticks"],
    )

    if dimensions != (200, 300, 800):
        raise ValueError(
            "Expected Level 4: 200 rows, 300 columns, 800 ticks."
        )

    regions, suitable = prepare(level)
    pointers = dict.fromkeys(SPECIES, 0)

    # Establish grass, roses, and other starter plants first.
    opening = (1, 19, 17, 2, 16, 6, 7, 5, 12, 1)

    # Directly support roses and lavender during winter.
    winter = (2, 6, 2, 6, 12, 5, 16, 7, 17, 19, 1)

    actions = []

    for tick in range(level["ticks"]):
        plants = []
        used = set()

        for slot in range(20):
            if tick < 200:
                target = opening[
                    (tick * 20 + slot) % len(opening)
                ]
                species = HOST.get(target, target)

            elif tick < 700:
                target = SPECIES[
                    (tick * 20 + slot) % len(SPECIES)
                ]

                if tick % 2 == 0:
                    species = HOST.get(target, target)
                else:
                    species = target

            else:
                target = winter[
                    (tick * 20 + slot) % len(winter)
                ]

                if tick % 4 == 0:
                    species = HOST.get(target, target)
                else:
                    species = target

            # Avoid giving oaks hundreds of ticks to dominate.
            if species == 12 and tick < 750:
                species = 2

            cells = regions[target]
            position = pointers[target] % len(cells)

            while cells[position] in used:
                pointers[target] += 1
                position = pointers[target] % len(cells)

            row, col = cells[position]
            pointers[target] += 1
            used.add((row, col))

            plants.append({
                "plant_index": species,
                "row": row,
                "col": col,
            })

        actions.append({
            "tick": tick,
            "plants": plants,
        })

    solution = {"actions": actions}
    validate(level, solution, suitable)
    return solution


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "level",
        nargs="?",
        default="data/levels/4.json",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="submissions/level4.json",
    )
    args = parser.parse_args()

    level = json.loads(
        Path(args.level).read_text(encoding="utf-8")
    )
    solution = generate(level)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(solution, indent=2) + "\n",
        encoding="utf-8",
    )

    counts = Counter(
        plant["plant_index"]
        for action in solution["actions"]
        for plant in action["plants"]
    )

    print(
        f"Saved {sum(counts.values())} scheduled placements "
        f"to {output}"
    )
    print("Scheduled counts, not final survivors:", dict(counts))


if __name__ == "__main__":
    main()