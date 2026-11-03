"""
Step 03 - Explore missing values and duplicates (report only, nothing is changed).

What this script does
---------------------
It reads the English dataset from step 02 and reports:
  A. Truly empty cells per column                  (decision #18)
  B. "Unknown" categories per field                (decisions #18 and #22)
  C. Duplicate rows under three definitions        (decision #19)
No rows are removed and no values are filled in (decision #20).
The results are printed and saved as small CSV files in the reports/ folder (decision #21).

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/03_explore_missing_and_duplicates.py OPENDATA_MAP_2017-2024_en.csv.gz reports
"""
import sys
from pathlib import Path

import pandas as pd

input_file = sys.argv[1]  # the English dataset from step 02
output_dir = Path(sys.argv[2])  # folder for the saved report files
output_dir.mkdir(exist_ok=True)

# --- 1. Read the data ---
# Columns that hold codes must be read as text, otherwise "01" would become 1.
header = pd.read_csv(input_file, nrows=0).columns
code_columns = [c for c in header if c.endswith("_code")]
df = pd.read_csv(input_file, dtype={c: str for c in code_columns})
total_rows = len(df)
print(f"Rows: {total_rows:,}   Columns: {df.shape[1]}\n")

# =====================================================================
# A. Truly empty cells
# =====================================================================
# isna() is True for every empty cell. We count them per column.
empty = pd.DataFrame({
    "empty_cells": df.isna().sum(),
    "percent_of_rows": (df.isna().mean() * 100).round(2),
})
empty.index.name = "column"
print("A. Truly empty cells per column (only columns with at least one):")
print(empty[empty["empty_cells"] > 0].to_string(), "\n")
empty.to_csv(output_dir / "missing_empty_cells.csv")

# =====================================================================
# B. "Unknown" categories (decision #22)
# =====================================================================
# For each field: the codes that mean "unknown / not specified". Codes are text.
UNKNOWN_CODES = {
    "crossway": ["9"],
    "built_up_area": ["9"],
    "road_type": ["9"],
    "weather": ["9"],
    "road_condition": ["9"],
    "light_condition": ["9"],
    "road_user_type1": ["99"],
    "road_user_type2": ["99"],
    "collision_type": ["0", "9"],  # 9 = "Other or unknown": ambiguous, flagged below
    "obstacle": ["99", "-1", "-3"],
    # accident_class has no unknown category
}

rows = []
for field, codes in UNKNOWN_CODES.items():
    for code in codes:
        in_this_code = df[f"{field}_code"] == code
        # The English text for this code (first row that has it), so the report is readable.
        text = df.loc[in_this_code, field].iloc[0] if in_this_code.any() else "(code not present)"
        rows.append((field, code, text, int(in_this_code.sum()), round(in_this_code.mean() * 100, 2)))

unknown = pd.DataFrame(rows, columns=["field", "code", "english_text", "rows", "percent_of_rows"])

# Per field total: a row counts once even if it matches more than one unknown code.
# (Codes in one field exclude each other, so the sum is exact; this keeps the check honest.)
unknown.to_csv(output_dir / "missing_unknown_categories.csv", index=False)
print('B. "Unknown" categories (one line per code):')
print(unknown.to_string(index=False))
print("Note: collision_type code 9 means 'Other or unknown', so it is ambiguous.\n")

# =====================================================================
# C. Duplicates under three definitions (decision #19)
# =====================================================================
DEFINITIONS = {
    "1_all_31_columns": list(df.columns),
    "2_all_except_coordinates": [c for c in df.columns if c not in ("x_coord", "y_coord")],
    "3_year_month_hour_municipality": ["collision_year", "collision_month", "collision_hour", "municipality_nis_code"],
}

result_rows = []
for name, columns in DEFINITIONS.items():
    # duplicated(keep=False) marks EVERY row that has at least one identical twin.
    in_a_group = df.duplicated(subset=columns, keep=False)
    # duplicated(keep="first") marks only the EXTRA copies (the first row of each group is not marked).
    extra_copies = df.duplicated(subset=columns, keep="first")
    # Size of each group of identical rows (groups of 1 are not duplicates).
    group_sizes = df[in_a_group].groupby(columns, dropna=False).size()
    result_rows.append((
        name,
        len(columns),
        int(in_a_group.sum()),
        round(in_a_group.mean() * 100, 2),
        int(extra_copies.sum()),
        round(extra_copies.mean() * 100, 2),
        len(group_sizes),
        int(group_sizes.max()) if len(group_sizes) else 0,
    ))

duplicates = pd.DataFrame(result_rows, columns=[
    "definition", "columns_compared",
    "rows_in_a_duplicate_group", "percent_in_group",
    "extra_copies", "percent_extra",
    "number_of_groups", "largest_group",
])
duplicates.to_csv(output_dir / "duplicates.csv", index=False)
print("C. Duplicates:")
print(duplicates.to_string(index=False))
print("\n'rows_in_a_duplicate_group' counts every row that has an identical twin.")
print("'extra_copies' counts only the surplus rows (what you would drop if you kept one per group).")
print(f"\nSaved 3 files in {output_dir}/")
