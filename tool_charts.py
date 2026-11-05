"""
Charts of the interactive tool (decisions #132-#144): Plotly figures built from the tables of tool_stats / logit_live (the FILTERED accidents).
Colour follows the entity: every road-user group keeps its own colour and marker whatever the selection (the validated categorical order, slots 1-8).
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import dashboard_extra as dx
import tool_data as td

GROUP_STYLE = {  # group -> (colour, marker symbol)
    "Bicycle": ("#2a78d6", "circle"), "Pedestrian": ("#eb6834", "square"), "Motorcycle": ("#1baf7a", "diamond"), "Moped": ("#eda100", "triangle-up"),
    "Passenger car": ("#e87ba4", "triangle-down"), "Van / light truck": ("#008300", "cross"), "Truck": ("#6250d6", "x"), "Bus": ("#e34948", "star"),
    "Other road user": ("#898781", "hexagon"), "Unknown": ("#898781", "circle-open"), "All accidents in the selection": ("#52514e", "line-ns"),
}
REFERENCE_NAME = "All accidents in the selection"
SEVERITY_COLOURS = {"fatal": "#184f95", "serious": "#3987e5", "slight": "#86b6ef"}
SEASON_COLORS = {"Winter": "#2a78d6", "Spring": "#eb6834", "Summer": "#1baf7a", "Autumn": "#eda100"}  # validated order, as in the study
OUTCOME_KEYS = {"Severe (fatal + serious)": "severe", "Fatal (class 1 + 2)": "fatal", "Seriously injured (class 3)": "serious"}


def style_of(group):
    return GROUP_STYLE.get(group, ("#52514e", "circle"))


def empty_figure(message):
    """A placeholder figure with a message (used when a selection has too little data)."""
    fig = go.Figure()
    fig.add_annotation(text=message, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return dx._layout(fig, 220)


def _hover(r, key):
    flag = f"<br><i>{r['note']}</i>" if isinstance(r.get("note"), str) and r["note"] else ""
    return f"<b>{r['group']}</b><br>{r[f'{key} %']:.2f}% of {r['accidents']:,} accidents<br>95% interval {r[f'{key} low']:.2f}-{r[f'{key} high']:.2f}%{flag}"


# --------------------------------------------------------------------------------------
# Overview and severity
# --------------------------------------------------------------------------------------
def fig_accidents_per_group(table):
    """Accidents involving each compared group (bars), with the share of all accidents in the selection."""
    d = table[table["group"] != REFERENCE_NAME]
    total = int(table.loc[table["group"] == REFERENCE_NAME, "accidents"].iat[0])
    if d.empty or total == 0:
        return empty_figure("No accidents in this selection.")
    d = d.sort_values("accidents")
    fig = go.Figure(go.Bar(y=d["group"], x=d["accidents"], orientation="h", marker_color=[style_of(g)[0] for g in d["group"]], width=0.55,
                           text=[f"{n:,} ({n / total * 100:.1f}%)" for n in d["accidents"]], textposition="outside", cliponaxis=False,
                           hovertemplate="<b>%{y}</b><br>%{x:,} accidents<extra></extra>"))
    fig.update_xaxes(range=[0, d["accidents"].max() * 1.3], title=f"accidents involving the group (of {total:,} in the selection)")
    return dx._layout(fig, max(220, 50 * len(d) + 90), showlegend=False, margin=dict(l=10, r=10, t=10, b=10))


def fig_severity_intervals(table, outcome):
    """Share of each group's accidents with the chosen outcome, with 95% intervals; the gray line is all accidents of the selection."""
    key = OUTCOME_KEYS[outcome]
    d = table[(table["group"] != REFERENCE_NAME) & table[f"{key} %"].notna()].sort_values(f"{key} %")
    ref = table[table["group"] == REFERENCE_NAME].iloc[0]
    if d.empty:
        return empty_figure("Too few accidents (under 30) in every selected group to show shares.")
    fig = go.Figure()
    fig.add_vline(x=ref[f"{key} %"], line_color=dx.GRAY, line_width=2, annotation_text=f"all accidents: {ref[f'{key} %']:.1f}%", annotation_position="top")
    for _, r in d.iterrows():
        colour, symbol = style_of(r["group"])
        fig.add_trace(go.Scatter(x=[r[f"{key} %"]], y=[r["group"]], mode="markers+text", text=[f"{r[f'{key} %']:.1f}%"], textposition="top center", showlegend=False,
                                 marker=dict(size=11, color="rgba(0,0,0,0)" if r["note"] else colour, symbol=symbol, line=dict(color=colour, width=2)),
                                 error_x=dict(type="data", symmetric=False, array=[r[f"{key} high"] - r[f"{key} %"]], arrayminus=[r[f"{key} %"] - r[f"{key} low"]], thickness=2, width=0, color=colour),
                                 hovertext=[_hover(r, key)], hovertemplate="%{hovertext}<extra></extra>"))
    fig.update_xaxes(ticksuffix="%", rangemode="tozero")
    return dx._layout(fig, max(240, 56 * len(d) + 110), margin=dict(l=10, r=40, t=40, b=10))


