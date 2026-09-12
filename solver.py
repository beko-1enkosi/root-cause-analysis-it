"""Deterministic Level 1 baseline; the official simulator evaluates survival."""
STARTERS = (12, 2, 6, 5, 1)


def planting_cells(level):
    overrides = {(c['row'], c['col']): c for c in level.get('cells', [])}
    cells = []

    for col in range(level['cols']):
        for row in range(level['rows']):
            cell = overrides.get((row, col), {})
            if cell.get('terrain', 0) == 0 and cell.get('soil', 0) in (0, 1):
                cells.append((row, col))

    return cells


def solve(level):
    cells = planting_cells(level)
    if not cells:
        return {'actions': []}

    actions = []
    duration = (len(cells) + 19) // 20
    start = level['ticks'] - duration

    if start < 0:
        raise ValueError('Insufficient ticks to plant every suitable cell once')
    
    for offset in range(0, len(cells), 20):
        plants = []
        for position in range(offset, min(offset + 20, len(cells))):
            row, col = cells[position]
            species = STARTERS[min(4, position * 5 // len(cells))]
            plants.append({'plant_index': species, 'row': row, 'col': col})
        actions.append({'tick': start + offset // 20, 'plants': plants})

    return {'actions': actions}
