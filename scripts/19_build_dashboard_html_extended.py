"""
Step 19 - Build the extended self-contained HTML dashboard with steps 1-4 (decisions #109-#114). It replaces the output of step 11.

It combines:
  dashboard_template.html          the step-1 page (design, filters, graphs of steps 1a-1c)
  dashboard_extra_template.html    the sections of steps 2-4 (HTML and the script that draws them)
  data/dashboard_data.csv          the summary table of step 1 (accidents per group, year and month)
  reports/*.csv, data/*            the SAVED results of steps 2-4, turned into Plotly figures by dashboard_extra.py
and writes one file, dashboard.html, with all data inside (no extra downloads except the chart library and fonts).

How to run (from the project folder, with `conda activate syntra-ds`):
    python scripts/19_build_dashboard_html_extended.py dashboard_template.html dashboard_extra_template.html data/dashboard_data.csv reports/accidents_per_road_user.csv dashboard.html
(no -I here: the script adds the project folder to Python's path so it can import dashboard_extra.py)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
import dashboard_extra as dx  # the same graph builders as the Streamlit app

template_file, extra_file, data_file, ranking_file, output_file = sys.argv[1:6]

# --- 1. Step 1: the summary table, as in step 11 ---
table = pd.read_csv(data_file)
ranking = pd.read_csv(ranking_file)["road_user_group"].tolist()
names = ["All accidents"] + ranking
index_of = {name: i for i, name in enumerate(names)}
rows = [[index_of[g], int(y), int(m), int(n)] for g, y, m, n in zip(table["road_user_group"], table["year"], table["month"], table["accidents"])]
data = {"names": names, "years": sorted(int(y) for y in table["year"].unique()), "rows": rows}
assert len(rows) == 11 * 8 * 12, "unexpected number of rows"


# --- 2. Steps 2-4: figures and tables from the saved results ---
def plain(fig):
    """A Plotly figure as plain JSON data (the page draws it with plotly.js); the default Python template is dropped."""
    figure = json.loads(fig.to_json())
    figure["layout"].pop("template", None)
    return figure


def strip_outline(figure):
    """The municipality borders are the same in every map: they are stored once and filled in by the page."""
    for trace in figure["data"]:
        if trace.get("name") == "municipality borders":
            trace["x"], trace["y"] = [], []
    return figure


def spec(df, filename=None, digits=3):
    """A table as headers and rows (numbers rounded, missing values as null) for the page."""
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].round(digits)
    rows_ = [[None if (isinstance(v, float) and np.isnan(v)) else (v.item() if hasattr(v, "item") else v) for v in r] for r in df.itertuples(index=False)]
    out = {"headers": [str(c) for c in df.columns], "rows": rows_}
    if filename:
        out["filename"] = filename
    return out


res, outlines, provinces, cells, positions = dx.load_results(), dx.load_outlines(), dx.load_provinces(), dx.load_hotspot_cells(), dx.load_positions()
figs, tables = {}, {}

scopes = list(dx.SCOPE_LABELS.items())
for scope, _ in scopes:
    figs[f"s2a|{scope}"] = plain(dx.fig_severity_intervals(res, scope))
    figs[f"s2b|{scope}"] = plain(dx.fig_severity_distribution(res, scope))
    a, b, c = (res[k][res[k]["scope"] == scope].set_index("road_user_group") for k in ("severity_a_fatal", "severity_b_serious", "severity_c_slight"))
    combined = a[["accidents", "count", "share_pct", "ci_low_pct", "ci_high_pct", "ratio_to_all", "gap_points"]].rename(columns={"count": "fatal", "share_pct": "fatal %", "ci_low_pct": "fatal low", "ci_high_pct": "fatal high", "ratio_to_all": "fatal ratio", "gap_points": "fatal gap"})
    combined["serious"], combined["serious %"] = b["count"], b["share_pct"]
    combined["slight"], combined["slight %"] = c["count"], c["share_pct"]
    tables[f"s2|{scope}"] = spec(combined.reset_index())

figs["s3a"] = plain(dx.fig_cyclists_ranked(res))
figs["s3map|bubble"] = strip_outline(plain(dx.fig_cyclists_bubble(res, outlines, positions)))
figs["s3map|choropleth"] = plain(dx.fig_cyclists_choropleth(res, outlines))
tables["s3a"] = spec(res["geo_a_cyclists_by_municipality"], digits=2)

hotspots = {}
for group in ("Pedestrian", "Motorcycle", "Moped"):
    for scope in ("2017-2024", "2022-2024"):
        fig = strip_outline(plain(dx.fig_hotspots(res, cells, outlines, group, scope)))
        c = cells[(cells["group"] == group) & (cells["scope"] == scope)]
        cx0, cy0 = int(c["cx"].min()), int(c["cy"].min())
        heat = [t for t in fig["data"] if t["type"] == "heatmap"][0]
        heat["z"] = []  # filled in by the page from the compact list of squares
        cov = res["geo_coverage"]
        cov = cov[(cov["group"] == group) & (cov["scope"] == scope)].iloc[0]
        top = res[f"geo_hotspots_{group.lower()}"]
        top = top[top["scope"] == scope].drop(columns=["scope"])
        hotspots[f"{group}|{scope}"] = {
            "fig": fig, "cx0": cx0, "cy0": cy0, "cols": int(c["cx"].max() - cx0 + 1), "rows": int(c["cy"].max() - cy0 + 1),
            "cx": [int(v) for v in c["cx"]], "cy": [int(v) for v in c["cy"]], "n": [int(v) for v in c["accidents"]],
            "coverage": f"{cov['with_coordinates']:,.0f} of {cov['accidents']:,.0f} accidents involving {group.lower()}s have usable coordinates ({100 - cov['left_out_pct']:.1f}%); the other {cov['left_out']:,.0f} are not on the map.",
            "table": spec(top, digits=2)}

figs["s4a1"] = plain(dx.fig_regional_overview(res))
figs["s4a2"] = plain(dx.fig_province_map(res, provinces))
figs["s4a3"] = plain(dx.fig_regional_groups(res))
figs["s4a4"] = plain(dx.fig_regional_roadtype(res))
figs["s4b1"] = plain(dx.fig_squares(res))
figs["s4b2"] = plain(dx.fig_density_classes(res))
figs["s4b3"] = plain(dx.fig_density_scatter(res))
figs["s4c1"] = plain(dx.fig_within_density(res))
figs["s4c2"] = plain(dx.fig_within_density(res, dx.GROUPS5))
figs["s4c3"] = plain(dx.fig_within_density_roadtype(res))
figs["s4c4"] = plain(dx.fig_gap_adjusted(res))
tables["s4a1"] = spec(res["severity_regional_regions_provinces"], "severity_regions_provinces.csv")
tables["s4a2"] = spec(res["severity_regional_roadtype"], "severity_regions_roadtype.csv")
tables["s4b1"] = spec(res["severity_by_square_concentration"], "severity_by_square_concentration.csv")
tables["s4b2"] = spec(res["severity_by_municipality_density"], "severity_by_municipality_density.csv")
tables["s4b3"] = spec(res["severity_density_correlation"], "severity_density_correlation.csv", digits=4)
tables["s4c1"] = spec(res["severity_regions_standardised"], "severity_regions_standardised.csv")
tables["s4c2"] = spec(res["severity_regions_logistic"], "severity_regions_logistic.csv", digits=4)

# step 5: the saved logistic models (script 20)
figs["s5|place"] = plain(dx.fig_logit_forest(res, ["Region", "Road type", "Intersection", "Lighting"]))
figs["s5|weather"] = plain(dx.fig_logit_forest(res, ["Weather", "Road surface"]))
figs["s5|time"] = plain(dx.fig_logit_forest(res, ["Year", "Month"]))
figs["s5|collision"] = plain(dx.fig_logit_forest(res, ["Collision type"]))
figs["s5|users"] = plain(dx.fig_logit_roadusers(res))
figs["s5|pred"] = plain(dx.fig_logit_predicted(res))
figs["s5|scen"] = plain(dx.fig_logit_scenarios(res))
figs["s5|cal"] = plain(dx.fig_logit_calibration(res))
figs["s5|inter"] = plain(dx.fig_logit_interactions(res))
for m in dx.MODELS5:
    for view, _ in dx.SINGLE_VIEWS:
        figs[f"s5one|{m}|{view}"] = plain(dx.fig_logit_model_view(res, m, view))
fit5 = res["severity_logit_fit"]
tables["s5fit"] = spec(fit5[fit5["spec"] == "full"][["model", "accidents", "events", "event_rate_pct", "parameters", "mcfadden_r2", "aic", "auc", "icc_outcome", "icc_residual", "median_se_ratio_robust_to_ordinary"]], digits=3)
coef5 = res["severity_logit_coefficients"]
for m in dx.MODELS5:
    tables[f"s5coef|{m}"] = spec(coef5[(coef5["model"] == m) & (coef5["spec"] == "full")][["term", "odds_ratio", "or_ci_low", "or_ci_high", "p_value", "accidents", "events"]], digits=4)

xs, ys = [], []  # the municipality borders once, as one line with gaps (None) between rings
for f in outlines["features"]:
    x, y = dx._ring_xy(f["polys"])
    xs += x; ys += y
# step 3b/3c, municipality view (script 24): the numbers per municipality, group and period; the page ranks and draws them in the browser, so the buttons can combine freely
periods_tbl = pd.read_csv(PROJECT / "reports" / "geo_municipality_periods.csv", dtype={"municipality_nis_code": str})
base_tbl = res["geo_a_cyclists_by_municipality"].set_index("municipality_nis_code")
feature_order = [f["nis"] for f in outlines["features"]]
pos_tbl = positions.set_index("municipality_nis_code")
starts, ends, at = [], [], 0
for f in outlines["features"]:                               # where each municipality's rings start and end in the shared outline lists
    x, _ = dx._ring_xy(f["polys"])
    starts.append(at); at += len(x); ends.append(at)
assert at == len(xs), "outline ranges do not match the shared outline"
period_keys = ["2017-2024", "2022-2024"] + [str(y) for y in range(2017, 2025)]
muni_groups = ["All accidents", "Bicycle", "Pedestrian", "Motorcycle", "Moped"]
by_key = {k: v.set_index("municipality_nis_code") for k, v in periods_tbl.groupby(["group", "period"])}
def ints(group, period, column):
    return [int(v) for v in by_key[(group, period)].loc[feature_order, column]]
muni = {
    "nis": feature_order, "name": [base_tbl.loc[n, "municipality"] for n in feature_order], "region": [base_tbl.loc[n, "region"] for n in feature_order],
    "bx": [round(float(pos_tbl.loc[n, "bubble_x"]), 1) for n in feature_order], "by": [round(float(pos_tbl.loc[n, "bubble_y"]), 1) for n in feature_order],
    "cx": [round(float(f["x"]), 1) for f in outlines["features"]], "cy": [round(float(f["y"]), 1) for f in outlines["features"]],
    "start": starts, "end": ends, "periods": period_keys,
    "total": {p: ints("All accidents", p, "accidents") for p in period_keys},
    "g": {g: {p: {"a": ints(g, p, "accidents"), "s": ints(g, p, "severe")} for p in period_keys} for g in muni_groups[1:]},
}
assert sum(muni["total"]["2017-2024"]) == 289532 and sum(muni["g"]["Pedestrian"]["2017-2024"]["a"]) == 29897

extra = {"muni": muni, "s5models": dx.MODELS5, "s5singleviews": [list(v) for v in dx.SINGLE_VIEWS], "outline": {"x": xs, "y": ys}, "scopes": [[k, v] for k, v in scopes], "figs": figs, "hotspots": hotspots, "tables": tables}

# --- 3. Put everything into the template ---
template = open(template_file, encoding="utf-8").read()
extra_html, extra_script = open(extra_file, encoding="utf-8").read().split("<!--EXTRA-SCRIPT-->")
assert template.count("/*__DATA__*/null") == 1 and extra_script.count("/*__EXTRA__*/null") == 1, "a data placeholder was not found exactly once"
anchor = '  <section id="sec-about" class="about">'
assert template.count(anchor) == 1, "the 'about' section was not found"
page = template.replace(anchor, extra_html + "\n" + anchor)
page = page.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
extra_script = extra_script.replace("/*__EXTRA__*/null", json.dumps(extra, separators=(",", ":"), allow_nan=False))
assert page.rstrip().endswith("</script>"), "unexpected end of the template"
page = page.rstrip() + "\n" + extra_script
Path(output_file).write_text(page, encoding="utf-8")
print(f"Saved {output_file}: {len(page) / 1e6:.1f} MB; figures {len(figs)}, hotspot sets {len(hotspots)}, tables {len(tables)}")