def fig_severity_distribution(table):
    """100% stacked bars: the fatal, serious and slight share of each group's accidents (and of all accidents in the selection)."""
    d = table[table["fatal %"].notna()]
    if d.empty:
        return empty_figure("Too few accidents (under 30) in every selected group to show shares.")
    d = pd.concat([d[d["group"] != REFERENCE_NAME].sort_values("fatal %", ascending=True), d[d["group"] == REFERENCE_NAME]])
    fig = go.Figure()
    for key, label in (("fatal", "Fatal"), ("serious", "Seriously injured"), ("slight", "Slightly injured")):
        fig.add_trace(go.Bar(y=d["group"], x=d[f"{key} %"], orientation="h", name=label, marker_color=SEVERITY_COLOURS[key], width=0.6,
                             hovertext=[f"<b>{g}</b><br>{label}: {v:.2f}% of {n:,} accidents" for g, v, n in zip(d["group"], d[f"{key} %"], d["accidents"])], hovertemplate="%{hovertext}<extra></extra>"))
    fig.update_layout(barmode="stack", legend=dict(orientation="h", y=-0.12))
    fig.update_xaxes(range=[0, 100], ticksuffix="%")
    return dx._layout(fig, max(240, 56 * len(d) + 110), margin=dict(l=10, r=10, t=10, b=10))


def fig_compare_groups(cmp_rows):
    """Severe share of group A and of each compared group B with 95% intervals (cmp_rows: list of compare_two results with the same group A)."""
    rows = []
    if cmp_rows:
        first = cmp_rows[0]
        rows.append((first["group A"], first["accidents A"], first["severe share A %"], None))
        for c in cmp_rows:
            rows.append((c["group B"], c["accidents B"], c["severe share B %"], c))
    if not rows:
        return empty_figure("Too few accidents (under 30) in one of the groups to compare.")
    fig = go.Figure()
    for g, n, share, c in rows:
        k = round(share / 100 * n)
        low, high = dx_wilson(k, n)
        colour, symbol = style_of(g)
        fig.add_trace(go.Scatter(x=[share], y=[g], mode="markers+text", text=[f"{share:.1f}%"], textposition="top center", showlegend=False, marker=dict(size=12, color=colour, symbol=symbol),
                                 error_x=dict(type="data", symmetric=False, array=[high - share], arrayminus=[share - low], thickness=2, width=0, color=colour),
                                 hovertext=[f"<b>{g}</b><br>{share:.2f}% of {n:,} accidents severe<br>95% interval {low:.2f}-{high:.2f}%"], hovertemplate="%{hovertext}<extra></extra>"))
    fig.update_xaxes(ticksuffix="%", rangemode="tozero", title="share of the group's accidents that are severe")
    fig.update_yaxes(autorange="reversed")
    return dx._layout(fig, max(220, 70 * len(rows) + 100), margin=dict(l=10, r=40, t=10, b=10))


