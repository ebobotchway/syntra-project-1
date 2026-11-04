"""
Step 04 - Two read-only checks (decisions #23 and #24). Nothing is changed.

  A. How are the EMPTY COORDINATES spread over year, region and accident severity?
     We only show percentages next to the overall share; you judge whether it looks even.
  B. A close look at the rows that are identical in all 31 columns AND have coordinates
     (the "probable duplicates" from step 03).

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/04_check_coordinates_and_duplicates.py OPENDATA_MAP_2017-2024_en.csv.gz reports
"""
import sys
from pathlib import Path

import pandas as pd

input_file = sys.argv[1]  # the English dataset from step 02
output_dir = Path(sys.argv[2])  # same reports/ folder as step 03
output_dir.mkdir(exist_ok=True)

# --- 1. Read the data (code columns as text so "01" keeps its zero) ---
header = pd.read_csv(input_file, nrows=0).columns
df = pd.read_csv(input_file, dtype={c: str for c in header if c.endswith("_code")})

# =====================================================================
# A. Empty coordinates by year, region and severity
# =====================================================================
# x and y should be empty together; if not, one column alone would tell a different story.
assert (df["x_coord"].isna() == df["y_coord"].isna()).all(), "x and y are not empty together"
df["coord_empty"] = df["x_coord"].isna()  # True where the coordinates are empty

overall = df["coord_empty"].mean() * 100
print(f"A. Empty coordinates overall: {df['coord_empty'].sum():,} of {len(df):,} rows = {overall:.2f}%\n")

# For each variable: how many rows, how many empty, and the share of empty rows.
# 'accident_class' is grouped by its code first so the order follows the severity codes 1-4.
variables = {
    "collision_year": ["collision_year"],
    "region": ["region"],
    "accident_class": ["accident_class_code", "accident_class"],
}
parts = []
for name, group_columns in variables.items():
    table = df.groupby(group_columns).agg(rows=("coord_empty", "size"), empty=("coord_empty", "sum"))
    table["percent_empty"] = (table["empty"] / table["rows"] * 100).round(2)
    table["points_vs_overall"] = (table["percent_empty"] - overall).round(2)  # difference in percentage points
    print(f"By {name}:")
    print(table.to_string(), "\n")
    # Save in one tidy table: variable, group label, then the numbers.
    tidy = table.reset_index()
    tidy.insert(0, "variable", name)
    tidy["group"] = tidy[group_columns[-1]].astype(str)  # the readable label (text or year/region)
    parts.append(tidy[["variable", "group", "rows", "empty", "percent_empty", "points_vs_overall"]])

pd.concat(parts).to_csv(output_dir / "coordinates_empty_by_group.csv", index=False)

# =====================================================================
# B. Probable duplicates: identical in all 31 columns, with coordinates
# =====================================================================
all_columns = [c for c in df.columns if c != "coord_empty"]  # the 31 original columns
identical_twin = df.duplicated(subset=all_columns, keep=False)  # every row that has an identical twin
probable = df[identical_twin & df["x_coord"].notna()].copy()

# Give every group of identical rows a number, and remember where each row sits in the file.
# dropna=False: an empty province or hour must still count as "the same" inside a group.
probable["group_id"] = probable.groupby(all_columns, dropna=False).ngroup() + 1
probable["row_in_file"] = probable.index + 2  # +1 for the header line, +1 because lines start at 1
probable = probable.sort_values(["group_id", "row_in_file"])

sizes = probable.groupby("group_id").size()
spread = probable.groupby("group_id")["row_in_file"].agg(lambda s: s.max() - s.min())  # distance between first and last copy

print(f"B. Probable duplicates (identical in all 31 columns, coordinates present): {len(probable)} rows in {len(sizes)} groups")
print("Group sizes:", sizes.value_counts().sort_index().to_dict(), "(size: number of groups)")
print(f"Distance in the file between first and last copy of a group: min {spread.min()}, median {spread.median():.0f}, max {spread.max()} lines")
print(f"Groups whose copies sit directly next to each other (distance 1): {(spread == 1).sum()} of {len(sizes)}\n")

# Show the first 12 groups with the most informative columns.
show = ["group_id", "row_in_file", "collision_year", "collision_month", "collision_hour",
        "municipality", "accident_class", "collision_type", "x_coord", "y_coord"]
first_groups = probable["group_id"].unique()[:12]
print("First 12 groups (all 31 columns are saved in the CSV):")
print(probable[probable["group_id"].isin(first_groups)][show].to_string(index=False))

# Save the complete rows so you can open them in Excel.
probable[["group_id", "row_in_file"] + all_columns].to_csv(output_dir / "probable_duplicates.csv", index=False)
print(f"\nSaved 2 files in {output_dir}/")
