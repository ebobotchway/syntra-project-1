"""
The Plotly graphs of steps 2-4 for the dashboards (decisions #109-#113). Every graph is built from the SAVED results in reports/ and data/
(the CSV files written by scripts 12-18); nothing is recalculated here (#110). Used by app.py (Streamlit) and by scripts/19_build_dashboard_html.py
(the claude.ai page). Coordinates are Belgian Lambert 1972 (EPSG:31370, metres).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = Path(__file__).parent
REPORTS, DATA = HERE / "reports", HERE / "data"

BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#898781"  # categorical slots 1-3 and the neutral gray
REGION_COLOURS = {"Brussels-Capital Region": BLUE, "Flemish Region": ORANGE, "Walloon Region": AQUA}
REGION_SHORT = {"Brussels-Capital Region": "Brussels", "Flemish Region": "Flanders", "Walloon Region": "Wallonia"}
SEVERITY_COLOURS = {"fatal": "#184f95", "serious": "#3987e5", "slight": "#86b6ef"}  # one blue ramp, dark = more severe
RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]  # five blue steps for map classes
NAMED = ["Passenger car", "Bicycle", "Pedestrian", "Van / light truck", "Moped", "Motorcycle", "Truck", "Bus"]
GROUPS5 = ["All accidents", "Bicycle", "Pedestrian", "Motorcycle", "Moped"]
ROAD_TYPES = ["Motorway", "Regional road", "Municipal road"]
SCOPE_LABELS = {"pooled_2017_2024": "All years 2017-2024", "pre_2017_2019": "Pre 2017-2019", "during_2020_2021": "During 2020-2021", "post_2022_2024": "Post 2022-2024"}
RESULT_FILES = ["severity_a_fatal", "severity_b_serious", "severity_c_slight", "severity_d_distribution", "geo_a_cyclists_by_municipality", "geo_hotspots_pedestrian",
                "geo_hotspots_motorcycle", "geo_hotspots_moped", "geo_coverage", "severity_regional_regions_provinces", "severity_regional_roadtype",
                "severity_by_square_concentration", "severity_by_municipality_density", "severity_density_correlation", "severity_municipality_density_table",
                "severity_regions_within_density", "severity_regions_within_density_roadtype", "severity_regions_standardised", "severity_regions_logistic",
                "severity_logit_coefficients", "severity_logit_fit", "severity_logit_predicted_by_category", "severity_logit_scenarios", "severity_logit_calibration",
                "severity_logit_interactions_pairs", "severity_logit_interactions_tests", "severity_logit_roaduser_with_without_collision"]


# --------------------------------------------------------------------------------------
# Loading the saved results
# --------------------------------------------------------------------------------------
def load_results():
    """All saved result tables, by file name (without .csv)."""
    return {name: pd.read_csv(REPORTS / f"{name}.csv", dtype={"municipality_nis_code": str}) for name in RESULT_FILES}


def load_outlines():
    return json.loads((DATA / "municipality_outlines.json").read_text(encoding="utf-8"))


def load_provinces():
    return json.loads((DATA / "province_outlines.json").read_text(encoding="utf-8"))


def load_hotspot_cells():
    return pd.read_csv(DATA / "hotspot_cells.csv")


def load_positions():
    return pd.read_csv(DATA / "municipality_positions.csv", dtype={"municipality_nis_code": str})


# --------------------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------------------
def _layout(fig, height, **extra):
    options = dict(height=height, margin=dict(l=10, r=10, t=60, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    options.update(extra)  # anything passed in (for example a different margin) replaces the default
    fig.update_layout(**options)
    return fig


def _dots(fig, row, col, x, y, low, high, colour, hover, orientation="h", hollow=None, name=None, legend=False, size=9):
    """Points with a 95% interval. 'h' = the value is on x (horizontal interval), 'v' = the value is on y (vertical interval)."""
    value = np.asarray(x if orientation == "h" else y, float)
    err = dict(type="data", symmetric=False, array=np.asarray(high, float) - value, arrayminus=value - np.asarray(low, float), thickness=2, width=0, color=colour)
    hollow = hollow if hollow is not None else [False] * len(value)
    if legend:  # the legend entry is its own solid dot, so it never copies a hollow first point
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=name, legendgroup=name, marker=dict(size=11, color=colour)), row=row, col=col)
    fig.add_trace(go.Scatter(
        x=list(x), y=list(y), mode="markers", name=name, showlegend=False, legendgroup=name,
        marker=dict(size=size, color=["rgba(0,0,0,0)" if h else colour for h in hollow], line=dict(color=colour, width=2)),
        error_x=err if orientation == "h" else None, error_y=err if orientation == "v" else None,
        hovertext=list(hover), hovertemplate="%{hovertext}<extra></extra>"), row=row, col=col)


def _share_text(r, label):
    count = r[f"{label}_count"] if f"{label}_count" in r.index else r[label]  # some tables call the count 'fatal_count', others just 'fatal'
    return (f"{r[f'{label}_share_pct']:.2f}% ({count:,.0f} of {r['accidents']:,.0f})<br>95% interval {r[f'{label}_ci_low']:.2f}-{r[f'{label}_ci_high']:.2f}%"
            + ("<br><i>fewer than 100 accidents: unstable</i>" if r["few_accidents"] else ""))


def _percent_axes(fig, axis="y"):
    (fig.update_yaxes if axis == "y" else fig.update_xaxes)(ticksuffix="%", tickformat="~g")


def _ring_xy(polys):
    """Flat ring lists -> x and y lists with None between rings (what a Plotly line/fill trace needs)."""
    xs, ys = [], []
    for polygon in polys:
        for ring in polygon:
            xs += ring[0::2] + [None]
            ys += ring[1::2] + [None]
    return xs, ys


def _equal_axes(fig, rows, cols):
    """A map: hide the axes and keep one metre the same length in x and y."""
    if rows == 1 and cols == 1:  # a single panel, made without make_subplots
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1)
        return
    n = 0
    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            n += 1
            fig.update_xaxes(visible=False, row=r, col=c)
            fig.update_yaxes(visible=False, scaleanchor=f"x{n if n > 1 else ''}", scaleratio=1, row=r, col=c)


def _quantile_classes(values, n=5):
    edges = np.unique(np.quantile(values, np.linspace(0, 1, n + 1)))
    return edges, np.clip(np.digitize(values, edges[1:-1], right=True), 0, len(edges) - 2)


def outline_trace(outlines, fill="rgba(137,135,129,0.10)"):
    """All municipality borders as one background trace."""
    xs, ys = [], []
    for f in outlines["features"]:
        x, y = _ring_xy(f["polys"])
        xs += x; ys += y
    return go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor=fill, line=dict(color="rgba(137,135,129,0.55)", width=0.5), hoverinfo="skip", showlegend=False, name="municipality borders")


# --------------------------------------------------------------------------------------
# Step 2: severity by road-user group
# --------------------------------------------------------------------------------------
def fig_severity_intervals(res, scope):
    """Fatal, serious and slight share per group with 95% intervals; the gray line is all accidents."""
    labels = (("severity_a_fatal", "a. Fatal (class 1 + 2)"), ("severity_b_serious", "b. Seriously injured (class 3)"), ("severity_c_slight", "c. Slightly injured (class 4)"))
    tables = {key: res[key][res[key]["scope"] == scope].set_index("road_user_group") for key, _ in labels}
    titles = [f"<b>{title}</b><br><sup>all accidents: {tables[key].loc['All accidents', 'share_pct']:.1f}% (gray line)</sup>" for key, title in labels]
    fig = make_subplots(rows=1, cols=3, subplot_titles=titles, horizontal_spacing=0.2)
    for i, (key, _) in enumerate(labels, start=1):
        t = tables[key]
        d = t.loc[NAMED].sort_values("share_pct")  # lowest first, so the highest ends up at the top
        y = list(range(len(d)))
        hover = [f"<b>{g}</b><br>{r['share_pct']:.2f}% ({r['count']:,.0f} of {r['accidents']:,.0f})<br>95% interval {r['ci_low_pct']:.2f}-{r['ci_high_pct']:.2f}%<br>ratio to all accidents {r['ratio_to_all']:.2f}, gap {r['gap_points']:+.2f} points" for g, r in d.iterrows()]
        _dots(fig, 1, i, d["share_pct"], y, d["ci_low_pct"], d["ci_high_pct"], BLUE, hover)
        fig.add_trace(go.Scatter(x=d["ci_high_pct"], y=y, mode="text", text=[f"  {v:.1f}%" for v in d["share_pct"]], textposition="middle right", hoverinfo="skip", showlegend=False), row=1, col=i)
        fig.add_vline(x=t.loc["All accidents", "share_pct"], line_color=GRAY, line_width=2, row=1, col=i)
        fig.update_yaxes(tickvals=y, ticktext=list(d.index), row=1, col=i)
        lo, hi = min(d["ci_low_pct"].min(), t.loc["All accidents", "share_pct"]), max(d["ci_high_pct"].max(), t.loc["All accidents", "share_pct"])
        fig.update_xaxes(range=[max(0, lo - (hi - lo) * 0.12), hi + (hi - lo) * 0.3], row=1, col=i)
    _percent_axes(fig, "x")
    return _layout(fig, 430)


def fig_severity_distribution(res, scope):
    """100% stacked bars: fatal, serious and slight share of each group's accidents, ordered by fatal share."""
    d = res["severity_d_distribution"]
    d = d[d["scope"] == scope].set_index("road_user_group")
    order = sorted(NAMED, key=lambda g: d.loc[g, "fatal_total_pct"]) + ["All accidents"]  # the highest fatal share (and the reference) at the top
    parts = (("fatal", "Fatal", "fatal_total_pct"), ("serious", "Seriously injured", "seriously_injured_class3_pct"), ("slight", "Slightly injured", "slightly_injured_class4_pct"))
    fig = go.Figure()
    for key, label, column in parts:
        hover = [f"<b>{g}</b><br>{label}: {d.loc[g, column]:.2f}%" + (f"<br>with fatalities {d.loc[g, 'with_fatalities_class1_pct']:.2f}%, fatally injured {d.loc[g, 'fatally_injured_class2_pct']:.2f}%" if key == "fatal" else "") for g in order]
        fig.add_trace(go.Bar(y=order, x=[d.loc[g, column] for g in order], orientation="h", name=label, marker_color=SEVERITY_COLOURS[key], hovertext=hover, hovertemplate="%{hovertext}<extra></extra>"))
    # The labels sit outside the plot, so x is in page coordinates: Plotly hides labels whose data coordinate is beyond the axis range.
    for g in order:
        fig.add_annotation(x=1.005, y=g, xref="paper", yref="y", xanchor="left", showarrow=False, text=f"fatal {d.loc[g, 'fatal_total_pct']:.1f}% · serious {d.loc[g, 'seriously_injured_class3_pct']:.1f}%", font=dict(size=11))
    fig.update_layout(barmode="stack", bargap=0.35, legend=dict(orientation="h", y=-0.12, traceorder="normal"), xaxis=dict(range=[0, 100], ticksuffix="%"))
    return _layout(fig, 470, margin=dict(l=10, r=190, t=30, b=10))


