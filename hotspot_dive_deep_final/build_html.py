"""
Builds the hotspot deep dive as ONE self-contained HTML file (hotspot_deep_dive.html).

It combines template.html (the page: design, step 1 (1a and 1b) from the focused dashboard, buttons and the scripts that draw the charts in the browser) with the SAVED results of scripts 01 and 02
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


# 0. Step 1 (1a, 1b) from the focused dashboard: the summary table of accidents per road-user group, year and month; the page calculates 1a and 1b from it in the browser
table1 = pd.read_csv(charts.DATA / "dashboard_data.csv")
ranking = pd.read_csv(charts.RESULTS / "accidents_per_road_user.csv")["road_user_group"].tolist()
names = ["All accidents"] + ranking
index_of = {name: i for i, name in enumerate(names)}
step1 = {"names": names, "years": sorted(int(y) for y in table1["year"].unique()),
         "rows": [[index_of[g], int(y), int(m), int(n)] for g, y, m, n in zip(table1["road_user_group"], table1["year"], table1["month"], table1["accidents"])]}
assert len(step1["rows"]) == 11 * 8 * 12, "unexpected number of rows in the step 1 table"

# 1. Grid cells, compact: per size, group and period the lists of cell columns, rows, accidents, severe and fatal accidents
cell_data, top_data, extent = {}, {}, {}
for size in charts.CELL_SIZES:
    for group in charts.GROUPS:
        c_all = cells[(cells["size"] == size) & (cells["group"] == group)]
        extent[f"{size}|{group}"] = [int(c_all["cx"].min()), int(c_all["cx"].max()), int(c_all["cy"].min()), int(c_all["cy"].max())]
        for period in charts.PERIODS:
            c = c_all[c_all["period"] == period]
            cell_data[f"{size}|{group}|{period}"] = {k: [int(v) for v in c[col]] for k, col in (("cx", "cx"), ("cy", "cy"), ("a", "accidents"), ("s", "severe"), ("f", "fatal"))}
            t = top[(top["size"] == size) & (top["group"] == group) & (top["period"] == period)]
            top_data[f"{size}|{group}|{period}"] = [
                {"rank": int(r["rank"]), "m": r["municipality"], "a": int(r["accidents"]), "py": float(r["per_year"]), "s": int(r["severe"]), "f": int(r["fatal"]),
                 "sev": None if pd.isna(r["severe %"]) else float(r["severe %"]), "fat": None if pd.isna(r["fatal %"]) else float(r["fatal %"]),
                 "share": float(r["share_of_located_pct"]), "x": float(r["centre_x_m"]), "y": float(r["centre_y_m"])} for _, r in t.iterrows()]
zmax_periods = {k: float(cells[(cells["size"] == k.split("|")[0]) & (cells["group"] == k.split("|")[1]) & cells["period"].isin(charts.THREE)]["per_year"].max()) for k in extent}

# 2. The severity charts and tables
figs, sev_tables = {}, {}
for size in charts.CELL_SIZES:
    for group in charts.GROUPS:
        figs[f"{size}|{group}"] = plain(charts.fig_hotspot_severity(summary, size, group))
        s = summary[(summary["size"] == size) & (summary["group"] == group)]
        sev_tables[f"{size}|{group}"] = spec(s[["period", "cells", "number of cells", "accidents", "severe", "severe %", "severe low", "severe high", "fatal", "fatal %", "serious", "serious %"]])

# 2b. The logistic regression (script 05): the odds-ratio chart, the tables and the numbers behind the text
lg = charts.load_logit()
fit, adj = lg["severity_fit"].iloc[0], lg["hotspot_adjusted"].iloc[0]
logit = {"fig": plain(charts.fig_logit_forest(lg["severity_model"])),
         "table": spec(charts.odds_ratio_table(lg["severity_model"]), 3),
         "selection": spec(lg["selection"]), "desc": spec(lg["severity_descriptives"], 3),
         "sub": f"One model for the four groups together (it does not follow the group or cell-size filters). Dependent variable: severe (fatal + serious injury) = 1, otherwise 0. Explanatory variables: hotspot (accident in one of the 40 busiest 5 x 5 km squares of its own group and period), period, group, built-up area and light condition. "
                f"{int(fit['rows']):,} rows ({int(fit['different accidents']):,} accidents; an accident with two groups is a row in both), {int(fit['severe accidents']):,} severe ({fit['severe %']:.1f}%). Standard errors are cluster-robust by municipality ({int(fit['clusters (municipalities)'])} clusters). Filled dots are significant at the 5% level (p below 0.05); a hollow gray dot is not significant (its interval includes 1).",
         "none": f"{adj['severe % if none in a hotspot']:.1f}%", "all": f"{adj['severe % if all in a hotspot']:.1f}%",
         "diff": f"{adj['difference (percentage points)']:.1f} points ({adj['difference low']:.1f} to {adj['difference high']:.1f})",
         "fit": f"Fit: AUC {fit['AUC']:.2f}, McFadden R2 {fit['McFadden R2']:.3f}, highest VIF {fit['highest VIF']:.2f}. The average adjusted prediction sets the hotspot term to 1 and to 0 for every row (other variables as observed) and averages the predicted probabilities; the interval uses 1,000 simulated coefficient sets."}

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
        "cells": cell_data, "top": top_data, "extent": extent, "zmaxPeriods": zmax_periods,
        "cov": {f"{r['group']}|{r['period']}": [int(r["accidents"]), int(r["with coordinates"])] for _, r in coverage.iterrows()},
        "figs": figs, "sevTables": sev_tables, "muni": muni, "outline": {"x": xs, "y": ys},
        "logit": logit, "findings": {"heat": fx.HEATMAPS, "sev": fx.SEVERITY, "logit": fx.LOGIT, "logitCare": fx.LOGIT_CARE, "rate": fx.RATES, "care": fx.CARE}}

template = (HERE / "template.html").read_text(encoding="utf-8")
assert template.count("/*__DATA__*/null") == 1, "the data placeholder was not found exactly once"
assert template.count("/*__STEP1__*/null") == 1, "the step 1 placeholder was not found exactly once"
page = template.replace("/*__STEP1__*/null", json.dumps(step1, separators=(",", ":"))).replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":"), allow_nan=False))
out = HERE / "hotspot_deep_dive.html"
out.write_text(page, encoding="utf-8")
print(f"Saved {out.name}: {len(page) / 1e6:.1f} MB; {len(cell_data)} cell sets, {len(figs)} severity charts")
