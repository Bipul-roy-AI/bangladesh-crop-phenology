"""Exploratory radar events and temporal agreement with optical episodes.

VH trough/peak/trough patterns are candidates for inspection, not crop labels.
No radar-to-NDVI conversion, interpolation or calibrated confidence is used.
"""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

from .cycles import detect, parse_date


def load_export(path):
    grouped = defaultdict(list)
    required = {'sample_id', 'date', 'ndvi', 'valid_pixels', 'vv_db', 'vh_db'}
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if required - set(reader.fieldnames or []):
            raise ValueError(f'Missing columns: {sorted(required-set(reader.fieldnames or []))}')
        seen = set()
        for raw in reader:
            day = parse_date(raw['date'])
            key = (raw['sample_id'], day)
            if key in seen:
                raise ValueError(f'Duplicate sample/date: {key}')
            seen.add(key)
            row = {'date': day}
            for name in ['ndvi', 'vv_db', 'vh_db']:
                value = float(raw[name]) if raw[name].strip() else None
                if value is not None and not math.isfinite(value):
                    raise ValueError(f'Nonfinite {name} at {key}')
                row[name] = value
            if row['ndvi'] is not None and not -1 <= row['ndvi'] <= 1:
                raise ValueError(f'NDVI outside [-1,1] at {key}')
            pixels = float(raw['valid_pixels'] or 0)
            if not math.isfinite(pixels) or pixels < 0:
                raise ValueError(f'Invalid valid_pixels at {key}')
            if pixels == 0:
                row['ndvi'] = None
            row['valid_pixels'] = pixels
            row['sample_id'] = raw['sample_id']
            row['district'] = raw.get('district', '')
            grouped[raw['sample_id']].append(row)
    if not grouped:
        raise ValueError('Empty export')
    return {k: sorted(v, key=lambda r: r['date']) for k, v in sorted(grouped.items())}


def smooth_vh(rows, step_days=15):
    smoothed = []
    for i, row in enumerate(rows):
        neighbours = rows[max(0, i-1):i+2]
        usable = (len(neighbours) == 3
                  and all(r['vh_db'] is not None for r in neighbours)
                  and all((b['date']-a['date']).days <= step_days*1.5
                          for a, b in zip(neighbours, neighbours[1:])))
        smoothed.append(median(r['vh_db'] for r in neighbours) if usable else row['vh_db'])
    return smoothed


def radar_events(rows, year, prominence_db=3.0, step_days=15,
                 flank_days=120, min_duration_days=45, peak_separation_days=45):
    if not math.isfinite(prominence_db) or prominence_db <= 0 or step_days < 1:
        raise ValueError('Positive finite prominence and cadence required')
    values = smooth_vh(rows, step_days)
    candidates = []
    for i in range(1, len(rows)-1):
        peak = values[i]
        day = rows[i]['date']
        # Last point of a flat maximum: deterministic plateau handling.
        if (day.year != year or peak is None or values[i-1] is None or values[i+1] is None
                or not (peak >= values[i-1] and peak > values[i+1])):
            continue
        before = [j for j in range(i) if values[j] is not None
                  and 0 < (day-rows[j]['date']).days <= flank_days]
        after = [j for j in range(i+1, len(rows)) if values[j] is not None
                 and 0 < (rows[j]['date']-day).days <= flank_days]
        if not before or not after:
            continue
        left = min(before, key=lambda j: (values[j], -j))
        right = min(after, key=lambda j: (values[j], j))
        rise, fall = peak-values[left], peak-values[right]
        duration = (rows[right]['date']-rows[left]['date']).days
        if min(rise, fall) < prominence_db or duration < min_duration_days:
            continue
        segment = rows[left:right+1]
        valid_dates = [r['date'] for r in segment if r['vh_db'] is not None]
        largest_gap = max((b-a).days for a, b in zip(valid_dates, valid_dates[1:]))
        if largest_gap > step_days*2 or len(valid_dates)/len(segment) < .8:
            continue
        flags = ['radar_pattern_not_crop_identity', 'uncalibrated_radar_threshold']
        if len(valid_dates) != len(segment) or largest_gap > step_days*1.5:
            flags.append('radar_gap_within_event')
        if any(r['vh_db'] is not None and r['vh_db'] < -30 for r in segment):
            flags.append('very_low_vh_water_or_noise_possible')
        candidates.append({
            'start_date': rows[left]['date'].isoformat(), 'peak_date': day.isoformat(),
            'end_date': rows[right]['date'].isoformat(), 'duration_days': duration,
            'vh_peak_db': round(peak, 4), 'rise_db': round(rise, 4),
            'fall_db': round(fall, 4), 'prominence_db': round(min(rise, fall), 4),
            'flags': flags})
    # Suppress nearby extrema; no claim that remaining events equal crop cycles.
    selected = []
    for event in sorted(candidates, key=lambda e: (-e['prominence_db'], e['peak_date'])):
        if all(abs((parse_date(event['peak_date'])-parse_date(e['peak_date'])).days)
               >= peak_separation_days for e in selected):
            selected.append(event)
    return sorted(selected, key=lambda e: e['peak_date'])


