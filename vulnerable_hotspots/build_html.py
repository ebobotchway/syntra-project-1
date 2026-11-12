"""
Builds the vulnerable hotspots analysis as ONE self-contained HTML file (vulnerable_hotspots.html).

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
import charts_focused as cf
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
        sev_tables[f"{size}|{group}"] = spec(s[["period", "cells", "number of cells", "accidents", "severe", "severe %", "severe low", "severe high", "fatal", "fatal %", "serious", "serious %"]])

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

# 4. The parts of the focused dashboard: step 2 (severity per group), the municipality top 20 and step 4a (regional severity, province map)
res_f, provinces_f, positions_f = cf.load_results(), cf.load_provinces(), cf.load_positions()
figs_f, tables_f = {}, {}
scopes_f = list(cf.SCOPE_LABELS.items())
for scope, _ in scopes_f:
    figs_f[f"s2a|{scope}"] = plain(cf.fig_severity_intervals(res_f, scope))
    figs_f[f"s2b|{scope}"] = plain(cf.fig_severity_distribution(res_f, scope))
    a, b, c = (res_f[k][res_f[k]["scope"] == scope].set_index("road_user_group") for k in ("severity_a_fatal", "severity_b_serious", "severity_c_slight"))
    combined = a[["accidents", "count", "share_pct", "ci_low_pct", "ci_high_pct", "ratio_to_all", "gap_points"]].rename(
        columns={"count": "fatal", "share_pct": "fatal %", "ci_low_pct": "fatal low", "ci_high_pct": "fatal high", "ratio_to_all": "fatal ratio", "gap_points": "fatal gap"})
    combined["serious"], combined["serious %"] = b["count"], b["share_pct"]
    combined["slight"], combined["slight %"] = c["count"], c["share_pct"]
    tables_f[f"s2|{scope}"] = spec(combined.reset_index())
figs_f["s4a1"] = plain(cf.fig_regional_overview(res_f))
figs_f["s4a2"] = plain(cf.fig_province_map(res_f, provinces_f))
regional = res_f["severity_regional_regions_provinces"]
tables_f["s4a1"] = spec(regional[regional["group"] == "All accidents"], digits=3)
tables_f["s4a1"]["filename"] = "severity_regions_provinces_all_accidents.csv"
# the numbers per municipality, group and period for the top 20 (the page ranks and draws them in the browser)
periods_tbl = cf.load_municipality_periods()
base_tbl = res_f["geo_a_cyclists_by_municipality"].set_index("municipality_nis_code")
pos_tbl = positions_f.set_index("municipality_nis_code")
period_keys = ["2017-2024", "2022-2024"] + [str(y) for y in range(2017, 2025)]
by_key = {k: v.set_index("municipality_nis_code") for k, v in periods_tbl.groupby(["group", "period"])}


def ints(group, period, column):
    return [int(v) for v in by_key[(group, period)].loc[feature_order, column]]


muni_f = {"nis": feature_order, "name": [base_tbl.loc[n, "municipality"] for n in feature_order], "region": [base_tbl.loc[n, "region"] for n in feature_order],
          "bx": [round(float(pos_tbl.loc[n, "bubble_x"]), 1) for n in feature_order], "by": [round(float(pos_tbl.loc[n, "bubble_y"]), 1) for n in feature_order],
          "cx": [round(float(f["x"]), 1) for f in outlines["features"]], "cy": [round(float(f["y"]), 1) for f in outlines["features"]], "start": starts, "end": ends, "periods": period_keys,
          "total": {p: ints("All accidents", p, "accidents") for p in period_keys},
          "g": {g: {p: {"a": ints(g, p, "accidents"), "s": ints(g, p, "severe")} for p in period_keys} for g in cf.GROUPS4}}
assert sum(muni_f["total"]["2017-2024"]) == 289532 and sum(muni_f["g"]["Pedestrian"]["2017-2024"]["a"]) == 29897 and sum(muni_f["g"]["Bicycle"]["2017-2024"]["a"]) == 71881
extra = {"muni": muni_f, "outline": None, "scopes": [[k, v] for k, v in scopes_f], "figs": figs_f, "hotspots": {}, "tables": tables_f}

data = {"groups": charts.GROUPS, "labels": charts.GROUP_LABELS, "words": charts.GROUP_WORDS, "sizes": list(charts.CELL_SIZES), "side": charts.CELL_SIZES, "periods": charts.PERIODS, "yearsIn": charts.YEARS_IN,
        "cells": cell_data, "top": top_data, "topRate": top_rate_data, "extent": extent, "zmaxPeriods": zmax_periods, "zmaxRatePeriods": zmax_rate_periods,
        "cov": {f"{r['group']}|{r['period']}": [int(r["accidents"]), int(r["with coordinates"])] for _, r in coverage.iterrows()},
        "figs": figs, "sevTables": sev_tables, "muni": muni,
        "findings": {"heat": fx.HEATMAPS, "sqrate": fx.SQUARE_RATES, "sev": fx.SEVERITY, "rate": fx.RATES, "care": fx.CARE}}

template = (HERE / "template.html").read_text(encoding="utf-8")
focused_html, focused_script = (HERE / "template_focused.html").read_text(encoding="utf-8").split("<!--EXTRA-SCRIPT-->")
assert template.count("/*__DATA__*/null") == 1 and template.count("/*__STEP1__*/null") == 1 and focused_script.count("/*__EXTRA__*/null") == 1, "a data placeholder was not found exactly once"
import re
sections = {k: re.search(rf'<section id="{k}">.*?</section>', focused_html, re.S).group(0) for k in ("sec-s2", "sec-s3", "sec-s4")}
for anchor, key in (('  <section id="sec-1">', "sec-s2"), ('  <section id="sec-4">', "sec-s3"), ('  <section id="sec-about" class="about">', "sec-s4")):
    assert template.count(anchor) == 1, f"anchor {anchor} not found exactly once"
    template = template.replace(anchor, sections[key] + "\n\n" + anchor)
plotly = '<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"></script>'
assert template.count(plotly) == 1
outline_json = json.dumps({"x": xs, "y": ys}, separators=(",", ":"), allow_nan=False)  # the municipality borders, once, for all maps
page = template.replace(plotly, plotly + "\n<script>const SHARED_OUTLINE = " + outline_json + ";</script>")
page = page.replace("/*__STEP1__*/null", json.dumps(step1, separators=(",", ":"))).replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":"), allow_nan=False))
focused_script = focused_script.replace("/*__EXTRA__*/null", json.dumps(extra, separators=(",", ":"), allow_nan=False))
assert page.rstrip().endswith("</script>"), "unexpected end of the template"
page = page.rstrip() + "\n" + focused_script
out = HERE / "vulnerable_hotspots.html"
out.write_text(page, encoding="utf-8")
print(f"Saved {out.name}: {len(page) / 1e6:.1f} MB; {len(cell_data)} cell sets, {len(figs)} severity charts, {len(figs_f)} charts from the focused dashboard")