def dx_wilson(k, n):
    import tool_stats as ts
    low, high = ts.wilson(k, n)
    return float(low), float(high)


def fig_odds_ratios(rows, title="odds ratio of a severe accident, group B against group A"):
    """Adjusted odds ratios (log scale) with 95% intervals: rows = list of (label, odds ratio, low, high)."""
    if not rows:
        return empty_figure("No adjusted comparison could be estimated for this selection.")
    fig = go.Figure()
    fig.add_vline(x=1, line_color=dx.GRAY, line_width=2)
    for label, o, lo, hi in rows:
        colour, symbol = style_of(label.split(" vs ")[0])
        fig.add_trace(go.Scatter(x=[o], y=[label], mode="markers+text", text=[f"{o:.2f}"], textposition="top center", showlegend=False, marker=dict(size=11, color=colour, symbol=symbol),
                                 error_x=dict(type="data", symmetric=False, array=[hi - o], arrayminus=[o - lo], thickness=2, width=0, color=colour),
                                 hovertext=[f"<b>{label}</b><br>odds ratio {o:.2f} (95% interval {lo:.2f}-{hi:.2f})"], hovertemplate="%{hovertext}<extra></extra>"))
    fig.update_xaxes(type="log", title=title)
    fig.update_yaxes(autorange="reversed")
    return dx._layout(fig, max(220, 70 * len(rows) + 100), margin=dict(l=10, r=40, t=10, b=10))


# --------------------------------------------------------------------------------------
# Time
# --------------------------------------------------------------------------------------
def fig_annual(table, metric):
    """One line per group over the years: accidents, the index (first year = 100) or the severe share (with 95% intervals)."""
    if table.empty:
        return empty_figure("No accidents in this selection.")
    column = {"Accidents": "accidents", "Index (first selected year = 100)": "index (first year = 100)", "Severe share %": "severe %"}[metric]
    fig = go.Figure()
    for g, part in table.groupby("group", sort=False):
        colour, symbol = style_of(g)
        part = part[part[column].notna()]
        err = None
        if column == "severe %":
            err = dict(type="data", symmetric=False, array=part["severe high"] - part["severe %"], arrayminus=part["severe %"] - part["severe low"], thickness=1.5, width=3, color=colour)
        fig.add_trace(go.Scatter(x=part["year"], y=part[column], mode="lines+markers", name=g, line=dict(color=colour, width=2), marker=dict(symbol=symbol, size=8), error_y=err,
                                 customdata=np.c_[part["accidents"], part["severe"]],
                                 hovertemplate="<b>" + g + "</b>, %{x}<br>" + {"accidents": "%{y:,.0f} accidents", "index (first year = 100)": "index %{y:.0f} (%{customdata[0]:,} accidents)", "severe %": "%{y:.1f}% severe (%{customdata[1]:,} of %{customdata[0]:,})"}[column] + "<extra></extra>"))
    fig.update_xaxes(tickmode="linear", dtick=1)
    if column == "severe %":
        fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    elif column == "index (first year = 100)":
        fig.add_hline(y=100, line_color=dx.GRAY, line_width=1)
    fig.update_layout(legend=dict(orientation="h", y=-0.15))
    return dx._layout(fig, 430, margin=dict(l=10, r=10, t=10, b=10))


def fig_monthly_heatmap(monthly, measure):
    """Groups x months. Colour = seasonal index (blue below an average month, red above; 100 = average); the numbers = the chosen measure."""
    if monthly.empty:
        return empty_figure("No accidents in this selection.")
    groups = list(dict.fromkeys(monthly["group"]))
    idx = monthly.pivot(index="group", columns="month", values="seasonal index").loc[groups]
    shown = monthly.pivot(index="group", columns="month", values=measure).loc[groups]
    fmt = ",.0f" if measure == "accidents" else ".1f"
    limit = max(30, int(np.ceil(np.nanmax(np.abs(idx.values - 100)) / 10) * 10)) if not idx.isna().all().all() else 30
    fig = go.Figure(go.Heatmap(z=idx.values, x=td.MONTHS, y=groups, text=[[format(v, fmt) if pd.notna(v) else "" for v in row] for row in shown.values], texttemplate="%{text}", xgap=2, ygap=2,
                               colorscale=[[0, "#2a78d6"], [0.5, "#f0efec"], [1, "#e34948"]], zmin=100 - limit, zmax=100 + limit, zmid=100, colorbar=dict(title="Index", thickness=12, len=0.8),
                               hovertemplate="<b>%{y}</b>, %{x}<br>seasonal index %{z:.0f}<extra></extra>"))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(side="top", showgrid=False)
    return dx._layout(fig, max(220, 50 * len(groups) + 100), margin=dict(l=10, r=10, t=30, b=10))


