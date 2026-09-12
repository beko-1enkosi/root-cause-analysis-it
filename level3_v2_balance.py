"""Level 3 v2: preserve the proven first 700 ticks, then rebalance hard.

Goals:
- keep the existing 233M ecosystem setup through tick 699;
- stop feeding late-game Oak / Razorgrass / Orange Blossom dominance;
- plant Rose, Lavender and Crystal Cactus heavily in the final 100 ticks;
- add Crimson Vine as a low-risk extra species;
- plant Crimson Vine in adjacent pairs so it is not isolated;
- delay Oak until tick 770 so it remains present without having as much time
  to dominate through shade and seed spread.
"""

import argparse
import json
import random
from collections import Counter
from pathlib import Path


# Original Level 3 regions, left to right.
# Oak, Rose, Ironthorn, Lavender, Orange Blossom,
# Sunflower, Crystal Cactus, Razorgrass, Grass.
SPECIES = (12, 2, 16, 6, 7, 5, 17, 19, 1)

HOST = {
    16: 2,
    7: 6,
    17: 1,
    19: 1,
}

OPENING = (1, 19, 17, 2, 16, 6, 7, 5, 12, 1)

# New species used only in the final balancing phase.
CRIMSON_VINE = 4

ALLOWED = set(SPECIES) | {CRIMSON_VINE}


def prepare(level):
    overrides = {
        (cell["row"], cell["col"]): cell
        for cell in level["cells"]
    }

    suitable = []

    for col in range(level["cols"]):
        for row in range(level["rows"]):
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

    rng = random.Random(20260912)

    for species in SPECIES:
        rng.shuffle(regions[species])

    return regions, set(suitable)


def generate(level):
    if (
        level["rows"],
        level["cols"],
        level["ticks"],
    ) != (150, 150, 800):
        raise ValueError("Expected Level 3: 150 x 150 cells, 800 ticks.")

    regions, suitable = prepare(level)
    pointers = dict.fromkeys(SPECIES, 0)
    actions = []

    # ---------------------------------------------------------------
    # Ticks 0-699: preserve the exact behaviour of the 233,271,319 run.
    # ---------------------------------------------------------------
    for tick in range(700):
        occupied = set()
        plants = []

        for slot in range(20):
            if tick < 120:
                target = OPENING[
                    (tick * 20 + slot) % len(OPENING)
                ]
                species = HOST.get(target, target)
            else:
                target = SPECIES[
                    (tick * 20 + slot) % len(SPECIES)
                ]

                if tick % 2 == 0:
                    species = HOST.get(target, target)
                else:
                    species = target

            # Preserve the successful lesson from Level 2.
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

    # ---------------------------------------------------------------
    # Ticks 700-799: use only cells that the participant schedule has
    # never targeted before. Natural spread can still occupy a cell,
    # but we remove guaranteed self-collisions from our own schedule.
    # ---------------------------------------------------------------
    tails = {
        species: list(regions[species][pointers[species]:])
        for species in SPECIES
    }

    # Exact final-phase allocation across 100 ticks:
    #   Rose       500
    #   Lavender   400
    #   Cactus     200
    #   Grass      100
    #   Crimson    400
    #   Sunflower  370
    #   Oak         30
    # Total       2000
    rose_cells = tails[2][:500]
    tails[2] = tails[2][500:]

    lavender_cells = tails[6][:400]
    tails[6] = tails[6][400:]

    cactus_cells = tails[17][:200]
    tails[17] = tails[17][200:]

    grass_cells = tails[1][:100]
    tails[1] = tails[1][100:]

    sunflower_cells = tails[5][:370]
    tails[5] = tails[5][370:]

    oak_cells = tails[12][:30]
    tails[12] = tails[12][30:]

    if not (
        len(rose_cells) == 500
        and len(lavender_cells) == 400
        and len(cactus_cells) == 200
        and len(grass_cells) == 100
        and len(sunflower_cells) == 370
        and len(oak_cells) == 30
    ):
        raise ValueError("Not enough unused tail cells for final phase.")

    # Crimson Vine dies if isolated. Build 200 disjoint adjacent pairs
    # from the remaining never-targeted cells and plant two pairs/tick.
    available = {
        cell
        for cells in tails.values()
        for cell in cells
    }

    crimson_pairs = []

    for cell in sorted(list(available)):
        if cell not in available:
            continue

        row, col = cell
        neighbours = (
            (row + 1, col),
            (row - 1, col),
            (row, col + 1),
            (row, col - 1),
        )

        partner = next(
            (other for other in neighbours if other in available),
            None,
        )

        if partner is not None:
            crimson_pairs.append((cell, partner))
            available.remove(cell)
            available.remove(partner)

            if len(crimson_pairs) == 200:
                break

    if len(crimson_pairs) < 200:
        raise ValueError("Could not find enough adjacent Crimson Vine pairs.")

    crimson_cells = [
        cell
        for pair in crimson_pairs
        for cell in pair
    ]

    rose_i = 0
    lavender_i = 0
    cactus_i = 0
    grass_i = 0
    crimson_i = 0
    sunflower_i = 0
    oak_i = 0

    for tick in range(700, 800):
        plants = []

        # Five Roses per tick.
        for _ in range(5):
            row, col = rose_cells[rose_i]
            rose_i += 1
            plants.append({
                "plant_index": 2,
                "row": row,
                "col": col,
            })

        # Four Lavender per tick.
        for _ in range(4):
            row, col = lavender_cells[lavender_i]
            lavender_i += 1
            plants.append({
                "plant_index": 6,
                "row": row,
                "col": col,
            })

        # Two Crystal Cactus per tick.
        for _ in range(2):
            row, col = cactus_cells[cactus_i]
            cactus_i += 1
            plants.append({
                "plant_index": 17,
                "row": row,
                "col": col,
            })

        # One Grass per tick: enough support without feeding it 273
        # late placements as the previous strategy did.
        row, col = grass_cells[grass_i]
        grass_i += 1
        plants.append({
            "plant_index": 1,
            "row": row,
            "col": col,
        })

        # Four Crimson Vine per tick, always as two adjacent pairs.
        for _ in range(4):
            row, col = crimson_cells[crimson_i]
            crimson_i += 1
            plants.append({
                "plant_index": CRIMSON_VINE,
                "row": row,
                "col": col,
            })

        # Keep Sunflower direct support. From tick 770 onward, trade
        # one Sunflower slot for one deliberately delayed Oak.
        sunflower_slots = 4 if tick < 770 else 3

        for _ in range(sunflower_slots):
            row, col = sunflower_cells[sunflower_i]
            sunflower_i += 1
            plants.append({
                "plant_index": 5,
                "row": row,
                "col": col,
            })

        if tick >= 770:
            row, col = oak_cells[oak_i]
            oak_i += 1
            plants.append({
                "plant_index": 12,
                "row": row,
                "col": col,
            })

        if len(plants) != 20:
            raise ValueError("Final phase must contain exactly 20 plants.")

        if len({
            (plant["row"], plant["col"])
            for plant in plants
        }) != 20:
            raise ValueError("Duplicate cell inside a tick.")

        actions.append({
            "tick": tick,
            "plants": plants,
        })

    solution = {"actions": actions}
    validate(level, solution, suitable)
    return solution


def validate(level, solution, suitable):
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
                raise ValueError("Invalid or duplicate planting cell.")

            if plant["plant_index"] not in ALLOWED:
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
        default="submissions/level3-v2-balance.json",
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
