"""Conservative threshold episodes in regular NDVI composites.

Each complete episode is a candidate vegetation cycle, not a crop identity.
Missing composites break episodes: no interpolation through monsoon gaps.
"""
from datetime import date
from statistics import median


def detect(points, year, min_amplitude=0.20, threshold_fraction=0.35,
           min_duration_days=40, max_duration_days=240, expected_step_days=15):
    if not 0 < threshold_fraction < 1 or min_amplitude <= 0:
        raise ValueError("Require positive amplitude and threshold fraction between 0 and 1")
    if min_duration_days < 1 or max_duration_days < min_duration_days or expected_step_days < 1:
        raise ValueError("Invalid duration or cadence")
    points = sorted(points)
    if len({d for d, _ in points}) != len(points):
        raise ValueError("Duplicate dates in one sample")
    if any(v is not None and not -1 <= v <= 1 for _, v in points):
        raise ValueError("NDVI must be finite and between -1 and 1")
    valid = sorted(v for _, v in points if v is not None)
    target = [(d, v) for d, v in points if d.year == year]
    if not target:
        return {"status": "no_target_year_data", "cycles": [], "count": None}
    if len(valid) < 5:
        return {"status": "insufficient_data", "cycles": [], "count": None}
    missing = any(v is None for d, v in target)
    gaps = any((b[0]-a[0]).days > expected_step_days*1.5 for a, b in zip(points, points[1:])
               if a[0].year == year or b[0].year == year)
    coverage = ((target[0][0]-date(year, 1, 1)).days <= expected_step_days
                and (date(year, 12, 31)-target[-1][0]).days <= expected_step_days)
    # Robust baseline; max retains brief seasonal peaks. Both are descriptive.
    baseline = valid[int(0.10 * (len(valid) - 1))]
    threshold = baseline + threshold_fraction * (max(valid) - baseline)
    low_amplitude = max(valid) - baseline < min_amplitude
    if low_amplitude:
        uncertain = missing or gaps or not coverage
        return {"status": "incomplete_or_gapped" if uncertain else "low_amplitude",
                "cycles": [], "count": None if uncertain else 0}
    smooth = []
    for i, (day, value) in enumerate(points):
        neighbours = points[max(0, i-1):i+2]
        # Do not fill missing observations or smooth across a long time gap.
        usable = (len(neighbours) == 3 and all(v is not None for _, v in neighbours)
                  and all((b[0]-a[0]).days <= expected_step_days * 1.5
                          for a, b in zip(neighbours, neighbours[1:])))
        smooth.append((day, median(v for _, v in neighbours) if usable else value))
    cycles = []
    start = peak = last = previous = None
    incomplete = False
    for day, value in smooth:
        gap = previous is not None and (day-previous[0]).days > expected_step_days * 1.5
        if gap or value is None:
            if start is not None:
                incomplete = True
            start = peak = last = None
            previous = None
            continue
        if value >= threshold:
            if start is None:
                # A rising crossing requires an actual preceding low observation.
                if previous is not None and previous[1] < threshold:
                    start, peak = day, (day, value)
                else:
                    incomplete = True
            elif value > peak[1]:
                peak = (day, value)
            last = day
        elif start is not None:
            duration = (day-start).days
            if (min_duration_days <= duration <= max_duration_days
                    and peak[1]-baseline >= min_amplitude and peak[0].year == year):
                cycles.append({"start_date": start.isoformat(), "peak_date": peak[0].isoformat(),
                               "end_date": day.isoformat(), "duration_days": duration,
                               "peak_ndvi": round(peak[1], 4)})
            start = peak = last = None
        previous = (day, value)
    if start is not None:
        incomplete = True
    incomplete = incomplete or missing or gaps or not coverage
    return {"status": "incomplete_or_gapped" if incomplete else "low_amplitude" if low_amplitude else "ok",
            "baseline": baseline, "threshold": threshold, "cycles": cycles,
            "count": None if incomplete else len(cycles),
            "accepted_complete_cycles": len(cycles)}


def parse_date(value):
    return date.fromisoformat(value[:10])
