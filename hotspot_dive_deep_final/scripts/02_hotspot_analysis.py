"""
Step 2 of the hotspot deep dive: hotspots of accidents with vulnerable road users before, during and after Covid-19, their severity, and rates per resident.

For the groups  pedestrians, cyclists, motorcycles, mopeds and "vulnerable (any of the four)"  and the periods  pre 2017-2019, during 2020-2021, post 2022-2024  (and all years), it calculates:

  A. GRID CELLS (two sizes, decision #170): cells of 5 km2 in area (side 2,236 m) and squares of 5 km x 5 km (25 km2).
     Per cell: accidents (and per year), severe, fatal and serious accidents (only accidents with usable coordinates).
  B. HOTSPOTS: the 20 cells with the most accidents per group, period and cell size, with their severity, and the severity of these 20 cells against all other cells.
  C. MUNICIPALITIES (decision #171): accidents per 100,000 residents per year, using the residents of each year (Statbel), with their severity.

Decisions applied: #33 an accident counts for a group if the group is road user 1 OR 2 (once per accident; "vulnerable" = any of the four, also once);
#38 periods; #90 coordinates outside Belgium are treated as missing; #116 severe = accident class 1, 2 or 3 (fatal = class 1 + 2, serious = class 3);
#74 Wilson 95% intervals; #172 severity as severe share; #175 small numbers: a share needs 30 accidents, a municipality rate needs 100 accidents of the group in the period.
Grid cells use the accidents WITH coordinates; municipality rates use ALL accidents of the municipality (every accident has a municipality code).

How to run (from the folder hotspot_deep_dive, with `conda activate syntra-ds`; the argument is the accident file of the main project):
    python -I scripts/02_hotspot_analysis.py "../OPENDATA_MAP_2017-2024_en_flagged.csv.gz"
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
DATA, RESULTS = HERE / "data", HERE / "results"

CELL_SIZES = {"5 km2 cells": 5 ** 0.5 * 1000, "5 x 5 km squares": 5000.0}  # side in metres: sqrt(5 km2) = 2,236.07 m and 5,000 m
GROUPS = {"Pedestrian": ["08"], "Bicycle": ["03"], "Motorcycle": ["07"], "Moped": ["06"], "Vulnerable (any of the four)": ["08", "03", "07", "06"]}
PERIODS = {"Pre Covid-19 (2017-2019)": range(2017, 2020), "During Covid-19 (2020-2021)": range(2020, 2022), "Post Covid-19 (2022-2024)": range(2022, 2025), "All years (2017-2024)": range(2017, 2025)}
MIN_SHARE, MIN_RATE = 30, 100  # decision #175

header = pd.read_csv(sys.argv[1], nrows=0).columns
df = pd.read_csv(sys.argv[1], dtype={c: str for c in header if c.endswith("_code")})
assert len(df) == 289532
usable = df["x_coord"].between(20_000, 300_000) & df["y_coord"].between(20_000, 250_000)  # decision #90
df["severe"] = df["accident_class_code"].isin(["1", "2", "3"])
df["fatal"] = df["accident_class_code"].isin(["1", "2"])
df["serious"] = df["accident_class_code"] == "3"
assert int(df["severe"].sum()) == 28532, "severe count differs from the main project"
involved = {name: df["road_user_type1_code"].isin(codes) | df["road_user_type2_code"].isin(codes) for name, codes in GROUPS.items()}  # road user 1 OR 2
for name, expected in (("Pedestrian", 29897), ("Bicycle", 71881), ("Motorcycle", 19792), ("Moped", 23258)):
    assert int(involved[name].sum()) == expected, f"{name}: count differs from the main project"
print(f"Vulnerable (any of the four): {int(involved['Vulnerable (any of the four)'].sum()):,} accidents (an accident with two of them counts once)")


def wilson(k, n, z=1.96):
    """95% Wilson interval for a share (in %), the same method as the main project (#74)."""
    k, n = np.asarray(k, float), np.asarray(n, float)
    p = np.divide(k, n, out=np.zeros_like(k), where=n > 0)
    centre = (p + z ** 2 / (2 * n.clip(1))) / (1 + z ** 2 / n.clip(1))
    half = z * np.sqrt(p * (1 - p) / n.clip(1) + z ** 2 / (4 * n.clip(1) ** 2)) / (1 + z ** 2 / n.clip(1))
    return (centre - half) * 100, (centre + half) * 100


def severity_columns(t, total_col="accidents"):
    """Shares (%) with 95% Wilson intervals; a share is only given from 30 accidents (decision #175)."""
    ok = t[total_col] >= MIN_SHARE
    for name in ("severe", "fatal", "serious"):
        lo, hi = wilson(t[name], t[total_col])
        t[f"{name} %"] = np.where(ok, t[name] / t[total_col].clip(1) * 100, np.nan)
        t[f"{name} low"], t[f"{name} high"] = np.where(ok, lo, np.nan), np.where(ok, hi, np.nan)
    return t


# ---------------------------------------------------------------------------------------------------------- A and B: grid cells and hotspots
cells_all, top_all, summary_all = [], [], []
for size_name, side in CELL_SIZES.items():
    located = df[usable].copy()
    located["cx"], located["cy"] = np.floor(located["x_coord"] / side).astype(int), np.floor(located["y_coord"] / side).astype(int)
    n_cells_belgium = located[["cx", "cy"]].drop_duplicates().shape[0]
    print(f"\n{size_name}: side {side:,.0f} m, {n_cells_belgium:,} cells contain at least one accident")
    for group in GROUPS:
        for period, years in PERIODS.items():
            sub = located[involved[group][located.index] & located["collision_year"].isin(years)]
            cells = sub.groupby(["cx", "cy"]).agg(accidents=("severe", "size"), severe=("severe", "sum"), fatal=("fatal", "sum"), serious=("serious", "sum")).reset_index()
            cells = cells.sort_values(["accidents", "cx", "cy"], ascending=[False, True, True]).reset_index(drop=True)
            assert cells["accidents"].sum() == len(sub)
            n_years = len(years)
            cells["per_year"] = cells["accidents"] / n_years
            cells.insert(0, "period", period); cells.insert(0, "group", group); cells.insert(0, "size", size_name)
            cells_all.append(cells)
            # the 20 hotspots: the 20 cells with the most accidents; the municipality is the most common one among the cell's accidents
            top = cells.head(20).copy()
            top.insert(3, "rank", range(1, len(top) + 1))
            key = sub.groupby(["cx", "cy"])["municipality"].agg(lambda s: s.mode().iat[0])
            top["municipality"] = [key.loc[(r.cx, r.cy)] for r in top.itertuples()]
            top["centre_x_m"], top["centre_y_m"] = (top["cx"] + 0.5) * side, (top["cy"] + 0.5) * side
            top["share_of_located_pct"] = top["accidents"] / len(sub) * 100
            top = severity_columns(top)
            top_all.append(top)
            # the severity of the 20 hotspots against all other cells
            is_hot = cells.index < 20
            for label, part in (("20 hotspot cells", cells[is_hot]), ("all other cells", cells[~is_hot]), ("all cells", cells)):
                summary_all.append({"size": size_name, "group": group, "period": period, "cells": label, "number of cells": len(part), "accidents": int(part["accidents"].sum()),
                                    "severe": int(part["severe"].sum()), "fatal": int(part["fatal"].sum()), "serious": int(part["serious"].sum())})
        print(f"  {group}: done")

cells_table = pd.concat(cells_all, ignore_index=True)
cells_table.to_csv(RESULTS / "grid_cells.csv", index=False, float_format="%.4f")
top_table = pd.concat(top_all, ignore_index=True)
top_table.to_csv(RESULTS / "hotspots_top20.csv", index=False, float_format="%.3f")
summary = severity_columns(pd.DataFrame(summary_all))
summary.to_csv(RESULTS / "hotspot_severity_summary.csv", index=False, float_format="%.3f")

# coverage: how many accidents of the group have usable coordinates
coverage = []
for group in GROUPS:
    for period, years in PERIODS.items():
        in_period = involved[group] & df["collision_year"].isin(years)
        coverage.append({"group": group, "period": period, "accidents": int(in_period.sum()), "with coordinates": int((in_period & usable).sum())})
coverage = pd.DataFrame(coverage)
coverage["left out %"] = (1 - coverage["with coordinates"] / coverage["accidents"]) * 100
coverage.to_csv(RESULTS / "coordinate_coverage.csv", index=False, float_format="%.2f")

# ---------------------------------------------------------------------------------------------------------- C: municipality rates per 100,000 residents
population = pd.read_csv(DATA / "population_by_municipality.csv", dtype={"municipality_nis_code": str})
base = df.groupby("municipality_nis_code").agg(municipality=("municipality", "first"), region=("region", "first"))
assert len(base) == 581 and set(base.index) == set(population["municipality_nis_code"])
rows = []
for group in GROUPS:
    for period, years in PERIODS.items():
        sub = df[involved[group] & df["collision_year"].isin(years)]
        counts = sub.groupby("municipality_nis_code").agg(accidents=("severe", "size"), severe=("severe", "sum"), fatal=("fatal", "sum"), serious=("serious", "sum")).reindex(base.index, fill_value=0).astype(int)
        resident_years = population[population["year"].isin(years)].groupby("municipality_nis_code")["residents"].sum().reindex(base.index)  # each year's own residents, added up
        t = base.join(counts)
        t["resident_years"] = resident_years
        t["average residents"] = resident_years / len(years)
        t["accidents per year"] = t["accidents"] / len(years)
        t["rate per 100,000 residents per year"] = t["accidents"] / resident_years * 100_000
        t["rate reliable"] = t["accidents"] >= MIN_RATE
        t = severity_columns(t)
        t.insert(0, "period", period); t.insert(0, "group", group)
        assert t["accidents"].sum() == len(sub), f"{group} {period}: municipality counts do not add up"
        rows.append(t.reset_index())
municipalities = pd.concat(rows, ignore_index=True)
municipalities.to_csv(RESULTS / "municipality_rates.csv", index=False, float_format="%.4f")

# ---------------------------------------------------------------------------------------------------------- the main numbers, printed for the report
print("\nCoverage (accidents with usable coordinates):")
print(coverage[coverage["period"] == "All years (2017-2024)"].to_string(index=False))
v = "Vulnerable (any of the four)"
for size_name in CELL_SIZES:
    print(f"\n{size_name}, {v}: top 3 hotspots per period")
    for period in PERIODS:
        t = top_table[(top_table["size"] == size_name) & (top_table["group"] == v) & (top_table["period"] == period)].head(3)
        print(f"  {period}: " + "; ".join(f"{r.municipality} {r.accidents:,} ({r.per_year:.0f} a year)" for r in t.itertuples()))
print("\nSeverity, hotspot cells against other cells (severe %):")
piv = summary[summary["group"] == v].pivot_table(index=["size", "period"], columns="cells", values="severe %")
print(piv.round(1).to_string())
print("\nMunicipalities with 100+ accidents (rate shown):")
print(municipalities.groupby(["group", "period"])["rate reliable"].sum().unstack().to_string())
print(f"\nWrote {len(cells_table):,} grid-cell rows, {len(top_table)} hotspot rows, {len(summary)} severity summary rows, {len(municipalities):,} municipality rows.")