# --------------------------------------------------------------------------------------
# Step 3: cyclists by municipality
# --------------------------------------------------------------------------------------
def fig_cyclists_ranked(res):
    """Top 20 municipalities by number of cyclist accidents and by cyclist share (municipalities with at least 100 accidents)."""
    t = res["geo_a_cyclists_by_municipality"]
    national = t["accidents_cyclists"].sum() / t["accidents_total"].sum() * 100
    panels = ((t.sort_values("accidents_cyclists", ascending=False).head(20), "accidents_cyclists", "Top 20 by accidents involving cyclists"),
              (t[t["ranked_by_share"]].sort_values("cyclist_share_pct", ascending=False).head(20), "cyclist_share_pct", f"Top 20 by cyclist share (100+ accidents)<br><sup>Belgium: {national:.1f}% (gray line)</sup>"))
    fig = make_subplots(rows=1, cols=2, subplot_titles=[f"<b>{p[2]}</b>" for p in panels], horizontal_spacing=0.28)
    for i, (d, column, _) in enumerate(panels, start=1):
        d = d.iloc[::-1]  # the biggest at the top
        is_share = column == "cyclist_share_pct"
        text = [f"{r[column]:.1f}%  ({r['accidents_cyclists']:,} of {r['accidents_total']:,})" if is_share else f"{r[column]:,}  ({r['cyclist_share_pct']:.0f}% of {r['accidents_total']:,})" for _, r in d.iterrows()]
        hover = [f"<b>{r['municipality']}</b> ({r['region']})<br>{r['accidents_cyclists']:,} accidents involve cyclists<br>{r['cyclist_share_pct']:.1f}% of its {r['accidents_total']:,} accidents" for _, r in d.iterrows()]
        fig.add_trace(go.Bar(y=d["municipality"], x=d[column], orientation="h", marker_color=BLUE, text=text, textposition="outside", cliponaxis=False, hovertext=hover, hovertemplate="%{hovertext}<extra></extra>", showlegend=False), row=1, col=i)
        fig.update_xaxes(range=[0, d[column].max() * 1.75], ticksuffix="%" if is_share else "", tickformat="~g" if is_share else ",d", row=1, col=i)
    fig.add_vline(x=national, line_color=GRAY, line_width=2, row=1, col=2)
    fig.update_yaxes(tickfont=dict(size=11))
    return _layout(fig, 640)


def fig_cyclists_bubble(res, outlines, positions):
    """A bubble per municipality at the average position of its accidents: size = cyclist accidents, colour = cyclist share (5 quantile classes)."""
    t = res["geo_a_cyclists_by_municipality"].merge(positions[["municipality_nis_code", "bubble_x", "bubble_y"]], on="municipality_nis_code")
    t = t[t["accidents_cyclists"] > 0].sort_values("accidents_cyclists", ascending=False)  # big bubbles first, small on top
    ranked = t[t["ranked_by_share"]]
    edges, _ = _quantile_classes(ranked["cyclist_share_pct"].values)
    classes = np.clip(np.digitize(t["cyclist_share_pct"].values, edges[1:-1], right=True), 0, len(edges) - 2)
    fig = go.Figure([outline_trace(outlines)])
    scale = 60 / np.sqrt(t["accidents_cyclists"].max())
    groups = [(k, RAMP[k], f"{edges[k]:.0f}-{edges[k + 1]:.0f}% cyclist share", (classes == k) & t["ranked_by_share"].values) for k in range(len(edges) - 1)]
    groups.append((-1, GRAY, "fewer than 100 accidents (not ranked)", ~t["ranked_by_share"].values))
    for _, colour, label, mask in groups:
        d = t[mask]
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=label, legendgroup=label, marker=dict(size=12, color=colour)))  # the legend entry: a clear dot of fixed size
        fig.add_trace(go.Scatter(x=d["bubble_x"], y=d["bubble_y"], mode="markers", name=label, legendgroup=label, showlegend=False, marker=dict(size=np.sqrt(d["accidents_cyclists"]) * scale, color=colour, opacity=0.85, line=dict(color="white", width=0.6)),
                                 hovertext=[f"<b>{r['municipality']}</b><br>{r['accidents_cyclists']:,} accidents involve cyclists<br>{r['cyclist_share_pct']:.1f}% of {r['accidents_total']:,} accidents" for _, r in d.iterrows()], hovertemplate="%{hovertext}<extra></extra>"))
    fig.update_layout(legend=dict(orientation="h", y=-0.02, x=0))
    _equal_axes(fig, 1, 1)
    return _layout(fig, 700, margin=dict(l=0, r=0, t=10, b=0))


