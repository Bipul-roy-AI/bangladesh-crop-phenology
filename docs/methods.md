# Methods and validation plan

## Question

When do observable vegetation growth episodes occur on sampled Bangladeshi
cropland, and how many independently verified crop cycles occur per reporting year?

## Current implementation

The Earth Engine script masks Sentinel-2 pixels using SCL classes 4, 5 and 6,
then produces 15-day median NDVI composites. Cloud-edge contamination can remain;
inspect observations and consider cloud-probability masks in a subsequent version.
Each sample receives mean NDVI and valid-pixel count. Count measures spatial
support, not number of valid observation days. Review scene counts and partial
field coverage before trusting a series.

Sentinel-1 IW VV/VH data are restricted to descending passes and one relative
orbit, selected as the smallest available orbit number. This is a reproducible
starter rule, not proof of adequate coverage: inspect coverage and select the
appropriate local orbit. Radar medians are in the collection's dB units.

The Python detector uses a local three-observation median where neighbours exist
without long gaps. Missing values are never filled. It uses a 10th-percentile
baseline and a threshold 35% of the way from baseline to maximum NDVI.
An accepted episode requires observed threshold crossings, at least 0.20 peak
amplitude above baseline, and 40–240 days duration. Defaults require calibration.
The event end is the first subsequent below-threshold composite. Neighbouring
peaks without an intervening threshold decline remain one episode.

Cycles are assigned to the reporting year by peak date. Missing composites,
cadence gaps, incomplete episodes or insufficient annual coverage result in a
null annual count. Complete episodes can still be inspected separately.
This conservatism may exclude otherwise useful seasons during the monsoon.

No crop classifier, phenological-stage model, field segmentation or operational
radar/optical fusion is implemented yet. The code does not calculate district-wide
cropping intensity from the provided agricultural table.

## Validation required before publication of maps

1. Obtain permissioned field polygons and crop identities with dated planting,
   establishment and harvest records for the selected year.
2. Sample single, double and triple cropping; fallow land; perennial vegetation;
   irrigated and rainfed areas; and seasonally inundated fields.
3. Separate calibration and evaluation by field and spatial group. For national
   transfer claims, hold out regions and preferably another year.
4. Report timing bias/MAE in days, cycle-count confusion matrices, and precision/
   recall for each validated crop label. Include unclassified/gapped samples.
5. Report performance by season and region, optical coverage, pixel/field size
   and sensitivity to compositing, threshold and duration settings.
6. Compare mapped area only with independently verified, year-matched statistics.
   Statistical totals alone do not validate field locations or crop sequences.

## Reuse and execution

Cloud tasks already have isolated checkouts. Use the existing checkout; do not
create worktrees unless requested. Local tools need no service process. Earth
Engine access, a configured project and authorization are necessary for exports;
no credentials belong in this repository.