def fig_seasonal(seasonal, measure):
    """Grouped bars: the four seasons for each group (meteorological seasons, whole months)."""
    if seasonal.empty:
        return empty_figure("No accidents in this selection.")
    fig = go.Figure()
    for season, colour in SEASON_COLORS.items():
        part = seasonal[seasonal["season"] == season]
        fig.add_trace(go.Bar(x=part["group"], y=part[measure], name=season, marker_color=colour,
                             hovertemplate="<b>%{x}</b><br>" + season + ": %{y:.1f}<extra></extra>"))
    if measure == "seasonal index":
        fig.add_hline(y=100, line_color=dx.GRAY, line_width=2)
    elif measure == "share of group's accidents %":
        fig.add_hline(y=25, line_color=dx.GRAY, line_width=2)
    fig.update_layout(barmode="group", bargap=0.25, legend=dict(orientation="h", y=-0.15))
    return dx._layout(fig, 400, margin=dict(l=10, r=10, t=10, b=10))


# --------------------------------------------------------------------------------------
# Place
# --------------------------------------------------------------------------------------
def fig_area_severity(table, outcome):
    """Share of the group's accidents with the chosen outcome per area (region or province), one marker per group, with 95% intervals."""
    key = OUTCOME_KEYS[outcome]
    d = table[table[f"{key} %"].notna()]
    if d.empty:
        return empty_figure("Too few accidents (under 30) in every area to show shares.")
    order = list(d.groupby("area")[f"{key} %"].mean().sort_values().index)
    fig = go.Figure()
    groups = list(dict.fromkeys(d["group"]))
    for i, g in enumerate(groups):
        part = d[d["group"] == g]
        colour, symbol = style_of(g)
        offset = (i - (len(groups) - 1) / 2) * 0.18
        y = [order.index(a) + offset for a in part["area"]]
        fig.add_trace(go.Scatter(x=part[f"{key} %"], y=y, mode="markers", name=g, marker=dict(size=9, symbol=symbol, color=colour),
                                 error_x=dict(type="data", symmetric=False, array=part[f"{key} high"] - part[f"{key} %"], arrayminus=part[f"{key} %"] - part[f"{key} low"], thickness=1.5, width=0, color=colour),
                                 hovertext=[f"<b>{g}, {a}</b><br>{v:.2f}% of {n:,} accidents<br>95% interval {lo:.2f}-{hi:.2f}%" + (f"<br><i>{nt}</i>" if nt else "")
                                            for a, v, n, lo, hi, nt in zip(part["area"], part[f"{key} %"], part["accidents"], part[f"{key} low"], part[f"{key} high"], part["note"])],
                                 hovertemplate="%{hovertext}<extra></extra>"))
    fig.update_yaxes(tickvals=list(range(len(order))), ticktext=order)
    fig.update_xaxes(ticksuffix="%", rangemode="tozero")
    fig.update_layout(legend=dict(orientation="h", y=-0.12))
    return dx._layout(fig, max(280, 40 * len(order) + 140), margin=dict(l=10, r=10, t=10, b=10))


