"""Level 4 v3.

Preserve the proven 237M strategy through tick 699.

For the final 100 ticks, stop feeding the dominant species
(Oak, Orange Blossom and Razorgrass) and directly reinforce
the weak survivors instead.
"""

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

    # ==========================================================
    # ORIGINAL OPENING
    #
    # Do not change this.
    # ==========================================================

    opening = (
        1, 19, 17, 2, 16,
        6, 7, 5, 12, 1
    )

    # ==========================================================
    # NEW FINAL-100-TICK DISTRIBUTION
    #
    # Exactly 20 entries:
    #
    # Rose              8 / tick = 800
    # Lavender          6 / tick = 600
    # Sunflower         3 / tick = 300
    # Crystal Cactus    2 / tick = 200
    # Grass             1 / tick = 100
    #
    # NO:
    # Oak
    # Orange Blossom
    # Razorgrass
    # Ironthorn
    #
    # Those already have an established ecosystem by tick 700.
    # ==========================================================

    final_balance = (
        2, 2, 2, 2,
        2, 2, 2, 2,

        6, 6, 6,
        6, 6, 6,

        5, 5, 5,

        17, 17,

        1,
    )

    actions = []

    for tick in range(level["ticks"]):
        plants = []
        used = set()

        for slot in range(20):

            # ==================================================
            # TICKS 0-199
            # EXACTLY the original strategy.
            # ==================================================

            if tick < 200:
                target = opening[
                    (tick * 20 + slot)
                    % len(opening)
                ]

                species = HOST.get(
                    target,
                    target,
                )

            # ==================================================
            # TICKS 200-699
            # EXACTLY the original 237M strategy.
            # ==================================================

            elif tick < 700:
                target = SPECIES[
                    (tick * 20 + slot)
                    % len(SPECIES)
                ]

                if tick % 2 == 0:
                    species = HOST.get(
                        target,
                        target,
                    )
                else:
                    species = target

            # ==================================================
            # TICKS 700-799
            #
            # New controlled rebalancing phase.
            #
            # Since final_balance contains exactly 20 items,
            # each tick gets the same deliberate allocation.
            # ==================================================

            else:
                target = final_balance[slot]
                species = target

            # ==================================================
            # ORIGINAL OAK SAFETY RULE
            #
            # Keep this because it preserves ticks 0-699.
            # There are no Oaks in our new final phase anyway.
            # ==================================================

            if species == 12 and tick < 750:
                species = 2

            # ==================================================
            # Choose next cell from that species' existing region.
            # ==================================================

            cells = regions[target]

            position = (
                pointers[target]
                % len(cells)
            )

            while cells[position] in used:
                pointers[target] += 1

                position = (
                    pointers[target]
                    % len(cells)
                )

            row, col = cells[position]

            pointers[target] += 1

            used.add(
                (row, col)
            )

            plants.append({
                "plant_index": species,
                "row": row,
                "col": col,
            })

        actions.append({
            "tick": tick,
            "plants": plants,
        })

    solution = {
        "actions": actions
    }

    validate(
        level,
        solution,
        suitable,
    )

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
        default="submissions/level4-v3.json",
    )

    args = parser.parse_args()

    level = json.loads(
        Path(args.level).read_text(
            encoding="utf-8"
        )
    )

    solution = generate(level)

    output = Path(args.output)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            solution,
            indent=2
        ) + "\n",
        encoding="utf-8",
    )

    counts = Counter(
        plant["plant_index"]
        for action in solution["actions"]
        for plant in action["plants"]
    )

    print(
        f"Saved {sum(counts.values())} "
        f"scheduled placements to {output}"
    )

    print(
        "Scheduled counts:",
        dict(sorted(counts.items()))
    )


if __name__ == "__main__":
    main()