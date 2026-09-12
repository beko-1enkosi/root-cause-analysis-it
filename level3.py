"""Level 3: spaced planting, delayed oaks, winter support."""

import argparse
import json
import random
from collections import Counter
from pathlib import Path


# Regions ordered from left to right.
# Oak, Rose, Ironthorn, Lavender, Orange Blossom,
# Sunflower, Crystal Cactus, Razorgrass, Grass.
SPECIES = (12, 2, 16, 6, 7, 5, 17, 19, 1)

# Starter species used while establishing each locked plant's region.
HOST = {
    16: 2,
    7: 6,
    17: 1,
    19: 1,
}


def prepare(level):
    overrides = {
        (cell["row"], cell["col"]): cell
        for cell in level["cells"]
    }

    suitable = []

    for col in range(level["cols"]):
        for row in range(level["rows"]):
            # Omitted cells are treated as default dirt.
            cell = overrides.get((row, col), {})

            if (
                cell.get("terrain", 0) == 0
                and cell.get("soil", 0) in (0, 1)
            ):
                suitable.append((row, col))

    if not suitable:
        raise ValueError("No suitable cells.")

    regions = {species: [] for species in SPECIES}

    for index, cell in enumerate(suitable):
        region = min(
            len(SPECIES) - 1,
            index * len(SPECIES) // len(suitable),
        )
        regions[SPECIES[region]].append(cell)

    # A fixed seed makes the planting order reproducible.
    rng = random.Random(20260912)

    for species in SPECIES:
        rng.shuffle(regions[species])

    if any(len(cells) < 20 for cells in regions.values()):
        raise ValueError("Map is too small for this strategy.")

    return regions, set(suitable)


def generate(level):
    dimensions = (
        level["rows"],
        level["cols"],
        level["ticks"],
    )

    if dimensions != (150, 150, 800):
        raise ValueError(
            "Expected Level 3: 150 x 150 cells, 800 ticks."
        )

    regions, suitable = prepare(level)
    pointers = dict.fromkeys(SPECIES, 0)
    actions = []

    # Prioritise grass and roses during establishment.
    opening = (1, 19, 17, 2, 16, 6, 7, 5, 12, 1)

    # Roses and lavender cannot spread during winter.
    winter = (2, 6, 2, 6, 12, 5, 16, 7, 17, 19, 1)

    for tick in range(level["ticks"]):
        occupied = set()
        plants = []

        for slot in range(20):
            if tick < 120:
                target = opening[
                    (tick * 20 + slot) % len(opening)
                ]
                species = HOST.get(target, target)

            elif tick < 700:
                target = SPECIES[
                    (tick * 20 + slot) % len(SPECIES)
                ]

                # Alternate starter support and unlock attempts.
                if tick % 2 == 0:
                    species = HOST.get(target, target)
                else:
                    species = target

            else:
                target = winter[
                    (tick * 20 + slot) % len(winter)
                ]

                # Keep some starter support during final winter.
                if tick % 4 == 0:
                    species = HOST.get(target, target)
                else:
                    species = target

            # Apply the lesson from the improved Level 2.
            if species == 12 and tick < 750:
                species = 2

            cells = regions[target]
            position = pointers[target] % len(cells)

            while cells[position] in occupied:
                pointers[target] += 1
                position = pointers[target] % len(cells)

            row, col = cells[position]
            pointers[target] += 1
            occupied.add((row, col))

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


def validate(level, solution, suitable):
    """Check instructions, not survival or unlock success."""
    seen_ticks = set()

    for action in solution["actions"]:
        tick = action["tick"]

        if (
            type(tick) is not int
            or not 0 <= tick < level["ticks"]
            or tick in seen_ticks
        ):
            raise ValueError("Invalid or repeated tick.")

        seen_ticks.add(tick)

        if len(action["plants"]) > 20:
            raise ValueError("Too many plants in one tick.")

        used = set()

        for plant in action["plants"]:
            cell = (plant["row"], plant["col"])

            if cell not in suitable or cell in used:
                raise ValueError(
                    "Invalid or duplicate planting cell."
                )

            if plant["plant_index"] not in SPECIES:
                raise ValueError("Unknown plant.")

            used.add(cell)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "level",
        nargs="?",
        default="data/levels/3.json",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="submissions/level3.json",
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