def _municipality_geometry(outlines, nis_set):
    xs, ys = [], []
    for f in outlines["features"]:
        if f["nis"] in nis_set:
            x, y = dx._ring_xy(f["polys"])
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
    edges, _ = dx._quantile_classes(values)
    classes = np.clip(np.digitize(values, edges[1:-1], right=True), 0, len(edges) - 2)
    fig = go.Figure()
    xs, ys = _municipality_geometry(outlines, {f["nis"] for f in outlines["features"]} - set(d["municipality_nis_code"]))
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor="rgba(137,135,129,0.12)", line=dict(color="rgba(137,135,129,0.5)", width=0.4), name="not coloured (outside the selection or too few accidents)", hoverinfo="skip"))
    unit = "%" if "%" in column else ""
    for k in range(len(edges) - 1):
        nis = set(d["municipality_nis_code"].to_numpy()[classes == k])
        xs, ys = _municipality_geometry(outlines, nis)
        label = f"{edges[k]:,.0f}-{edges[k + 1]:,.0f}" if not unit else f"{edges[k]:.1f}-{edges[k + 1]:.1f}%"
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor=dx.RAMP[k], line=dict(color="rgba(255,255,255,0.7)", width=0.4), name=label, hoverinfo="skip"))
    pos = {f["nis"]: (f["x"], f["y"], f["name"]) for f in outlines["features"]}
    fig.add_trace(go.Scatter(x=[pos[n][0] for n in d["municipality_nis_code"]], y=[pos[n][1] for n in d["municipality_nis_code"]], mode="markers", marker=dict(size=8, opacity=0), showlegend=False,
                             hovertext=[f"<b>{r['municipality']}</b> ({r['region']})<br>{r['accidents']:,} accidents involve {group.lower()}s ({r['share of all accidents %']:.1f}% of its {r['all accidents']:,})"
                                        + (f"<br>{r['severe %']:.1f}% severe ({r['severe']:,})" if pd.notna(r["severe %"]) else "") for _, r in d.iterrows()],
                             hovertemplate="%{hovertext}<extra></extra>"))
    dx._equal_axes(fig, 1, 1)
    fig.update_layout(legend=dict(orientation="h", y=-0.02))
    return dx._layout(fig, 640, margin=dict(l=0, r=0, t=10, b=0))


def fig_province_map(area_table, provinces, outcome, group):
    """The provinces (and Brussels) of the selection coloured by the share with the chosen outcome (five quantile classes), for one group."""
    key = OUTCOME_KEYS[outcome]
    d = area_table[(area_table["group"] == group) & area_table[f"{key} %"].notna()].set_index("area")
    feats = [f for f in provinces["features"] if f["name"] in d.index]
    if len(feats) < 2:
        return empty_figure("Fewer than two provinces have enough accidents (30) for a map. Use the chart view instead.")
    values = np.array([d.loc[f["name"], f"{key} %"] for f in feats])
    edges, classes = dx._quantile_classes(values)
    fig = go.Figure()
    xs, ys = [], []
    for f in provinces["features"]:
        x, y = dx._ring_xy(f["polys"]); xs += x; ys += y
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor="rgba(137,135,129,0.12)", line=dict(color="rgba(137,135,129,0.6)", width=0.6), name="not coloured", hoverinfo="skip"))
    for k in range(len(edges) - 1):
        xs, ys = [], []
        for f, c in zip(feats, classes):
            if c == k:
                x, y = dx._ring_xy(f["polys"]); xs += x; ys += y
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor=dx.RAMP[k], line=dict(color="rgba(255,255,255,0.9)", width=1), name=f"{edges[k]:.1f}-{edges[k + 1]:.1f}%", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[f["x"] for f in feats], y=[f["y"] for f in feats], mode="text+markers", marker=dict(size=14, opacity=0), showlegend=False,
                             text=[f"{f['name'].replace(' (no province)', '')}<br><b>{v:.1f}%</b>" for f, v in zip(feats, values)], textfont=dict(size=11, color="#ffffff"),
                             textposition=["middle left" if f["name"].startswith("Brussels") else "middle right" if f["name"] == "Flemish Brabant" else "middle center" for f in feats],
                             hovertext=[f"<b>{f['name']}</b><br>{d.loc[f['name'], f'{key} %']:.2f}% of {int(d.loc[f['name'], 'accidents']):,} {group.lower()} accidents" for f in feats], hovertemplate="%{hovertext}<extra></extra>"))
    dx._equal_axes(fig, 1, 1)
    fig.update_layout(legend=dict(orientation="h", y=-0.02))
    return dx._layout(fig, 560, margin=dict(l=0, r=0, t=10, b=0))


