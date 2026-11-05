"""
Step 18 - Export the small data files that the dashboards need for the maps of steps 2-4 (decisions #109-#113).

The dashboards show SAVED results (#110). For the maps they also need geometry and a few point lists, in a form that needs no mapping library:
  data/municipality_outlines.json   one outline per municipality (Statbel, CC BY 4.0; rounded to 20 m), with its name, region, province and a label position
  data/province_outlines.json       the 10 provinces + Brussels, made from the municipality outlines
  data/hotspot_cells.csv            accidents per 500 m square for pedestrians, motorcycles and mopeds (all years and 2022-2024)
  data/municipality_positions.csv   the average position of each municipality's accidents (for the bubble map)
All coordinates are Belgian Lambert 1972 (EPSG:31370, metres), like the accident data.

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/18_export_dashboard_extra_data.py OPENDATA_MAP_2017-2024_en_flagged.csv.gz data/municipality_outlines.gpkg data
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

accidents_file = sys.argv[1]  # the flagged English dataset from step 05
outlines_file = sys.argv[2]   # the municipality outlines from step 13
output_dir = Path(sys.argv[3])  # the data/ folder

header = pd.read_csv(accidents_file, nrows=0).columns
df = pd.read_csv(accidents_file, dtype={c: str for c in header if c.endswith("_code")})
usable = df["x_coord"].between(20_000, 300_000) & df["y_coord"].between(20_000, 250_000)  # decision #90
outlines = gpd.read_file(outlines_file)
CELL = 500
STEP = 20  # coordinates are rounded to 20 m in the outline files


def flat(coords):
    """A ring as one flat list [x0, y0, x1, y1, ...], rounded to 20 m."""
    out = []
    for point in coords:  # some points also carry a height (z); only x and y are needed
        out += [int(round(point[0] / STEP) * STEP), int(round(point[1] / STEP) * STEP)]
    return out


def polygons_of(geometry):
    """All polygons of a geometry as lists of rings (the first ring is the outer border, the others are holes)."""
    parts = geometry.geoms if geometry.geom_type == "MultiPolygon" else [geometry]
    return [[flat(p.exterior.coords)] + [flat(i.coords) for i in p.interiors] for p in parts]


# --- 1. Municipality outlines with names, region and province ---
names = df.groupby("municipality_nis_code").agg(name=("municipality", "first"), region=("region", "first"), province=("province", "first"))
names["province"] = names["province"].fillna("Brussels (no province)")
features = []
for row in outlines.itertuples():
    info = names.loc[row.nis_code]
    label = row.geometry.representative_point()
    features.append({"nis": row.nis_code, "name": info["name"], "region": info["region"], "province": info["province"],
                     "x": int(label.x), "y": int(label.y), "polys": polygons_of(row.geometry)})
assert len(features) == 581, "expected 581 municipalities"
(output_dir / "municipality_outlines.json").write_text(json.dumps({"crs": "EPSG:31370", "source": "Statbel statistical sectors 2023, CC BY 4.0", "features": features}, separators=(",", ":")), encoding="utf-8")

# --- 2. Province outlines (10 provinces + Brussels), dissolved from the municipality outlines ---
outlines["province"] = outlines["nis_code"].map(names["province"])
provinces = outlines.dissolve(by="province").reset_index()
provinces["geometry"] = provinces.geometry.buffer(100).buffer(-100).simplify(150, preserve_topology=True)  # closes the tiny gaps between the separately simplified outlines, then keeps the shape light
province_features = []
for row in provinces.itertuples():
    label = row.geometry.representative_point()
    province_features.append({"name": row.province, "x": int(label.x), "y": int(label.y), "polys": polygons_of(row.geometry)})
assert len(province_features) == 11, "expected 10 provinces + Brussels"
(output_dir / "province_outlines.json").write_text(json.dumps({"crs": "EPSG:31370", "source": "Statbel statistical sectors 2023, CC BY 4.0", "features": province_features}, separators=(",", ":")), encoding="utf-8")

# --- 3. Accidents per 500 m square for the three hotspot groups ---
GROUPS = {"Pedestrian": "08", "Motorcycle": "07", "Moped": "06"}
SCOPES = {"2017-2024": range(2017, 2025), "2022-2024": range(2022, 2025)}
rows = []
for group, code in GROUPS.items():
    involved = (df["road_user_type1_code"] == code) | (df["road_user_type2_code"] == code)  # road user 1 OR 2
    for scope, years in SCOPES.items():
        sub = df[involved & df["collision_year"].isin(years) & usable]
        cells = sub.assign(cx=(sub["x_coord"] // CELL).astype(int), cy=(sub["y_coord"] // CELL).astype(int)).groupby(["cx", "cy"]).size().rename("accidents").reset_index()
        assert cells["accidents"].sum() == len(sub), "cell counts do not add up"
        cells.insert(0, "scope", scope); cells.insert(0, "group", group)
        rows.append(cells)
hotspot_cells = pd.concat(rows)
hotspot_cells.to_csv(output_dir / "hotspot_cells.csv", index=False)
# check against the hotspot tables of step 14 (rank 1 square must have the same number of accidents)
for group in GROUPS:
    saved = pd.read_csv(f"reports/geo_hotspots_{group.lower()}.csv")
    for scope in SCOPES:
        best = hotspot_cells[(hotspot_cells["group"] == group) & (hotspot_cells["scope"] == scope)]["accidents"].max()
        assert best == saved[(saved["scope"] == scope) & (saved["rank"] == 1)]["accidents"].iat[0], f"{group} {scope}: busiest square differs from step 14"

# --- 4. Average position of the accidents of each municipality (bubble map, decision #82) ---
positions = df[usable].groupby("municipality_nis_code").agg(municipality=("municipality", "first"), bubble_x=("x_coord", "mean"), bubble_y=("y_coord", "mean")).round(1)
assert len(positions) == 581, "a municipality has no usable coordinates"
positions.to_csv(output_dir / "municipality_positions.csv")

# --- 5. Area of each municipality in km2 (for accidents per km2 in the interactive tool) ---
areas = outlines.assign(area_km2=outlines.geometry.area / 1e6)[["nis_code", "area_km2"]].rename(columns={"nis_code": "municipality_nis_code"})
assert len(areas) == 581 and 30_600 < areas["area_km2"].sum() < 30_800, "the areas do not add up to the size of Belgium"
areas.round(4).to_csv(output_dir / "municipality_areas.csv", index=False)

for name in ("municipality_outlines.json", "province_outlines.json", "hotspot_cells.csv", "municipality_positions.csv", "municipality_areas.csv"):
    print(f"{name}: {(output_dir / name).stat().st_size / 1e6:.2f} MB")
print(f"Checks passed: 581 municipalities, 11 province areas, hotspot squares match step 14, {len(hotspot_cells):,} squares in total.")