def compare_sample(rows, year, prominence_db=3, step_days=15, match_days=45):
    optical = detect([(r['date'], r['ndvi']) for r in rows], year,
                     expected_step_days=step_days)
    radar = radar_events(rows, year, prominence_db=prominence_db, step_days=step_days)
    pairs = []
    for oi, o in enumerate(optical['cycles']):
        for ri, r in enumerate(radar):
            lag = abs((parse_date(o['peak_date'])-parse_date(r['peak_date'])).days)
            overlap = max(parse_date(o['start_date']), parse_date(r['start_date'])) <= min(
                parse_date(o['end_date']), parse_date(r['end_date']))
            if lag <= match_days and overlap:
                pairs.append((lag, oi, ri))
    matched_o, matched_r, events = set(), set(), []
    # One-to-one matching prevents double-counting the same optical episode.
    for lag, oi, ri in sorted(pairs):
        if oi in matched_o or ri in matched_r:
            continue
        matched_o.add(oi); matched_r.add(ri)
        events.append({'evidence': 'temporal_agreement_unvalidated',
                       'optical': optical['cycles'][oi], 'radar': radar[ri],
                       'peak_difference_days': lag})
    events.extend({'evidence': 'optical_only_unvalidated', 'optical': o}
                  for i, o in enumerate(optical['cycles']) if i not in matched_o)
    events.extend({'evidence': 'radar_only_unvalidated', 'radar': r}
                  for i, r in enumerate(radar) if i not in matched_r)
    for event in events:
        candidate = event.get('radar') or event['optical']
        peak = parse_date(candidate['peak_date'])
        nearby = [r['ndvi'] for r in rows if abs((r['date']-peak).days) <= 30
                  and r['ndvi'] is not None]
        event['near_peak_optical_observations'] = len(nearby)
        event['near_peak_max_ndvi'] = max(nearby) if nearby else None
        event['flags'] = ['no_independent_crop_validation', 'dates_are_composite_proxies']
        event['flags'].extend(candidate.get('flags', []))
        if not nearby:
            event['flags'].append('no_optical_observation_within_30_days_of_peak')
        elif max(nearby) < .35:
            event['flags'].append('weak_near_peak_vegetation_signal')
    events.sort(key=lambda e: (e.get('radar') or e['optical'])['peak_date'])
    target = [r for r in rows if r['date'].year == year]
    flags = ['no_independent_crop_validation', 'historical_2021_sampling_frame',
             'uncalibrated_detection_parameters', 'radar_sensitive_to_water_and_soil_moisture']
    if not target:
        flags.append('no_target_year_data')
    if any(r['ndvi'] is None for r in target):
        flags.append('optical_gaps')
    if any(r['vh_db'] is None or r['vv_db'] is None for r in target):
        flags.append('radar_gaps')
    if any(r['valid_pixels'] == 1 for r in target):
        flags.append('single_pixel_sample_not_field_mean')
    valid_vh_dates = [r['date'] for r in target if r['vh_db'] is not None]
    if any((b-a).days > step_days*2 for a,b in zip(valid_vh_dates, valid_vh_dates[1:])):
        flags.append('long_radar_gap')
    return {'district': rows[0]['district'], 'optical_status': optical['status'],
            'target_composites': len(target),
            'valid_optical_composites': sum(r['ndvi'] is not None for r in target),
            'valid_radar_composites': sum(r['vh_db'] is not None and r['vv_db'] is not None for r in target),
            'optical_episode_count': len(optical['cycles']), 'radar_event_count': len(radar),
            'matched_event_count': len(matched_o), 'unmatched_radar_event_count': len(radar)-len(matched_r),
            'candidate_event_count': len(events), 'annual_crop_cycle_count': None,
            'status': 'exploratory_unvalidated', 'flags': flags, 'events': events}


