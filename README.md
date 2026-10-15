# Bangladesh Crop Phenology

An initial research workflow for detecting candidate vegetation growth cycles in
Bangladesh using Google Earth Engine and checking the supporting AgriclimateBD
crop-calendar dataset.

**Status: research prototype.** Local processing is tested with synthetic series
and the supplied AgriclimateBD CSV. The first user-run Earth Engine export (Barguna) has been inspected and processed;
see [the results and coverage limitations](docs/results/barguna-2025.md).
No outputs are field-validated; no crop-area maps or accuracy claims are presented.

## Research scope

- Estimate green-up, peak growth, decline and candidate cycle duration.
- Investigate single, double and triple cropping after independent validation.
- Compare detected timing with Aus, Aman and Boro calendars.
- Keep crop identity, calendar guidance and satellite observations distinct.

The study scope is **Bangladesh, calendar year 2025**. Use
[the national district-batched export](gee/national_2025.js) for exploratory
sampling across Bangladesh, or the field-polygon export for surveyed locations.
Satellite acquisition includes **5 July 2024–29 June 2026** (end-exclusive
30 June 2026) to capture cycles crossing the reporting-year boundaries.
See [the national execution plan](docs/bangladesh-2025.md).

## Quick start

Python 3.10+ and Node.js (only for JavaScript syntax checks) are sufficient for
local checks. The Python tools use the standard library: no API key or package
installation is required for those operations.

```bash
cd /workspace/bangladesh-crop-phenology  # or your own checkout
export PYTHONPATH="$PWD/src"
python -m unittest discover -s tests -v
node --check gee/export_time_series.js
node --check gee/national_2025.js
```

Optional packaging installation: `python -m pip install -e .`.

### 1. Audit the reference dataset

Keep the original CSV in `data/raw/AgriclimateBD.csv` (ignored by Git).

```bash
PYTHONPATH=src python -m bdphenology.cli audit data/raw/AgriclimateBD.csv \
  --output data/derived/agriclimate_audit.json
```

See [the audited findings](docs/data-quality.md). Do not use this dataset as
field-level training or validation data: observation year and field locations
are absent, and several source issues remain unresolved.

### 2. Export satellite time series

For national coverage, begin with `gee/national_2025.js`: export one district,
inspect coverage, then repeat for every district index. It requests up to 50
historical-cropland sample points per district. The resulting sample analysis is
not a national wall-to-wall crop map. See the execution plan for limitations.

For surveyed field polygons:

1. Open the [Earth Engine Code Editor](https://code.earthengine.google.com/)
   with an authorized account and configured Cloud project.
2. Draw/import a polygon named `geometry`.
3. Paste [gee/export_time_series.js](gee/export_time_series.js).
4. Set the year and replace the demo sample with surveyed field polygons when
   available. Every feature must have a unique `sample_id`.
5. Inspect the Sentinel-1 relative-orbit coverage printed by the script.
6. Run the export task and download the CSV to `data/raw/gee_timeseries.csv`.

The export contains 15-day Sentinel-2 NDVI and Sentinel-1 VV/VH summaries.
It retains missing optical intervals rather than inventing observations.
The NDVI-only detector does not use radar. The new radar-aware prototype
compares VH events with optical episodes; it does not reconstruct missing NDVI
or provide calibrated crop labels. See [radar methods](docs/radar-prototype.md).

### 3. Detect candidate cycles

```bash
PYTHONPATH=src python -m bdphenology.cli cycles data/raw/gee_timeseries.csv \
  --year 2025 --step-days 15 --output data/derived/cycles.json
```

To try an explicitly synthetic example:

```bash
PYTHONPATH=src python -m bdphenology.cli cycles examples/synthetic_timeseries.csv \
  --year 2024 --output data/derived/synthetic_cycles.json
```

The detector requires observed rising and falling threshold crossings. It assigns
cycles to the year of their peak; the export includes 180 days of padding on
each side of the reporting year. An uncertain annual count is `null`, not zero.
Dates are 15-day composite-bin approximations, not observed planting/harvest dates.

### 4. Compare radar and optical candidates

```bash
PYTHONPATH=src python -m bdphenology.cli radar data/raw/gee_timeseries.csv \
  --year 2025 --output-dir data/derived/radar_comparison --plots
```

Plotting requires matplotlib (`python -m pip install -e '.[plots]'`); omit
`--plots` for standard-library-only analysis. Outputs include event evidence,
uncertainty flags, threshold sensitivity and comparison plots.

Read the [Barguna radar results](docs/results/barguna-2025-radar.md). Candidate
counts are not confirmed crop-cycle counts; all annual crop counts remain
undetermined pending validation.

## Repository structure

| Path | Purpose |
| --- | --- |
| `gee/` | Earth Engine export script |
| `src/bdphenology/` | CSV audit, cycle detection and CLI |
| `tests/` | Synthetic signal and data-audit tests |
| `examples/` | Clearly labelled synthetic input |
| `docs/` | Methods, data quality and validation plan |
| `data/raw/` | Local inputs, excluded from Git |
| `data/derived/` | Local outputs, excluded from Git |

## Interpretation and limitations

- A vegetation cycle is not automatically a crop or rice season.
- NDVI threshold defaults are hypotheses for calibration, not validated national
  parameters. Evergreen vegetation, weeds, floods and mixed pixels can mislead.
- Optical gaps remain a major monsoon limitation. Radar-aware event comparison
  is available, but it is not independently validated crop phenology.
- Satellite green-up and decline do not equal exact transplanting and harvest.
- Calendar seasons differ between references. This project retains dates rather
  than forcing every crop into a fixed season window.
- Sampling only a few polygons cannot establish district-wide cropping intensity.

Read [methods and validation](docs/methods.md) before using outputs in research.

## Data and attribution

Satellite collections: `COPERNICUS/S2_SR_HARMONIZED` and `COPERNICUS/S1_GRD`.
Consult their Earth Engine catalog documentation for processing and attribution.
The supplied AgriclimateBD CSV and dictionary have not been redistributed:
their license, source year, original agricultural units and climate extraction
details still require confirmation.

The implementation here is original starter code. Ahrari's
[Earth Engine tutorial repository](https://github.com/AmirhosseinAhrari/GoogleEarthEngine)
was inspected as background; its scripts are not bundled.

## Development roadmap

- [x] Reproducible reference-data audit
- [x] Configurable satellite time-series export
- [x] Conservative NDVI cycle detector and synthetic tests
- [x] Inspect the first user-run Earth Engine export (Barguna)
- [ ] Collect dated crop and field-boundary validation records
- [ ] Calibrate parameters across contrasting agroecological zones
- [x] Implement radar-aware event comparison, uncertainty flags and plots
- [ ] Calibrate and validate radar/optical integration against independent observations
- [ ] Produce validated field and regional maps

Code is MIT licensed. This does not grant rights to third-party datasets.
