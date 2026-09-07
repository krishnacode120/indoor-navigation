"""Generate 80 survey locations, with repeated noisy measurements per location."""
import argparse
from pathlib import Path
import random
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from backend.simulator import AP_NAMES, simulate_scan


def generate_dataset(output=ROOT / "data/dataset.csv", seed=42, repeats=12):
    if repeats < 1:
        raise ValueError("repeats must be positive")
    rng = random.Random(seed)
    rows = [dict(x=x, y=y, floor=floor, **simulate_scan(x, y, floor, rng))
            for floor in (1, 2) for y in (0, 4, 8, 12)
            for x in range(0, 19, 2) for _ in range(repeats)]
    df = pd.DataFrame(rows, columns=["x", "y", "floor", *AP_NAMES])
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/dataset.csv")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--repeats", type=int, default=12)
    args = parser.parse_args()
    data = generate_dataset(args.output, args.seed, args.repeats)
    print(f"Generated {len(data)} scans at 80 locations: {args.output}")
