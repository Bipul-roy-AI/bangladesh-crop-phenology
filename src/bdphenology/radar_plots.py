"""Optional matplotlib figures; analysis itself uses only the standard library."""
from datetime import date


def create_plots(grouped, results, summary, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from .radar import smooth_vh
    year = summary['year']
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), layout='constrained')
    months = range(1, 13)
    for field, offset, label in [('ndvi', -.18, 'NDVI'), ('vh_db', .18, 'VH radar')]:
        coverage = []
        for month in months:
            rows = [r for rs in grouped.values() for r in rs
                    if r['date'].year == year and r['date'].month == month]
            coverage.append(100*sum(r[field] is not None for r in rows)/len(rows) if rows else 0)
        axes[0].bar([m+offset for m in months], coverage, width=.36, label=label)
    axes[0].set(xticks=list(months), ylim=(0, 105), xlabel='Month', ylabel='Valid sample-composites (%)',
                title='Observation coverage'); axes[0].legend()
    labels = ['Optical only', 'Temporal agreement', 'Radar only']
    counts = [summary['optical_episodes']-summary['temporally_matched_events'],
              summary['temporally_matched_events'], summary['unmatched_radar_events']]
    bars = axes[1].bar(labels, counts, color=['#2166ac', '#238b45', '#d95f02'])
    axes[1].bar_label(bars); axes[1].tick_params(axis='x', labelrotation=20)
    axes[1].set(ylabel='Candidate events, not crop cycles', title='Evidence after one-to-one matching')
    tests = summary['threshold_sensitivity']
    axes[2].plot([t['prominence_db'] for t in tests], [t['radar_events'] for t in tests], marker='o')
    axes[2].set(xlabel='Required VH rise AND fall (dB)', ylabel='Radar candidate events',
                title='Uncalibrated threshold sensitivity')
    fig.suptitle(f'Barguna {year}: {len(results)} exploratory sample points — no crop validation')
    fig.savefig(out/'comparison_overview.png', dpi=160); plt.close(fig)

    # Deterministic examples cover agreement, radar-only, low-VH and low-event cases.
    choices = []
    predicates = [lambda r: r['matched_event_count'] > 0,
                  lambda r: r['unmatched_radar_event_count'] > 0,
                  lambda r: any('very_low_vh_water_or_noise_possible' in e['flags'] for e in r['events']),
                  lambda r: r['radar_event_count'] == 0]
    for predicate in predicates:
        keys = [k for k in results if k not in choices and predicate(results[k])]
        if keys:
            choices.append(keys[0])
    choices += [k for k in results if k not in choices][:4-len(choices)]
    fig, axes = plt.subplots(len(choices), 2, figsize=(15, 3.5*len(choices)),
                             squeeze=False, layout='constrained')
    for pair, sample in zip(axes, choices):
        rows = [r for r in grouped[sample] if r['date'].year == year]
        dates = [r['date'] for r in rows]
        ndvi = [r['ndvi'] if r['ndvi'] is not None else float('nan') for r in rows]
        pair[0].plot(dates, ndvi, marker='o', markersize=3, label='NDVI')
        missing = [r['date'] for r in rows if r['ndvi'] is None]
        pair[0].scatter(missing, [-.15]*len(missing), color='red', marker='x', label='Missing')
        for field in ['vv_db', 'vh_db']:
            pair[1].plot(dates, [r[field] if r[field] is not None else float('nan') for r in rows],
                         marker='o', markersize=3, label=field)
        all_rows = grouped[sample]
        smoothed = smooth_vh(all_rows, summary['parameters']['step_days'])
        selected = [(r['date'], v) for r, v in zip(all_rows, smoothed) if r['date'].year == year]
        pair[1].plot([d for d,v in selected], [v if v is not None else float('nan') for d,v in selected],
                     color='black', linestyle='--', linewidth=1.2, label='VH median (detector)')
        for event in results[sample]['events']:
            for sensor, ax, color in [('optical', pair[0], '#2166ac'), ('radar', pair[1], '#d95f02')]:
                if sensor in event:
                    cycle = event[sensor]
                    ax.axvspan(date.fromisoformat(cycle['start_date']), date.fromisoformat(cycle['end_date']),
                               alpha=.10, color=color)
                    ax.axvline(date.fromisoformat(cycle['peak_date']), alpha=.4, color=color, linestyle=':')
        pair[0].set(ylim=(-.2, 1), ylabel='NDVI', title=sample+' — optical candidates')
        r = results[sample]
        pair[1].set(ylabel='Backscatter (dB)', title=f"Radar patterns: {r['radar_event_count']}; matched: {r['matched_event_count']}")
        for ax in pair:
            ax.set_xlim(date(year,1,1), date(year,12,31));ax.grid(alpha=.2);ax.legend(fontsize=8)
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    fig.suptitle('Candidate intervals are algorithmic patterns, not planting/harvest observations')
    fig.savefig(out/'sample_sensor_comparison.png', dpi=160);plt.close(fig)
