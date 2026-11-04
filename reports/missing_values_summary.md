# Missing values and duplicates: summary

Dataset: Belgian road accidents 2017-2024 (`OPENDATA_MAP_2017-2024.xlsx`), translated to English.
**289,532 rows.** 31 columns in the English file, 32 in the flagged file (one extra flag column).
Numbers in this summary come from the scripts in `scripts/` and the CSV files in `reports/`.
`#n` refers to an entry in `beslissingslogboek.md`, where the decision and the reason are written down.

## Files

| File | What it is | Script |
|---|---|---|
| `OPENDATA_MAP_2017-2024.csv.gz` | Original data (French + Dutch), 45 columns | converted from the xlsx |
| `OPENDATA_MAP_2017-2024_en.csv.gz` | English translation, 31 columns | `01`, `02` |
| `OPENDATA_MAP_2017-2024_en_flagged.csv.gz` | Same plus `is_possible_duplicate`, 32 columns | `05` |
| `translation/` | The 120 approved translations and the 31 column names | `01` |
| `reports/*.csv` | Result tables of the exploration | `03`, `04`, `06` |

## 1. Truly empty cells

| Column | Empty cells | % of rows |
|---|---|---|
| `x_coord`, `y_coord` | 35,881 | 12.39% |
| `province` | 30,022 | 10.37% |
| `collision_hour` | 3 | 0.00% |

All other columns have no empty cells.
- **Province:** Every empty province is a Brussels-Capital Region row. Brussels has no province, so "empty" means "not applicable".
- **Hour:** The 3 empty hours were the value `99` (unknown) in the source (#11).
- **Treatment:** Nothing is filled in or removed (#20). Rows without coordinates are only left out of map and location analyses.

## 2. "Unknown" categories

Counted separately from empty cells (#18, #22). Percentages overlap between fields, so do not add them up.

| Field (codes counted as unknown) | Rows | % of rows |
|---|---|---|
| `road_user_type1` (99) | 28,502 | 9.84% |
| `road_user_type2` (99) | 28,311 | 9.78% |
| `weather` (9) | 27,763 | 9.59% |
| `road_condition` (9) | 24,236 | 8.37% |
| `collision_type` (0 "not specified") | 14,528 | 5.02% |
| `collision_type` (9 "Other or unknown", ambiguous) | 11,140 | 3.85% |
| `obstacle` (-1) | 14,528 | 5.02% |
| `obstacle` (-3) | 11,538 | 3.99% |
| `obstacle` (99) | 342 | 0.12% |
| `built_up_area` (9) | 12,070 | 4.17% |
| `light_condition` (9) | 9,918 | 3.43% |
| `road_type` (9) | 1,502 | 0.52% |
| `crossway` (9) | 4 | 0.00% |

- `collision_type` 0 and `obstacle` -1 are the same 14,528 rows (checked).
- `accident_class` has no unknown category.
- **Treatment:** "Unknown" stays its own category and is not merged into "Other". For each analysis, decide whether to show it or leave it out of a percentage, and state the denominator.

## 3. Duplicates

The data has no accident ID and no day, only year, month and hour. Three definitions were compared (#19):

| Definition | Rows with an identical twin | Surplus copies | Largest group |
|---|---|---|---|
| Identical in all 31 columns | 129 (0.04%) | 66 | 3 |
| Identical except coordinates | 1,981 (0.68%) | 1,010 | 5 |
| Same year, month, hour, municipality | 137,416 (47.46%) | 92,639 | 41 |

- The third definition is not a duplicate test. Many accidents legitimately share municipality and hour.
- Of the 129 rows in definition 1, **67 have empty coordinates** and only look identical because the coordinates are empty. The other **62 have coordinates** (30 groups: 28 pairs, 2 triples) (#23).
- Only 6 of the 30 groups sit directly next to each other in the file. Some neighbouring groups share place and time and differ only in severity or collision type (for example two groups in Borgloon, 2020, month 9, hour 11), which looks like several records of one event. Without a day or ID, these rows cannot be proven to be duplicates (#25).
- **Treatment:** Nothing is deleted. In the flagged file, the later copies of the 30 groups are marked `is_possible_duplicate = True`: **32 rows** (0.011%) (#25, #27, #28). The first row of each group is `False`.

## 4. Empty coordinates are not evenly spread

Overall 12.39% (#24, #26). Share of accidents with empty coordinates, by year and region:

| Year | Brussels | Flemish | Walloon | All |
|---|---|---|---|---|
| 2017 | 14.9 | 13.5 | 19.1 | 15.3 |
| 2018 | 15.8 | 13.4 | 24.6 | 16.8 |
| 2019 | 15.8 | 13.8 | 25.1 | 17.2 |
| 2020 | 14.9 | 16.1 | 26.9 | 19.0 |
| 2021 | 15.2 | 15.3 | 25.6 | 18.3 |
| 2022 | 3.9 | 3.8 | 7.0 | 4.7 |
| 2023 | 2.6 | 2.7 | 4.7 | 3.2 |
| 2024 | **16.4** | 4.0 | 5.8 | 5.8 |

- **Severity:** Even, between 11.4% and 12.7% across the four classes.
- **Year:** Sharp drop between 2021 and 2022 in all regions.
- **Region:** The Walloon Region is above the Flemish Region in every year, so the regional gap is not only the year effect.
- **Brussels 2024:** Jumps from 2.6% in 2023 to 16.4%.
- **Consequence:** Maps, location trends over the years, and comparisons between Wallonia and the other regions are the most affected.
- **Treatment:** All rows are kept. Exclude rows without coordinates only from location analyses, and say so each time.

## 5. Open questions

- **Brussels 2024:** Why do empty coordinates jump to 16.4%? Not investigated (#29). It could be a recording change or a data delivery issue; this is not known.
- **Accident class 1 vs 2:** "With fatalities" and "Fatally injured" are translated literally; the difference is unverified (#15).
- **`collision_type` 9:** "Other or unknown" mixes two meanings (#22).
- **`obstacle` -1:** The source text says "Collision type not specified"; it looks like a copy error in the source (#14).
- **Coordinate system:** The values look like a Belgian grid (probably Lambert 72) but this is not verified.
- **Why the drop in 2022:** The cause of the large fall in empty coordinates after 2021 is unknown.

## How to use the files

```python
import pandas as pd

# Whole numbers with empty values need the "Int64" type; code columns must stay text to keep "01".
header = pd.read_csv("OPENDATA_MAP_2017-2024_en_flagged.csv.gz", nrows=0).columns
dtypes = {c: str for c in header if c.endswith("_code")}
dtypes["collision_hour"] = "Int64"
df = pd.read_csv("OPENDATA_MAP_2017-2024_en_flagged.csv.gz", dtype=dtypes)

df_clean = df[~df["is_possible_duplicate"]]    # without the 32 flagged later copies
df_located = df[df["x_coord"].notna()]         # only for maps / location analyses
```
