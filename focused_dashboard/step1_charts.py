"""
The two Plotly graphs of step 1 (1a and 1b) of the focused dashboard (a trimmed copy of dashboard_charts.py of the main project).
Each function takes the tables from step1_logic.py and returns a figure.
"""
import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import step1_logic as dl

BLUE, GRAY = "#2a78d6", "#898781"  # blue = a named group, gray = Unknown / Other road user
BAND_COLORS = {  # translucent washes for the three periods, so they work in light and dark mode
    "Pre Covid-19 (2017-2019)": "rgba(137,135,129,0.07)",
    "During Covid-19 (2020-2021)": "rgba(137,135,129,0.22)",
    "Post Covid-19 (2022-2024)": "rgba(137,135,129,0.13)",
}


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
