"""Level 3 v3: unlock Blue Moss, suppress Oak, maximise diversity."""

import argparse
import json
import random
from collections import Counter
from pathlib import Path


# Original Level 3 species/regions.
SPECIES = (12, 2, 16, 6, 7, 5, 17, 19, 1)

HOST = {
    16: 2,
    7: 6,
    17: 1,
    19: 1,
}

OPENING = (1, 19, 17, 2, 16, 6, 7, 5, 12, 1)

BLUE_MOSS = 3
CRIMSON_VINE = 4

ALLOWED = set(SPECIES) | {BLUE_MOSS, CRIMSON_VINE}


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

    regions = {species: [] for species in SPECIES}

    for index, cell in enumerate(suitable):
        region_index = min(
            len(SPECIES) - 1,
            index * len(SPECIES) // len(suitable),
        )

        regions[SPECIES[region_index]].append(cell)

    rng = random.Random(20260912)

    for species in SPECIES:
        rng.shuffle(regions[species])

    return regions, suitable


def generate(level):
    if (
        level["rows"],
        level["cols"],
        level["ticks"],
    ) != (150, 150, 800):
        raise ValueError(
            "Expected Level 3: 150 x 150, 800 ticks."
        )

    regions, suitable = prepare(level)

    pointers = dict.fromkeys(SPECIES, 0)

    actions = []
    scheduled = set()

    # ==========================================================
    # PHASE 1
    # Ticks 0-599:
    # Preserve the behaviour that already gave us 252M.
    # ==========================================================

    for tick in range(600):
        plants = []
        used = set()

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

            # Do not allow Oak to establish early.
            if species == 12:
                species = 2

            cells = regions[target]

            position = pointers[target] % len(cells)

            while cells[position] in used:
                pointers[target] += 1
                position = pointers[target] % len(cells)

            row, col = cells[position]

            pointers[target] += 1

            used.add((row, col))
            scheduled.add((row, col))

            plants.append({
                "plant_index": species,
                "row": row,
                "col": col,
            })

        actions.append({
            "tick": tick,
            "plants": plants,
        })

    # ==========================================================
    # Build a pool of cells WE have never scheduled before.
    #
    # This does not prevent natural spread from occupying them,
    # but guarantees we never issue the same coordinate twice.
    # ==========================================================

    fresh = [
        cell
        for cell in suitable
        if cell not in scheduled
    ]

    # ==========================================================
    # Reserve sparse cells for Blue Moss.
    #
    # Blue Moss dies when it has >4 neighbours.
    # row % 3 == 0 and col % 3 == 0 keeps our Blue Moss
    # placements separated from each other.
    # ==========================================================

    blue_cells = [
        cell
        for cell in fresh
        if cell[0] % 3 == 0
        and cell[1] % 3 == 0
    ][:640]

    if len(blue_cells) < 640:
        raise ValueError("Not enough spaced Blue Moss cells.")

    blue_set = set(blue_cells)

    available = set(fresh) - blue_set

    # ==========================================================
    # Reserve 79 adjacent Crimson Vine pairs.
    #
    # Crimson Vine dies if isolated, so every placement gets
    # an adjacent partner in the SAME tick.
    # ==========================================================

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

        partner = None

        for other in neighbours:
            if other in available:
                partner = other
                break

        if partner is not None:

            crimson_pairs.append((cell, partner))

            available.remove(cell)
            available.remove(partner)

            if len(crimson_pairs) == 79:
                break

    if len(crimson_pairs) < 79:
        raise ValueError(
            "Could not find enough Crimson Vine pairs."
        )

    crimson_cells = []

    for pair in crimson_pairs:
        crimson_cells.append(pair[0])
        crimson_cells.append(pair[1])

    # ==========================================================
    # Remaining unique cells for normal plants.
    # ==========================================================

    general = list(available)

    random.Random(20260913).shuffle(general)

    iterator = iter(general)

    # Final 200 ticks allocation:
    #
    # Rose       1720
    # Grass       481
    # Sunflower   500
    # Cactus      500
    # Blue Moss   640
    # Crimson     158
    # Oak           1
    #
    # Total       4000

    rose_cells = [
        next(iterator)
        for _ in range(1720)
    ]

    grass_cells = [
        next(iterator)
        for _ in range(481)
    ]

    sunflower_cells = [
        next(iterator)
        for _ in range(500)
    ]

    cactus_cells = [
        next(iterator)
        for _ in range(500)
    ]

    oak_cell = next(iterator)

    rose_i = 0
    grass_i = 0
    sunflower_i = 0
    cactus_i = 0
    blue_i = 0
    crimson_i = 0

    # ==========================================================
    # PHASE 2
    # Ticks 600-699 = Autumn
    #
    # MASSIVE ROSE BOOST.
    #
    # Rose can still spread in Autumn.
    # Goal: push Rose above 1% coverage BEFORE Winter,
    # which is the missing Blue Moss condition.
    # ==========================================================

    for tick in range(600, 700):

        plants = []

        # 12 Rose
        for _ in range(12):

            row, col = rose_cells[rose_i]
            rose_i += 1

            plants.append({
                "plant_index": 2,
                "row": row,
                "col": col,
            })

        # 4 Grass
        for _ in range(4):

            row, col = grass_cells[grass_i]
            grass_i += 1

            plants.append({
                "plant_index": 1,
                "row": row,
                "col": col,
            })

        # 2 Sunflower
        for _ in range(2):

            row, col = sunflower_cells[sunflower_i]
            sunflower_i += 1

            plants.append({
                "plant_index": 5,
                "row": row,
                "col": col,
            })

        # 2 Crystal Cactus
        for _ in range(2):

            row, col = cactus_cells[cactus_i]
            cactus_i += 1

            plants.append({
                "plant_index": 17,
                "row": row,
                "col": col,
            })

        actions.append({
            "tick": tick,
            "plants": plants,
        })

    # ==========================================================
    # PHASE 3
    # Ticks 700-719 = early Winter
    #
    # Continue Rose support briefly before trying Blue Moss.
    # ==========================================================

    for tick in range(700, 720):

        plants = []

        # 10 Rose
        for _ in range(10):

            row, col = rose_cells[rose_i]
            rose_i += 1

            plants.append({
                "plant_index": 2,
                "row": row,
                "col": col,
            })

        # 4 Grass
        for _ in range(4):

            row, col = grass_cells[grass_i]
            grass_i += 1

            plants.append({
                "plant_index": 1,
                "row": row,
                "col": col,
            })

        # 3 Sunflower
        for _ in range(3):

            row, col = sunflower_cells[sunflower_i]
            sunflower_i += 1

            plants.append({
                "plant_index": 5,
                "row": row,
                "col": col,
            })

        # 3 Crystal Cactus
        for _ in range(3):

            row, col = cactus_cells[cactus_i]
            cactus_i += 1

            plants.append({
                "plant_index": 17,
                "row": row,
                "col": col,
            })

        actions.append({
            "tick": tick,
            "plants": plants,
        })

    # ==========================================================
    # PHASE 4
    # Ticks 720-798
    #
    # Blue Moss unlock attempts begin.
    #
    # By now:
    # - Grass should comfortably exceed 3%
    # - Rose has received 1400 additional attempts
    # - Loamcrawlers should have had opportunity to appear
    # ==========================================================

    for tick in range(720, 799):

        plants = []

        # 8 Blue Moss
        for _ in range(8):

            row, col = blue_cells[blue_i]
            blue_i += 1

            plants.append({
                "plant_index": BLUE_MOSS,
                "row": row,
                "col": col,
            })

        # 4 Rose
        for _ in range(4):

            row, col = rose_cells[rose_i]
            rose_i += 1

            plants.append({
                "plant_index": 2,
                "row": row,
                "col": col,
            })

        # 3 Sunflower
        for _ in range(3):

            row, col = sunflower_cells[sunflower_i]
            sunflower_i += 1

            plants.append({
                "plant_index": 5,
                "row": row,
                "col": col,
            })

        # 3 Crystal Cactus
        for _ in range(3):

            row, col = cactus_cells[cactus_i]
            cactus_i += 1

            plants.append({
                "plant_index": 17,
                "row": row,
                "col": col,
            })

        # 2 Crimson Vine = one adjacent pair.
        for _ in range(2):

            row, col = crimson_cells[crimson_i]
            crimson_i += 1

            plants.append({
                "plant_index": CRIMSON_VINE,
                "row": row,
                "col": col,
            })

        actions.append({
            "tick": tick,
            "plants": plants,
        })

    # ==========================================================
    # FINAL TICK
    #
    # ONE Oak.
    #
    # It remains represented in the ecosystem but has literally
    # no time to mature into another 1,700-tree takeover.
    # ==========================================================

    plants = []

    for _ in range(8):

        row, col = blue_cells[blue_i]
        blue_i += 1

        plants.append({
            "plant_index": BLUE_MOSS,
            "row": row,
            "col": col,
        })

    for _ in range(4):

        row, col = rose_cells[rose_i]
        rose_i += 1

        plants.append({
            "plant_index": 2,
            "row": row,
            "col": col,
        })

    for _ in range(3):

        row, col = sunflower_cells[sunflower_i]
        sunflower_i += 1

        plants.append({
            "plant_index": 5,
            "row": row,
            "col": col,
        })

    for _ in range(3):

        row, col = cactus_cells[cactus_i]
        cactus_i += 1

        plants.append({
            "plant_index": 17,
            "row": row,
            "col": col,
        })

    row, col = grass_cells[grass_i]
    grass_i += 1

    plants.append({
        "plant_index": 1,
        "row": row,
        "col": col,
    })

    row, col = oak_cell

    plants.append({
        "plant_index": 12,
        "row": row,
        "col": col,
    })

    actions.append({
        "tick": 799,
        "plants": plants,
    })

    solution = {
        "actions": actions
    }

    validate(level, solution, set(suitable))

    return solution


