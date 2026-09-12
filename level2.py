"""Generate a deterministic planting schedule for Level 2."""

import argparse
import json
from collections import Counter
from pathlib import Path


# Oak, Rose Bush, Lavender, Dwarf Sunflower, Grass.
STARTERS = (12, 2, 6, 5, 1)

# Orange Blossom, Razorgrass, Ironthorn Shrub.
UNLOCK_ATTEMPTS = (7, 19, 16)


def make_regions(level):
    overrides = {}

    for cell in level["cells"]:
        location = (cell["row"], cell["col"])
        overrides[location] = cell

    suitable = []

    # Assumption: omitted cells are default dirt soil.
    for col in range(level["cols"]):
        for row in range(level["rows"]):
            cell = overrides.get((row, col), {})

            if (
                cell.get("terrain", 0) == 0
                and cell.get("soil", 0) in (0, 1)
            ):
                suitable.append((row, col))

    regions = {plant: [] for plant in STARTERS}

    # Divide suitable cells into five vertical regions.
    for index, cell in enumerate(suitable):
        region_index = min(4, index * 5 // len(suitable))
        species = STARTERS[region_index]
        regions[species].append(cell)

    # Plant spaced positions before filling their neighbours.
    def spacing_key(cell):
        row, col = cell
        return (row % 3, col % 3, row // 3, col // 3)

    for cells in regions.values():
        cells.sort(key=spacing_key)

    if any(len(cells) < 1080 for cells in regions.values()):
        raise ValueError(
            "This strategy is sized for the supplied Level 2 map."
        )

    return regions, set(suitable)


def generate(level):
    dimensions = (
        level["rows"],
        level["cols"],
        level["ticks"],
    )

    if dimensions != (70, 100, 500):
        raise ValueError(
            "Use this script only for Level 2: 70 x 100, 500 ticks."
        )

    regions, suitable = make_regions(level)
    pointers = dict.fromkeys(STARTERS, 0)
    actions = []

    for wave_start in (0, 200, 400):
        for day in range(100):
            tick = wave_start + day
            plants = []
            occupied = set()

            # Eighteen placements use unlocked starter species.
            for slot in range(18):
                species = STARTERS[(day * 18 + slot) % 5]
                cells = regions[species]

                position = pointers[species] % len(cells)
                row, col = cells[position]
                pointers[species] += 1

                plants.append({
                    "plant_index": species,
                    "row": row,
                    "col": col,
                })
                occupied.add((row, col))

            # Two additional placements attempt useful unlocks.
            # The simulator ignores them if conditions are unmet.
            for extra in range(2):
                if tick >= 40:
                    species = UNLOCK_ATTEMPTS[
                        (day * 2 + extra) % 3
                    ]
                else:
                    species = STARTERS[(day + extra) % 5]

                # Place each attempted species in a suitable region.
                host_regions = {
                    7: 6,    # Orange Blossom: lavender region.
                    19: 1,   # Razorgrass: grass region.
                    16: 2,   # Ironthorn: rose region.
                }
                host = host_regions.get(species, species)
                cells = regions[host]

                position = (
                    len(cells) - 1 - tick * 2 - extra
                ) % len(cells)

                while cells[position] in occupied:
                    position = (position - 1) % len(cells)

                row, col = cells[position]

                plants.append({
                    "plant_index": species,
                    "row": row,
                    "col": col,
                })
                occupied.add((row, col))

            actions.append({
                "tick": tick,
                "plants": plants,
            })

    result = {"actions": actions}
    check(level, result, suitable)
    return result


def check(level, result, suitable):
    """Check instructions, not simulated survival or unlocks."""
    seen_ticks = set()

    for action in result["actions"]:
        tick = action["tick"]

        if tick in seen_ticks or not 0 <= tick < level["ticks"]:
            raise ValueError("Invalid or duplicate tick.")

        seen_ticks.add(tick)

        if len(action["plants"]) > 20:
            raise ValueError("More than 20 placements in one tick.")

        locations = set()

        for plant in action["plants"]:
            cell = (plant["row"], plant["col"])

            if cell not in suitable or cell in locations:
                raise ValueError("Unsuitable or duplicate cell.")

            if plant["plant_index"] not in (
                STARTERS + UNLOCK_ATTEMPTS
            ):
                raise ValueError("Unknown species.")

            locations.add(cell)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "level",
        nargs="?",
        default="data/levels/2.json",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="submissions/level2.json",
    )
    args = parser.parse_args()

    level = json.loads(
        Path(args.level).read_text(encoding="utf-8")
    )
    result = generate(level)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )

    counts = Counter(
        plant["plant_index"]
        for action in result["actions"]
        for plant in action["plants"]
    )

    print(
        f"Saved {sum(counts.values())} scheduled placements "
        f"to {output}"
    )
    print("Scheduled counts (not final survivors):", dict(counts))


if __name__ == "__main__":
    main()