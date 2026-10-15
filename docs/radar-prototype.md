# Radar-aware candidate comparison

This prototype complements the NDVI-only detector with Sentinel-1 VH pattern
screening. It compares evidence at the event level; it is not a calibrated
radar/optical crop classifier or a radar-to-NDVI reconstruction model.

## Reproduce

Python analysis uses only the standard library. Plotting optionally requires
matplotlib (`python -m pip install -e '.[plots]'`).

```bash
PYTHONPATH=src python -m bdphenology.cli radar \
  data/raw/bangladesh_phenology_2025_district_0.csv \
  --year 2025 --prominence-db 3 --step-days 15 \
  --output-dir data/derived/barguna_radar_2025 --plots
```

Omit `--plots` to run without matplotlib. The command writes:

- `summary.json`: source SHA-256, parameters, counts and threshold sensitivity.
- `sample_results.json`: nested event evidence and uncertainty flags.
- `sample_comparison.csv`: one record per location.
- `candidate_events.csv`: optical/radar timing and evidence category per candidate.
- `comparison_overview.png` and `sample_sensor_comparison.png` with `--plots`.

These outputs are deterministic for a given source and parameters; input CSVs
are never modified. Plot examples are selected by explicit evidence categories,
not presented as representative random samples.

## Radar detection

1. Use exported VH dB values, retaining missing observations. VV is plotted as
   context, not used for event acceptance in this first version.
2. Apply a three-observation median where all neighbours exist without a long
   cadence gap. A missing value stays missing. No interpolation is performed.
3. Find local maxima in the smoothed VH series. For each maximum, select the
   lowest smoothed observation within 120 days before and 120 days after it.
4. Require both a rise and fall of at least 3 dB and a trough-to-trough duration
   of at least 45 days (at most 240 days by construction).
5. Require at least 80% valid VH observations within the interval, with no valid
   observation gap exceeding 30 days at the default 15-day cadence. Allowed
   smaller gaps are explicitly flagged.
6. Retain stronger candidates when peak dates are less than 45 days apart.
   Candidate intervals can still overlap: these are not independent crop cycles.
7. Include only candidates whose radar peak occurs in the reporting year.

The plateau rule selects the last equal-valued maximum. Trough selection searches
for extrema rather than demonstrating a physical planting or harvest event.
A median-smoothed peak can differ from a raw VH maximum; plots show both.

## Matching and evidence categories

An optical episode and radar event can be matched only when their intervals
intersect and peak dates differ by no more than 45 days. Greedy matching chooses
smaller differences first, with at most one match per optical/radar event. This
is temporal compatibility, not independent biological validation or accuracy.

Categories:

- `temporal_agreement_unvalidated`: compatible optical/radar timing.
- `optical_only_unvalidated`: accepted NDVI episode without matched radar event.
- `radar_only_unvalidated`: radar pattern without matched complete NDVI episode.

The output also reports optical observations within 30 days of the candidate
peak. Maximum observed NDVI below 0.35 is flagged as weak vegetation evidence;
this threshold is an uncalibrated screen and does not accept/reject a crop.
A high NDVI observation alone does not establish temporal agreement.

## Uncertainty

Every sample remains unvalidated; annual crop-cycle count remains `null`.
Flags cover optical/radar gaps, single-pixel rather than field-mean support,
historical 2021 sampling frame, uncalibrated parameters, missing optical support,
very low VH (below -30 dB), and possible water/moisture confounding. Flags are
categorical cautions, not calibrated confidence probabilities or error bounds.

Because the export lacks per-point radar acquisition counts, incidence angles
and independent land-use verification, radar quality and crop identity are not
fully established. Radar extremes can reflect water, soil moisture, roughness,
speckle or changing scattering mechanisms. A strong rise/fall is not proof of
rice or any other crop.

Sensitivity runs at 2, 3 and 4 dB are reported without selecting the threshold
that yields the most candidates. They are parameter sensitivity, not uncertainty
intervals. Next priorities are 2025 sample verification and independent dated
reference observations, followed by spatially held-out calibration/evaluation.