def fig_cyclists_choropleth(res, outlines):
    """Two maps: accidents involving cyclists (all municipalities) and cyclist share (municipalities with 100+ accidents), 5 quantile classes each."""
    t = res["geo_a_cyclists_by_municipality"].set_index("municipality_nis_code")
    feats = outlines["features"]
    count = np.array([t.loc[f["nis"], "accidents_cyclists"] for f in feats], float)
    share = np.array([t.loc[f["nis"], "cyclist_share_pct"] for f in feats], float)
    ranked = np.array([bool(t.loc[f["nis"], "ranked_by_share"]) for f in feats])
    fig = make_subplots(rows=1, cols=2, subplot_titles=["<b>Accidents involving cyclists</b>", "<b>Cyclist share of the municipality's accidents</b>"], horizontal_spacing=0.02)
    for col, (values, mask, unit) in enumerate(((count, np.ones(len(feats), bool), "accidents"), (share, ranked, "%")), start=1):
        edges, _ = _quantile_classes(values[mask])  # the class limits come from the municipalities that count ...
        classes = np.clip(np.digitize(values, edges[1:-1], right=True), 0, len(edges) - 2)  # ... and are then applied to every municipality
        parts = [(RAMP[k], f"{edges[k]:,.0f}-{edges[k + 1]:,.0f}" if unit == "accidents" else f"{edges[k]:.0f}-{edges[k + 1]:.0f}%", mask & (classes == k)) for k in range(len(edges) - 1)]
        if unit == "%":
            parts.append((GRAY, "fewer than 100 accidents (not ranked)", ~mask))
        for colour, label, selected in parts:
            xs, ys = [], []
            for f, s in zip(feats, selected):
                if s:
                    x, y = _ring_xy(f["polys"]); xs += x; ys += y
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor=colour, line=dict(color="rgba(255,255,255,0.7)", width=0.4), name=label, legendgroup=f"{col}-{label}", hoverinfo="skip"), row=1, col=col)
        fig.add_trace(go.Scatter(x=[f["x"] for f in feats], y=[f["y"] for f in feats], mode="markers", marker=dict(size=9, opacity=0), showlegend=False,
                                 hovertext=[f"<b>{f['name']}</b><br>{count[i]:,.0f} accidents involve cyclists<br>{share[i]:.1f}% of {t.loc[f['nis'], 'accidents_total']:,} accidents" + ("" if ranked[i] else "<br><i>too few accidents to rank by share</i>") for i, f in enumerate(feats)],
                                 hovertemplate="%{hovertext}<extra></extra>"), row=1, col=col)
    _equal_axes(fig, 1, 2)
    fig.update_layout(legend=dict(orientation="h", y=-0.02))
    return _layout(fig, 560, margin=dict(l=0, r=0, t=50, b=0))


