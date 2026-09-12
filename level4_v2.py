"""Level 4 v2: diversity-first unlock cascade.

Preserve the useful first 200 ticks of the previous strategy, then:
- heavily reinforce Rose/Grass before attempting unlocks;
- suppress Orange Blossom, Oak and Razorgrass until very late;
- unlock Blue Moss -> Silver Fern;
- establish Crimson Vine in adjacent pairs;
- use unique scheduled coordinates across the entire run.
"""

import argparse
import json
import random
from collections import Counter
from pathlib import Path


# Original Level 3/4 region order.
SPECIES = (12, 2, 16, 6, 7, 5, 17, 19, 1)

HOST = {
    16: 2,   # Ironthorn region -> Rose while locked
    7: 6,    # Orange region -> Lavender while locked
    17: 1,   # Crystal region -> Grass while locked
    19: 1,   # Razor region -> Grass while locked
}

OPENING = (
    1, 19, 17, 2, 16,
    6, 7, 5, 12, 1
)

BLUE_MOSS = 3
CRIMSON_VINE = 4
SILVER_FERN = 8
PURPLE_CANOPY = 10
STONE_REED = 11

ALLOWED = {
    1, 2, 3, 4, 5, 6, 7, 8,
    10, 11, 12, 16, 17, 19
}


def prepare(level):
    overrides = {
        (cell["row"], cell["col"]): cell
        for cell in level["cells"]
    }

    suitable = []

    # Keep the same column-major ordering as the proven baseline.
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

    regions = {
        species: []
        for species in SPECIES
    }

    for index, cell in enumerate(suitable):
        region_index = min(
            len(SPECIES) - 1,
            index * len(SPECIES) // len(suitable),
        )

        regions[
            SPECIES[region_index]
        ].append(cell)

    # Same seed as the previous Level 3/4 strategy.
    rng = random.Random(20260912)

    for species in SPECIES:
        rng.shuffle(regions[species])

    return overrides, suitable, regions


