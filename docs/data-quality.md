# AgriclimateBD audit

Inspected inputs: `AgriclimateBD.csv` and `AgriclimateBD_data_dictionary.pdf`,
supplied by the project owner. Source files are not committed. See
`agriclimate-audit.json` for reproducible counts.

## Observed structure

- 4,607 records, 33 columns, 64 districts.
- 72 named crop labels and one erroneous `#REF!` crop label.
- Chattogram has 72 records, representing the district, not city-only fields.
- No year, observation dates or field coordinates/boundaries are supplied.
- Each district/season/crop combination occurs once.

## Issues requiring source clarification

| Finding | Treatment |
| --- | --- |
| Maximum humidity is lower than minimum humidity in all 4,607 rows | Flag; do not automatically swap labels |
| 416 `#DIV/0!` AP ratios and 416 zero-area records | Undefined ratio, not zero yield |
| One `#REF!` crop name in Noakhali | Recover from source before crop-specific use |
| All 4,191 calculable AP ratios match production/area | Interpret as yield only after verifying units |
| Crop growth/harvest calendars and temperature/humidity entries repeat across districts within each crop label | Do not assume locally observed phenology/weather |
| Observation year is absent | Do not align climate and production with an arbitrary satellite year |
| Dictionary lists solar radiation in kWh/m²/day | Verify the original NASA POWER parameter and units |
| Area is labelled hectares; production metric tonnes | Verify against the original agricultural tables before area/yield comparison |

No blank cells were found, but spreadsheet errors and unspecified calendar
descriptions are still unusable observations. Completeness is not validity.

## Calendar as supplied

| Crop | Transplant | Growth | Harvest |
| --- | --- | --- | --- |
| Aus | March | April–July | August |
| Aman | June | July–October | November–December |
| Boro | November | December–March | April |

Dataset season windows: Kharif 1 = March–July; Kharif 2 = July–November;
Rabi = November–March. These differ from the mid-month seasonal definitions
discussed earlier. Treat windows as reference conventions, not training labels.

Perennial crops must not be treated as short annual cropping cycles. Recover
crop-specific meaning before parsing every `Transplant` entry as transplanting.