# --------------------------------------------------------------------------------------
# Step 3: hotspots (500 m squares)
# --------------------------------------------------------------------------------------
HOTSPOT_BREAKS = [1, 2, 3, 5, 10, 20, 50]  # colour steps of the heatmap (accidents per square)
HOTSPOT_COLOURS = ["#cde2fb", "#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]


def hotspot_colourscale(top):
    """A stepped colour scale: each step starts at one of the break values (in accidents per square)."""
    breaks = [b for b in HOTSPOT_BREAKS if b < top] or [1]
    stops = []
    for i, b in enumerate(breaks):
        start = (b - 1) / max(top - 1, 1)
        end = ((breaks[i + 1] - 1) / max(top - 1, 1)) if i + 1 < len(breaks) else 1.0
        stops += [[start, HOTSPOT_COLOURS[i]], [end, HOTSPOT_COLOURS[i]]]
    stops[0][0] = 0.0
    return stops


def fig_hotspots(res, cells, outlines, group, scope):
    """The accidents per 500 m square as a zoomable heat map, with the 20 busiest squares marked (hover for details)."""
    c = cells[(cells["group"] == group) & (cells["scope"] == scope)]
    x0, y0 = c["cx"].min(), c["cy"].min()
    z = np.full((c["cy"].max() - y0 + 1, c["cx"].max() - x0 + 1), np.nan)
    z[c["cy"].values - y0, c["cx"].values - x0] = c["accidents"].values
    top_table = res[f"geo_hotspots_{group.lower()}"]
    top_table = top_table[top_table["scope"] == scope]
    top = float(c["accidents"].max())
    fig = go.Figure([outline_trace(outlines)])
    fig.add_trace(go.Heatmap(z=z, x0=x0 * 500 + 250, dx=500, y0=y0 * 500 + 250, dy=500, zmin=1, zmax=top, colorscale=hotspot_colourscale(top), hoverongaps=False,
                             colorbar=dict(title="accidents<br>per square", thickness=12, len=0.6), hovertemplate="%{z:.0f} accidents in this 500 m square<extra></extra>"))
    fig.add_trace(go.Scatter(x=top_table["centre_x_m"], y=top_table["centre_y_m"], mode="markers", name="20 busiest squares", marker=dict(symbol="square-open", size=10, color="#0b0b0b", line=dict(width=1.5)),
                             hovertext=[f"<b>Rank {r['rank']}: {r['municipality']}</b><br>{r['accidents']:,} accidents involving {group.lower()}s<br>{r['all_accidents_in_square']:,} accidents of all road users in the square ({r['group_share_of_square_pct']:.0f}% involve {group.lower()}s)" for _, r in top_table.iterrows()],
                             hovertemplate="%{hovertext}<extra></extra>"))
    fig.update_layout(legend=dict(orientation="h", y=-0.02))
    _equal_axes(fig, 1, 1)
    return _layout(fig, 640, margin=dict(l=0, r=0, t=10, b=0))


# --------------------------------------------------------------------------------------
# Step 4a: regional severity
# --------------------------------------------------------------------------------------
def fig_regional_overview(res):
    """Fatal and serious share per region and province, all accidents; the gray line is Belgium."""
    t = res["severity_regional_regions_provinces"]
    t = t[t["group"] == "All accidents"]
    refs = {label: t[t["level"] == "Belgium"][f"{label}_share_pct"].iat[0] for label in ("fatal", "serious")}
    fig = make_subplots(rows=1, cols=2, subplot_titles=[f"<b>Fatal accidents (class 1 + 2)</b><br><sup>Belgium: {refs['fatal']:.1f}% (gray line)</sup>", f"<b>Seriously injured accidents (class 3)</b><br><sup>Belgium: {refs['serious']:.1f}% (gray line)</sup>"], horizontal_spacing=0.3)
    for i, label in enumerate(("fatal", "serious"), start=1):
        ref = refs[label]
        rows, ticks, y = [], [], 0
        for block, name in (("Province", "Provinces"), ("Region", "Regions")):  # bottom to top: provinces first, regions on top
            d = t[t["level"] == block].sort_values(f"{label}_share_pct")
            for _, r in d.iterrows():
                rows.append((y, r)); ticks.append((y, r["area"])); y += 1
            ticks.append((y, f"<b>{name}</b>")); y += 1.4
        ys = [p[0] for p in rows]
        d = pd.DataFrame([p[1] for p in rows])
        _dots(fig, 1, i, d[f"{label}_share_pct"], ys, d[f"{label}_ci_low"], d[f"{label}_ci_high"], BLUE,
              [f"<b>{r['area']}</b><br>" + _share_text(r, label) + f"<br>ratio to Belgium {r[f'{label}_ratio_to_belgium']:.2f}, gap {r[f'{label}_gap_points']:+.2f} points" for _, r in d.iterrows()])
        fig.add_trace(go.Scatter(x=d[f"{label}_ci_high"], y=ys, mode="text", text=[f"  {v:.1f}%" for v in d[f"{label}_share_pct"]], textposition="middle right", hoverinfo="skip", showlegend=False), row=1, col=i)
        fig.add_vline(x=ref, line_color=GRAY, line_width=2, row=1, col=i)
        fig.update_yaxes(tickvals=[p[0] for p in ticks], ticktext=[p[1] for p in ticks], row=1, col=i)
        fig.update_xaxes(range=[max(0, d[f"{label}_ci_low"].min() * 0.5), d[f"{label}_ci_high"].max() * 1.22], row=1, col=i)
    _percent_axes(fig, "x")
    return _layout(fig, 600)


def fig_regional_groups(res):
    """Fatal and serious share per region, per road-user group (2 rows x 5 columns); the gray line is Belgium for that group."""
    t = res["severity_regional_regions_provinces"]
    t = t[t["level"].isin(["Region", "Belgium"])]
    fig = make_subplots(rows=2, cols=5, subplot_titles=[f"<b>{g}</b>" for g in GROUPS5], horizontal_spacing=0.05, vertical_spacing=0.18)
    for c, group in enumerate(GROUPS5, start=1):
        for r_i, label in enumerate(("fatal", "serious"), start=1):
            g = t[t["group"] == group]
            ref = g[g["level"] == "Belgium"][f"{label}_share_pct"].iat[0]
            for k, (region, colour) in enumerate(REGION_COLOURS.items()):
                d = g[g["area"] == region]
                _dots(fig, r_i, c, [k], [d[f"{label}_share_pct"].iat[0]], [d[f"{label}_ci_low"].iat[0]], [d[f"{label}_ci_high"].iat[0]], colour,
                      [f"<b>{group}, {REGION_SHORT[region]}</b><br>" + _share_text(d.iloc[0], label)], orientation="v", name=REGION_SHORT[region], legend=(c == 1 and r_i == 1))
            fig.add_hline(y=ref, line_color=GRAY, line_width=1.5, row=r_i, col=c)
            fig.update_yaxes(range=[0, max(g[f"{label}_ci_high"].max(), ref) * 1.15], row=r_i, col=c, title_text=("fatal share" if label == "fatal" else "serious share") if c == 1 else None)
            fig.update_xaxes(tickvals=[0, 1, 2], ticktext=["Bru", "Fla", "Wal"], range=[-0.6, 2.6], row=r_i, col=c)
    _percent_axes(fig, "y")
    fig.update_layout(legend=dict(orientation="h", y=-0.08))
    return _layout(fig, 560)


def fig_regional_roadtype(res):
    """The same within each road type; hollow dots = fewer than 100 accidents (they can run off the panel); gray tick = Belgium on that road type."""
    t = res["severity_regional_roadtype"]
    fig = make_subplots(rows=2, cols=5, subplot_titles=[f"<b>{g}</b>" for g in GROUPS5], horizontal_spacing=0.05, vertical_spacing=0.18)
    for c, group in enumerate(GROUPS5, start=1):
        for r_i, label in enumerate(("fatal", "serious"), start=1):
            tops = []
            for k, (region, colour) in enumerate(REGION_COLOURS.items()):
                d = t[(t["group"] == group) & (t["region"] == region) & (t["road_type"].isin(ROAD_TYPES)) & (t["accidents"] > 0)]
                x = [ROAD_TYPES.index(rt) + (k - 1) * 0.22 for rt in d["road_type"]]
                _dots(fig, r_i, c, x, d[f"{label}_share_pct"], d[f"{label}_ci_low"], d[f"{label}_ci_high"], colour,
                      [f"<b>{group}, {REGION_SHORT[region]}, {r['road_type']}</b><br>" + _share_text(r, label) for _, r in d.iterrows()], orientation="v", hollow=list(d["few_accidents"]),
                      name=REGION_SHORT[region], legend=(c == 1 and r_i == 1), size=8)
                tops += list(d.loc[~d["few_accidents"], f"{label}_ci_high"])
            for j, rt in enumerate(ROAD_TYPES):  # Belgium on this road type
                d = t[(t["group"] == group) & (t["road_type"] == rt)]
                fig.add_shape(type="line", x0=j - 0.4, x1=j + 0.4, y0=d[f"{label}_count"].sum() / d["accidents"].sum() * 100, y1=d[f"{label}_count"].sum() / d["accidents"].sum() * 100, line=dict(color=GRAY, width=2), row=r_i, col=c)
            fig.update_yaxes(range=[0, (max(tops) if tops else 1) * 1.12], row=r_i, col=c, title_text=("fatal share" if label == "fatal" else "serious share") if c == 1 else None)
            fig.update_xaxes(tickvals=[0, 1, 2], ticktext=["Mwy", "Reg", "Mun"], range=[-0.6, 2.6], row=r_i, col=c)
    _percent_axes(fig, "y")
    fig.update_layout(legend=dict(orientation="h", y=-0.08))
    return _layout(fig, 560)


def fig_province_map(res, provinces):
    """The 10 provinces + Brussels coloured by fatal share and by serious share (5 quantile classes), all accidents."""
    t = res["severity_regional_regions_provinces"]
    t = t[(t["group"] == "All accidents") & (t["level"] == "Province")].set_index("area")
    feats = provinces["features"]
    fig = make_subplots(rows=1, cols=2, subplot_titles=["<b>Fatal share of accidents</b>", "<b>Serious-injury share of accidents</b>"], horizontal_spacing=0.02)
    for col, label in enumerate(("fatal", "serious"), start=1):
        values = np.array([t.loc[f["name"], f"{label}_share_pct"] for f in feats])
        edges, classes = _quantile_classes(values)
        for k in range(len(edges) - 1):
            xs, ys = [], []
            for f, c in zip(feats, classes):
                if c == k:
                    x, y = _ring_xy(f["polys"]); xs += x; ys += y
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor=RAMP[k], line=dict(color="rgba(255,255,255,0.9)", width=1), name=f"{edges[k]:.1f}-{edges[k + 1]:.1f}%", legendgroup=f"{col}{k}", hoverinfo="skip"), row=1, col=col)
        fig.add_trace(go.Scatter(x=[f["x"] for f in feats], y=[f["y"] for f in feats], mode="text+markers", marker=dict(size=14, opacity=0), showlegend=False,
                                 text=[f"{f['name'].replace(' (no province)', '')}<br><b>{v:.1f}%</b>" for f, v in zip(feats, values)], textfont=dict(size=11, color="#ffffff"),
                                 textposition=["middle left" if f["name"].startswith("Brussels") else "middle right" if f["name"] == "Flemish Brabant" else "middle center" for f in feats],
                                 hovertext=[f"<b>{f['name']}</b><br>" + _share_text(t.loc[f["name"]], label) for f in feats], hovertemplate="%{hovertext}<extra></extra>"), row=1, col=col)
    _equal_axes(fig, 1, 2)
    fig.update_layout(legend=dict(orientation="h", y=-0.02))
    return _layout(fig, 520, margin=dict(l=0, r=0, t=50, b=0))


# --------------------------------------------------------------------------------------
# Step 4b: concentration versus severity
# --------------------------------------------------------------------------------------
SQUARE_CLASSES = ["1", "2-4", "5-9", "10-19", "20-49", "50-99", "100+"]


