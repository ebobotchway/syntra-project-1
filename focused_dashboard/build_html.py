"""
Builds the focused dashboard as ONE self-contained HTML file (focused_dashboard.html): step 1 (1a, 1b), step 2, step 3b/3c with a group filter, and step 4a.

It combines
  template_page.html    the page: design, sidebar filters, and step 1 (1a and 1b), drawn in the browser from the summary table data/dashboard_data.csv
  template_extra.html   the sections of steps 2, 3b/3c and 4a (HTML and the script that draws them)
  results/*, data/*     the SAVED results, turned into Plotly figures by charts.py (the same charts as the Streamlit app)
and writes one file with all data inside (no downloads except the chart library, which needs internet, and the fonts).

How to run (from this folder, with `conda activate syntra-ds`):
    python build_html.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import charts

HERE = Path(__file__).parent
OUTPUT = HERE / "focused_dashboard.html"

# --- 1. Step 1: the summary table (accidents per group, year and month); the page calculates 1a and 1b from it in the browser ---
table = pd.read_csv(charts.DATA / "dashboard_data.csv")
ranking = pd.read_csv(charts.RESULTS / "accidents_per_road_user.csv")["road_user_group"].tolist()
names = ["All accidents"] + ranking
index_of = {name: i for i, name in enumerate(names)}
rows = [[index_of[g], int(y), int(m), int(n)] for g, y, m, n in zip(table["road_user_group"], table["year"], table["month"], table["accidents"])]
data = {"names": names, "years": sorted(int(y) for y in table["year"].unique()), "rows": rows}
assert len(rows) == 11 * 8 * 12, "unexpected number of rows"


# --- 2. Steps 2, 3b/3c and 4a: figures and tables from the saved results ---
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


res, outlines, provinces, cells, positions = charts.load_results(), charts.load_outlines(), charts.load_provinces(), charts.load_hotspot_cells(), charts.load_positions()
figs, tables = {}, {}

# step 2: one pair of figures and one table per period
scopes = list(charts.SCOPE_LABELS.items())
for scope, _ in scopes:
    figs[f"s2a|{scope}"] = plain(charts.fig_severity_intervals(res, scope))
    figs[f"s2b|{scope}"] = plain(charts.fig_severity_distribution(res, scope))
    a, b, c = (res[k][res[k]["scope"] == scope].set_index("road_user_group") for k in ("severity_a_fatal", "severity_b_serious", "severity_c_slight"))
    combined = a[["accidents", "count", "share_pct", "ci_low_pct", "ci_high_pct", "ratio_to_all", "gap_points"]].rename(
        columns={"count": "fatal", "share_pct": "fatal %", "ci_low_pct": "fatal low", "ci_high_pct": "fatal high", "ratio_to_all": "fatal ratio", "gap_points": "fatal gap"})
    combined["serious"], combined["serious %"] = b["count"], b["share_pct"]
    combined["slight"], combined["slight %"] = c["count"], c["share_pct"]
    tables[f"s2|{scope}"] = spec(combined.reset_index())

# step 3b/3c, hotspots: for each group and period a heat map; the page fills in the squares from a compact list
hotspots = {}
for group in charts.GROUPS4:
    for scope in ("2017-2024", "2022-2024"):
        fig = strip_outline(plain(charts.fig_hotspots(res, cells, outlines, group, scope)))
        c = cells[(cells["group"] == group) & (cells["scope"] == scope)]
        cx0, cy0 = int(c["cx"].min()), int(c["cy"].min())
        heat = [t for t in fig["data"] if t["type"] == "heatmap"][0]
        heat["z"] = []  # filled in by the page from the compact list of squares
        cov = res["geo_coverage"]
        cov = cov[(cov["group"] == group) & (cov["scope"] == scope)].iloc[0]
        top = res[f"geo_hotspots_{group.lower()}"]
        top = top[top["scope"] == scope].drop(columns=["scope"])
        plural = charts.GROUP_WORDS[group][1]
        hotspots[f"{group}|{scope}"] = {
            "fig": fig, "cx0": cx0, "cy0": cy0, "cols": int(c["cx"].max() - cx0 + 1), "rows": int(c["cy"].max() - cy0 + 1),
            "cx": [int(v) for v in c["cx"]], "cy": [int(v) for v in c["cy"]], "n": [int(v) for v in c["accidents"]],
            "coverage": f"{cov['with_coordinates']:,.0f} of {cov['accidents']:,.0f} accidents involving {plural} have usable coordinates ({100 - cov['left_out_pct']:.1f}%); the other {cov['left_out']:,.0f} are not on the map.",
            "table": spec(top, digits=2)}

# step 4a
figs["s4a1"] = plain(charts.fig_regional_overview(res))
figs["s4a2"] = plain(charts.fig_province_map(res, provinces))
regional = res["severity_regional_regions_provinces"]
tables["s4a1"] = spec(regional[regional["group"] == "All accidents"], "severity_regions_provinces_all_accidents.csv")

# --- 3. Step 3b/3c, municipalities: the numbers per municipality, group and period; the page ranks and draws them in the browser, so the buttons can combine freely ---
periods_tbl = charts.load_municipality_periods()
base_tbl = res["geo_a_cyclists_by_municipality"].set_index("municipality_nis_code")
feature_order = [f["nis"] for f in outlines["features"]]
pos_tbl = positions.set_index("municipality_nis_code")
xs, ys = [], []  # the municipality borders once, as one line with gaps (None) between rings
starts, ends = [], []  # where each municipality's rings start and end in those lists (for the choropleth)
for f in outlines["features"]:
    x, y = charts._ring_xy(f["polys"])
    starts.append(len(xs)); xs += x; ys += y; ends.append(len(xs))
period_keys = ["2017-2024", "2022-2024"] + [str(y) for y in range(2017, 2025)]
by_key = {k: v.set_index("municipality_nis_code") for k, v in periods_tbl.groupby(["group", "period"])}


def ints(group, period, column):
    return [int(v) for v in by_key[(group, period)].loc[feature_order, column]]


muni = {
    "nis": feature_order, "name": [base_tbl.loc[n, "municipality"] for n in feature_order], "region": [base_tbl.loc[n, "region"] for n in feature_order],
    "bx": [round(float(pos_tbl.loc[n, "bubble_x"]), 1) for n in feature_order], "by": [round(float(pos_tbl.loc[n, "bubble_y"]), 1) for n in feature_order],
    "cx": [round(float(f["x"]), 1) for f in outlines["features"]], "cy": [round(float(f["y"]), 1) for f in outlines["features"]],
    "start": starts, "end": ends, "periods": period_keys,
    "total": {p: ints("All accidents", p, "accidents") for p in period_keys},
    "g": {g: {p: {"a": ints(g, p, "accidents"), "s": ints(g, p, "severe")} for p in period_keys} for g in charts.GROUPS4},
}
assert sum(muni["total"]["2017-2024"]) == 289532 and sum(muni["g"]["Pedestrian"]["2017-2024"]["a"]) == 29897 and sum(muni["g"]["Bicycle"]["2017-2024"]["a"]) == 71881

extra = {"muni": muni, "outline": {"x": xs, "y": ys}, "scopes": [[k, v] for k, v in scopes], "figs": figs, "hotspots": hotspots, "tables": tables}

# --- 4. Put everything into the templates ---
template = (HERE / "template_page.html").read_text(encoding="utf-8")
extra_html, extra_script = (HERE / "template_extra.html").read_text(encoding="utf-8").split("<!--EXTRA-SCRIPT-->")
assert template.count("/*__DATA__*/null") == 1 and extra_script.count("/*__EXTRA__*/null") == 1, "a data placeholder was not found exactly once"
anchor = '  <section id="sec-about" class="about">'
assert template.count(anchor) == 1, "the 'about' section was not found"
page = template.replace(anchor, extra_html + "\n" + anchor)
page = page.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
extra_script = extra_script.replace("/*__EXTRA__*/null", json.dumps(extra, separators=(",", ":"), allow_nan=False))
assert page.rstrip().endswith("</script>"), "unexpected end of the template"
page = page.rstrip() + "\n" + extra_script
OUTPUT.write_text(page, encoding="utf-8")
print(f"Saved {OUTPUT.name}: {len(page) / 1e6:.1f} MB; figures {len(figs)}, hotspot sets {len(hotspots)}, tables {len(tables)}")
