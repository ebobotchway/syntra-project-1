"""
Step 10 - Build the small summary table that feeds the dashboard (decisions #60-#68).

The dashboard does not need the 289,532 accidents themselves. Everything it shows (totals, annual change,
monthly and seasonal distributions) can be rebuilt from ONE small table:
accidents per road-user group, per year, per month (11 lines x 8 years x 12 months = 1,056 rows).

Counting rules from step 07 (#33-#35): an accident counts once for every road-user group it involves
(road user 1 OR road user 2); "All accidents" counts every accident once; all 289,532 rows are used.

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/10_build_dashboard_data.py OPENDATA_MAP_2017-2024_en_flagged.csv.gz reports data/dashboard_data.csv
"""
import sys
from pathlib import Path

import pandas as pd

input_file = sys.argv[1]   # the flagged English dataset from step 05
reports_dir = Path(sys.argv[2])  # reports/ folder with the results of steps 07 and 08 (used for checking)
output_file = Path(sys.argv[3])  # the summary table for the dashboard
output_file.parent.mkdir(exist_ok=True)

# --- 1. Read the data (code columns as text so "01" keeps its zero) ---
header = pd.read_csv(input_file, nrows=0).columns
df = pd.read_csv(input_file, dtype={c: str for c in header if c.endswith("_code")})
group_names = dict(zip(df["road_user_type1_code"], df["road_user_type1"]))  # code -> name

# --- 2. Count accidents per group, year and month ---
parts = []
for code, name in group_names.items():
    involved = (df["road_user_type1_code"] == code) | (df["road_user_type2_code"] == code)  # road user 1 OR 2
    counts = df[involved].groupby(["collision_year", "collision_month"]).size().rename("accidents").reset_index()
    counts.insert(0, "road_user_group", name)
    parts.append(counts)
everything = df.groupby(["collision_year", "collision_month"]).size().rename("accidents").reset_index()
everything.insert(0, "road_user_group", "All accidents")  # the reference line
parts.append(everything)

table = pd.concat(parts, ignore_index=True).rename(columns={"collision_year": "year", "collision_month": "month"})
# Make sure every group-year-month exists, with 0 where nothing happened.
full_index = pd.MultiIndex.from_product([table["road_user_group"].unique(), sorted(df["collision_year"].unique()), range(1, 13)],
                                        names=["road_user_group", "year", "month"])
table = table.set_index(["road_user_group", "year", "month"]).reindex(full_index, fill_value=0).reset_index()

# --- 3. Checks against the earlier steps ---
step7 = pd.read_csv(reports_dir / "accidents_per_road_user.csv")  # totals per group
totals = table.groupby("road_user_group")["accidents"].sum()
for group, accidents in zip(step7["road_user_group"], step7["accidents"]):
    assert totals[group] == accidents, f"{group}: total differs from step 07"
assert totals["All accidents"] == len(df), "All accidents does not equal the number of rows"

step8 = pd.read_csv(reports_dir / "annual_accidents_by_group.csv", index_col="road_user_group")  # per year
per_year = table.pivot_table(index="road_user_group", columns="year", values="accidents", aggfunc="sum")
for group in step8.index:
    assert (per_year.loc[group].values == step8.loc[group].values).all(), f"{group}: yearly counts differ from step 08"

step9 = pd.read_csv(reports_dir / "distribution_monthly_accidents.csv")  # per month, pooled scope
step9 = step9[step9["scope"] == "pooled_2017_2024"].set_index("road_user_group").drop(columns="scope")
per_month = table.pivot_table(index="road_user_group", columns="month", values="accidents", aggfunc="sum")
for group in step9.index:
    assert (per_month.loc[group].values == step9.loc[group].values).all(), f"{group}: monthly counts differ from step 09"
print("Checks passed: totals, yearly counts and monthly counts match steps 07, 08 and 09.")

# --- 4. Save ---
table.to_csv(output_file, index=False)
print(f"Saved {len(table):,} rows ({table['road_user_group'].nunique()} lines x {table['year'].nunique()} years x 12 months) to {output_file}")
