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
    r = commands.add_parser("radar", help="Exploratory VH/NDVI candidate comparison")
    r.add_argument("csv")
    r.add_argument("--year", type=int, required=True)
    r.add_argument("--output-dir", required=True)
    r.add_argument("--prominence-db", type=float, default=3.0)
    r.add_argument("--step-days", type=int, default=15)
    r.add_argument("--plots", action="store_true", help="Requires matplotlib")
    v = commands.add_parser("reference", help="Prepare blind reference-label worksheets")
    v.add_argument("csv", help="GEE export with sample locations")
    v.add_argument("--year", type=int, default=2025)
    v.add_argument("--output-dir", required=True)
    check = commands.add_parser("check-reference", help="Check entered annual reference labels")
    check.add_argument("csv")
    check.add_argument("--year", type=int, default=2025)
    check.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "reference":
        from .reference import make_package
        print(json.dumps(make_package(args.csv, args.output_dir, args.year), indent=2))
        return
    if args.command == "radar":
        from .radar import write_analysis
        result = write_analysis(args.csv, args.output_dir, args.year,
                                args.prominence_db, args.step_days, args.plots)
        print(json.dumps(result, indent=2))
        return
    if args.command == "check-reference":
        from .reference import check_reference
        result = check_reference(args.csv, args.year)
    elif args.command == "audit":
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
