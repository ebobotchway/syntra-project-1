"""
Hotspot deep dive (Streamlit): hotspots of accidents with vulnerable road users before, during and after Covid-19, their severity, and rates per resident.

It shows SAVED results (results/ and data/), made by scripts 01 and 02, so it needs no accident file. One sidebar holds the choice of view and the filters of that view.

How to run (from this folder, with `conda activate syntra-ds`):
    python -m streamlit run app.py
"""
import pandas as pd
import streamlit as st

import charts
import findings as fx

st.set_page_config(page_title="Hotspot deep dive", layout="wide")
VIEWS = ["1  Hotspot heat map", "2  Compare the three periods", "3  How severe are the hotspots?", "4  Residents: rates per 100,000"]
MEASURES = {"Accidents per year": "per_year", "Severe share (fatal + serious)": "severe"}


@st.cache_data
def cells():
    return charts.load_cells()


@st.cache_data
def top():
    return charts.load_top()


@st.cache_data
def summary():
    return charts.load_summary()


@st.cache_data
def coverage():
    return charts.load_coverage()


@st.cache_data
def municipalities():
    return charts.load_municipalities()


@st.cache_data
def outlines():
    return charts.load_outlines()


def findings(lines, note=fx.FIXED_NOTE):
    with st.container(border=True):
        st.markdown(f"**Key findings**  \n*{note}*")
        for line in lines:
            st.markdown(f"- {line}")


def show_table(df, name, decimals=2):
    shown = df.round(decimals)
    st.dataframe(shown, hide_index=True, width="stretch")
    st.download_button("Download as CSV", shown.to_csv(index=False).encode("utf-8"), file_name=f"{name}.csv", mime="text/csv", key=f"download_{name}")


def plot(fig):
    st.plotly_chart(fig, width="stretch")


st.sidebar.title("Hotspot deep dive")
view = st.sidebar.radio("View", VIEWS, key="view")
st.sidebar.divider()
st.sidebar.subheader("Filters")
group = st.sidebar.radio("Road-user group", charts.GROUPS, format_func=charts.GROUP_LABELS.get, key="group",
                         help="An accident counts for a group if the group is road user 1 or 2, once per accident. 'All four' counts an accident with two of them once.")
words = charts.GROUP_WORDS[group]

st.title("Hotspots of accidents with vulnerable road users")
st.caption("Before (2017-2019), during (2020-2021) and after (2022-2024) Covid-19: where accidents concentrate, how severe they are there, and how that looks per resident. "
           "Counts and rates, not causes. The period names are my own definition; the data states no cause.")

# ================================================================ 1 hotspot heat map
if view == VIEWS[0]:
    size = st.sidebar.radio("Cell size", list(charts.CELL_SIZES), key="size", help="5 km2 cells have a side of 2.24 km; the squares are 5 km x 5 km (25 km2).")
    measure_label = st.sidebar.radio("Measure", list(MEASURES), key="measure", help="Severe share: only cells with 30 or more accidents are coloured.")
    period = st.sidebar.radio("Period", charts.PERIODS, key="period")
    measure = MEASURES[measure_label]
    st.header("1  Hotspot heat map")
    cov = coverage()
    cov = cov[(cov["group"] == group) & (cov["period"] == period)].iloc[0]
    st.caption(f"{measure_label} per {size[:-1] if size.endswith('s') else size}, {words}, {period}. {int(cov['with coordinates']):,} of {int(cov['accidents']):,} accidents involving {words} have usable coordinates "
               f"({100 - cov['left out %']:.1f}%); the others are not on the map. Black squares = the 20 busiest cells (hover for rank, municipality and severity).")
    plot(charts.fig_heatmap(cells(), top(), outlines(), size, measure, group, period))
    t = top()
    t = t[(t["size"] == size) & (t["group"] == group) & (t["period"] == period)]
    with st.expander("The 20 busiest cells, with their severity", expanded=True):
        show_table(t[["rank", "municipality", "accidents", "per_year", "severe", "severe %", "severe low", "severe high", "fatal", "fatal %", "serious", "serious %", "share_of_located_pct", "centre_x_m", "centre_y_m"]],
                   f"hotspots_{group}_{size}_{period}".replace(" ", "_"))
    findings(fx.HEATMAPS)
    st.caption(fx.CARE)

