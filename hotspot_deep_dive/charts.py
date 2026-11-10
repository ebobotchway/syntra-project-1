"""
The Plotly charts of the hotspot deep dive. Every chart is built from the SAVED result tables in results/ and data/ (nothing is recalculated here).
Used by app.py (Streamlit) and build_html.py (the HTML page). Coordinates are Belgian Lambert 1972 (EPSG:31370, metres).

Heat maps:  accidents per year per grid cell (log colour scale, because a few city cells have hundreds a year and most have less than one),
            severe share per grid cell (cells with fewer than 30 accidents stay empty),
            accidents per 100,000 residents per year per municipality (5 quantile classes; 30-99 accidents faded and flagged).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = Path(__file__).parent
RESULTS, DATA = HERE / "results", HERE / "data"

BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#898781"
RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]                         # blue: counts and rates (low to high)
WARM = [[0, "#fdeadf"], [0.25, "#f8c3a2"], [0.5, "#eb6834"], [0.75, "#b8431a"], [1, "#6e260c"]]  # warm: severity
CELL_SIZES = {"5 km2 cells": 5 ** 0.5 * 1000, "5 x 5 km squares": 5000.0}
GROUPS = ["Vulnerable (any of the four)", "Pedestrian", "Bicycle", "Motorcycle", "Moped"]
GROUP_LABELS = {"Vulnerable (any of the four)": "All four vulnerable groups", "Pedestrian": "Pedestrians", "Bicycle": "Cyclists", "Motorcycle": "Motorcycles", "Moped": "Mopeds"}
GROUP_WORDS = {"Vulnerable (any of the four)": "vulnerable road users", "Pedestrian": "pedestrians", "Bicycle": "cyclists", "Motorcycle": "motorcycles", "Moped": "mopeds"}
PERIODS = ["Pre Covid-19 (2017-2019)", "During Covid-19 (2020-2021)", "Post Covid-19 (2022-2024)", "All years (2017-2024)"]
THREE = PERIODS[:3]
YEARS_IN = {PERIODS[0]: 3, PERIODS[1]: 2, PERIODS[2]: 3, PERIODS[3]: 8}
MIN_SHARE, MIN_RATE = 30, 100
RATE = "rate per 100,000 residents per year"
REGION_SHORT = {"Brussels-Capital Region": "Brussels", "Flemish Region": "Flanders", "Walloon Region": "Wallonia"}


# ---------------------------------------------------------------- loading
def load_cells():
    return pd.read_csv(RESULTS / "grid_cells.csv")


def load_top():
    return pd.read_csv(RESULTS / "hotspots_top20.csv")


def load_summary():
    return pd.read_csv(RESULTS / "hotspot_severity_summary.csv")


def load_coverage():
    return pd.read_csv(RESULTS / "coordinate_coverage.csv")


def load_municipalities():
    return pd.read_csv(RESULTS / "municipality_rates.csv", dtype={"municipality_nis_code": str})


def load_outlines():
    return json.loads((DATA / "municipality_outlines.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- helpers
def layout(fig, height, **extra):
    options = dict(height=height, margin=dict(l=10, r=10, t=60, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    options.update(extra)
    fig.update_layout(**options)
    return fig


def empty_figure(message, height=260):
    fig = go.Figure()
    fig.add_annotation(text=message, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return layout(fig, height)


def ring_xy(polys):
    """Flat ring lists -> x and y lists with None between rings (what a Plotly line/fill trace needs)."""
    xs, ys = [], []
    for polygon in polys:
        for ring in polygon:
            xs += ring[0::2] + [None]
            ys += ring[1::2] + [None]
    return xs, ys


def outline_trace(outlines):
    xs, ys = [], []
    for f in outlines["features"]:
        x, y = ring_xy(f["polys"])
        xs += x; ys += y
    return go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor="rgba(137,135,129,0.10)", line=dict(color="rgba(137,135,129,0.55)", width=0.5),
                      hoverinfo="skip", showlegend=False, name="municipality borders")


def equal_axes(fig, rows, cols):
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


def quantile_classes(values, n=5):
    edges = np.unique(np.quantile(values, np.linspace(0, 1, n + 1)))
    return edges, np.clip(np.digitize(values, edges[1:-1], right=True), 0, len(edges) - 2)


# ---------------------------------------------------------------- grid heat maps
def grid_array(cells, side, extent, column):
    """The cells as a 2D array (rows = y, columns = x) on a fixed extent, so that panels of different periods line up. Empty cells are NaN."""
    cx0, cx1, cy0, cy1 = extent
    z = np.full((cy1 - cy0 + 1, cx1 - cx0 + 1), np.nan)
    z[cells["cy"].to_numpy() - cy0, cells["cx"].to_numpy() - cx0] = cells[column].to_numpy()
    return z


def extent_of(cells):
    return int(cells["cx"].min()), int(cells["cx"].max()), int(cells["cy"].min()), int(cells["cy"].max())


def heat_values(cells, measure):
    """The numbers shown for a measure: 'per_year' = accidents per year; 'severe' = severe share in % (only from 30 accidents)."""
    c = cells.copy()
    if measure == "severe":
        c["value"] = np.where(c["accidents"] >= MIN_SHARE, c["severe"] / c["accidents"] * 100, np.nan)
    else:
        c["value"] = c["per_year"]
    return c.dropna(subset=["value"])


def heat_trace(c, side, extent, measure, zmax_count=None, showscale=True, xaxis=None, yaxis=None, scale_name=None):
    """One heat map trace. Accidents per year are drawn on a log scale (the colour bar shows real numbers); the severe share on a linear scale."""
    cx0, _, cy0, _ = extent
    z = grid_array(c, side, extent, "value")
    hover = np.full(z.shape, "", dtype=object)
    for r in c.itertuples():
        hover[r.cy - cy0, r.cx - cx0] = (f"{r.accidents:,} accidents ({r.per_year:.1f} a year)<br>{r.severe:,} severe ({r.severe / r.accidents * 100:.1f}%), {r.fatal:,} fatal"
                                         + ("" if r.accidents >= MIN_SHARE else "<br><i>fewer than 30 accidents: no share</i>"))
    kw = dict(x0=(cx0 + 0.5) * side, dx=side, y0=(cy0 + 0.5) * side, dy=side, hoverongaps=False, text=hover, hovertemplate="%{text}<extra></extra>")
    if xaxis:
        kw.update(xaxis=xaxis, yaxis=yaxis)
    if measure == "severe":
        top = 40.0
        return go.Heatmap(z=np.clip(z, 0, top), zmin=0, zmax=top, colorscale=WARM, showscale=showscale,
                          colorbar=dict(title="severe<br>share", ticksuffix="%", thickness=12, len=0.6), **kw)
    top = zmax_count or float(np.nanmax(z))
    lo = 0.1
    ticks = [t for t in (0.1, 0.3, 1, 3, 10, 30, 100, 300) if lo <= t <= top * 1.05]
    return go.Heatmap(z=np.log10(np.clip(z, lo, None)), zmin=np.log10(lo), zmax=np.log10(top), colorscale=[[0, "#cde2fb"], [0.25, "#86b6ef"], [0.5, "#2a78d6"], [0.75, "#104281"], [1, "#0d366b"]],
                      showscale=showscale, colorbar=dict(title="accidents<br>per year", tickvals=[np.log10(t) for t in ticks], ticktext=[f"{t:g}" for t in ticks], thickness=12, len=0.6), **kw)


def hotspot_markers(top, name="20 busiest cells", xaxis=None, yaxis=None, show_legend=True):
    kw = dict(xaxis=xaxis, yaxis=yaxis) if xaxis else {}
    return go.Scatter(x=top["centre_x_m"], y=top["centre_y_m"], mode="markers", name=name, showlegend=show_legend, marker=dict(symbol="square-open", size=9, color="#0b0b0b", line=dict(width=1.4)),
                      hovertext=[f"<b>Rank {r['rank']}: {r['municipality']}</b><br>{r['accidents']:,} accidents ({r['per_year']:.1f} a year)"
                                 + (f"<br>{r['severe %']:.1f}% severe, {r['fatal %']:.1f}% fatal" if not pd.isna(r["severe %"]) else "") for _, r in top.iterrows()],
                      hovertemplate="%{hovertext}<extra></extra>", **kw)


def fig_heatmap(cells, top, outlines, size, measure, group, period):
    """One heat map: accidents per year (or severe share) per grid cell for one group and period, with the 20 busiest cells marked."""
    side = CELL_SIZES[size]
    c = cells[(cells["size"] == size) & (cells["group"] == group) & (cells["period"] == period)]
    if c.empty:
        return empty_figure("No accidents with coordinates in this selection.")
    cv = heat_values(c, measure)
    if cv.empty:
        return empty_figure("No cell has 30 or more accidents in this selection, so no severe share can be shown.")
    t = top[(top["size"] == size) & (top["group"] == group) & (top["period"] == period)]
    fig = go.Figure([outline_trace(outlines), heat_trace(cv, side, extent_of(c), measure), hotspot_markers(t)])
    fig.update_layout(legend=dict(orientation="h", y=-0.02))
    equal_axes(fig, 1, 1)
    return layout(fig, 640, margin=dict(l=0, r=0, t=10, b=0))


def fig_heatmap_periods(cells, top, outlines, size, measure, group):
    """The three periods side by side on the same grid and the same colour scale."""
    side = CELL_SIZES[size]
    c_all = cells[(cells["size"] == size) & (cells["group"] == group)]
    if c_all.empty:
        return empty_figure("No accidents with coordinates in this selection.")
    extent = extent_of(c_all)
    zmax = float(c_all[c_all["period"].isin(THREE)]["per_year"].max())
    fig = make_subplots(rows=1, cols=3, subplot_titles=[f"<b>{p}</b>" for p in THREE], horizontal_spacing=0.01)
    for col, period in enumerate(THREE, start=1):
        c = c_all[c_all["period"] == period]
        cv = heat_values(c, measure)
        outline = outline_trace(outlines)
        fig.add_trace(outline, row=1, col=col)
        if not cv.empty:
            fig.add_trace(heat_trace(cv, side, extent, measure, zmax_count=zmax, showscale=(col == 3)), row=1, col=col)
        t = top[(top["size"] == size) & (top["group"] == group) & (top["period"] == period)]
        fig.add_trace(hotspot_markers(t, show_legend=(col == 1)), row=1, col=col)
    equal_axes(fig, 1, 3)
    fig.update_layout(legend=dict(orientation="h", y=-0.02))
    return layout(fig, 520, margin=dict(l=0, r=0, t=50, b=0))


# ---------------------------------------------------------------- severity of the hotspots
def fig_hotspot_severity(summary, size, group):
    """Severe, fatal and serious share in the 20 hotspot cells against all other cells, per period (dots with 95% intervals)."""
    s = summary[(summary["size"] == size) & (summary["group"] == group) & (summary["period"].isin(THREE))]
    measures = [("severe", "Severe (fatal + serious)"), ("fatal", "Fatal (class 1 + 2)"), ("serious", "Seriously injured (class 3)")]
    fig = make_subplots(rows=1, cols=3, subplot_titles=[f"<b>{m[1]}</b>" for m in measures], horizontal_spacing=0.08)
    for i, (key, _) in enumerate(measures, start=1):
        for label, colour, offset in (("20 hotspot cells", ORANGE, -0.1), ("all other cells", BLUE, 0.1)):
            d = s[s["cells"] == label].set_index("period").reindex(THREE)
            x = [k + offset for k in range(3)]
            value = d[f"{key} %"].to_numpy(float)
            err_hi, err_lo = d[f"{key} high"].to_numpy(float) - value, value - d[f"{key} low"].to_numpy(float)
            fig.add_trace(go.Scatter(x=x, y=value, mode="markers", name=label, legendgroup=label, showlegend=(i == 1), marker=dict(color=colour, size=10),
                                     error_y=dict(type="data", symmetric=False, array=err_hi, arrayminus=err_lo, thickness=2, width=0, color=colour),
                                     hovertext=[f"<b>{label}</b>, {p}<br>{v:.2f}% {key} ({int(d.loc[p, key]):,} of {int(d.loc[p, 'accidents']):,} accidents)" if not np.isnan(v) else f"{label}: fewer than 30 accidents" for p, v in zip(THREE, value)],
                                     hovertemplate="%{hovertext}<extra></extra>"), row=1, col=i)
        fig.update_xaxes(tickvals=[0, 1, 2], ticktext=["Pre<br>2017-19", "During<br>2020-21", "Post<br>2022-24"], range=[-0.5, 2.5], row=1, col=i)
        fig.update_yaxes(ticksuffix="%", rangemode="tozero", row=1, col=i)
    fig.update_layout(legend=dict(orientation="h", y=-0.2))
    return layout(fig, 430, margin=dict(l=10, r=10, t=60, b=10))


# ---------------------------------------------------------------- municipalities: rates per 100,000 residents
def municipality_table(m, group, period):
    t = m[(m["group"] == group) & (m["period"] == period)].copy()
    t["reliable"] = t["accidents"] >= MIN_RATE
    t["flagged"] = (t["accidents"] >= MIN_SHARE) & ~t["reliable"]
    return t


def fig_rate_map(t, outlines, group):
    """Municipalities coloured by accidents per 100,000 residents per year (5 quantile classes of the municipalities with 100+ accidents).
    Municipalities with 30-99 accidents get the same colours but faded (flagged: few accidents); fewer than 30 accidents stay gray."""
    feats = outlines["features"]
    t = t.set_index("municipality_nis_code")
    rel = t[t["reliable"]]
    if rel.empty:
        return empty_figure("No municipality has 100 or more accidents of this group in this period.", 300)
    edges, _ = quantile_classes(rel[RATE].to_numpy())
    cls = lambda v: int(np.clip(np.digitize(v, edges[1:-1], right=True), 0, len(edges) - 2))
    fig = go.Figure([outline_trace(outlines)])
    layers = []
    for k in range(len(edges) - 1):
        layers.append((RAMP[k], 1.0, f"{edges[k]:.0f}-{edges[k + 1]:.0f}" if edges[1] > 10 else f"{edges[k]:.1f}-{edges[k + 1]:.1f}", lambda r, k=k: r["reliable"] and cls(r[RATE]) == k))
    for k in range(len(edges) - 1):
        layers.append((RAMP[k], 0.4, "faded: 30-99 accidents (flagged)" if k == 0 else None, lambda r, k=k: r["flagged"] and cls(r[RATE]) == k))
    for colour, alpha, label, test in layers:
        xs, ys = [], []
        for f in feats:
            r = t.loc[f["nis"]]
            if test(r):
                x, y = ring_xy(f["polys"]); xs += x; ys += y
        if not xs:
            continue
        rgb = tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},{alpha})", line=dict(color="rgba(255,255,255,0.7)", width=0.4),
                                 name=label or "", showlegend=label is not None, legendgroup=label or colour, hoverinfo="skip"))
    hover = []
    for f in feats:
        r = t.loc[f["nis"]]
        rate = f"{r[RATE]:.1f} per 100,000 residents per year" if r["accidents"] >= MIN_SHARE else "too few accidents for a rate"
        hover.append(f"<b>{r['municipality']}</b> ({REGION_SHORT.get(r['region'], r['region'])})<br>{int(r['accidents']):,} accidents involve {GROUP_WORDS[group]} ({r['accidents per year']:.1f} a year)<br>"
                     f"{int(r['average residents']):,} residents on average<br>{rate}" + ("<br><i>flagged: fewer than 100 accidents</i>" if r["flagged"] else ""))
    fig.add_trace(go.Scatter(x=[f["x"] for f in feats], y=[f["y"] for f in feats], mode="markers", marker=dict(size=9, opacity=0), showlegend=False, hovertext=hover, hovertemplate="%{hovertext}<extra></extra>"))
    fig.update_layout(legend=dict(orientation="h", y=-0.02))
    equal_axes(fig, 1, 1)
    return layout(fig, 660, margin=dict(l=0, r=0, t=10, b=0))


def fig_rate_ranking(t, group, by="rate", n=20):
    """Top municipalities by accidents per 100,000 residents (100+ accidents) or by number of accidents; the bars are labelled with the other measure."""
    d = t[t["reliable"]] if by == "rate" else t[t["accidents"] > 0]
    d = d.sort_values(RATE if by == "rate" else "accidents", ascending=False).head(n).iloc[::-1]
    if d.empty:
        return empty_figure("No municipality has 100 or more accidents of this group in this period.", 300)
    x = d[RATE] if by == "rate" else d["accidents per year"]
    text = [f"{r[RATE]:.0f} per 100,000  ({r['accidents per year']:.0f} a year)" if by == "rate" else f"{r['accidents per year']:.0f} a year  ({r[RATE]:.0f} per 100,000)" for _, r in d.iterrows()]
    hover = [f"<b>{r['municipality']}</b> ({REGION_SHORT.get(r['region'], r['region'])})<br>{int(r['accidents']):,} accidents ({r['accidents per year']:.1f} a year)<br>{int(r['average residents']):,} residents on average<br>{r[RATE]:.1f} per 100,000 residents per year"
             for _, r in d.iterrows()]
    fig = go.Figure(go.Bar(y=d["municipality"], x=x, orientation="h", marker_color=BLUE if by == "rate" else GRAY, text=text, textposition="outside", cliponaxis=False, hovertext=hover, hovertemplate="%{hovertext}<extra></extra>"))
    fig.update_xaxes(range=[0, float(x.max()) * 1.75])
    fig.update_yaxes(tickfont=dict(size=11))
    title = "per 100,000 residents per year (100+ accidents)" if by == "rate" else "accidents per year"
    fig.update_layout(title=dict(text=f"<b>Top {len(d)} by {title}</b>", x=0.01, xanchor="left"))
    return layout(fig, 110 + 26 * len(d), margin=dict(l=10, r=10, t=50, b=10))