def fig_hotspot_map(cells, top, outlines, group):
    """Accidents involving the group per 500 m square as a zoomable heat map; the 20 busiest squares are marked."""
    if cells.empty:
        return empty_figure("No accidents with coordinates for this group and selection.")
    cx0, cy0 = int(cells["cx"].min()), int(cells["cy"].min())
    z = np.full((int(cells["cy"].max()) - cy0 + 1, int(cells["cx"].max()) - cx0 + 1), np.nan)
    z[cells["cy"].to_numpy() - cy0, cells["cx"].to_numpy() - cx0] = cells["accidents"].to_numpy()
    topmax = float(cells["accidents"].max())
    fig = go.Figure([dx.outline_trace(outlines)])
    fig.add_trace(go.Heatmap(z=z, x0=cx0 * 500 + 250, dx=500, y0=cy0 * 500 + 250, dy=500, zmin=1, zmax=max(topmax, 2), colorscale=dx.hotspot_colourscale(max(topmax, 2)), hoverongaps=False,
                             colorbar=dict(title="accidents<br>per square", thickness=12, len=0.6), hovertemplate="%{z:.0f} accidents in this 500 m square<extra></extra>"))
    fig.add_trace(go.Scatter(x=top["centre x (m)"], y=top["centre y (m)"], mode="markers", name="20 busiest squares", marker=dict(symbol="square-open", size=10, color="#0b0b0b", line=dict(width=1.5)),
                             hovertext=[f"<b>Rank {r['rank']}: {r['municipality']}</b><br>{r['accidents']:,} accidents involving {group.lower()}s ({r['severe share %']:.0f}% severe)" for _, r in top.iterrows()],
                             hovertemplate="%{hovertext}<extra></extra>"))
    # zoom to the data when the selection is small
    pad = 3000
    fig.update_layout(legend=dict(orientation="h", y=-0.02))
    dx._equal_axes(fig, 1, 1)
    fig.update_xaxes(range=[cx0 * 500 - pad, (cx0 + z.shape[1]) * 500 + pad])
    fig.update_yaxes(range=[cy0 * 500 - pad, (cy0 + z.shape[0]) * 500 + pad])
    return dx._layout(fig, 640, margin=dict(l=0, r=0, t=10, b=0))


# --------------------------------------------------------------------------------------
# Concentration
# --------------------------------------------------------------------------------------
def fig_square_concentration(table, outcome):
    """Share with the chosen outcome by the number of the group's accidents in the accident's 500 m square, per group."""
    key = OUTCOME_KEYS[outcome] if outcome in OUTCOME_KEYS else outcome
    d = table[table[f"{key} %"].notna()]
    if d.empty:
        return empty_figure("Too few accidents with coordinates (30 per class) to show shares.")
    fig = go.Figure()
    groups = list(dict.fromkeys(d["group"]))
    for i, g in enumerate(groups):
        part = d[d["group"] == g]
        colour, symbol = style_of(g)
        x = [td_index(c) + (i - (len(groups) - 1) / 2) * 0.12 for c in part["accidents in the square"]]
        fig.add_trace(go.Scatter(x=x, y=part[f"{key} %"], mode="markers", name=g, marker=dict(size=9, symbol=symbol, color=["rgba(0,0,0,0)" if nt else colour for nt in part["note"]], line=dict(color=colour, width=2)),
                                 error_y=dict(type="data", symmetric=False, array=part[f"{key} high"] - part[f"{key} %"], arrayminus=part[f"{key} %"] - part[f"{key} low"], thickness=1.5, width=0, color=colour),
                                 hovertext=[f"<b>{g}</b>: squares with {c} accidents<br>{v:.2f}% of {n:,} accidents" + (f"<br><i>{nt}</i>" if nt else "") for c, v, n, nt in zip(part["accidents in the square"], part[f"{key} %"], part["accidents"], part["note"])],
                                 hovertemplate="%{hovertext}<extra></extra>"))
    import tool_stats as ts
    fig.update_xaxes(tickvals=list(range(len(ts.SQUARE_LABELS))), ticktext=ts.SQUARE_LABELS, title="accidents of the group in the same 500 m square")
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    fig.update_layout(legend=dict(orientation="h", y=-0.2))
    return dx._layout(fig, 430, margin=dict(l=10, r=10, t=10, b=10))