# ================================================================ 2 compare the three periods
elif view == VIEWS[1]:
    size = st.sidebar.radio("Cell size", list(charts.CELL_SIZES), key="size")
    measure_label = st.sidebar.radio("Measure", list(MEASURES), key="measure")
    measure = MEASURES[measure_label]
    st.header("2  Compare the three periods")
    st.caption(f"{measure_label}, {words}. The three maps use the same grid and the same colour scale. Black squares = the 20 busiest cells of each period.")
    plot(charts.fig_heatmap_periods(cells(), top(), outlines(), size, measure, group))
    c = cells()
    c = c[(c["size"] == size) & (c["group"] == group) & c["period"].isin(charts.THREE)]
    cov = coverage()
    cov = cov[(cov["group"] == group) & cov["period"].isin(charts.THREE)].set_index("period")
    table = pd.DataFrame({"period": charts.THREE,
                          "located accidents per year": [c[c["period"] == p]["accidents"].sum() / charts.YEARS_IN[p] for p in charts.THREE],
                          "accidents without coordinates %": [cov.loc[p, "left out %"] for p in charts.THREE],
                          "cells with 30+ accidents": [int((c[c["period"] == p]["accidents"] >= 30).sum()) for p in charts.THREE]})
    show_table(table, f"periods_{group}_{size}".replace(" ", "_"), decimals=1)
    st.caption("Many more accidents lack coordinates before Covid-19 than after it, so counts per year in the first two maps are understated compared with the third. The severe-share view and the resident rates (view 4) do not have this problem to the same degree.")
    findings(fx.HEATMAPS)

# ================================================================ 3 severity of the hotspots
elif view == VIEWS[2]:
    size = st.sidebar.radio("Cell size", list(charts.CELL_SIZES), key="size")
    st.header("3  How severe are the hotspots?")
    st.caption(f"Share of the accidents involving {words} that are severe (fatal + serious injury), fatal, or serious, in the 20 hotspot cells against all other cells. Dot = share, line = 95% Wilson interval.")
    plot(charts.fig_hotspot_severity(summary(), size, group))
    s = summary()
    s = s[(s["size"] == size) & (s["group"] == group)]
    with st.expander("Table", expanded=True):
        show_table(s[["period", "cells", "number of cells", "accidents", "severe", "severe %", "severe low", "severe high", "fatal", "fatal %", "serious", "serious %"]], f"hotspot_severity_{group}_{size}".replace(" ", "_"))
    findings(fx.SEVERITY)
    st.caption("Read with care: severity is the class of the whole accident, not the harm to one road user. Hotspot cells are cities with lower speeds and more stop-and-go traffic, but speed is not in the data: an association, not a cause.")

# ================================================================ 4 residents: rates per 100,000
else:
    period = st.sidebar.radio("Period", charts.PERIODS, key="period")
    by_label = st.sidebar.radio("Rank by", ["Accidents per 100,000 residents per year", "Accidents per year (the count)"], key="rank_by")
    by = "rate" if by_label.startswith("Accidents per 100,000") else "count"
    st.header("4  Residents: accidents per 100,000 residents per year")
    t = charts.municipality_table(municipalities(), group, period)
    belgium = t["accidents"].sum() / t["resident_years"].sum() * 100_000
    st.caption(f"{words.capitalize()}, {period}. Rate = accidents of the group in the municipality divided by its residents, using the residents of each year (Statbel, 1 January), per 100,000. Belgium: {belgium:.1f}. "
               f"{int(t['reliable'].sum())} of {len(t)} municipalities have 100 or more accidents of the group (full colour); {int(t['flagged'].sum())} have 30-99 (faded: flagged as unreliable); the rest stay gray.")
    plot(charts.fig_rate_map(t, outlines(), group))
    plot(charts.fig_rate_ranking(t, group, by))
    with st.expander("All municipalities with 30 or more accidents", expanded=False):
        d = t[t["accidents"] >= charts.MIN_SHARE].sort_values(charts.RATE, ascending=False)
        show_table(d[["municipality", "region", "accidents", "accidents per year", "average residents", charts.RATE, "reliable", "severe", "severe %", "fatal", "fatal %"]], f"rates_{group}_{period}".replace(" ", "_"), decimals=1)
    findings(fx.RATES)
    st.caption(fx.CARE)
