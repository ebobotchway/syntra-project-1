"""
Step 6 (OpenStreetMap version): the corners of every grid square in longitude and latitude (WGS84), so the squares can be drawn on top of an OpenStreetMap map.

Why: the accident coordinates and the grid are in Belgian Lambert 1972 (EPSG:31370, metres). A web map (OpenStreetMap) works in longitude and latitude (EPSG:4326, degrees),
so every square is converted corner by corner. The square keeps its four corners, so it is drawn slightly rotated, exactly as it lies on the ground.
Only the corners are converted; no accident is moved or recounted. The numbers in results/ do not change.

Input:  results/grid_cells.csv (cx, cy = the square's column and row; the square covers x from cx*side to (cx+1)*side, the same for y)
Output: data/grid_lonlat.csv, one row per size, cx, cy with the four corners (south-west, south-east, north-east, north-west)

How to run (from this folder, with `conda activate syntra-ds`; needs pyproj, which is in the course environment):
    python scripts/06_grid_lonlat.py
"""
from pathlib import Path

import pandas as pd
from pyproj import Transformer

HERE = Path(__file__).resolve().parent.parent
CELL_SIZES = {"5 km2 cells": 5 ** 0.5 * 1000, "5 x 5 km squares": 5000.0}  # the same sizes as in charts.py

cells = pd.read_csv(HERE / "results" / "grid_cells.csv", usecols=["size", "cx", "cy"]).drop_duplicates()
to_lonlat = Transformer.from_crs("EPSG:31370", "EPSG:4326", always_xy=True)  # always_xy: x (east) first, so it returns longitude, latitude

rows = []
for size, side in CELL_SIZES.items():
    c = cells[cells["size"] == size]
    x0, y0 = c["cx"].to_numpy() * side, c["cy"].to_numpy() * side
    corners = {}
    for name, (dx, dy) in {"sw": (0, 0), "se": (side, 0), "ne": (side, side), "nw": (0, side)}.items():
        corners[f"lon_{name}"], corners[f"lat_{name}"] = to_lonlat.transform(x0 + dx, y0 + dy)
    rows.append(pd.DataFrame({"size": size, "cx": c["cx"].to_numpy(), "cy": c["cy"].to_numpy(), **corners}).round(5))
out = pd.concat(rows).sort_values(["size", "cx", "cy"])
out.to_csv(HERE / "data" / "grid_lonlat.csv", index=False)

# Check: Brussels (Lambert x 148698, y 171059 in the hotspot table) must come out near 4.35 E, 50.85 N, and Belgium must lie within its bounding box
lon, lat = to_lonlat.transform(148698.5, 171059.2)
assert 4.2 < lon < 4.5 and 50.7 < lat < 51.0, (lon, lat)
assert out["lon_sw"].between(2.4, 6.5).all() and out["lat_sw"].between(49.4, 51.6).all()
print(f"Saved data/grid_lonlat.csv: {len(out):,} squares; Brussels check {lon:.3f} E, {lat:.3f} N")