def write_analysis(source, output_dir, year, prominence_db=3, step_days=15, plots=False):
    grouped = load_export(source)
    results = {sample: compare_sample(rows, year, prominence_db, step_days)
               for sample, rows in grouped.items()}
    summary = {'year': year, 'samples': len(results),
               'source_sha256': hashlib.sha256(Path(source).read_bytes()).hexdigest(),
               'parameters': {'prominence_db': prominence_db, 'step_days': step_days,
                              'flank_days': 120, 'peak_separation_days': 45,
                              'match_days': 45, 'near_peak_ndvi_screen': .35},
               'optical_episodes': sum(r['optical_episode_count'] for r in results.values()),
               'radar_events': sum(r['radar_event_count'] for r in results.values()),
               'temporally_matched_events': sum(r['matched_event_count'] for r in results.values()),
               'unmatched_radar_events': sum(r['unmatched_radar_event_count'] for r in results.values()),
               'candidate_events_after_matching': sum(r['candidate_event_count'] for r in results.values()),
               'validated_annual_crop_counts': 0,
               'sample_flag_counts': dict(Counter(f for r in results.values() for f in r['flags'])),
               'event_flag_counts': dict(Counter(f for r in results.values() for e in r['events'] for f in e['flags'])),
               'threshold_sensitivity': []}
    for threshold in sorted({2.0, 3.0, 4.0, float(prominence_db)}):
        events = [radar_events(rows, year, threshold, step_days) for rows in grouped.values()]
        summary['threshold_sensitivity'].append({'prominence_db': threshold,
            'radar_events': sum(map(len, events)), 'samples_with_events': sum(bool(e) for e in events)})
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    (out/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    (out/'sample_results.json').write_text(json.dumps(results, indent=2, allow_nan=False)+'\n')
    sample_table = [{'sample_id': k, **{field: value for field, value in r.items() if field != 'events'}}
                    for k, r in results.items()]
    _write_csv(out/'sample_comparison.csv', sample_table)
    event_table = []
    for sample, result in results.items():
        for event in result['events']:
            base = {'sample_id': sample, 'evidence': event['evidence'],
                    'near_peak_optical_observations': event['near_peak_optical_observations'],
                    'near_peak_max_ndvi': event['near_peak_max_ndvi'],
                    'peak_difference_days': event.get('peak_difference_days'),
                    'radar_prominence_db': event.get('radar', {}).get('prominence_db'),
                    'radar_rise_db': event.get('radar', {}).get('rise_db'),
                    'radar_fall_db': event.get('radar', {}).get('fall_db'),
                    'optical_peak_ndvi': event.get('optical', {}).get('peak_ndvi'),
                    'flags': event['flags']}
            for sensor in ['optical', 'radar']:
                for field in ['start_date', 'peak_date', 'end_date']:
                    base[f'{sensor}_{field}'] = event.get(sensor, {}).get(field)
            event_table.append(base)
    _write_csv(out/'candidate_events.csv', event_table,
               fallback_fields=['sample_id', 'evidence', 'flags'])
    if plots:
        from .radar_plots import create_plots
        create_plots(grouped, results, summary, out)
    return summary


def _write_csv(path, rows, fallback_fields=None):
    fields = list(rows[0]) if rows else fallback_fields
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v) if isinstance(v, list) else v for k,v in row.items()})
