"""
Step 1b of the hotspot deep dive: the number of residents in every 5 km x 5 km square (decision #183).

Statbel publishes the residents per statistical sector (about 19,800 small areas) on 1 January 2023: OPENDATA_SECTOREN_2023 (CC BY 4.0,
https://statbel.fgov.be/en/open-data/population-statistical-sector-11). The sector codes are those of the Statbel sector map of 2023, which is already in the main project.
Each sector is cut by the 5 x 5 km grid (the same grid as the accident cells: column = floor(x / 5000), row = floor(y / 5000), Belgian Lambert 1972), and the residents of the sector
are shared over the pieces in proportion to their AREA (people are assumed to be spread evenly inside a sector; the sectors are small compared with a 25 km2 square).
A square gets the residents of all the pieces inside it. Script 02 then multiplies the residents of each piece by the growth of its municipality for every year (the residents that year / the residents in 2023).

Checks: every sector of the map has residents, the pieces of a sector add up to its area, and the residents of all squares add up to the Belgian total of 1 January 2023 (11,697,557).

How to run (from the folder hotspot_deep_dive, with `conda activate syntra-ds`; the argument is the Statbel sector map of the main project):
    python -I scripts/01b_cell_residents.py "../data/external/statbel_sectors_2023/sh_statbel_statistical_sectors_31370_20230101.shp/sh_statbel_statistical_sectors_31370_20230101.shp"
"""
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

HERE = Path(__file__).resolve().parent.parent
RAW = HERE / "raw_population"
RAW.mkdir(exist_ok=True)
URL = "https://statbel.fgov.be/sites/default/files/files/opendata/bevolking/sectoren/OPENDATA_SECTOREN_2023.zip"
SIDE = 5000  # metres: the 5 x 5 km squares

path = RAW / "OPENDATA_SECTOREN_2023.zip"
if not path.exists():
    urllib.request.urlretrieve(URL, path)
with zipfile.ZipFile(path) as z:
    raw = z.read(z.namelist()[0])
try:
    text = raw.decode("utf-8-sig")
except UnicodeDecodeError:
    text = raw.decode("cp1252")
pop = pd.read_csv(io.StringIO(text), sep="|", dtype=str)
pop["residents"] = pop["TOTAL"].astype(int)
assert pop["CD_SECTOR"].is_unique, "a sector appears twice in the population file"
total_file = int(pop["residents"].sum())

sectors = gpd.read_file(sys.argv[1])[["CS01012023", "CNIS5_2023", "geometry"]]
assert sectors.crs.to_epsg() == 31370
sectors = sectors.merge(pop[["CD_SECTOR", "residents"]], left_on="CS01012023", right_on="CD_SECTOR", how="left")
no_residents_row = int(sectors["residents"].isna().sum())
sectors["residents"] = sectors["residents"].fillna(0)
# Statbel has one extra row per municipality ("not to be located in a sector", 0.07% of the residents). They are spread over the sectors of their municipality in proportion to the residents
# of the sectors, so the municipality totals stay exact.
unlocated = pop[~pop["CD_SECTOR"].isin(sectors["CS01012023"])]
assert unlocated["TX_DESCR_SECTOR_NL"].str.startswith("NIET TE LOKALISEREN").all(), "an unknown sector row that is not the 'not to be located' row"
extra = unlocated.groupby("CD_REFNIS")["residents"].sum()
located = sectors.groupby("CNIS5_2023")["residents"].sum()
factor = (located + extra.reindex(located.index).fillna(0)) / located
sectors["residents"] = sectors["residents"] * sectors["CNIS5_2023"].map(factor)
print(f"{len(sectors):,} sectors on the map; {no_residents_row} have no row in the population file; {len(unlocated)} rows 'not to be located in a sector' with {int(unlocated['residents'].sum()):,} residents "
      f"({unlocated['residents'].sum() / total_file * 100:.2f}%) are spread over the sectors of their municipality")
assert total_file == 11_697_557, "the Belgian total of 1 January 2023 is not what Statbel published"

# the grid cells that touch Belgium, and the pieces of every sector inside every cell
minx, miny, maxx, maxy = sectors.total_bounds
cx0, cx1, cy0, cy1 = int(np.floor(minx / SIDE)), int(np.floor(maxx / SIDE)), int(np.floor(miny / SIDE)), int(np.floor(maxy / SIDE))
grid = gpd.GeoDataFrame([{"cx": cx, "cy": cy, "geometry": box(cx * SIDE, cy * SIDE, (cx + 1) * SIDE, (cy + 1) * SIDE)} for cx in range(cx0, cx1 + 1) for cy in range(cy0, cy1 + 1)], crs=sectors.crs)
sectors["sector_area"] = sectors.geometry.area
pieces = gpd.overlay(sectors[["CS01012023", "CNIS5_2023", "residents", "sector_area", "geometry"]], grid, how="intersection", keep_geom_type=True)
pieces["fraction"] = pieces.geometry.area / pieces["sector_area"]
by_sector = pieces.groupby("CS01012023")["fraction"].sum()
assert np.allclose(by_sector.to_numpy(), 1.0, atol=1e-6), "the pieces of a sector do not add up to the sector"
pieces["residents_2023"] = pieces["residents"] * pieces["fraction"]
out = pieces.groupby(["cx", "cy", "CNIS5_2023"])["residents_2023"].sum().reset_index().rename(columns={"CNIS5_2023": "municipality_nis_code"})
out["residents_2023"] = out["residents_2023"].round(3)
assert abs(out["residents_2023"].sum() - 11_697_557) < 1, "the residents of the squares do not add up to the Belgian total"
out.to_csv(HERE / "data" / "cell_residents_2023.csv", index=False)
cells = out.groupby(["cx", "cy"])["residents_2023"].sum()
print(f"Wrote data/cell_residents_2023.csv: {len(out):,} pieces in {len(cells):,} squares; {int(out['residents_2023'].sum()):,} residents; "
      f"{int((cells >= 1000).sum())} squares have 1,000 or more residents; the most populated square has {int(cells.max()):,} residents")
