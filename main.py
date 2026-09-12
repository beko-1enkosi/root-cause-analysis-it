"""Usage: python main.py data/levels/1.json solutions/level1.json"""
import argparse
import json
from pathlib import Path
from solver import solve
from validate import validate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('level', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    level = json.loads(args.level.read_text(encoding='utf-8'))
    solution = solve(level)
    count = validate(level, solution)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(solution, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {count} planting actions across {len(solution["actions"])} ticks to {args.output}')


if __name__ == '__main__':
    main()
