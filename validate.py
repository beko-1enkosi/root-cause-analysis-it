"""Static submission checks, not an ecological simulator."""
from solver import STARTERS, planting_cells


def validate(level, solution):
    allowed = set(planting_cells(level))
    seen_ticks = set()
    total = 0

    for action in solution['actions']:
        tick = action['tick']

        if type(tick) is not int or not 0 <= tick < level['ticks']:
            raise ValueError('Invalid tick')
        
        if tick in seen_ticks:
            raise ValueError('Duplicate tick entry')
        
        seen_ticks.add(tick)

        if len(action['plants']) > 20:
            raise ValueError('More than 20 plants in a tick')
        
        seen_cells = set()

        for plant in action['plants']:
            location = (plant['row'], plant['col'])
            if any(type(v) is not int for v in location):
                raise ValueError('Coordinates must be integers')

            
            if location not in allowed or location in seen_cells:
                raise ValueError('Unsuitable or duplicate location')
            if type(plant['plant_index']) is not int or plant['plant_index'] not in STARTERS:
                raise ValueError('Invalid starter species')
            
            seen_cells.add(location)
            total += 1
            
    return total
