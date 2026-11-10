"""
Step 1 of the hotspot deep dive: the number of residents per municipality and year (2017-2024), from Statbel open data.

Source: Statbel, "Population by place of residence, nationality, marital status, age and sex" (one file per year, the population on 1 January),
CC BY 4.0, https://statbel.fgov.be/en/open-data/population-place-residence-nationality-marital-status-age-and-sex-13
The files are downloaded to raw_population/ (not part of the repository: 21 MB) and added up to residents per municipality.

The problem: on 1 January 2019 many Flemish municipalities merged and got NEW NIS codes. The 2017 and 2018 files still use the 589 OLD codes, while the accident data and the outlines
use the 581 current (2023) codes. The Statbel statistical sectors of 2023 solve this: every sector carries the code of its old municipality (first 5 characters of C_NIS6) and the
current code of the municipality it now belongs to (CNIS5_2023). That gives an exact table old code -> current code; the residents of merged municipalities are added up.

How to run (from the folder hotspot_deep_dive, with `conda activate syntra-ds`; the argument is the Statbel sector file already in the main project):
    python -I scripts/01_prepare_population.py "../data/external/statbel_sectors_2023/sh_statbel_statistical_sectors_31370_20230101.shp/sh_statbel_statistical_sectors_31370_20230101.shp"
"""
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
RAW = HERE / "raw_population"
RAW.mkdir(exist_ok=True)
URL = ("https://statbel.fgov.be/sites/default/files/files/opendata/bevolking%20naar%20woonplaats%2C%20nationaliteit%20burgelijke%20staat%20%2C%20leeftijd%20en%20geslacht/"
       "TF_SOC_POP_STRUCT_{year}.zip")
YEARS = range(2017, 2025)

# 1. The table old municipality code -> current (2023) code, from the statistical sectors
sectors = gpd.read_file(sys.argv[1]).drop(columns="geometry")
sectors["old_code"] = sectors["C_NIS6"].str[:5]
mapping = sectors.groupby("old_code")["CNIS5_2023"].agg(lambda s: sorted(set(s)))
assert (mapping.map(len) == 1).all(), "an old code belongs to two current municipalities"
mapping = mapping.map(lambda s: s[0])
current = set(sectors["CNIS5_2023"])
names = sectors.groupby("CNIS5_2023")["T_MUN_NL"].first()
assert len(current) == 581

# 2. Download (once) and add up the residents per municipality
rows = []
for year in YEARS:
    path = RAW / f"TF_SOC_POP_STRUCT_{year}.zip"
    if not path.exists():
        urllib.request.urlretrieve(URL.format(year=year), path)
    with zipfile.ZipFile(path) as z:
        raw = z.read(z.namelist()[0])
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:  # the 2022 file is in Windows-1252
        text = raw.decode("cp1252")
    table = pd.read_csv(io.StringIO(text), sep="|", dtype=str)
    code_column = "CD_REFNIS" if "CD_REFNIS" in table.columns else "CD_MUNTY_REFNIS"  # the 2017 and 2018 files use other column names
    table["residents"] = table["MS_POPULATION"].astype(int)
    per_old_code = table.groupby(code_column)["residents"].sum()
    new_code = [mapping.get(c, c if c in current else None) for c in per_old_code.index]
    assert None not in new_code, f"{year}: a code could not be mapped"
    per_municipality = per_old_code.groupby(new_code).sum()
    assert set(per_municipality.index) == current, f"{year}: not all 581 municipalities have residents"
    out = per_municipality.rename_axis("municipality_nis_code").reset_index()
    out["year"] = year
    rows.append(out)
    print(f"{year}: {len(per_old_code)} codes in the file -> 581 municipalities, {int(per_municipality.sum()):,} residents on 1 January")

population = pd.concat(rows, ignore_index=True)
population.insert(1, "municipality", population["municipality_nis_code"].map(names))
assert (population["residents"] > 0).all()
growth = population.pivot(index="municipality_nis_code", columns="year", values="residents").sum()
assert (growth.pct_change().dropna().abs() < 0.02).all(), "total residents jump by more than 2% in a year"
population.to_csv(HERE / "data" / "population_by_municipality.csv", index=False)
pd.DataFrame({"old_code": mapping.index, "current_code": mapping.values}).to_csv(HERE / "data" / "nis_old_to_2023.csv", index=False)
print(f"Wrote data/population_by_municipality.csv ({len(population):,} rows) and data/nis_old_to_2023.csv ({len(mapping):,} old codes).")
