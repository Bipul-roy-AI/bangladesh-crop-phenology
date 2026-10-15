# Bangladesh, 2025: scope and execution plan

## Fixed scope

- Geography: Bangladesh, using FAO GAUL 2015 district boundaries for batching.
- Reporting period: 1 January–31 December 2025.
- Cycle assignment: peak date in 2025, even if establishment/decline crosses years.
- Acquisition window: 5 July 2024 to 30 June 2026, end-exclusive.
- Sampling export: Sentinel-2 NDVI and Sentinel-1 VV/VH, 15-day composites.
- Outputs sought: candidate growth dates and counts, uncertainty flags and,
  after independent validation, crop labels and cropping-intensity estimates.

## Run the national sampling export

1. Use an Earth Engine-authorized account and Cloud project in the Code Editor.
2. Paste `gee/national_2025.js`; no drawn geometry is required.
3. Inspect the printed district count (expected 64), names and selected district.
   Boundaries/names are historical and must be checked against your reporting needs.
4. Run district index 0 first. Check the actual sample count, image coverage,
   radar orbit and missing optical intervals before scaling up.
5. Run and download its CSV export. Then repeat indices 1 through count minus 1.
   Process manageable batches rather than launching every national task at once.
6. For each CSV run, from the checkout:

```bash
PYTHONPATH=src python -m bdphenology.cli cycles data/raw/district_0.csv \
  --year 2025 --step-days 15 --output data/derived/district_0_cycles.json
```

Sample IDs include district code and coordinates. Keep source CSVs so results
can be joined back to sample locations. Record district index, actual sample
count, export task, sample coverage and exclusions for each batch.

## Sampling versus national maps

The script requests 50 points per district (approximately 3,200 points if all
64 districts provide the full sample). Points are sampled from ESA WorldCover
2021's cropland class, not confirmed 2025 fields. This is an exploratory frame:

- land-use changes since 2021 can create omissions and false inclusions;
- points are not surveyed crop labels or field polygons;
- equal samples per district do not imply equal national sampling weights;
- count percentages must not be presented as national area percentages;
- small fields, mixed pixels, floods and monsoon gaps require inspection.

National wall-to-wall maps and area estimates remain a separate implementation
and validation stage. They require a defensible 2025 cropland frame, spatial
processing tiles, calibrated models and independent reference data. This export
does not produce those maps.

## Outstanding prerequisites

Earth Engine exports have not yet been executed here. A configured authorized
Cloud project is required; never commit credentials. AgriclimateBD still lacks
an observation year and cannot supply independent 2025 validation labels.
Radar/optical fusion remains unimplemented; radar is exported for inspection.

For validation, obtain dated 2025 field records for establishment, crop type and
harvest, or independently interpreted reference observations with documented
uncertainty. Hold out fields/regions during evaluation and report unclassified
samples alongside successful detections.
