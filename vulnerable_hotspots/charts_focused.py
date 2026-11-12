"""
The Plotly charts of the focused-dashboard parts of the vulnerable hotspots analysis: step 2 (severity per group), the municipality top 20 of step 3b/3c and step 4a (regional severity, province map). The 500 m hotspot squares of the focused dashboard are NOT used here (replaced by the new grids, see charts.py). Every chart is built from the SAVED result tables in results/ and data/
(nothing is recalculated here), and is used by both app.py (Streamlit) and build_html.py (the HTML page).
Coordinates are Belgian Lambert 1972 (EPSG:31370, metres).

This file is a trimmed copy of dashboard_extra.py and tool_charts.py of the main project: only what the focused dashboard needs.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = Path(__file__).parent
RESULTS, DATA = HERE / "results", HERE / "data"

BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#898781"  # categorical slots 1-3 and the neutral gray
REGION_SHORT = {"Brussels-Capital Region": "Brussels", "Flemish Region": "Flanders", "Walloon Region": "Wallonia"}
SEVERITY_COLOURS = {"fatal": "#184f95", "serious": "#3987e5", "slight": "#86b6ef"}  # one blue ramp, dark = more severe
RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]  # five blue steps for map classes
SCOPE_LABELS = {"pooled_2017_2024": "All years 2017-2024", "pre_2017_2019": "Pre 2017-2019", "during_2020_2021": "During 2020-2021", "post_2022_2024": "Post 2022-2024"}
RESULT_FILES = ["severity_a_fatal", "severity_b_serious", "severity_c_slight", "severity_d_distribution", "geo_a_cyclists_by_municipality", "severity_regional_regions_provinces"]
NAMED = ["Passenger car", "Bicycle", "Pedestrian", "Van / light truck", "Moped", "Motorcycle", "Truck", "Bus"]  # the eight named road-user groups of step 2
GROUPS4 = ["Pedestrian", "Motorcycle", "Moped", "Bicycle"]  # the four vulnerable road-user groups of step 3b/3c


# --------------------------------------------------------------------------------------
# Loading the saved results
# --------------------------------------------------------------------------------------
def load_results():
    """All saved result tables, by file name (without .csv)."""
    return {name: pd.read_csv(RESULTS / f"{name}.csv", dtype={"municipality_nis_code": str}) for name in RESULT_FILES}


def load_outlines():
    return json.loads((DATA / "municipality_outlines.json").read_text(encoding="utf-8"))


def load_provinces():
    return json.loads((DATA / "province_outlines.json").read_text(encoding="utf-8"))


def load_hotspot_cells():
    return pd.read_csv(DATA / "hotspot_cells.csv")


def load_positions():
    return pd.read_csv(DATA / "municipality_positions.csv", dtype={"municipality_nis_code": str})


def load_municipality_periods():
    """The accidents per municipality, group and period (all years, 2022-2024 and every year), written by script 24 of the main project."""
    return pd.read_csv(RESULTS / "geo_municipality_periods.csv", dtype={"municipality_nis_code": str})


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
# Step 3b/3c: municipalities, top 20 per group
# --------------------------------------------------------------------------------------
GROUP_WORDS = {"Bicycle": ("cyclist", "cyclists"), "Pedestrian": ("pedestrian", "pedestrians"), "Motorcycle": ("motorcycle", "motorcycles"), "Moped": ("moped", "mopeds")}
GROUP_FILES = {"Bicycle": "geo_a_cyclists_by_municipality", "Pedestrian": "geo_a_pedestrians_by_municipality", "Motorcycle": "geo_a_motorcycles_by_municipality", "Moped": "geo_a_mopeds_by_municipality"}


def group_municipality_table(res, group):
    """The saved municipality table of one group with the same column names for every group (accidents_group, group_share_pct)."""
    t = res[GROUP_FILES[group]]
    return t.rename(columns={"accidents_cyclists": "accidents_group", "cyclist_share_pct": "group_share_pct"})


def fig_group_ranked(t, group, region=None):
    """Top 20 municipalities by number of accidents involving the group and by its share (municipalities with at least 100 accidents); region = None or a region name."""
    one, many = GROUP_WORDS[group]
    if region:
        t = t[t["region"] == region]
    national = t["accidents_group"].sum() / t["accidents_total"].sum() * 100
    where = "Belgium" if not region else REGION_SHORT.get(region, region)
    panels = ((t.sort_values("accidents_group", ascending=False).head(20), "accidents_group", f"Top 20 by accidents involving {many}"),
              (t[t["ranked_by_share"]].sort_values("group_share_pct", ascending=False).head(20), "group_share_pct", f"Top 20 by {one} share (100+ accidents)<br><sup>{where}: {national:.1f}% (gray line)</sup>"))
    fig = make_subplots(rows=1, cols=2, subplot_titles=[f"<b>{p[2]}</b>" for p in panels], horizontal_spacing=0.28)
    for i, (d, column, _) in enumerate(panels, start=1):
        d = d.iloc[::-1]  # the biggest at the top
        is_share = column == "group_share_pct"
        text = [f"{r[column]:.1f}%  ({r['accidents_group']:,} of {r['accidents_total']:,})" if is_share else f"{r[column]:,}  ({r['group_share_pct']:.0f}% of {r['accidents_total']:,})" for _, r in d.iterrows()]
        hover = [f"<b>{r['municipality']}</b> ({r['region']})<br>{r['accidents_group']:,} accidents involve {many}<br>{r['group_share_pct']:.1f}% of its {r['accidents_total']:,} accidents" for _, r in d.iterrows()]
        fig.add_trace(go.Bar(y=d["municipality"], x=d[column], orientation="h", marker_color=BLUE, text=text, textposition="outside", cliponaxis=False, hovertext=hover, hovertemplate="%{hovertext}<extra></extra>", showlegend=False), row=1, col=i)
        if len(d):
            fig.update_xaxes(range=[0, d[column].max() * 1.75], ticksuffix="%" if is_share else "", tickformat="~g" if is_share else ",d", row=1, col=i)
    fig.add_vline(x=national, line_color=GRAY, line_width=2, row=1, col=2)
    fig.update_yaxes(tickfont=dict(size=11))
    return _layout(fig, 640)


def fig_group_bubble(t, outlines, positions, group):
    """A bubble per municipality at the average position of its accidents: size = accidents with the group, colour = its share (5 quantile classes)."""
    one, many = GROUP_WORDS[group]
    t = t.merge(positions[["municipality_nis_code", "bubble_x", "bubble_y"]], on="municipality_nis_code")
    t = t[t["accidents_group"] > 0].sort_values("accidents_group", ascending=False)  # big bubbles first, small on top
    ranked = t[t["ranked_by_share"]]
    edges, _ = _quantile_classes(ranked["group_share_pct"].values)
    classes = np.clip(np.digitize(t["group_share_pct"].values, edges[1:-1], right=True), 0, len(edges) - 2)
    fig = go.Figure([outline_trace(outlines)])
    scale = 60 / np.sqrt(t["accidents_group"].max())
    fmt = (lambda a: f"{a:.0f}") if group == "Bicycle" else (lambda a: f"{a:.1f}")
    groups = [(k, RAMP[k], f"{fmt(edges[k])}-{fmt(edges[k + 1])}% {one} share", (classes == k) & t["ranked_by_share"].values) for k in range(len(edges) - 1)]
    groups.append((-1, GRAY, "fewer than 100 accidents (not ranked)", ~t["ranked_by_share"].values))
    for _, colour, label, mask in groups:
        d = t[mask]
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=label, legendgroup=label, marker=dict(size=12, color=colour)))  # the legend entry: a clear dot of fixed size
        fig.add_trace(go.Scatter(x=d["bubble_x"], y=d["bubble_y"], mode="markers", name=label, legendgroup=label, showlegend=False, marker=dict(size=np.sqrt(d["accidents_group"]) * scale, color=colour, opacity=0.85, line=dict(color="white", width=0.6)),
                                 hovertext=[f"<b>{r['municipality']}</b><br>{r['accidents_group']:,} accidents involve {many}<br>{r['group_share_pct']:.1f}% of {r['accidents_total']:,} accidents" for _, r in d.iterrows()], hovertemplate="%{hovertext}<extra></extra>"))
    fig.update_layout(legend=dict(orientation="h", y=-0.02, x=0))
    _equal_axes(fig, 1, 1)
    return _layout(fig, 700, margin=dict(l=0, r=0, t=10, b=0))


def fig_group_choropleth(t, outlines, group):
    """Two maps: accidents involving the group (all municipalities) and its share (municipalities with 100+ accidents), 5 quantile classes each."""
    one, many = GROUP_WORDS[group]
    t = t.set_index("municipality_nis_code")
    feats = outlines["features"]
    count = np.array([t.loc[f["nis"], "accidents_group"] for f in feats], float)
    share = np.array([t.loc[f["nis"], "group_share_pct"] for f in feats], float)
    ranked = np.array([bool(t.loc[f["nis"], "ranked_by_share"]) for f in feats])
    fig = make_subplots(rows=1, cols=2, subplot_titles=[f"<b>Accidents involving {many}</b>", f"<b>{one.capitalize()} share of the municipality's accidents</b>"], horizontal_spacing=0.02)
    for col, (values, mask, unit) in enumerate(((count, np.ones(len(feats), bool), "accidents"), (share, ranked, "%")), start=1):
        edges, _ = _quantile_classes(values[mask])  # the class limits come from the municipalities that count ...
        classes = np.clip(np.digitize(values, edges[1:-1], right=True), 0, len(edges) - 2)  # ... and are then applied to every municipality
        digits = 0 if group == "Bicycle" else 1
        parts = [(RAMP[k], f"{edges[k]:,.0f}-{edges[k + 1]:,.0f}" if unit == "accidents" else f"{edges[k]:.{digits}f}-{edges[k + 1]:.{digits}f}%", mask & (classes == k)) for k in range(len(edges) - 1)]
        if unit == "%":
            parts.append((GRAY, "fewer than 100 accidents (not ranked)", ~mask))
        for colour, label, selected in parts:
            xs, ys = [], []
            for f, s in zip(feats, selected):
                if s:
                    x, y = _ring_xy(f["polys"]); xs += x; ys += y
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor=colour, line=dict(color="rgba(255,255,255,0.7)", width=0.4), name=label, legendgroup=f"{col}-{label}", hoverinfo="skip"), row=1, col=col)
        fig.add_trace(go.Scatter(x=[f["x"] for f in feats], y=[f["y"] for f in feats], mode="markers", marker=dict(size=9, opacity=0), showlegend=False,
                                 hovertext=[f"<b>{f['name']}</b><br>{count[i]:,.0f} accidents involve {many}<br>{share[i]:.1f}% of {t.loc[f['nis'], 'accidents_total']:,} accidents" + ("" if ranked[i] else "<br><i>too few accidents to rank by share</i>") for i, f in enumerate(feats)],
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
# Step 3b/3c: the municipality choropleth and the top-20 bars for a chosen group, period and region (from tool_charts.py of the main project)
# --------------------------------------------------------------------------------------
def empty_figure(message):
    """A placeholder figure with a message (used when a selection has too little data)."""
    fig = go.Figure()
    fig.add_annotation(text=message, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _layout(fig, 220)


def _municipality_geometry(outlines, nis_set):
    xs, ys = [], []
    for f in outlines["features"]:
        if f["nis"] in nis_set:
            x, y = _ring_xy(f["polys"])
            xs += x; ys += y
    return xs, ys


def fig_municipality_map(table, outlines, metric, group):
    """Municipalities of the selection coloured in five quantile classes. metric: 'accidents', 'share of all accidents %' or 'severe %'. Others stay light gray."""
    in_selection = set(table["municipality_nis_code"])
    column = metric
    d = table[table[column].notna()] if column in table else table
    if d.empty:
        return empty_figure("No municipality has enough accidents for this map (a share needs at least 30 accidents).")
    values = d[column].to_numpy(float)
    edges, _ = _quantile_classes(values)
    classes = np.clip(np.digitize(values, edges[1:-1], right=True), 0, len(edges) - 2)
    fig = go.Figure()
    xs, ys = _municipality_geometry(outlines, {f["nis"] for f in outlines["features"]} - set(d["municipality_nis_code"]))
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor="rgba(137,135,129,0.12)", line=dict(color="rgba(137,135,129,0.5)", width=0.4), name="not coloured (outside the selection or too few accidents)", hoverinfo="skip"))
    unit = "%" if "%" in column else ""
    for k in range(len(edges) - 1):
        nis = set(d["municipality_nis_code"].to_numpy()[classes == k])
        xs, ys = _municipality_geometry(outlines, nis)
        label = f"{edges[k]:,.0f}-{edges[k + 1]:,.0f}" if not unit else f"{edges[k]:.1f}-{edges[k + 1]:.1f}%"
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor=RAMP[k], line=dict(color="rgba(255,255,255,0.7)", width=0.4), name=label, hoverinfo="skip"))
    pos = {f["nis"]: (f["x"], f["y"], f["name"]) for f in outlines["features"]}
    fig.add_trace(go.Scatter(x=[pos[n][0] for n in d["municipality_nis_code"]], y=[pos[n][1] for n in d["municipality_nis_code"]], mode="markers", marker=dict(size=8, opacity=0), showlegend=False,
                             hovertext=[f"<b>{r['municipality']}</b> ({r['region']})<br>{r['accidents']:,} accidents involve {group.lower()}s ({r['share of all accidents %']:.1f}% of its {r['all accidents']:,})"
                                        + (f"<br>{r['severe %']:.1f}% severe ({r['severe']:,})" if pd.notna(r["severe %"]) else "") for _, r in d.iterrows()],
                             hovertemplate="%{hovertext}<extra></extra>"))
    _equal_axes(fig, 1, 1)
    fig.update_layout(legend=dict(orientation="h", y=-0.02))
    return _layout(fig, 640, margin=dict(l=0, r=0, t=10, b=0))


def fig_municipality_top(top, group, by, belgium_share=None):
    """Horizontal bars of the top municipalities (biggest at the top), labelled with count and share; by = 'accidents' or 'share'."""
    if top.empty:
        return empty_figure("No municipality qualifies in this selection (a share ranking needs 100 or more accidents in the municipality).")
    d = top.iloc[::-1]
    is_share = by == "share"
    column = "share of all accidents %" if is_share else "accidents"
    text = [f"{r[column]:.1f}%  ({r['accidents']:,} of {r['all accidents']:,})" if is_share else f"{r[column]:,}  ({r['share of all accidents %']:.0f}% of {r['all accidents']:,})" for _, r in d.iterrows()]
    hover = [f"<b>{r['municipality']}</b> ({r['region']})<br>{r['accidents']:,} accidents involve {group.lower()}s<br>{r['share of all accidents %']:.1f}% of its {r['all accidents']:,} accidents"
             + (f"<br>{r['severe %']:.1f}% severe ({r['severe']:,})" if pd.notna(r.get("severe %")) else "") for _, r in d.iterrows()]
    fig = go.Figure(go.Bar(y=d["municipality"], x=d[column], orientation="h", marker_color=BLUE, text=text, textposition="outside", cliponaxis=False, hovertext=hover, hovertemplate="%{hovertext}<extra></extra>"))
    if is_share and belgium_share is not None:
        fig.add_vline(x=belgium_share, line_color=GRAY, line_width=2, annotation_text=f"selection {belgium_share:.1f}%", annotation_position="top")
    fig.update_xaxes(range=[0, d[column].max() * 1.7], ticksuffix="%" if is_share else "", tickformat="~g" if is_share else ",d")
    fig.update_yaxes(tickfont=dict(size=11))
    return _layout(fig, 90 + 26 * len(d), margin=dict(l=10, r=10, t=30, b=10))
