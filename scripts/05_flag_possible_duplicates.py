"""
Step 05 - Flag possible duplicates (decisions #25, #27 and #28). No row is removed.

What this script does
---------------------
It adds ONE column, `is_possible_duplicate`, to the English dataset and saves a NEW file.
  - A row is a possible duplicate when it is identical in all 31 columns to an EARLIER row
    in the file AND it has coordinates.
  - Only the later copies are True (32 rows). The first row of each group stays False (#27).
  - Rows with empty coordinates are never flagged: they only look identical because
    the coordinates are empty (see step 04).
The step-2 file stays untouched (#28).

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/05_flag_possible_duplicates.py OPENDATA_MAP_2017-2024_en.csv.gz OPENDATA_MAP_2017-2024_en_flagged.csv.gz
"""
import sys

import pandas as pd

input_file = sys.argv[1]   # the English dataset from step 02
output_file = sys.argv[2]  # the new file with the extra column

# --- 1. Read everything as text so that NO value can change (no "1" -> "1.0", no rounded coordinates) ---
df = pd.read_csv(input_file, dtype=str)
original = df.copy()  # kept to prove at the end that the 31 original columns are unchanged

# --- 2. Find the later copies ---
# duplicated(keep="first") is True for every row that equals an EARLIER row in all columns.
later_copy = df.duplicated(keep="first")
has_coordinates = df["x_coord"].notna()

# --- 3. Add the flag column ---
df["is_possible_duplicate"] = later_copy & has_coordinates

# --- 4. Checks ---
n_flagged = int(df["is_possible_duplicate"].sum())
# Step 04 found 62 rows in 30 groups, so 62 - 30 = 32 later copies are expected.
assert n_flagged == 32, f"expected 32 flagged rows, got {n_flagged}"
assert len(df) == len(original), "row count changed"
assert df.drop(columns="is_possible_duplicate").equals(original), "an original column changed"

# --- 5. Save and report ---
df.to_csv(output_file, index=False, encoding="utf-8")
print(f"Rows: {len(df):,}  Columns: {df.shape[1]}")
print(f"Flagged as possible duplicate: {n_flagged} rows ({n_flagged / len(df) * 100:.3f}%)")
print("All checks passed. Saved:", output_file)
