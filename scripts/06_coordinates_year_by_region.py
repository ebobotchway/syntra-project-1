"""
Step 06 - Empty coordinates: year x region (decision #26). Read-only, nothing is changed.

Step 04 showed that empty coordinates are more common in 2017-2021 than in 2022-2024,
and more common in the Walloon Region than in the Flemish Region.
Question: is the regional gap just the year effect, or does it exist in every year?
We show three tables (rows, empty, % empty) for every combination of year and region.
You judge the pattern yourself (decision #24); no statistical test.

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/06_coordinates_year_by_region.py OPENDATA_MAP_2017-2024_en.csv.gz reports
"""
import sys
from pathlib import Path

import pandas as pd

input_file = sys.argv[1]  # the English dataset from step 02
output_dir = Path(sys.argv[2])  # the reports/ folder
output_dir.mkdir(exist_ok=True)

# Only the three columns we need.
df = pd.read_csv(input_file, usecols=["collision_year", "region", "x_coord"])
df["coord_empty"] = df["x_coord"].isna()  # True where the coordinates are empty

# One row per (year, region): how many rows, how many with empty coordinates.
table = df.groupby(["collision_year", "region"]).agg(rows=("coord_empty", "size"), empty=("coord_empty", "sum"))
table["percent_empty"] = (table["empty"] / table["rows"] * 100).round(2)
table.reset_index().to_csv(output_dir / "coordinates_empty_year_by_region.csv", index=False)

# Reshape so the years are the rows and the regions are the columns (easier to read).
# margins=True adds a total row/column.
rows_wide = table["rows"].unstack("region")
empty_wide = table["empty"].unstack("region")
percent_wide = (empty_wide / rows_wide * 100).round(1)
percent_wide["All regions"] = (df.groupby("collision_year")["coord_empty"].mean() * 100).round(1)
percent_wide.loc["All years"] = (df.groupby("region")["coord_empty"].mean() * 100).round(1).tolist() + [round(df["coord_empty"].mean() * 100, 1)]

print("Number of accidents (rows):")
print(rows_wide.to_string(), "\n")
print("% with EMPTY coordinates:")
print(percent_wide.to_string(), "\n")
print(f"Saved coordinates_empty_year_by_region.csv in {output_dir}/")