def generate(level):
    dimensions = (
        level["rows"],
        level["cols"],
        level["ticks"],
    )

    if dimensions != (200, 300, 800):
        raise ValueError(
            "Expected Level 4: 200 x 300, 800 ticks."
        )

    overrides, suitable, regions = prepare(level)

    pointers = dict.fromkeys(SPECIES, 0)

    actions = []

    # Every coordinate WE schedule is remembered globally.
    # Natural spreading can still occupy future cells, but
    # we never intentionally submit the same coordinate twice.
    scheduled = set()

    # ==========================================================
    # PHASE 1: ticks 0-199
    #
    # Preserve the strongest part of the 237M baseline.
    #
    # Only starter/host plants are used here:
    # Grass, Rose, Lavender and Sunflower.
    # Oak is converted to Rose.
    # ==========================================================

    for tick in range(200):
        plants = []
        used = set()

        for slot in range(20):
            target = OPENING[
                (tick * 20 + slot) % len(OPENING)
            ]

            species = HOST.get(target, target)

            # Zero early Oak domination.
            if species == 12:
                species = 2

            cells = regions[target]

            position = (
                pointers[target] % len(cells)
            )

            while cells[position] in used:
                pointers[target] += 1
                position = (
                    pointers[target] % len(cells)
                )

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
    # Build unused cell pools.
    # ==========================================================

    unused = set(suitable) - scheduled

    def spacing_key(cell):
        row, col = cell

        return (
            row % 5,
            col % 5,
            row // 5,
            col // 5,
        )

    band_lists = {}

    for target in SPECIES:
        band_lists[target] = sorted(
            [
                cell
                for cell in regions[target]
                if cell in unused
            ],
            key=spacing_key,
        )

    band_pos = {
        target: 0
        for target in SPECIES
    }

    # ==========================================================
    # Stone Reed reservation.
    #
    # Its weakness says it must be adjacent to rock/path.
    # Reserve cells beside terrain 2/4 in the Grass band.
    # ==========================================================

    def terrain_at(cell):
        return overrides.get(
            cell,
            {}
        ).get("terrain", 0)

    stone_candidates = []

    for cell in band_lists[1]:
        row, col = cell

        neighbours = (
            (row + 1, col),
            (row - 1, col),
            (row, col + 1),
            (row, col - 1),
        )

        adjacent_feature = False

        for r, c in neighbours:
            if (
                0 <= r < level["rows"]
                and 0 <= c < level["cols"]
                and terrain_at((r, c)) in (2, 4)
            ):
                adjacent_feature = True
                break

        if adjacent_feature:
            stone_candidates.append(cell)

    stone_cells = stone_candidates[:101]

    if len(stone_cells) < 101:
        raise ValueError(
            "Not enough Stone Reed cells."
        )

    stone_reserved = set(stone_cells)
    stone_index = 0

    # ==========================================================
    # Blue Moss reservation.
    #
    # Blue Moss dislikes excessive neighbours, so use a
    # checkerboard inside the region that previously belonged
    # to Oak.
    # ==========================================================

    blue_cells = [
        cell
        for cell in band_lists[12]
        if (
            cell[0] + cell[1]
        ) % 2 == 0
    ]

    blue_cells = blue_cells[:2399]

    if len(blue_cells) < 2399:
        raise ValueError(
            "Not enough Blue Moss cells."
        )

    blue_reserved = set(blue_cells)
    blue_index = 0

    # ==========================================================
    # Crimson Vine reservation.
    #
    # Crimson dies if isolated, so create adjacent PAIRS.
    # ==========================================================

    available_crimson = set(
        band_lists[16]
    )

    crimson_pairs = []

    for cell in sorted(
        available_crimson,
        key=spacing_key,
    ):
        if cell not in available_crimson:
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
            if other in available_crimson:
                partner = other
                break

        if partner is not None:
            crimson_pairs.append(
                (cell, partner)
            )

            available_crimson.remove(cell)
            available_crimson.remove(partner)

            if len(crimson_pairs) == 999:
                break

    if len(crimson_pairs) < 999:
        raise ValueError(
            "Not enough Crimson Vine pairs."
        )

    crimson_index = 0

    crimson_reserved = {
        cell
        for pair in crimson_pairs
        for cell in pair
    }

    reserved = (
        stone_reserved
        | blue_reserved
        | crimson_reserved
    )

    # ==========================================================
    # Cell access helpers.
    # ==========================================================

    def take_band(target):
        cells = band_lists[target]

        position = band_pos[target]

        while position < len(cells):
            cell = cells[position]

            position += 1

            if (
                cell in unused
                and cell not in reserved
            ):
                band_pos[target] = position

                unused.remove(cell)

                return cell

        raise ValueError(
            f"Ran out of cells in region {target}."
        )

    def take_blue(amount):
        nonlocal blue_index

        result = []

        for _ in range(amount):
            while (
                blue_index < len(blue_cells)
                and blue_cells[blue_index]
                not in unused
            ):
                blue_index += 1

            if blue_index >= len(blue_cells):
                raise ValueError(
                    "Ran out of Blue Moss cells."
                )

            cell = blue_cells[blue_index]
            blue_index += 1

            unused.remove(cell)

            result.append(cell)

        return result

    def take_crimson(amount):
        nonlocal crimson_index

        if amount % 2 != 0:
            raise ValueError(
                "Crimson must be planted in pairs."
            )

        result = []

        for _ in range(amount // 2):
            pair = crimson_pairs[
                crimson_index
            ]

            crimson_index += 1

            for cell in pair:
                if cell not in unused:
                    raise ValueError(
                        "Crimson cell already used."
                    )

                unused.remove(cell)

                result.append(cell)

        return result

    def take_stone():
        nonlocal stone_index

        while (
            stone_index < len(stone_cells)
            and stone_cells[stone_index]
            not in unused
        ):
            stone_index += 1

        if stone_index >= len(stone_cells):
            raise ValueError(
                "Ran out of Stone Reed cells."
            )

        cell = stone_cells[stone_index]

        stone_index += 1

        unused.remove(cell)

        return cell

    def add(plants, species, cells):
        for row, col in cells:
            plants.append({
                "plant_index": species,
                "row": row,
                "col": col,
            })

    # ==========================================================
    # PHASE 2: ticks 200-279
    #
    # Autumn.
    #
    # Push Rose + Grass hard BEFORE attempting Blue Moss.
    # ==========================================================

    for tick in range(200, 280):
        plants = []

        add(
            plants,
            2,
            [take_band(2) for _ in range(8)],
        )

        add(
            plants,
            1,
            [take_band(1) for _ in range(6)],
        )

        add(
            plants,
            6,
            [take_band(6) for _ in range(3)],
        )

        add(
            plants,
            5,
            [take_band(5) for _ in range(3)],
        )

        actions.append({
            "tick": tick,
            "plants": plants,
        })

    # ==========================================================
    # PHASE 3: ticks 280-299
    #
    # Drought has fired at 280.
    #
    # Push Rose/Grass a little further so that Blue Moss,
    # Crystal Cactus and Loamcrawlers prerequisites are safer.
    # ==========================================================

    for tick in range(280, 300):
        plants = []

        add(
            plants,
            2,
            [take_band(2) for _ in range(8)],
        )

        add(
            plants,
            1,
            [take_band(1) for _ in range(8)],
        )

        add(
            plants,
            6,
            [take_band(6) for _ in range(2)],
        )

        add(
            plants,
            5,
            [take_band(5) for _ in range(2)],
        )

        actions.append({
            "tick": tick,
            "plants": plants,
        })

    # ==========================================================
    # PHASE 4: ticks 300-399
    #
    # Winter.
    #
    # Stop depending on Rose/Lavender spread.
    # Start Blue Moss + Crimson Vine + Crystal Cactus.
    # ==========================================================

    for tick in range(300, 400):
        plants = []

        add(
            plants,
            BLUE_MOSS,
            take_blue(8),
        )

        add(
            plants,
            CRIMSON_VINE,
            take_crimson(4),
        )

        add(
            plants,
            17,
            [take_band(17) for _ in range(4)],
        )

        add(
            plants,
            5,
            [take_band(5) for _ in range(3)],
        )

        add(
            plants,
            1,
            [take_band(1)],
        )

        actions.append({
            "tick": tick,
            "plants": plants,
        })

    # ==========================================================
    # PHASE 5: ticks 400-499
    #
    # Spring.
    # Grow Blue/Crimson and restore flower balance.
    # ==========================================================

    for tick in range(400, 500):
        plants = []

        add(
            plants,
            BLUE_MOSS,
            take_blue(6),
        )

        add(
            plants,
            CRIMSON_VINE,
            take_crimson(4),
        )

        add(
            plants,
            2,
            [take_band(2) for _ in range(4)],
        )

        add(
            plants,
            6,
            [take_band(6) for _ in range(3)],
        )

        add(
            plants,
            5,
            [take_band(5) for _ in range(3)],
        )

        actions.append({
            "tick": tick,
            "plants": plants,
        })

    # ==========================================================
    # PHASE 6: ticks 500-599
    #
    # Blue should now have had substantial time to establish.
    # Begin Silver Fern attempts.
    #
    # IMPORTANT: still NO Orange Blossom.
    # ==========================================================

    for tick in range(500, 600):
        plants = []

        add(
            plants,
            BLUE_MOSS,
            take_blue(4),
        )

        add(
            plants,
            CRIMSON_VINE,
            take_crimson(4),
        )

        add(
            plants,
            SILVER_FERN,
            [take_band(7) for _ in range(4)],
        )

        add(
            plants,
            2,
            [take_band(2) for _ in range(3)],
        )

        add(
            plants,
            6,
            [take_band(6) for _ in range(2)],
        )

        add(
            plants,
            5,
            [take_band(5) for _ in range(2)],
        )

        add(
            plants,
            17,
            [take_band(17)],
        )

        actions.append({
            "tick": tick,
            "plants": plants,
        })

    # ==========================================================
    # PHASE 7: ticks 600-699
    #
    # Balanced diversity.
    # Stone Reed / Razorgrass alternate: only ONE per tick.
    # ==========================================================

    for tick in range(600, 700):
        plants = []

        add(
            plants,
            BLUE_MOSS,
            take_blue(3),
        )

        add(
            plants,
            CRIMSON_VINE,
            take_crimson(4),
        )

        add(
            plants,
            SILVER_FERN,
            [take_band(7) for _ in range(4)],
        )

        add(
            plants,
            2,
            [take_band(2) for _ in range(3)],
        )

        add(
            plants,
            6,
            [take_band(6) for _ in range(2)],
        )

        add(
            plants,
            5,
            [take_band(5) for _ in range(2)],
        )

        add(
            plants,
            17,
            [take_band(17)],
        )

        if tick % 2 == 0:
            add(
                plants,
                STONE_REED,
                [take_stone()],
            )

        else:
            add(
                plants,
                19,
                [take_band(19)],
            )

        actions.append({
            "tick": tick,
            "plants": plants,
        })

    # ==========================================================
    # PHASE 8: ticks 700-789
    #
    # Winter + Earthquake.
    # Keep direct diversity support.
    # ==========================================================

    for tick in range(700, 790):
        plants = []

        add(
            plants,
            BLUE_MOSS,
            take_blue(3),
        )

        add(
            plants,
            CRIMSON_VINE,
            take_crimson(4),
        )

        add(
            plants,
            SILVER_FERN,
            [take_band(7) for _ in range(4)],
        )

        add(
            plants,
            2,
            [take_band(2) for _ in range(3)],
        )

        add(
            plants,
            6,
            [take_band(6) for _ in range(2)],
        )

        add(
            plants,
            5,
            [take_band(5) for _ in range(2)],
        )

        add(
            plants,
            17,
            [take_band(17)],
        )

        if tick % 2 == 0:
            add(
                plants,
                STONE_REED,
                [take_stone()],
            )

        else:
            add(
                plants,
                19,
                [take_band(19)],
            )

        actions.append({
            "tick": tick,
            "plants": plants,
        })

    # ==========================================================
    # PHASE 9: ticks 790-798
    #
    # Tiny Ironthorn attempts.
    # No dangerous Orange/Oak yet.
    # ==========================================================

    for tick in range(790, 799):
        plants = []

        add(
            plants,
            BLUE_MOSS,
            take_blue(3),
        )

        add(
            plants,
            CRIMSON_VINE,
            take_crimson(4),
        )

        add(
            plants,
            SILVER_FERN,
            [take_band(7) for _ in range(3)],
        )

        add(
            plants,
            2,
            [take_band(2) for _ in range(3)],
        )

        add(
            plants,
            6,
            [take_band(6) for _ in range(2)],
        )

        add(
            plants,
            5,
            [take_band(5) for _ in range(2)],
        )

        add(
            plants,
            17,
            [take_band(17)],
        )

        if tick % 2 == 0:
            add(
                plants,
                STONE_REED,
                [take_stone()],
            )

        else:
            add(
                plants,
                19,
                [take_band(19)],
            )

        # Ironthorn attempt.
        add(
            plants,
            16,
            [take_band(16)],
        )

        actions.append({
            "tick": tick,
            "plants": plants,
        })

    # ==========================================================
    # FINAL TICK 799
    #
    # Give dangerous species essentially ZERO time to explode.
    #
    # Purple Canopy is an opportunistic unlock attempt.
    # If its condition is not met, only that one slot is lost.
    # ==========================================================

    plants = []

    add(
        plants,
        BLUE_MOSS,
        take_blue(2),
    )

    add(
        plants,
        CRIMSON_VINE,
        take_crimson(2),
    )

    add(
        plants,
        SILVER_FERN,
        [take_band(7) for _ in range(2)],
    )

    add(
        plants,
        2,
        [take_band(2) for _ in range(3)],
    )

    add(
        plants,
        6,
        [take_band(6) for _ in range(2)],
    )

    add(
        plants,
        5,
        [take_band(5) for _ in range(2)],
    )

    add(
        plants,
        17,
        [take_band(17)],
    )

    add(
        plants,
        STONE_REED,
        [take_stone()],
    )

    add(
        plants,
        19,
        [take_band(19)],
    )

    add(
        plants,
        16,
        [take_band(16)],
    )

    # One Orange Blossom only.
    add(
        plants,
        7,
        [take_band(7)],
    )

    # One Oak only.
    add(
        plants,
        12,
        [take_band(12)],
    )

    # One Purple Canopy attempt.
    add(
        plants,
        PURPLE_CANOPY,
        [take_band(12)],
    )

    actions.append({
        "tick": 799,
        "plants": plants,
    })

    solution = {
        "actions": actions
    }

    validate(
        level,
        solution,
        set(suitable),
    )

    return solution


def validate(level, solution, suitable):
    ticks = set()
    all_cells = set()

    for action in solution["actions"]:
        tick = action["tick"]

        if tick in ticks:
            raise ValueError(
                f"Duplicate tick {tick}."
            )

        ticks.add(tick)

        if len(action["plants"]) != 20:
            raise ValueError(
                f"Tick {tick} has "
                f"{len(action['plants'])} plants."
            )

        local = set()

        for plant in action["plants"]:
            cell = (
                plant["row"],
                plant["col"],
            )

            if cell not in suitable:
                raise ValueError(
                    f"Unsuitable cell {cell}."
                )

            if cell in local:
                raise ValueError(
                    f"Duplicate cell inside "
                    f"tick {tick}: {cell}"
                )

            if cell in all_cells:
                raise ValueError(
                    f"Coordinate scheduled twice: "
                    f"{cell}"
                )

            if (
                plant["plant_index"]
                not in ALLOWED
            ):
                raise ValueError(
                    f"Unexpected plant "
                    f"{plant['plant_index']}"
                )

            local.add(cell)
            all_cells.add(cell)

    if len(solution["actions"]) != 800:
        raise ValueError(
            "Expected exactly 800 ticks."
        )


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
        default="submissions/level4-v2.json",
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
        f"placements to {output}"
    )

    print(
        "Scheduled counts:",
        dict(sorted(counts.items()))
    )


if __name__ == "__main__":
    main()