def td_index(label):
    import tool_stats as ts
    return ts.SQUARE_LABELS.index(label)


def fig_density_classes(table, outcome):
    """Share with the chosen outcome by municipality density class (five equal-sized classes), per group."""
    key = OUTCOME_KEYS[outcome] if outcome in OUTCOME_KEYS else outcome
    d = table[table[f"{key} %"].notna()]
    if d.empty:
        return empty_figure("Too few municipalities or accidents for density classes in this selection.")
    fig = go.Figure()
    groups = list(dict.fromkeys(d["group"]))
    for i, g in enumerate(groups):
        part = d[d["group"] == g]
        colour, symbol = style_of(g)
        x = part["density class (1 = least dense)"] + (i - (len(groups) - 1) / 2) * 0.12
        fig.add_trace(go.Scatter(x=x, y=part[f"{key} %"], mode="markers+lines", name=g, line=dict(color=colour, width=1), marker=dict(size=9, symbol=symbol, color=colour),
                                 error_y=dict(type="data", symmetric=False, array=part[f"{key} high"] - part[f"{key} %"], arrayminus=part[f"{key} %"] - part[f"{key} low"], thickness=1.5, width=0, color=colour),
                                 hovertext=[f"<b>{g}</b>, density class {int(c)}<br>{r:.3f} to {u:.3f} accidents per km2 per year<br>{v:.2f}% of {n:,} accidents ({m} municipalities)"
                                            for c, r, u, v, n, m in zip(part["density class (1 = least dense)"], part["density from"], part["density to"], part[f"{key} %"], part["accidents"], part["municipalities"])],
                                 hovertemplate="%{hovertext}<extra></extra>"))
    fig.update_xaxes(tickvals=[1, 2, 3, 4, 5], ticktext=["1 least dense", "2", "3", "4", "5 densest"], title="municipality density class (accidents per km2 per year of the group)")
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    fig.update_layout(legend=dict(orientation="h", y=-0.2))
    return dx._layout(fig, 430, margin=dict(l=10, r=10, t=10, b=10))


# --------------------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------------------
def fig_forest(coef, title="adjusted odds ratio of a severe accident (log scale)"):
    """All terms of a model as a forest plot grouped by variable, first variable at the top (the reference category of each variable is 1)."""
    c = coef.copy()
    if c.empty:
        return empty_figure("No terms to show.")
    rows, y, ticks = [], 0, []
    for var in list(dict.fromkeys(c["variable"])):
        part = c[c["variable"] == var]
        if var == "Month":
            part = part.assign(_o=part["category"].map({m: i for i, m in enumerate(td.MONTHS)})).sort_values("_o")
        ticks.append((y, f"<b>{var}</b>")); y += 1  # a header line, then the terms from top to bottom
        for _, r in part.iterrows():
            rows.append((y, r)); ticks.append((y, str(r["category"]))); y += 1
        y += 0.6
    fig = go.Figure()
    fig.add_vline(x=1, line_color=dx.GRAY, line_width=2)
    ys = [p[0] for p in rows]
    d = pd.DataFrame([p[1] for p in rows])
    sig = d["p-value"] < 0.05
    fig.add_trace(go.Scatter(x=d["odds ratio"], y=ys, mode="markers", showlegend=False,
                             marker=dict(size=9, color=["#2a78d6" if s_ else "rgba(0,0,0,0)" for s_ in sig], line=dict(color="#2a78d6", width=2)),
                             error_x=dict(type="data", symmetric=False, array=d["OR high"] - d["odds ratio"], arrayminus=d["odds ratio"] - d["OR low"], thickness=1.5, width=0, color="#2a78d6"),
                             hovertext=[f"<b>{r['term']}</b><br>odds ratio {r['odds ratio']:.2f} (95% interval {r['OR low']:.2f}-{r['OR high']:.2f})<br>p = {r['p-value']:.3g}; {r['accidents']:,} accidents, {r['events']:,} severe" for _, r in d.iterrows()],
                             hovertemplate="%{hovertext}<extra></extra>"))
    low, high = max(0.05, float(d["OR low"].min()) * 0.9), float(d["OR high"].max()) * 1.1
    ticks_x = [t for t in (0.1, 0.25, 0.5, 1, 2, 4, 8, 16, 32) if low <= t <= high]
    fig.update_yaxes(tickvals=[t[0] for t in ticks], ticktext=[t[1] for t in ticks], autorange="reversed")
    fig.update_xaxes(type="log", range=[np.log10(low), np.log10(high)], tickvals=ticks_x, ticktext=[f"{t:g}" for t in ticks_x], title=title)
    return dx._layout(fig, max(300, 22 * y + 100), margin=dict(l=10, r=10, t=10, b=10))


