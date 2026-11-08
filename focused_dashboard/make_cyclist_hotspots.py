"""
Step A of the focused dashboard: the hotspot squares for CYCLISTS (3b/3c with a cyclist filter).

The main project only has 500 m hotspot squares for pedestrians, motorcycles and mopeds (script 14). This script repeats exactly that method
for cyclists and adds the results to the focused dashboard's own files:
  results/geo_hotspots_bicycle.csv   the 20 busiest squares (same columns as the other three groups)
  results/geo_coverage.csv           + two rows: how many cyclist accidents have usable coordinates (all years and 2022-2024)
  data/hotspot_cells.csv             + the accident count of every 500 m square for cyclists (for the heat map)

To prove that the method is the same, the script first recalculates the pedestrians and checks that it reproduces the saved numbers.

Decisions applied: #33 counting (road user 1 OR 2), #83 two periods, #86 500 m squares in Belgian Lambert 1972, #87 top 20 with the municipality named, #90 impossible coordinates are treated as missing.

How to run (from this folder, with `conda activate syntra-ds`; the argument is the accident file of the main project):
    python make_cyclist_hotspots.py "../OPENDATA_MAP_2017-2024_en_flagged.csv.gz"
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
accidents_file = sys.argv[1]

CELL = 500
SCOPES = {"2017-2024": range(2017, 2025), "2022-2024": range(2022, 2025)}
CODES = {"Pedestrian": "08", "Bicycle": "03"}  # pedestrians only as the check; Bicycle is the new group

header = pd.read_csv(accidents_file, nrows=0).columns
df = pd.read_csv(accidents_file, dtype={c: str for c in header if c.endswith("_code")})
usable = df["x_coord"].between(20_000, 300_000) & df["y_coord"].between(20_000, 250_000)  # decision #90
df["cx"], df["cy"] = (df["x_coord"] // CELL).where(usable).astype("Int64"), (df["y_coord"] // CELL).where(usable).astype("Int64")


def hotspots(group):
    """For one group: the coverage rows, the squares and the top-20 table of both periods, exactly as in script 14."""
    code = CODES[group]
    involved = (df["road_user_type1_code"] == code) | (df["road_user_type2_code"] == code)
    coverage, cells_all, tops = [], [], []
    for scope, years in SCOPES.items():
        in_scope = involved & df["collision_year"].isin(years)
        used = in_scope & usable
        coverage.append((group, scope, int(in_scope.sum()), int(used.sum()), int(in_scope.sum() - used.sum()), round((in_scope.sum() - used.sum()) / in_scope.sum() * 100, 2)))
        sub = df[used]
        cells = sub.groupby(["cx", "cy"]).size().rename("accidents").reset_index().sort_values(["accidents", "cx", "cy"], ascending=[False, True, True]).reset_index(drop=True)
        cells["cx"], cells["cy"] = cells["cx"].astype(int), cells["cy"].astype(int)
        assert cells["accidents"].sum() == len(sub), "cell counts do not add up to the located accidents"
        top = cells.head(20).copy()
        top.insert(0, "rank", range(1, len(top) + 1))
        top["municipality"] = [sub[(sub["cx"] == r.cx) & (sub["cy"] == r.cy)]["municipality"].mode().iat[0] for r in top.itertuples()]  # most common municipality in the square
        top["centre_x_m"], top["centre_y_m"] = top["cx"] * CELL + CELL / 2, top["cy"] * CELL + CELL / 2
        top["share_of_located_pct"] = top["accidents"] / len(sub) * 100
        all_in_cell = df[usable & df["collision_year"].isin(years)].groupby(["cx", "cy"]).size()
        top["all_accidents_in_square"] = [int(all_in_cell.get((r.cx, r.cy), 0)) for r in top.itertuples()]
        top["group_share_of_square_pct"] = top["accidents"] / top["all_accidents_in_square"] * 100
        top.insert(0, "scope", scope)
        tops.append(top.drop(columns=["cx", "cy"]))
        cells_all.append(cells.assign(group=group, scope=scope)[["group", "scope", "cx", "cy", "accidents"]])
    return coverage, pd.concat(cells_all), pd.concat(tops)


# 1. The check: the pedestrians must come out exactly as in the saved files of the main project
cov_p, cells_p, top_p = hotspots("Pedestrian")
saved_top = pd.read_csv(HERE / "results" / "geo_hotspots_pedestrian.csv")
assert top_p["accidents"].tolist() == saved_top["accidents"].tolist(), "pedestrian hotspots differ from the saved results"
assert top_p["municipality"].tolist() == saved_top["municipality"].tolist(), "pedestrian hotspot municipalities differ from the saved results"
saved_cov = pd.read_csv(HERE / "results" / "geo_coverage.csv")
saved_cov = saved_cov[saved_cov["group"] == "Pedestrian"].reset_index(drop=True)
assert [list(c[2:5]) for c in cov_p] == saved_cov[["accidents", "with_coordinates", "left_out"]].values.tolist(), "pedestrian coverage differs"
print("Check passed: the method reproduces the saved pedestrian hotspots exactly.")

# 2. The cyclists
cov_b, cells_b, top_b = hotspots("Bicycle")
top_b.to_csv(HERE / "results" / "geo_hotspots_bicycle.csv", index=False, float_format="%.2f")
coverage = pd.read_csv(HERE / "results" / "geo_coverage.csv")
coverage = pd.concat([coverage[coverage["group"] != "Bicycle"], pd.DataFrame(cov_b, columns=coverage.columns)], ignore_index=True)
coverage.to_csv(HERE / "results" / "geo_coverage.csv", index=False)
cells = pd.read_csv(HERE / "data" / "hotspot_cells.csv")
cells = pd.concat([cells[cells["group"] != "Bicycle"], cells_b], ignore_index=True)
cells.to_csv(HERE / "data" / "hotspot_cells.csv", index=False)

for scope in SCOPES:
    t = top_b[top_b["scope"] == scope]
    c = [x for x in cov_b if x[1] == scope][0]
    print(f"Cyclists, {scope}: {c[2]:,} accidents, {c[3]:,} with coordinates ({100 - c[5]:.1f}%); busiest square {t['municipality'].iat[0]} with {t['accidents'].iat[0]} accidents; "
          f"top-20 municipalities: {', '.join(t['municipality'].value_counts().head(4).index)}")
