"""Audit the supplied AgriclimateBD schema without silently repairing it."""
import csv
from collections import Counter
from pathlib import Path


def audit(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        rows = list(reader)
    required = {"District", "Crop Name", "Season", "Area", "Production", "AP Ratio",
                "Max Relative Humidity", "Min Relative Humidity"}
    if required - set(columns):
        raise ValueError(f"Missing required columns: {sorted(required - set(columns))}")
    errors = Counter()
    blank = Counter()
    invalid_numeric = Counter()
    humidity_reversed = zero_area = ratio_matches = 0
    for row in rows:
        for key, value in row.items():
            if value is None or not value.strip():
                blank[key] += 1
            elif value.startswith(("#REF!", "#DIV/0!", "#VALUE!", "#N/A", "#NUM!", "#NAME?")):
                errors[f"{key}: {value}"] += 1
        def number(key):
            try:
                return float(row[key])
            except (TypeError, ValueError):
                invalid_numeric[key] += 1
                return None
        high, low = number("Max Relative Humidity"), number("Min Relative Humidity")
        humidity_reversed += high is not None and low is not None and high < low
        area, production, ratio = number("Area"), number("Production"), number("AP Ratio")
        zero_area += area == 0
        if area and production is not None and ratio is not None:
            ratio_matches += abs(ratio - production / area) < 1e-6
    identities = Counter((r["District"], r["Season"], r["Crop Name"]) for r in rows)
    return {
        "rows": len(rows), "columns": len(columns),
        "districts": dict(sorted(Counter(r["District"] for r in rows).items())),
        "seasons": dict(Counter(r["Season"] for r in rows)),
        "named_crop_labels": sorted({r["Crop Name"] for r in rows if not r["Crop Name"].startswith("#")}),
        "blank_cells_by_column": dict(blank), "spreadsheet_errors": dict(errors),
        "invalid_numeric_cells": dict(invalid_numeric),
        "humidity_max_below_min_rows": humidity_reversed,
        "zero_area_rows": zero_area,
        "ratio_matches_production_divided_by_area": ratio_matches,
        "repeated_district_season_crop_keys": sum(v - 1 for v in identities.values()),
        "year_column_present": any(c.lower() in {"year", "observation_year", "crop_year"} for c in columns),
        "limitations": ["No source corrections are applied.",
                        "Dictionary units and source year require independent verification.",
                        "District records are not field-level phenology observations."]}