def fig_squares(res):
    """Fatal and serious share by the number of accidents in the 500 m square (two periods); hollow = fewer than 100 accidents."""
    t = res["severity_by_square_concentration"]
    fig = make_subplots(rows=2, cols=5, subplot_titles=[f"<b>{g}</b>" for g in GROUPS5], horizontal_spacing=0.05, vertical_spacing=0.2)
    for c, group in enumerate(GROUPS5, start=1):
        g = t[(t["group"] == group) & (t["accidents"] > 0)]
        classes = [k for k in SQUARE_CLASSES if k in set(g["square_class"].astype(str))]
        for r_i, label in enumerate(("fatal", "serious"), start=1):
            tops = []
            for scope, colour, shift in (("2017-2024", BLUE, -0.13), ("2022-2024", ORANGE, 0.13)):
                d = g[g["scope"] == scope]
                d = d[d["square_class"].astype(str).isin(classes)]
                x = [classes.index(str(k)) + shift for k in d["square_class"]]
                _dots(fig, r_i, c, x, d[f"{label}_share_pct"], d[f"{label}_ci_low"], d[f"{label}_ci_high"], colour,
                      [f"<b>{group}, {scope}</b><br>{r['square_class']} accidents in the square ({r['squares']:,} squares)<br>" + _share_text(r, label) for _, r in d.iterrows()], orientation="v", hollow=list(d["few_accidents"]),
                      name=scope, legend=(c == 1 and r_i == 1), size=8)
                tops += list(d.loc[~d["few_accidents"], f"{label}_ci_high"])
            overall = g[f"overall_{label}_share_pct"].iloc[0]
            fig.add_hline(y=overall, line_color=GRAY, line_width=1.5, row=r_i, col=c)
            fig.update_yaxes(range=[0, max(tops + [overall]) * 1.12], row=r_i, col=c, title_text=("fatal share" if label == "fatal" else "serious share") if c == 1 else None)
            fig.update_xaxes(tickvals=list(range(len(classes))), ticktext=classes, tickangle=-35, range=[-0.6, len(classes) - 0.4], row=r_i, col=c)
    _percent_axes(fig, "y")
    fig.update_layout(legend=dict(orientation="h", y=-0.1))
    return _layout(fig, 600)


def fig_density_classes(res):
    """Fatal and serious share by municipality density class (5 equal-sized classes of accidents per km2 per year of that group)."""
    t = res["severity_by_municipality_density"]
    fig = make_subplots(rows=2, cols=5, subplot_titles=[f"<b>{g}</b>" for g in GROUPS5], horizontal_spacing=0.05, vertical_spacing=0.18)
    for c, group in enumerate(GROUPS5, start=1):
        d = t[t["group"] == group].sort_values("density_class")
        for r_i, label in enumerate(("fatal", "serious"), start=1):
            hover = [f"<b>{group}, density class {r['density_class']}</b><br>{r['municipalities']:.0f} municipalities, {r['density_min']:.2f}-{r['density_max']:.2f} accidents per km2 per year<br>{r[f'{label}_share_pct']:.2f}% of {r['accidents']:,.0f} accidents<br>95% interval {r[f'{label}_ci_low']:.2f}-{r[f'{label}_ci_high']:.2f}%" for _, r in d.iterrows()]
            _dots(fig, r_i, c, d["density_class"], d[f"{label}_share_pct"], d[f"{label}_ci_low"], d[f"{label}_ci_high"], BLUE, hover, orientation="v")
            fig.add_trace(go.Scatter(x=d["density_class"], y=d[f"{label}_ci_high"], mode="text", text=[f"{v:.1f}%" for v in d[f"{label}_share_pct"]], textposition="top center", hoverinfo="skip", showlegend=False), row=r_i, col=c)
            overall = d[f"{label}_count"].sum() / d["accidents"].sum() * 100
            fig.add_hline(y=overall, line_color=GRAY, line_width=1.5, row=r_i, col=c)
            fig.update_yaxes(range=[0, d[f"{label}_ci_high"].max() * 1.25], row=r_i, col=c, title_text=("fatal share" if label == "fatal" else "serious share") if c == 1 else None)
            fig.update_xaxes(tickvals=[1, 2, 3, 4, 5], ticktext=["1 low", "2", "3", "4", "5 high"], range=[0.4, 5.6], row=r_i, col=c)
    _percent_axes(fig, "y")
    return _layout(fig, 560)


def fig_density_scatter(res):
    """One dot per municipality: accidents per km2 per year (log scale) against the fatal / serious share; rho = Spearman rank correlation."""
    t = res["severity_municipality_density_table"]
    t = t[t["used_in_correlation"] & (t["density_per_km2_per_year"] > 0)]
    corr = res["severity_density_correlation"]
    fig = make_subplots(rows=2, cols=5, subplot_titles=[f"<b>{g}</b>" for g in GROUPS5], horizontal_spacing=0.05, vertical_spacing=0.2)
    for c, group in enumerate(GROUPS5, start=1):
        d = t[t["group"] == group]
        for r_i, label in enumerate(("fatal", "serious"), start=1):
            fig.add_trace(go.Scatter(x=d["density_per_km2_per_year"], y=d[f"{label}_share_pct"], mode="markers", showlegend=False,
                                     marker=dict(size=np.sqrt(d["accidents"]) * 0.2 + 3, color=BLUE, opacity=0.55, line=dict(color="white", width=0.4)),
                                     hovertext=[f"<b>{r['municipality']}</b> ({r['region']})<br>{r['density_per_km2_per_year']:.2f} accidents per km2 per year<br>{r[f'{label}_share_pct']:.1f}% {label} of {r['accidents']:,.0f} accidents" for _, r in d.iterrows()],
                                     hovertemplate="%{hovertext}<extra></extra>"), row=r_i, col=c)
            rho = corr[(corr["group"] == group) & (corr["indicator"] == label)].iloc[0]
            fig.add_annotation(text=f"rho = {rho['spearman_rho']:+.2f}<br>{int(rho['municipalities_used'])} municipalities", xref="x domain" if (r_i - 1) * 5 + c == 1 else f"x{(r_i - 1) * 5 + c} domain",
                               yref="y domain" if (r_i - 1) * 5 + c == 1 else f"y{(r_i - 1) * 5 + c} domain", x=0.98, y=0.98, xanchor="right", yanchor="top", showarrow=False, font=dict(size=11))
            fig.update_xaxes(type="log", dtick=1, tickformat="~g", row=r_i, col=c, title_text="accidents per km2 per year" if r_i == 2 else None)  # one tick per decade
            fig.update_yaxes(rangemode="tozero", row=r_i, col=c, title_text=("fatal share" if label == "fatal" else "serious share") if c == 1 else None)
    _percent_axes(fig, "y")
    return _layout(fig, 600)


# --------------------------------------------------------------------------------------
# Step 4c: regions within density classes
# --------------------------------------------------------------------------------------
def _region_dots(fig, d, label, row, col, x_of, legend, group_name):
    tops = []
    for k, (region, colour) in enumerate(REGION_COLOURS.items()):
        part = d[d["region"] == region]
        if part.empty:
            continue
        _dots(fig, row, col, [x_of(r) + (k - 1) * 0.22 for _, r in part.iterrows()], part[f"{label}_share_pct"], part[f"{label}_ci_low"], part[f"{label}_ci_high"], colour,
              [f"<b>{group_name}, {REGION_SHORT[region]}</b><br>density class {r['density_class']}" + (f", {r['road_type']}" if "road_type" in part else "") + "<br>" + _share_text(r, label) for _, r in part.iterrows()],
              orientation="v", hollow=list(part["few_accidents"]), name=REGION_SHORT[region], legend=legend, size=8)
        tops += list(part.loc[~part["few_accidents"], f"{label}_ci_high"])
    return max(tops) if tops else 1