def fig_predicted(pred, variables):
    """Average adjusted predicted probability of a severe accident per category of the chosen variables."""
    d = pred[pred["variable"].isin(variables)]
    if d.empty:
        return empty_figure("No predicted probabilities for the chosen variables.")
    fig = make_subplots(rows=1, cols=len(variables), subplot_titles=[f"<b>{v}</b>" for v in variables], horizontal_spacing=0.1)
    for i, var in enumerate(variables, start=1):
        part = d[d["variable"] == var]
        fig.add_trace(go.Scatter(x=list(range(len(part))), y=part["predicted %"], mode="markers", showlegend=False, marker=dict(size=9, color="#2a78d6"),
                                 error_y=dict(type="data", symmetric=False, array=part["high %"] - part["predicted %"], arrayminus=part["predicted %"] - part["low %"], thickness=2, width=0, color="#2a78d6"),
                                 hovertext=[f"<b>{c}</b><br>{p:.1f}% (95% interval {lo:.1f}-{hi:.1f}%)" for c, p, lo, hi in zip(part["category"], part["predicted %"], part["low %"], part["high %"])], hovertemplate="%{hovertext}<extra></extra>"), row=1, col=i)
        fig.update_xaxes(tickvals=list(range(len(part))), ticktext=[c[:14] for c in part["category"]], tickangle=-35, row=1, col=i)
        fig.update_yaxes(ticksuffix="%", rangemode="tozero", row=1, col=i)
    return dx._layout(fig, 420, margin=dict(l=10, r=10, t=60, b=10))


def fig_calibration(cal, auc_value):
    """Predicted against observed share of severe accidents in ten groups of accidents (in-sample)."""
    top = max(cal["mean predicted %"].max(), cal["observed %"].max()) * 1.08
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, top], y=[0, top], mode="lines", line=dict(color=dx.GRAY, width=2), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=cal["mean predicted %"], y=cal["observed %"], mode="markers", showlegend=False, marker=dict(size=10, color="#2a78d6"),
                             hovertext=[f"decile {d}: predicted {p:.1f}%, observed {o:.1f}%" for d, p, o in zip(cal["decile"], cal["mean predicted %"], cal["observed %"])], hovertemplate="%{hovertext}<extra></extra>"))
    fig.update_xaxes(title="mean predicted (decile)", ticksuffix="%", range=[0, top])
    fig.update_yaxes(title="observed share severe", ticksuffix="%", range=[0, top])
    fig.add_annotation(text=f"AUC {auc_value:.2f} (in-sample)", xref="paper", yref="paper", x=0.03, y=0.97, showarrow=False, xanchor="left", yanchor="top")
    return dx._layout(fig, 380, margin=dict(l=10, r=10, t=10, b=10))
