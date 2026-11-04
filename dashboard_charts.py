"""
The four Plotly graphs of the dashboard (used by app.py). Each function takes the tables from dashboard_logic.py
and returns a figure, so the graphs can also be tested on their own.
"""
import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import dashboard_logic as dl

BLUE, GRAY = "#2a78d6", "#898781"  # blue = a named group, gray = Unknown / Other road user
SEASON_COLORS = {"Winter": "#2a78d6", "Spring": "#eb6834", "Summer": "#1baf7a", "Autumn": "#eda100"}  # validated order
BAND_COLORS = {  # translucent washes for the three periods, so they work in light and dark mode
    "Pre Covid-19 (2017-2019)": "rgba(137,135,129,0.07)",
    "During Covid-19 (2020-2021)": "rgba(137,135,129,0.22)",
    "Post Covid-19 (2022-2024)": "rgba(137,135,129,0.13)",
}
DECIMALS = {"Accidents": ",.0f", "% share": ".1f", "Per day": ".1f", "Seasonal index": ".0f"}  # number format per measure


def totals_figure(result):
    """1a: horizontal bars, accidents involving each group, with count and % of all accidents at the tip."""
    ranked = result.iloc[::-1]  # reversed so the biggest bar ends up at the top
    fig = go.Figure(go.Bar(
        y=ranked["road_user_group"], x=ranked["accidents"], orientation="h", width=0.5,
        marker_color=[GRAY if g in dl.NOT_A_GROUP else BLUE for g in ranked["road_user_group"]],
        text=[f"{n:,} ({p:.1f}%)" for n, p in zip(ranked["accidents"], ranked["percent_of_all_accidents"])],
        textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{x:,} accidents<extra></extra>",
    ))
    fig.update_xaxes(range=[0, result["accidents"].max() * 1.3], showgrid=True, gridwidth=1, title=None)
    fig.update_layout(height=max(260, 46 * len(result) + 90), margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    return fig


def annual_figure(groups, counts, index, summary, first_year, last_year):
    """1b: one small line panel per group, indexed to the first selected year, with the three period bands.
    If the pre AND post period are both inside the selection, thin average lines and 'post vs pre' are added."""
    n = len(groups)
    columns_n = min(4, n)
    rows_n = math.ceil(n / columns_n)
    fig = make_subplots(rows=rows_n, cols=columns_n, subplot_titles=[f"<b>{g}</b>" for g in groups], shared_yaxes="all",
                        horizontal_spacing=0.04, vertical_spacing=0.16)
    lowest, highest = index.loc[groups].min().min(), index.loc[groups].max().max()
    y_range = [math.floor(lowest / 10) * 10 - 10, math.ceil(highest / 10) * 10 + 10]
    for i, group in enumerate(groups):
        row, col = i // columns_n + 1, i % columns_n + 1
        above = True  # end label above the dot, unless the post-average line is there
        averages = []  # (start, end, level) of the thin pre and post average lines
        if summary is not None:
            base = counts.loc[group, first_year]
            for label, column, (start, end) in (("pre", "average per year pre", dl.PERIODS["Pre Covid-19 (2017-2019)"]),
                                                ("post", "average per year post", dl.PERIODS["Post Covid-19 (2022-2024)"])):
                level = summary.loc[group, column] / base * 100
                averages.append((start, end, level))
                if label == "post":
                    above = index.loc[group, last_year] >= level
        fig.add_trace(go.Scatter(
            x=list(index.columns), y=index.loc[group].values, mode="lines", line=dict(color=BLUE, width=2),
            customdata=counts.loc[group].values, hovertemplate="<b>%{x}</b><br>Index: %{y:.0f}<br>Accidents: %{customdata:,}<extra></extra>",
        ), row=row, col=col)
        fig.add_trace(go.Scatter(
            x=[last_year], y=[index.loc[group, last_year]], mode="markers+text", marker=dict(color=BLUE, size=9, line=dict(color="white", width=2)),
            text=[f"{index.loc[group, last_year]:.0f}"], textposition="top center" if above else "bottom center",
            customdata=[counts.loc[group, last_year]], hovertemplate="<b>%{x}</b><br>Index: %{y:.0f}<br>Accidents: %{customdata:,}<extra></extra>",
        ), row=row, col=col)
        # Bands and average lines come AFTER the traces: this Plotly version silently ignores shapes on an empty subplot.
        for period, (start, end) in dl.PERIODS.items():  # light bands for the periods that overlap the selection
            if end >= first_year and start <= last_year:
                fig.add_vrect(x0=max(start, first_year) - 0.5, x1=min(end, last_year) + 0.5, fillcolor=BAND_COLORS[period],
                              line_width=0, layer="below", row=row, col=col)
        for start, end, level in averages:
            fig.add_shape(type="line", x0=start - 0.5, x1=end + 0.5, y0=level, y1=level, line=dict(color=GRAY, width=2), row=row, col=col)
        if summary is not None:
            fig.add_annotation(text=f"post vs pre: {summary.loc[group, 'post vs pre %']:+.0f}%", row=row, col=col, xref="x domain", yref="y domain",
                               x=0.04, y=0.05, showarrow=False, xanchor="left", yanchor="bottom", font=dict(size=11))
    fig.update_yaxes(range=y_range, showgrid=True)
    fig.update_xaxes(range=[first_year - 0.5, last_year + 0.5], tickmode="array",
                     tickvals=sorted({first_year, last_year, *[y for y in (2020,) if first_year < y < last_year]}), showgrid=False)
    fig.update_layout(height=250 * rows_n + 70, showlegend=False, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def heatmap_figure(monthly, measure, groups):
    """1c: months as columns. Colour = seasonal index (decision #65); the numbers in the cells = the chosen measure."""
    index_table, shown = monthly["Seasonal index"], monthly[measure]
    limit = max(30, math.ceil(abs(index_table.values - 100).max() / 10) * 10)  # symmetric colour range around 100
    decimals = DECIMALS[measure]
    rows_labels = [dl.REFERENCE, ""] + list(groups)  # an empty row separates the reference line
    z_values = [index_table.loc[dl.REFERENCE].tolist(), [None] * 12] + [index_table.loc[g].tolist() for g in groups]
    text_values = [[format(v, decimals) for v in shown.loc[dl.REFERENCE]], [""] * 12] + [[format(v, decimals) for v in shown.loc[g]] for g in groups]
    fig = go.Figure(go.Heatmap(
        z=z_values, x=dl.MONTH_NAMES, y=rows_labels, text=text_values, texttemplate="%{text}", xgap=2, ygap=2, hoverongaps=False,
        colorscale=[[0, "#2a78d6"], [0.5, "#f0efec"], [1, "#e34948"]], zmin=100 - limit, zmax=100 + limit, zmid=100,
        colorbar=dict(title="Index", thickness=12, len=0.8),
        hovertemplate="<b>%{y}</b>, %{x}<br>Seasonal index: %{z:.0f}<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(side="top", showgrid=False)
    fig.update_layout(height=max(300, 42 * len(rows_labels) + 90), margin=dict(l=10, r=10, t=10, b=10))
    return fig


def seasonal_figure(seasonal, measure, groups):
    """1c: grouped bars, the four seasons for every group; the highest season of each group is labelled."""
    rows_bars = [dl.REFERENCE] + list(groups)
    table = seasonal[measure]
    best = table.idxmax(axis=1)  # the highest season of every group
    decimals = DECIMALS[measure]
    fig = go.Figure()
    for season, color in SEASON_COLORS.items():
        fig.add_trace(go.Bar(
            name=season, x=rows_bars, y=[table.loc[g, season] for g in rows_bars], marker_color=color,
            text=[format(table.loc[g, season], decimals) + ("%" if measure == "% share" else "") if best[g] == season else "" for g in rows_bars],
            textposition="outside", cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>" + season + ": %{y:" + decimals + "}<extra></extra>",
        ))
    even = {"% share": 25, "Seasonal index": 100}.get(measure)  # the even share (reference line) only exists for these two measures
    if even is not None:
        fig.add_hline(y=even, line_color=GRAY, line_width=2)
        # The label sits in free space to the right of the last group, so it never covers a bar.
        fig.add_annotation(x=len(rows_bars) - 0.4, y=even, xref="x", yref="y", text=f"even share ({even}{'%' if measure == '% share' else ''})",
                           showarrow=False, xanchor="left", yanchor="bottom", font=dict(size=11))
    fig.update_xaxes(range=[-0.6, len(rows_bars) + 0.5])
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.03, height=430, margin=dict(l=10, r=10, t=10, b=10),
                      legend=dict(orientation="h", y=-0.15), yaxis_title=measure)
    return fig