def fig_within_density(res, groups=None):
    """Regions within the same density class: all accidents (2 panels), or all 5 groups (2 rows x 5)."""
    t = res["severity_regions_within_density"]
    groups = groups or ["All accidents"]
    cols = len(groups)
    fig = make_subplots(rows=2, cols=cols, subplot_titles=[f"<b>{g}</b>" for g in groups], horizontal_spacing=0.06 if cols > 2 else 0.1, vertical_spacing=0.18)
    for c, group in enumerate(groups, start=1):
        d = t[t["group"] == group]
        for r_i, label in enumerate(("fatal", "serious"), start=1):
            top = _region_dots(fig, d, label, r_i, c, lambda r: r["density_class"], legend=(c == 1 and r_i == 1), group_name=group)
            fig.update_yaxes(range=[0, top * 1.12], row=r_i, col=c, title_text=("fatal share" if label == "fatal" else "serious share") if c == 1 else None)
            fig.update_xaxes(tickvals=[1, 2, 3, 4, 5], ticktext=["1 low", "2", "3", "4", "5 high"], range=[0.4, 5.6], row=r_i, col=c, title_text="density class" if r_i == 2 else None)
    _percent_axes(fig, "y")
    fig.update_layout(legend=dict(orientation="h", y=-0.12))
    return _layout(fig, 560)


def fig_within_density_roadtype(res):
    """All accidents: regions within the same density class AND road type."""
    t = res["severity_regions_within_density_roadtype"]
    t = t[t["group"] == "All accidents"]
    fig = make_subplots(rows=2, cols=3, subplot_titles=[f"<b>{rt}</b>" for rt in ROAD_TYPES], horizontal_spacing=0.07, vertical_spacing=0.2)
    for c, rt in enumerate(ROAD_TYPES, start=1):
        d = t[t["road_type"] == rt]
        for r_i, label in enumerate(("fatal", "serious"), start=1):
            top = _region_dots(fig, d, label, r_i, c, lambda r: r["density_class"], legend=(c == 1 and r_i == 1), group_name="All accidents")
            fig.update_yaxes(range=[0, top * 1.12], row=r_i, col=c, title_text=("fatal share" if label == "fatal" else "serious share") if c == 1 else None)
            fig.update_xaxes(tickvals=[1, 2, 3, 4, 5], ticktext=["1 low", "2", "3", "4", "5 high"], range=[0.4, 5.6], row=r_i, col=c, title_text="density class" if r_i == 2 else None)
    _percent_axes(fig, "y")
    fig.update_layout(legend=dict(orientation="h", y=-0.1))
    return _layout(fig, 600)


def fig_gap_adjusted(res):
    """How much of the Wallonia-Flanders gap remains: crude -> same density class -> same density class and road type (standardised ratio and odds ratio)."""
    std, logit = res["severity_regions_standardised"], res["severity_regions_logistic"]
    fig = make_subplots(rows=2, cols=2, subplot_titles=["<b>Fatal: standardised ratio (Wallonia / Flanders)</b>", "<b>Serious: standardised ratio (Wallonia / Flanders)</b>",
                                                        "<b>Fatal: odds ratio, Wallonia vs Flanders</b>", "<b>Serious: odds ratio, Wallonia vs Flanders</b>"], horizontal_spacing=0.2, vertical_spacing=0.16)
    series = (("crude / region only", "circle-open", GRAY, 0.2), ("same density class", "diamond", BLUE, 0.0), ("same density class and road type", "square", BLUE, -0.2))
    for c, outcome in enumerate(("fatal", "serious"), start=1):
        for name, symbol, colour, dy in series:
            ys, xs, lows, highs, hover = [], [], [], [], []
            for i, group in enumerate(GROUPS5[::-1]):
                if name == "crude / region only":
                    s = std[(std["group"] == group) & (std["outcome"] == outcome) & (std["strata"] == "density_class")].iloc[0]
                    xs.append(s["ratio_crude"]); lows.append(s["ratio_crude"]); highs.append(s["ratio_crude"]); hover.append(f"<b>{group}</b><br>crude ratio {s['ratio_crude']:.2f}")
                else:
                    key = "density_class" if name == "same density class" else "density_class+road_type"
                    s = std[(std["group"] == group) & (std["outcome"] == outcome) & (std["strata"] == key)].iloc[0]
                    xs.append(s["ratio_standardised"]); lows.append(s["ratio_standardised_ci_low"]); highs.append(s["ratio_standardised_ci_high"])
                    hover.append(f"<b>{group}</b><br>{name}: ratio {s['ratio_standardised']:.2f} (95% interval {s['ratio_standardised_ci_low']:.2f}-{s['ratio_standardised_ci_high']:.2f})<br>Wallonia in Flanders' mix: {s['wallonia_standardised_share_pct']:.2f}%, Flanders {s['flanders_share_pct']:.2f}%")
                ys.append(i + dy)
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", name=name, legendgroup=name, showlegend=(c == 1), marker=dict(symbol=symbol, size=9, color=colour if symbol != "circle-open" else colour, line=dict(color=colour, width=2)),
                                     error_x=dict(type="data", symmetric=False, array=np.array(highs) - np.array(xs), arrayminus=np.array(xs) - np.array(lows), thickness=2, width=0, color=colour) if name != "crude / region only" else None,
                                     hovertext=hover, hovertemplate="%{hovertext}<extra></extra>"), row=1, col=c)
            models = {"crude / region only": "region only", "same density class": "+ density class", "same density class and road type": "+ density class + road type"}
            xs, lows, highs, hover = [], [], [], []
            for group in GROUPS5[::-1]:
                lg = logit[(logit["group"] == group) & (logit["outcome"] == outcome) & (logit["model"] == models[name]) & (logit["term"] == "Wallonia vs Flanders")].iloc[0]
                xs.append(lg["odds_ratio"]); lows.append(lg["ci_low"]); highs.append(lg["ci_high"])
                hover.append(f"<b>{group}</b><br>{name}: odds ratio {lg['odds_ratio']:.2f} (95% interval {lg['ci_low']:.2f}-{lg['ci_high']:.2f})")
            fig.add_trace(go.Scatter(x=xs, y=[i + dy for i in range(len(GROUPS5))], mode="markers", name=name, legendgroup=name, showlegend=False, marker=dict(symbol=symbol, size=9, color=colour, line=dict(color=colour, width=2)),
                                     error_x=dict(type="data", symmetric=False, array=np.array(highs) - np.array(xs), arrayminus=np.array(xs) - np.array(lows), thickness=2, width=0, color=colour),
                                     hovertext=hover, hovertemplate="%{hovertext}<extra></extra>"), row=2, col=c)
    for r_i in (1, 2):
        for c in (1, 2):
            fig.add_vline(x=1, line_color=GRAY, line_width=1.5, row=r_i, col=c)
            fig.update_yaxes(tickvals=list(range(len(GROUPS5))), ticktext=GROUPS5[::-1], row=r_i, col=c)
    fig.update_xaxes(title_text="1 = no difference between the regions", row=2)
    fig.update_layout(legend=dict(orientation="h", y=-0.1))
    return _layout(fig, 680)


# --------------------------------------------------------------------------------------
# Step 5: the saved logistic models (script 20)
# --------------------------------------------------------------------------------------
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
LOG_TICKS = [0.25, 0.5, 1, 2, 4, 8, 16]
MODELS5 = ["Baseline", "Cyclists", "Pedestrians", "Motorcyclists", "Mopeds"]
MODEL_STYLE = {"Baseline": ("#2a78d6", "circle"), "Cyclists": ("#eb6834", "square"), "Pedestrians": ("#1baf7a", "diamond"), "Motorcyclists": ("#eda100", "triangle-up"), "Mopeds": ("#e87ba4", "triangle-down")}


