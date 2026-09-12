"""Generate a deterministic planting schedule for Level 2."""

import argparse
import json
from collections import Counter
from pathlib import Path


# Ordered left-to-right across the grid's columns. Grass and Rose Bush sit
# together at one edge, insulated by a Dwarf Sunflower buffer band from the
# Oak Tree / Lavender edge on the other side (where Orange Blossom gets
# seeded and explodes outward, invasiveness_rank 7 with spread_range 4).
# This keeps the two species we need coverage thresholds for (Grass >= 5%,
# Rose Bush >= 4%, to unlock Razorgrass and Ironthorn Shrub) as far as
# possible from the map's most invasive species.
STARTERS = (1, 2, 5, 12, 6)  # Grass | Rose Bush | Dwarf Sunflower | Oak Tree | Lavender

# 300 days x 18 starter slots / 5 species = 1080 guaranteed placements per
# species across the whole game. A region smaller than that makes the
# placement pointer wrap around and re-plant cells instead of reaching
# fresh ones, so every region needs at least this many cells. Anything
# above that 5x1080 floor goes entirely to Grass and Rose Bush, since those
# are the two species gating the Razorgrass / Ironthorn Shrub unlocks.
REGION_FLOOR = 1080
BOOST_SPECIES = (1, 2)  # Grass, Rose Bush split all the surplus cells.

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

    total = len(suitable)
    slack = total - REGION_FLOOR * len(STARTERS)

    if slack < 0:
        raise ValueError("Not enough suitable cells for this map.")

    sizes = {species: REGION_FLOOR for species in STARTERS}
    boost_each, remainder = divmod(slack, len(BOOST_SPECIES))
    for species in BOOST_SPECIES:
        sizes[species] += boost_each
    sizes[BOOST_SPECIES[0]] += remainder  # keep the total exact

    regions = {}
    start = 0
    for species in STARTERS:
        end = start + sizes[species]
        regions[species] = suitable[start:end]
        start = end

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

            # Suppress Oak Tree for the first two waves so it can't spread
            # across the map before Grass/Rose Bush coverage is established;
            # channel that quota into extra Rose Bush coverage instead (a
            # cell's species only affects the global coverage count, not
            # its location, so this tops up Rose Bush's percentage without
            # any added invasion exposure). Oak only plants for real in the
            # final wave (tick >= 400), giving it a contained ~100-tick
            # window to mature and spread.
            if tick < 400:
                for plant in plants:
                    if plant["plant_index"] == 12:
                        plant["plant_index"] = 2

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