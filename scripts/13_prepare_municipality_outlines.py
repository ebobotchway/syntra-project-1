"""
Step 13 - Prepare municipality outlines for the maps of analysis 3 (decision #84).

Source (external data, not part of the accident data):
  Statbel (Statistics Belgium), "Statistical sectors" on 1 January 2023, licence CC BY 4.0
  https://statbel.fgov.be/en/open-data/statistical-sectors-2023
  The file used: sh_statbel_statistical_sectors_31370_20230101.shp.zip (Belgian Lambert 1972 = EPSG:31370, the same
  coordinate system as the accident coordinates). It was downloaded into its own folder data/external/statbel_sectors_2023_download/
  and unpacked into data/external/statbel_sectors_2023/ (both are kept out of git because the raw file is large):
      curl -L -o sectors_31370_20230101.shp.zip "https://statbel.fgov.be/sites/default/files/files/opendata/Statistische%20sectoren/sh_statbel_statistical_sectors_31370_20230101.shp.zip"

What this script does
  1. reads the sectors (about 19,800 small areas),
  2. joins them into ONE outline per municipality (the 5-digit NIS code, column CNIS5_2023),
  3. checks the result against the municipalities in the accident data (same NIS codes?),
  4. simplifies the outlines a little (50 m) so the file is small, and saves them as a GeoPackage in EPSG:31370.
Only this small derived file (data/municipality_outlines.gpkg) is committed, together with an attribution note.

How to run (from the project folder, with `conda activate syntra-ds`; paths are arguments):
    python -I scripts/13_prepare_municipality_outlines.py data/external/statbel_sectors_2023/sh_statbel_statistical_sectors_31370_20230101.shp/sh_statbel_statistical_sectors_31370_20230101.shp OPENDATA_MAP_2017-2024_en_flagged.csv.gz data/municipality_outlines.gpkg
"""
import sys

import geopandas as gpd
import pandas as pd

sectors_file = sys.argv[1]   # the unpacked Statbel shapefile
accidents_file = sys.argv[2]  # the accident data (to compare the NIS codes)
output_file = sys.argv[3]    # the small result file

# --- 1. Read the sectors and check the coordinate system ---
sectors = gpd.read_file(sectors_file)
assert sectors.crs is not None and sectors.crs.to_epsg() == 31370, f"unexpected coordinate system: {sectors.crs}"
print(f"Sectors read: {len(sectors):,}, coordinate system EPSG:{sectors.crs.to_epsg()} (Belgian Lambert 1972)")

# --- 2. One outline per municipality: join all sectors with the same NIS code ---
municipalities = sectors.dissolve(by="CNIS5_2023", aggfunc={"T_MUN_NL": "first", "T_MUN_FR": "first", "T_REGIO_NL": "first"}).reset_index()
municipalities = municipalities.rename(columns={"CNIS5_2023": "nis_code", "T_MUN_NL": "name_nl", "T_MUN_FR": "name_fr", "T_REGIO_NL": "region_nl"})
print(f"Municipalities after joining the sectors: {len(municipalities)}")

# --- 3. Compare with the municipalities in the accident data ---
accidents = pd.read_csv(accidents_file, usecols=["municipality_nis_code", "municipality"], dtype=str).drop_duplicates()
codes_data, codes_map = set(accidents["municipality_nis_code"]), set(municipalities["nis_code"])
only_in_data, only_on_map = sorted(codes_data - codes_map), sorted(codes_map - codes_data)
print(f"NIS codes in the accident data: {len(codes_data)}; on the map: {len(codes_map)}; in both: {len(codes_data & codes_map)}")
print("Only in the accident data:", only_in_data[:10], "| only on the map:", only_on_map[:10])
# Names must agree too, otherwise the join would put numbers on the wrong municipality.
merged = accidents.merge(municipalities[["nis_code", "name_nl"]], left_on="municipality_nis_code", right_on="nis_code")
different = merged[merged["municipality"].str.lower() != merged["name_nl"].str.lower()]
print(f"Municipalities whose name differs between the data and the map: {len(different)}")
if len(different):
    print(different[["municipality_nis_code", "municipality", "name_nl"]].head(12).to_string(index=False))
assert len(codes_data & codes_map) >= 0.99 * len(codes_data), "too many municipality codes do not match"

# --- 4. Sanity check on the size, then simplify and save ---
total_area_km2 = municipalities.geometry.area.sum() / 1e6
print(f"Total area of the outlines: {total_area_km2:,.0f} km2 (Belgium is about 30,689 km2)")
municipalities["geometry"] = municipalities.geometry.simplify(50, preserve_topology=True)  # 50 m: invisible on a country map
municipalities.to_file(output_file, driver="GPKG", layer="municipalities")
print(f"Saved {output_file}")