def fig_logit_forest(res, variables, models=None, height=None):
    """Adjusted odds ratios of the saved models (script 20, with collision type) for the given variables: one row per term, one marker per model, 95% cluster-robust intervals."""
    c = res["severity_logit_coefficients"]
    c = c[(c["spec"] == "full") & c["variable"].isin(variables)]
    models = models or MODELS5
    terms = []
    for var in variables:
        part = c[c["variable"] == var]
        terms += list(dict.fromkeys(part.sort_values("model", key=lambda m: m.map({k: i for i, k in enumerate(MODELS5)}), kind="stable")["term"]))
    fig = go.Figure()
    fig.add_vline(x=1, line_color=GRAY, line_width=2)
    offsets = np.linspace(-0.3, 0.3, len(MODELS5))
    for m, off in zip(MODELS5, offsets):
        if m not in models:
            continue
        colour, symbol = MODEL_STYLE[m]
        ys, xs, lo, hi, hover = [], [], [], [], []
        for i, term in enumerate(terms):
            r = c[(c["model"] == m) & (c["term"] == term)]
            if r.empty:
                continue
            r = r.iloc[0]
            ys.append(len(terms) - 1 - i + off * 0.6); xs.append(r["odds_ratio"]); lo.append(r["or_ci_low"]); hi.append(r["or_ci_high"])
            hover.append(f"<b>{m}</b>: {term}<br>odds ratio {r['odds_ratio']:.2f} (95% interval {r['or_ci_low']:.2f}-{r['or_ci_high']:.2f})<br>{int(r['accidents']):,} accidents, {int(r['events']):,} severe")
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", name=m, marker=dict(size=7, color=colour, symbol=symbol),
                                 error_x=dict(type="data", symmetric=False, array=np.array(hi) - np.array(xs), arrayminus=np.array(xs) - np.array(lo), thickness=1.4, width=0, color=colour),
                                 hovertext=hover, hovertemplate="%{hovertext}<extra></extra>"))
    fig.update_yaxes(tickvals=list(range(len(terms))), ticktext=[t.split(": ", 1)[1] if ": " in t else t for t in terms][::-1])
    fig.update_xaxes(type="log", range=[np.log10(0.15), np.log10(25)], tickvals=LOG_TICKS, ticktext=[f"{t:g}" for t in LOG_TICKS], title="adjusted odds ratio of a severe accident (log scale; 1 = the reference category)")
    fig.update_layout(legend=dict(orientation="h", y=1.02, x=0))
    return _layout(fig, height or max(320, 24 * len(terms) + 120), margin=dict(l=10, r=10, t=40, b=10))


def fig_logit_roadusers(res):
    """The road-user terms: the baseline 'group involved' and the 'counterpart' of the four group models."""
    fig = make_subplots(rows=1, cols=2, subplot_titles=["<b>Baseline: group involved (vs car only)</b>", "<b>Group models: counterpart (vs passenger car)</b>"], horizontal_spacing=0.22)
    for col, (variable, models) in enumerate((("Group involved", ["Baseline"]), ("Counterpart", MODELS5[1:])), start=1):
        sub = fig_logit_forest(res, [variable], models)
        for tr in sub.data:
            tr.showlegend = (col == 2) or tr.name == "Baseline"
            fig.add_trace(tr, row=1, col=col)
        fig.update_yaxes(tickvals=sub.layout.yaxis.tickvals, ticktext=sub.layout.yaxis.ticktext, row=1, col=col)
        fig.update_xaxes(type="log", range=[np.log10(0.15), np.log10(25)], tickvals=LOG_TICKS, ticktext=[f"{t:g}" for t in LOG_TICKS], row=1, col=col)
        fig.add_vline(x=1, line_color=GRAY, line_width=2, row=1, col=col)
    fig.update_layout(legend=dict(orientation="h", y=-0.12))
    return _layout(fig, 560)


def fig_logit_predicted(res):
    """Average adjusted predicted probability of a severe accident per category (six variables), per model, with 95% intervals."""
    p = res["severity_logit_predicted_by_category"]
    variables = ["Region", "Road type", "Intersection", "Lighting", "Year", "Month"]
    fig = make_subplots(rows=2, cols=3, subplot_titles=[f"<b>{v}</b>" for v in variables], horizontal_spacing=0.07, vertical_spacing=0.2)
    for i, var in enumerate(variables):
        r, c = i // 3 + 1, i % 3 + 1
        part = p[p["variable"] == var]
        cats = list(dict.fromkeys(part[part["model"] == "Baseline"]["category"]))
        if var == "Month":
            cats = MONTH_NAMES
        cats = [x for x in cats if not x.startswith("Unknown")]
        for m, off in zip(MODELS5, np.linspace(-0.3, 0.3, 5)):
            d = part[part["model"] == m].set_index("category")
            sel = [x for x in cats if x in d.index]
            colour, symbol = MODEL_STYLE[m]
            fig.add_trace(go.Scatter(x=[cats.index(x) + off for x in sel], y=d.loc[sel, "predicted_pct"], mode="markers", name=m, legendgroup=m, showlegend=(i == 0), marker=dict(size=6, color=colour, symbol=symbol),
                                     error_y=dict(type="data", symmetric=False, array=d.loc[sel, "ci_high_pct"] - d.loc[sel, "predicted_pct"], arrayminus=d.loc[sel, "predicted_pct"] - d.loc[sel, "ci_low_pct"], thickness=1.3, width=0, color=colour),
                                     hovertext=[f"<b>{m}</b>: {x}<br>{d.loc[x, 'predicted_pct']:.1f}% (95% interval {d.loc[x, 'ci_low_pct']:.1f}-{d.loc[x, 'ci_high_pct']:.1f}%)" for x in sel], hovertemplate="%{hovertext}<extra></extra>"), row=r, col=c)
        fig.update_xaxes(tickvals=list(range(len(cats))), ticktext=[x.replace("Night, public lighting present and lit", "Night, lit").replace("Night, public lighting present but not lit", "Night, not lit").replace("Night, no public lighting", "Night, no light").replace(" Region", "").replace("-Capital", "")[:16] for x in cats], tickangle=-30, row=r, col=c)
        fig.update_yaxes(ticksuffix="%", row=r, col=c)
    fig.update_layout(legend=dict(orientation="h", y=-0.1))
    return _layout(fig, 640)


def fig_logit_scenarios(res):
    """Predicted probability of a severe accident in four typical situations (2024), per model."""
    sc = res["severity_logit_scenarios"]
    rows = list(dict.fromkeys(sc["model"] + " | " + sc["evaluated_as"]))
    names = list(dict.fromkeys(sc["scenario"]))
    fig = make_subplots(rows=1, cols=4, subplot_titles=[f"<b>{n}</b>" for n in names], horizontal_spacing=0.03, shared_yaxes=True)
    for i, name in enumerate(names, start=1):
        part = sc[sc["scenario"] == name]
        for j, row in enumerate(rows):
            r = part[(part["model"] + " | " + part["evaluated_as"]) == row].iloc[0]
            if np.isnan(r["predicted_pct"]):
                continue
            colour, symbol = MODEL_STYLE[r["model"]]
            hollow = r["model"] == "Baseline" and r["evaluated_as"] != "car-only accident"
            fig.add_trace(go.Scatter(x=[r["predicted_pct"]], y=[row.replace(" | (counterpart: passenger car)", " vs car").replace(" | ", ": ")], mode="markers+text", text=[f"  {r['predicted_pct']:.1f}%"], textposition="middle right", showlegend=False,
                                     marker=dict(size=9, color="rgba(0,0,0,0)" if hollow else colour, symbol=symbol, line=dict(color=colour, width=2)),
                                     error_x=dict(type="data", symmetric=False, array=[r["ci_high_pct"] - r["predicted_pct"]], arrayminus=[r["predicted_pct"] - r["ci_low_pct"]], thickness=1.6, width=0, color=colour),
                                     hovertext=[f"<b>{row}</b><br>{name}<br>{r['predicted_pct']:.1f}% (95% interval {r['ci_low_pct']:.1f}-{r['ci_high_pct']:.1f}%)"], hovertemplate="%{hovertext}<extra></extra>"), row=1, col=i)
        fig.update_xaxes(range=[0, 52], ticksuffix="%", row=1, col=i)
    fig.update_yaxes(autorange="reversed")
    return _layout(fig, 480)


