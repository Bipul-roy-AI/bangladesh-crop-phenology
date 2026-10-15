import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from .audit import audit
from .cycles import detect, parse_date


def main():
    parser = argparse.ArgumentParser(description="Bangladesh phenology research tools")
    commands = parser.add_subparsers(dest="command", required=True)
    a = commands.add_parser("audit")
    a.add_argument("csv")
    a.add_argument("--output", required=True)
    c = commands.add_parser("cycles")
    c.add_argument("csv", help="GEE export with sample_id,date,ndvi,valid_pixels")
    c.add_argument("--year", type=int, required=True)
    c.add_argument("--output", required=True)
    c.add_argument("--min-amplitude", type=float, default=0.20)
    c.add_argument("--step-days", type=int, default=15)
    args = parser.parse_args()
    if args.command == "audit":
        result = audit(args.csv)
    else:
        grouped = defaultdict(list)
        with open(args.csv, encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if {"sample_id", "date", "ndvi", "valid_pixels"} - set(reader.fieldnames or []):
                raise ValueError("Expected sample_id,date,ndvi,valid_pixels columns")
            for row in reader:
                value = float(row["ndvi"]) if row["ndvi"] and float(row["valid_pixels"] or 0) > 0 else None
                grouped[row["sample_id"]].append((parse_date(row["date"]), value))
        result = {key: detect(points, args.year, min_amplitude=args.min_amplitude,
                               expected_step_days=args.step_days) for key, points in grouped.items()}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
