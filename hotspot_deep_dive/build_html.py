"""
Builds the hotspot deep dive as ONE self-contained HTML file (hotspot_deep_dive.html).

It combines template.html (the page: design, step 1 (1a and 1b), buttons and the scripts that draw the charts in the browser) with the SAVED results of scripts 01 and 02
(results/*.csv, data/*), packed as compact lists. The severity charts are built here with charts.py and embedded as Plotly figures.
The page needs internet only for the chart library (plotly.js from a CDN) and the fonts.

How to run (from this folder, with `conda activate syntra-ds`):
    python build_html.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import charts
import findings as fx

HERE = Path(__file__).parent
cells, top, summary, coverage, mun, outlines = charts.load_cells(), charts.load_top(), charts.load_summary(), charts.load_coverage(), charts.load_municipalities(), charts.load_outlines()
population_check = pd.read_csv(charts.DATA / "population_by_municipality.csv", dtype={"municipality_nis_code": str})


def plain(fig):
    figure = json.loads(fig.to_json())
    figure["layout"].pop("template", None)
    return figure


def spec(df, digits=2):
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].round(digits)
    rows = [[None if (isinstance(v, float) and np.isnan(v)) else (v.item() if hasattr(v, "item") else v) for v in r] for r in df.itertuples(index=False)]
    return {"headers": [str(c) for c in df.columns], "rows": rows}


# 0. Step 1 (1a, 1b): the summary table of accidents per road-user group, year and month; the page calculates 1a and 1b from it in the browser
table1 = pd.read_csv(charts.DATA / "dashboard_data.csv")
ranking = pd.read_csv(charts.RESULTS / "accidents_per_road_user.csv")["road_user_group"].tolist()
names = ["All accidents"] + ranking
index_of = {name: i for i, name in enumerate(names)}
step1 = {"names": names, "years": sorted(int(y) for y in table1["year"].unique()),
         "rows": [[index_of[g], int(y), int(m), int(n)] for g, y, m, n in zip(table1["road_user_group"], table1["year"], table1["month"], table1["accidents"])]}
assert len(step1["rows"]) == 11 * 8 * 12, "unexpected number of rows in the step 1 table"

# 1. Grid squares, compact: per size, group and period the lists of square columns, rows, accidents, severe and fatal accidents and resident-years
cell_data, top_data, top_rate_data, extent = {}, {}, {}, {}
for size in charts.CELL_SIZES:
    for group in charts.GROUPS:
        c_all = cells[(cells["size"] == size) & (cells["group"] == group)]
        extent[f"{size}|{group}"] = [int(c_all["cx"].min()), int(c_all["cx"].max()), int(c_all["cy"].min()), int(c_all["cy"].max())]
        for period in charts.PERIODS:
            c = c_all[c_all["period"] == period]
            cell_data[f"{size}|{group}|{period}"] = {k: [int(v) for v in c[col]] for k, col in (("cx", "cx"), ("cy", "cy"), ("a", "accidents"), ("s", "severe"), ("f", "fatal"))}
            cell_data[f"{size}|{group}|{period}"]["ry"] = [int(round(v)) for v in c["resident_years"]]
            for ranking_name, store in (("accidents", top_data), ("rate", top_rate_data)):
                t = top[(top["size"] == size) & (top["group"] == group) & (top["period"] == period) & (top["ranking"] == ranking_name)]
                store[f"{size}|{group}|{period}"] = [
                    {"rank": int(r["rank"]), "m": r["municipality"], "a": int(r["accidents"]), "py": float(r["per_year"]), "s": int(r["severe"]), "f": int(r["fatal"]), "avg": float(r["average residents"]), "rate": float(r["rate"]) if not pd.isna(r["rate"]) else 0.0,
                     "sev": None if pd.isna(r["severe %"]) else float(r["severe %"]), "fat": None if pd.isna(r["fatal %"]) else float(r["fatal %"]),
                     "share": float(r["share_of_located_pct"]), "x": float(r["centre_x_m"]), "y": float(r["centre_y_m"])} for _, r in t.iterrows()]
zmax_rate_periods = {k: float(cells[(cells["size"] == k.split("|")[0]) & (cells["group"] == k.split("|")[1]) & cells["period"].isin(charts.THREE) & cells["rate_ok"]]["rate"].max()) for k in extent}
zmax_periods = {k: float(cells[(cells["size"] == k.split("|")[0]) & (cells["group"] == k.split("|")[1]) & cells["period"].isin(charts.THREE)]["per_year"].max()) for k in extent}

# 2. The severity charts and tables
figs, sev_tables = {}, {}
for size in charts.CELL_SIZES:
    for group in charts.GROUPS:
        figs[f"{size}|{group}"] = plain(charts.fig_hotspot_severity(summary, size, group))
        s = summary[(summary["size"] == size) & (summary["group"] == group)]
        sev_tables[f"{size}|{group}"] = spec(s[["period", "squares", "number of squares", "accidents", "severe", "severe %", "severe low", "severe high", "fatal", "fatal %", "serious", "serious %"]])

# 3. Municipalities: accidents, severe, fatal and resident-years per group and period, in the order of the outline features
feature_order = [f["nis"] for f in outlines["features"]]
base = mun.drop_duplicates("municipality_nis_code").set_index("municipality_nis_code")
xs, ys, starts, ends = [], [], [], []
for f in outlines["features"]:
    x, y = charts.ring_xy(f["polys"])
    starts.append(len(xs)); xs += x; ys += y; ends.append(len(xs))
by_key = {k: v.set_index("municipality_nis_code") for k, v in mun.groupby(["group", "period"])}
muni = {"nis": feature_order, "name": [base.loc[n, "municipality"] for n in feature_order], "region": [base.loc[n, "region"] for n in feature_order],
        "cx": [round(float(f["x"]), 1) for f in outlines["features"]], "cy": [round(float(f["y"]), 1) for f in outlines["features"]], "start": starts, "end": ends,
        "g": {g: {p: {"a": [int(v) for v in by_key[(g, p)].loc[feature_order, "accidents"]], "s": [int(v) for v in by_key[(g, p)].loc[feature_order, "severe"]],
                      "f": [int(v) for v in by_key[(g, p)].loc[feature_order, "fatal"]], "ry": [int(v) for v in by_key[(g, p)].loc[feature_order, "resident_years"]]} for p in charts.PERIODS} for g in charts.GROUPS}}
assert sum(muni["g"]["Vulnerable (any of the four)"]["All years (2017-2024)"]["a"]) == 136627
assert sum(muni["g"]["Vulnerable (any of the four)"]["All years (2017-2024)"]["ry"]) == int(population_check["residents"].sum())

data = {"groups": charts.GROUPS, "labels": charts.GROUP_LABELS, "words": charts.GROUP_WORDS, "sizes": list(charts.CELL_SIZES), "side": charts.CELL_SIZES, "periods": charts.PERIODS, "yearsIn": charts.YEARS_IN,
        "cells": cell_data, "top": top_data, "topRate": top_rate_data, "extent": extent, "zmaxPeriods": zmax_periods, "zmaxRatePeriods": zmax_rate_periods,
        "cov": {f"{r['group']}|{r['period']}": [int(r["accidents"]), int(r["with coordinates"])] for _, r in coverage.iterrows()},
        "figs": figs, "sevTables": sev_tables, "muni": muni, "outline": {"x": xs, "y": ys},
        "findings": {"heat": fx.HEATMAPS, "sqrate": fx.SQUARE_RATES, "sev": fx.SEVERITY, "rate": fx.RATES, "care": fx.CARE}}

template = (HERE / "template.html").read_text(encoding="utf-8")
assert template.count("/*__DATA__*/null") == 1 and template.count("/*__STEP1__*/null") == 1, "a data placeholder was not found exactly once"
page = template.replace("/*__STEP1__*/null", json.dumps(step1, separators=(",", ":"))).replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":"), allow_nan=False))
out = HERE / "hotspot_deep_dive.html"
out.write_text(page, encoding="utf-8")
print(f"Saved {out.name}: {len(page) / 1e6:.1f} MB; {len(cell_data)} cell sets, {len(figs)} severity charts")