def fig_logit_calibration(res):
    """Predicted against observed share of severe accidents in ten groups of accidents, per model (in-sample)."""
    cal, fit = res["severity_logit_calibration"], res["severity_logit_fit"]
    fig = make_subplots(rows=1, cols=5, subplot_titles=[f"<b>{m}</b>" for m in MODELS5], horizontal_spacing=0.05)
    for i, m in enumerate(MODELS5, start=1):
        d = cal[cal["model"] == m]
        top = max(d["mean_predicted_pct"].max(), d["observed_pct"].max()) * 1.08
        colour, symbol = MODEL_STYLE[m]
        fig.add_trace(go.Scatter(x=[0, top], y=[0, top], mode="lines", line=dict(color=GRAY, width=2), showlegend=False, hoverinfo="skip"), row=1, col=i)
        fig.add_trace(go.Scatter(x=d["mean_predicted_pct"], y=d["observed_pct"], mode="markers", showlegend=False, marker=dict(size=8, color=colour, symbol=symbol),
                                 hovertext=[f"decile {k}: predicted {a:.1f}%, observed {b:.1f}%" for k, a, b in zip(d["decile"], d["mean_predicted_pct"], d["observed_pct"])], hovertemplate="%{hovertext}<extra></extra>"), row=1, col=i)
        f = fit[(fit["model"] == m) & (fit["spec"] == "full")].iloc[0]
        fig.add_annotation(text=f"AUC {f['auc']:.2f}<br>R2 {f['mcfadden_r2']:.3f}", xref=f"x{i if i > 1 else ''} domain", yref=f"y{i if i > 1 else ''} domain", x=0.04, y=0.96, showarrow=False, xanchor="left", yanchor="top", font=dict(size=11))
        fig.update_xaxes(range=[0, top], ticksuffix="%", row=1, col=i)
        fig.update_yaxes(range=[0, top], ticksuffix="%", row=1, col=i)
    return _layout(fig, 360)


def fig_logit_interactions(res):
    """Odds of a severe accident for each pair of road-user groups against a car-only accident: what the baseline adds up, and with the pair's own effect."""
    t = res["severity_logit_interactions_pairs"]
    t = t[t["spec"] == "full"]
    order = list(t[t["version"] == "with the pair's own effect"].sort_values("accidents", ascending=True)["pair"])
    fig = go.Figure()
    fig.add_vline(x=1, line_color=GRAY, line_width=2)
    for version, colour, symbol, name in (("additive (baseline model)", "#898781", "circle-open", "what the baseline predicts (the two group effects added up)"), ("with the pair's own effect", "#2a78d6", "square", "with the pair's own effect (model with pair interactions)")):
        d = t[t["version"] == version].set_index("pair").loc[order]
        fig.add_trace(go.Scatter(x=d["odds_ratio_vs_car_only"], y=[f"{p}  ({int(n):,})" for p, n in zip(order, d["accidents"])], mode="markers", name=name,
                                 marker=dict(size=9, color=colour if symbol == "square" else "rgba(0,0,0,0)", symbol=symbol, line=dict(color=colour, width=2)),
                                 error_x=dict(type="data", symmetric=False, array=d["ci_high"] - d["odds_ratio_vs_car_only"], arrayminus=d["odds_ratio_vs_car_only"] - d["ci_low"], thickness=1.5, width=0, color=colour),
                                 hovertext=[f"<b>{p}</b><br>{name}<br>odds ratio {o:.2f} (95% interval {lo:.2f}-{hi:.2f})" for p, o, lo, hi in zip(order, d["odds_ratio_vs_car_only"], d["ci_low"], d["ci_high"])], hovertemplate="%{hovertext}<extra></extra>"))
    fig.update_xaxes(type="log", tickvals=[0.5, 1, 2, 4, 8, 16], ticktext=["0.5", "1", "2", "4", "8", "16"], title="odds ratio of a severe accident against a car-only accident (log scale)")
    fig.update_layout(legend=dict(orientation="h", y=1.04))
    return _layout(fig, 24 * len(order) + 140, margin=dict(l=10, r=10, t=40, b=10))


def fig_logit_single(res, model):
    """ONE saved model (script 20, with collision type) as a forest plot: all terms grouped by variable in one panel, filled dots = significant at 5%."""
    c = res["severity_logit_coefficients"]
    c = c[(c["model"] == model) & (c["spec"] == "full")]
    rows, ticks, y = [], [], 0
    for var in list(dict.fromkeys(c["variable"])):
        part = c[c["variable"] == var]
        if var == "Month":
            part = part.assign(_o=part["category"].map({m: i for i, m in enumerate(MONTH_NAMES)})).sort_values("_o")
        ticks.append((y, f"<b>{var}</b>")); y += 1
        for _, r in part.iterrows():
            rows.append((y, r)); ticks.append((y, str(r["category"]))); y += 1
        y += 0.6
    d = pd.DataFrame([r for _, r in rows])
    ys = [p for p, _ in rows]
    sig = d["p_value"] < 0.05
    colour = MODEL_STYLE[model][0]
    fig = go.Figure()
    fig.add_vline(x=1, line_color=GRAY, line_width=2)
    fig.add_trace(go.Scatter(x=d["odds_ratio"], y=ys, mode="markers", showlegend=False,
                             marker=dict(size=9, color=[colour if s_ else "rgba(0,0,0,0)" for s_ in sig], symbol=MODEL_STYLE[model][1], line=dict(color=colour, width=2)),
                             error_x=dict(type="data", symmetric=False, array=d["or_ci_high"] - d["odds_ratio"], arrayminus=d["odds_ratio"] - d["or_ci_low"], thickness=1.5, width=0, color=colour),
                             hovertext=[f"<b>{r['term']}</b><br>odds ratio {r['odds_ratio']:.2f} (95% interval {r['or_ci_low']:.2f}-{r['or_ci_high']:.2f})<br>p = {r['p_value']:.3g}; {int(r['accidents']):,} accidents, {int(r['events']):,} severe" for _, r in d.iterrows()],
                             hovertemplate="%{hovertext}<extra></extra>"))
    low, high = max(0.05, float(d["or_ci_low"].min()) * 0.9), float(d["or_ci_high"].max()) * 1.1
    tx = [t for t in (0.1, 0.25, 0.5, 1, 2, 4, 8, 16, 32) if low <= t <= high]
    fig.update_yaxes(tickvals=[t[0] for t in ticks], ticktext=[t[1] for t in ticks], autorange="reversed")
    fig.update_xaxes(type="log", range=[np.log10(low), np.log10(high)], tickvals=tx, ticktext=[f"{t:g}" for t in tx], title=f"{model}: adjusted odds ratio of a severe accident (log scale; filled = significant at 5%)")
    return _layout(fig, max(400, int(22 * y + 110)), margin=dict(l=10, r=10, t=10, b=10))
