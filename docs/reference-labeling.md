# Independent reference labeling: Barguna 2025

The project owner can identify crops. This package records those identifications
without treating the detector's output as truth. All reference labels start blank.

## Files for the reviewer

Download the review package and open `location_atlas.html` locally. The coordinate
index includes all 50 locations; the Google Earth link locates each point but does
not automatically select a dated historical image. It is not proof of 2025 land use.

Open `annual_reference.csv` in a spreadsheet. For an initial batch, review any five
locations you actually know. Record only supported information:

| Column | How to fill |
| --- | --- |
| `sample_id`, coordinates, district, year | Keep supplied identifiers unchanged |
| `reference_land_cover` | `cropland`, `noncrop`, `mixed`, or `uncertain` |
| `crop_sequence_2025` | Crops and fallow periods you know, in chronological order; add approximate months if known |
| `annual_review_complete` | `yes` only if you can account for the entire 2025 reporting year; otherwise `no` or `uncertain` |
| `reference_cycle_count` | Leave blank unless the entire year is established; 0 means verified no crop cycles, not unknown |
| `source_type` | `field_record`, `farmer_record`, `local_knowledge`, `independent_imagery`, `multiple`, or `other` |
| `source_reference` | Record/document identifier, imagery identifier or description of local knowledge; avoid private contact details |
| `source_dates` | Dates or period actually supported by that evidence |
| `reviewer`, `review_date` | Reviewer identifier and ISO date, YYYY-MM-DD |
| `notes` | Uncertain crop identity, mixed pixels, approximate dates, changed land use, etc. |

Do not copy a suggested crop or cycle count from prototype outputs. Crop identity
alone does not establish how many crops grew at the same point during the year.
Partial labels remain useful; do not invent dates to complete the worksheet.

Use `episode_reference.csv` optionally for observed crop intervals. Exact dates
may remain blank; record approximate descriptions and uncertainty in notes.
`date_uncertainty_days` should reflect evidence, not model resolution. The checker
currently validates the annual worksheet only, not the optional episode file.

Annual cycles in this project are assigned by their growth peak in 2025. Crops
crossing year boundaries need particular care; if the year assignment cannot be
established, leave the annual count blank and describe the sequence instead.

## Scientific independence

Local knowledge and farmer recall are valuable but have different uncertainties
from dated field records. Dated image interpretation should record sensor and
acquisition date; interpretation of the same imagery used by the detector is not
fully independent of its sensor errors. A single current image cannot validate
2025 crops, fallow periods or a whole year's cycle count.

## Check a completed or partially completed worksheet

```bash
PYTHONPATH=src python -m bdphenology.cli check-reference annual_reference.csv \
  --year 2025 --output data/derived/reference_check.json
```

The checker reports blank, invalid, uncertain and structurally complete rows. It
never generates accuracy from blank labels. Passing checks is not verification
that the underlying evidence is correct. Identified invalid entries must be fixed
before a row is used in validation.

## Spatial split for later analysis

The package GeoJSON assigns entire 0.1-degree spatial blocks to calibration or
evaluation using a fixed hash seed. This creates 36 planned calibration and 14
planned evaluation samples across 17 blocks for this export. These are initial
roles, not guarantees of independence; adjacent blocks can share correlated
conditions and may require buffers or revised region-level splits.

The reviewer worksheet and atlas omit detector predictions and split roles.
Keep evaluation labels separate from threshold tuning. Candidate-guided selection
or incomplete labeling can bias performance estimates. Full samples and uncertain
cases must be reported when evaluating the final method.

## Recreate an empty package

```bash
PYTHONPATH=src python -m bdphenology.cli reference \
  data/raw/bangladesh_phenology_2025_district_0.csv --year 2025 \
  --output-dir data/derived/new_reference_package
```

The destination must be empty. The command refuses to overwrite existing labels.