def validate(level, solution, suitable):

    ticks = set()
    all_scheduled_cells = set()

    for action in solution["actions"]:

        tick = action["tick"]

        if tick in ticks:
            raise ValueError("Duplicate tick.")

        ticks.add(tick)

        if len(action["plants"]) != 20:
            raise ValueError(
                f"Tick {tick} does not contain 20 plants."
            )

        local = set()

        for plant in action["plants"]:

            cell = (
                plant["row"],
                plant["col"],
            )

            if cell not in suitable:
                raise ValueError(
                    f"Unsuitable cell: {cell}"
                )

            if cell in local:
                raise ValueError(
                    f"Duplicate cell in tick {tick}: {cell}"
                )

            if cell in all_scheduled_cells:
                raise ValueError(
                    f"Cell scheduled more than once: {cell}"
                )

            if plant["plant_index"] not in ALLOWED:
                raise ValueError(
                    f"Unknown plant: {plant['plant_index']}"
                )

            local.add(cell)
            all_scheduled_cells.add(cell)

    if len(solution["actions"]) != 800:
        raise ValueError("Expected exactly 800 actions.")


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
        default="submissions/level3-v3.json",
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
        exist_ok=True
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
        f"Saved {sum(counts.values())} placements "
        f"to {output}"
    )

    print(
        "Scheduled counts:",
        dict(sorted(counts.items()))
    )


if __name__ == "__main__":
    main()