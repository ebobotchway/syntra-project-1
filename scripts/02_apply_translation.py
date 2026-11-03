"""
Step 02 - Apply the approved translation and save the English dataset.

What this script does
---------------------
It reads the ORIGINAL data plus the two approved review files from step 01
(translation/translation_table.csv and translation/column_names.csv) and writes a NEW file
with English column names and English category texts. The original file is not changed.

Decisions applied (see beslissingslogboek.md):
  #4  column names and category values are translated; municipality names are not.
  #5  each French/Dutch pair becomes ONE English column; the CD_ code columns are kept.
  #8  region and province in English, municipality in Dutch.
  #10 column names in lowercase snake_case.
  #11 hour 99 (unknown) becomes empty; the 3 rows stay in the table.
  #16 year, month and hour are whole numbers; code columns stay text.

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/02_apply_translation.py OPENDATA_MAP_2017-2024.csv.gz translation OPENDATA_MAP_2017-2024_en.csv.gz
"""
import sys

import pandas as pd

input_file = sys.argv[1]      # original gzipped CSV (French + Dutch)
translation_dir = sys.argv[2]  # folder with the approved review files from step 01
output_file = sys.argv[3]     # the new English file

# --- 1. Read the original data and the approved translation files ---
# dtype=str: keep everything as text for now so no value is changed by accident.
df = pd.read_csv(input_file, dtype=str)

# keep_default_na=False: an empty code (for region/province) must stay "" and not become NaN.
table = pd.read_csv(f"{translation_dir}/translation_table.csv", dtype=str, keep_default_na=False)
column_names = pd.read_csv(f"{translation_dir}/column_names.csv", dtype=str)

# --- 2. Start the new table with the columns that are only renamed ---
out = pd.DataFrame(index=df.index)  # same rows, same order as the original
out["collision_year"] = df["DT_YEAR_COLLISION"]
out["collision_month"] = df["DT_MONTH_COLLISION"]
out["collision_hour"] = df["DT_TIME"].replace("99", pd.NA)  # decision #11: 99 = unknown -> empty
out["municipality_nis_code"] = df["CD_NIS"]
out["municipality"] = df["TX_MUNTY_COLLISION_NL"]  # decision #8: Dutch name
out["x_coord"] = df["MS_X_COORD"]  # untouched, missing values stay empty
out["y_coord"] = df["MS_Y_COORD"]

# --- 3. Region and province: look up the English name by the French text ---
for field, fr_col in [("region", "TX_RGN_COLLISION_FR"), ("province", "TX_PROV_COLLISION_FR")]:
    rows = table[table["field"] == field]
    lookup = dict(zip(rows["french"], rows["english"]))
    out[field] = df[fr_col].map(lookup)  # missing provinces stay missing (NaN maps to NaN)

# --- 4. The 11 code + text fields: keep the code, add the English text ---
CODE_COLUMNS = {  # new field name -> code column in the original data
    "crossway": "CD_CROSSWAY",
    "weather": "CD_WEATHER",
    "road_condition": "CD_ROAD_CONDITION",
    "built_up_area": "CD_BUILD_UP_AREA",
    "light_condition": "CD_LIGHT_CONDITION",
    "road_type": "CD_ROAD_TYPE",
    "accident_class": "CD_CLASS_ACCIDENTS",
    "road_user_type1": "CD_ROAD_USR_TYPE1",
    "road_user_type2": "CD_ROAD_USR_TYPE2",
    "collision_type": "CD_COLLISION_TYPE",
    "obstacle": "CD_OBSTACLES",
}
for field, code_col in CODE_COLUMNS.items():
    rows = table[table["field"] == field]
    lookup = dict(zip(rows["code"], rows["english"]))  # code -> English text
    out[f"{field}_code"] = df[code_col]
    out[field] = df[code_col].map(lookup)

# --- 5. Put the columns in the approved order (from column_names.csv) ---
out = out[column_names["new_column"].tolist()]

# --- 6. Year, month, hour become whole numbers (decision #16) ---
# "Int64" (capital I) is pandas' whole-number type that allows empty values.
for col in ["collision_year", "collision_month", "collision_hour"]:
    out[col] = pd.to_numeric(out[col]).astype("Int64")

# --- 7. Checks: stop with an error if anything went wrong ---
assert len(out) == len(df), "row count changed"
assert out.shape[1] == len(column_names) == 31, "unexpected number of columns"

# Every translated text must exist wherever the source had a value.
for field in list(CODE_COLUMNS) + ["region"]:
    assert out[field].notna().all(), f"{field}: some values were not translated"
# Province may be empty ONLY where it was empty in the source (30,022 rows).
assert out["province"].isna().sum() == df["TX_PROV_COLLISION_FR"].isna().sum(), "province missing count changed"
assert out["x_coord"].isna().sum() == df["MS_X_COORD"].isna().sum(), "coordinate missing count changed"
assert out["collision_hour"].isna().sum() == (df["DT_TIME"] == "99").sum(), "hour missing count unexpected"

# Codes must be unchanged compared with the original.
for field, code_col in CODE_COLUMNS.items():
    assert (out[f"{field}_code"] == df[code_col]).all(), f"{field}_code changed"

# --- 8. Save as gzipped CSV (decision #6) and report ---
out.to_csv(output_file, index=False, encoding="utf-8")
print(f"Rows: {len(out):,}  Columns: {out.shape[1]}")
print(f"Missing province: {out['province'].isna().sum():,}  Missing coordinates: {out['x_coord'].isna().sum():,}  Missing hour: {out['collision_hour'].isna().sum()}")
print("All checks passed. Saved:", output_file)
