"""
Vulnerable hotspots (Streamlit): step 1 (who is involved, annual change), step 2 (severity per road-user group), the hotspots of accidents with vulnerable road users before, during and after Covid-19
on a grid of 5 km2 cells and 5 x 5 km squares (heat maps, severity at the hotspots, rates per resident of the cell), the municipality top 20, rates per municipality, and regional severity.

It shows SAVED results (results/ and data/), made by scripts 01, 01b and 02 and copied from the focused dashboard, so it needs no accident file. One sidebar holds the choice of view and the filters of that view.

How to run (from this folder, with `conda activate syntra-ds`):
    python -m streamlit run app.py
"""
import numpy as np
import pandas as pd
import streamlit as st

import charts
import charts_focused as cf
import findings as fx
import step1_charts
import step1_logic as dl
import tables as tb

st.set_page_config(page_title="Vulnerable hotspots", layout="wide")
VIEWS = ["1  Burden and annual change (1a, 1b)", "2  Severity per road-user group", "3  Hotspot heat map", "4  Compare the three periods", "5  How severe are the hotspots?", "6  Municipalities: top 20", "7  Residents: rates per municipality", "8  Regional severity and province map"]
MEASURES = {"Accidents per year": "per_year", "Accidents per 100,000 residents of the cell per year": "rate", "Severe share (fatal + serious)": "severe"}
GROUP_LABELS = {"Pedestrian": "Pedestrians", "Motorcycle": "Motorcycles", "Moped": "Mopeds", "Bicycle": "Cyclists"}
REGIONS = {"Belgium": None, "Flanders": "Flemish Region", "Wallonia": "Walloon Region", "Brussels": "Brussels-Capital Region"}


@st.cache_data
def step1_table():
    return dl.load_data(charts.DATA / "dashboard_data.csv")


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


@st.cache_data
def results_f():
    return cf.load_results()


@st.cache_data
def outlines_f():
    return cf.load_outlines()


@st.cache_data
def provinces_f():
    return cf.load_provinces()


@st.cache_data
def positions_f():
    return cf.load_positions()


@st.cache_data
def municipality_periods_f():
    return cf.load_municipality_periods()


def findings(lines, note=fx.FIXED_NOTE):
    with st.container(border=True):
        st.markdown(f"**Key findings**  \n*{note}*")
        for line in lines:
            st.markdown(f"- {line}")


def show_table(df, name, decimals=2, index=False):
    shown = df.round(decimals)
    st.dataframe(shown, hide_index=not index, width="stretch")
    st.download_button("Download as CSV", shown.to_csv(index=index).encode("utf-8"), file_name=f"{name}.csv", mime="text/csv", key=f"download_{name}")


def plot(fig):
    st.plotly_chart(fig, width="stretch")


st.sidebar.title("Vulnerable hotspots")
view = st.sidebar.radio("View", VIEWS, key="view")
st.sidebar.divider()
st.sidebar.subheader("Filters")
if view in (VIEWS[2], VIEWS[3], VIEWS[4], VIEWS[6]):
    group = st.sidebar.radio("Road-user group", charts.GROUPS, format_func=charts.GROUP_LABELS.get, key="group",
                             help="An accident counts for a group if the group is road user 1 or 2, once per accident. 'All four' counts an accident with two of them once.")
    words = charts.GROUP_WORDS[group]

st.title("Accident hotspots with vulnerable road users")
st.caption("Step 1: who is involved and how it changed; step 2: severity per road-user group. Then, before (2017-2019), during (2020-2021), after (2022-2024) Covid-19 and in all years: where accidents with vulnerable road users concentrate, how severe they are there, and how that looks per resident. "
           "Counts and rates, not causes. The period names are my own definition; the data states no cause.")

# ================================================================ 1 burden and annual change (1a, 1b)
if view == VIEWS[0]:
    df = step1_table()
    first_year, last_year = st.sidebar.slider("Years", dl.YEARS[0], dl.YEARS[-1], (dl.YEARS[0], dl.YEARS[-1]), key="years")
    chosen = st.sidebar.multiselect("Road-user groups", dl.NAMED_GROUPS, default=dl.NAMED_GROUPS, key="groups")
    show_others = st.sidebar.checkbox("Also show Unknown and Other road user", value=False, key="others", help="Both are not a specific group. They are shown in gray and are off by default.")
    groups = [g for g in dl.GROUPS if g in chosen or (show_others and g in dl.NOT_A_GROUP)]
    st.header("1  Which road user bears the greatest accident burden?")
    if not groups:
        st.warning("Choose at least one road-user group in the sidebar.")
    else:
        result, all_accidents = dl.totals(df, groups, first_year, last_year)
        st.subheader("1a  Accidents involving each road-user group")
        st.caption(f"Share of all {all_accidents:,} accidents in {first_year}-{last_year}. Blue = a named road-user group. Gray = not a specific group (Unknown, Other road user).")
        plot(step1_charts.totals_figure(result))
        with st.expander("Table"):
            show_table(result.rename(columns={"road_user_group": "Road-user group", "accidents": "Accidents", "percent_of_all_accidents": "% of all accidents"}), "accidents_per_road_user")
        st.subheader("1b  Annual change")
        if first_year == last_year:
            st.info("Select at least two years in the sidebar to see the annual change.")
        else:
            counts = dl.yearly(df, groups, first_year, last_year)
            index = dl.yearly_index(df, groups, first_year, last_year)
            summary_ = dl.period_summary(df, groups, first_year, last_year)
            st.caption(f"Index: {first_year} = 100 for every group. Shaded bands are the three periods (names are my own definition; the data does not state a cause). "
                       + ("Thin lines mark the average per year in the pre and post period." if summary_ is not None else "Select 2017-2024 to also see the pre and post averages and 'post vs pre'."))
            plot(step1_charts.annual_figure(groups, counts, index, summary_, first_year, last_year))
            with st.expander("Tables"):
                st.markdown("**Accidents per year**")
                show_table(counts, "annual_accidents_by_group", index=True)
                st.markdown(f"**Index ({first_year} = 100)**")
                show_table(index, "annual_index", decimals=1, index=True)
                if summary_ is not None:
                    st.markdown("**Pre and post period**")
                    show_table(summary_, "annual_pre_post", decimals=1, index=True)
        findings(fx.STEP_1A + fx.STEP_1B)
        st.caption(fx.CARE_1)

# ================================================================ 2 severity per road-user group (step 2 of the focused dashboard)
elif view == VIEWS[1]:
    res = results_f()
    scope = st.sidebar.radio("Period", list(cf.SCOPE_LABELS), format_func=cf.SCOPE_LABELS.get, key="severity_scope", help="Pre, during and post Covid-19 are my own period names; the data states no cause.")
    st.header("2  Severity per road-user group")
    st.caption("Who experiences the most severe outcomes? The severity class belongs to the WHOLE accident, not to one road user: a car-pedestrian accident counts for both groups. This is the severity of all accidents of a group; section 5 shows the severity at the hotspots.")
    st.markdown("**Share of the group's accidents that are fatal, seriously injured or slightly injured** (dot = share, line = 95% interval, gray line = all accidents)")
    plot(cf.fig_severity_intervals(res, scope))
    st.markdown("**Severity distribution per group** (ordered by fatal share)")
    plot(cf.fig_severity_distribution(res, scope))
    findings(fx.STEP_2)
    st.caption(fx.CARE_2)
    with st.expander("Table"):
        a, b, c = (res[k][res[k]["scope"] == scope].set_index("road_user_group") for k in ("severity_a_fatal", "severity_b_serious", "severity_c_slight"))
        combined = a[["accidents", "count", "share_pct", "ci_low_pct", "ci_high_pct", "ratio_to_all", "gap_points"]].rename(
            columns={"count": "fatal", "share_pct": "fatal %", "ci_low_pct": "fatal low", "ci_high_pct": "fatal high", "ratio_to_all": "fatal ratio", "gap_points": "fatal gap"})
        combined["serious"], combined["serious %"] = b["count"], b["share_pct"]
        combined["slight"], combined["slight %"] = c["count"], c["share_pct"]
        show_table(combined.reset_index(), f"severity_{scope}")

# ================================================================ 2 hotspot heat map
elif view == VIEWS[2]:
    size = st.sidebar.radio("Cell size", list(charts.CELL_SIZES), key="size", help="5 km2 cells have a side of 2.24 km; the squares are 5 km x 5 km (25 km2).")
    measure_label = st.sidebar.radio("Measure", list(MEASURES), key="measure",
                                     help="Severe share and rate: only cells with 30 or more accidents are coloured; a rate also needs 1,000 residents in the cell. "
                                          "Residents: Statbel, spread over the squares by area (#183).")
    period = st.sidebar.radio("Period", charts.PERIODS, key="period")
    measure = MEASURES[measure_label]
    st.header("3  Hotspot heat map")
    cov = coverage()
    cov = cov[(cov["group"] == group) & (cov["period"] == period)].iloc[0]
    marked = "the 20 highest rates (cells with 1,000+ residents and 30+ accidents)" if measure == "rate" else "the 20 busiest cells"
    st.caption(f"{measure_label}, {size}, {words}, {period}. {int(cov['with coordinates']):,} of {int(cov['accidents']):,} accidents involving {words} have usable coordinates "
               f"({100 - cov['left out %']:.1f}%); the others are not on the map. Black squares = {marked} (hover for rank, municipality, residents and severity).")
    plot(charts.fig_heatmap(cells(), top(), outlines(), size, measure, group, period))
    t = top()
    ranking = "rate" if measure == "rate" else "accidents"
    t = t[(t["size"] == size) & (t["group"] == group) & (t["period"] == period) & (t["ranking"] == ranking)]
    with st.expander("The 20 highest rates, with their severity" if measure == "rate" else "The 20 busiest cells, with their severity", expanded=True):
        show_table(t[["rank", "municipality", "accidents", "per_year", "average residents", "rate", "severe", "severe %", "severe low", "severe high", "fatal", "fatal %", "serious", "serious %", "share_of_located_pct", "centre_x_m", "centre_y_m"]]
                   .rename(columns={"rate": "per 100,000 residents per year"}), f"hotspots_{group}_{ranking}_{period}".replace(" ", "_"))
    findings(fx.SQUARE_RATES[size] if measure == "rate" else fx.HEATMAPS[size])
    st.caption(fx.CARE)

# ================================================================ 3 compare the three periods
elif view == VIEWS[3]:
    size = st.sidebar.radio("Cell size", list(charts.CELL_SIZES), key="size")
    measure_label = st.sidebar.radio("Measure", list(MEASURES), key="measure")
    measure = MEASURES[measure_label]
    st.header("4  Compare the three periods")
    st.caption(f"{measure_label}, {words}. The three maps use the same grid and the same colour scale. Black squares = " + ("the 20 highest rates" if measure == "rate" else "the 20 busiest cells") + " of each period.")
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
    st.caption("Many more accidents lack coordinates before Covid-19 than after it, so counts per year in the first two maps are understated compared with the third. The severe-share view and the resident rates (view 7, and the rate per cell in view 3) do not have this problem to the same degree: a rate divides by residents but still counts only accidents with coordinates.")
    findings(fx.HEATMAPS[size])

# ================================================================ 4 severity of the hotspots
elif view == VIEWS[4]:
    size = st.sidebar.radio("Cell size", list(charts.CELL_SIZES), key="size")
    st.header("5  How severe are the hotspots?")
    st.caption(f"Share of the accidents involving {words} that are severe (fatal + serious injury), fatal, or serious, in the 20 busiest cells (hotspots) against all other cells. Dot = share, line = 95% Wilson interval.")
    plot(charts.fig_hotspot_severity(summary(), size, group))
    s = summary()
    s = s[(s["size"] == size) & (s["group"] == group)]
    with st.expander("Table", expanded=True):
        show_table(s[["period", "cells", "number of cells", "accidents", "severe", "severe %", "severe low", "severe high", "fatal", "fatal %", "serious", "serious %"]], f"hotspot_severity_{group}_{size}".replace(" ", "_"))
    findings(fx.SEVERITY[size])
    st.caption("Read with care: severity is the class of the whole accident, not the harm to one road user. Hotspot cells are cities with lower speeds and more stop-and-go traffic, but speed is not in the data: an association, not a cause.")

# ================================================================ 6 municipalities: top 20 (step 3b/3c of the focused dashboard)
elif view == VIEWS[5]:
    res, outl = results_f(), outlines_f()
    group6 = st.sidebar.radio("Road-user group", cf.GROUPS4, format_func=GROUP_LABELS.get, key="group6")
    group, many = group6, cf.GROUP_WORDS[group6][1]
    st.header("6  Municipalities: where are vulnerable road users most exposed?")
    by_label = st.sidebar.radio("Top 20 by", ["Number of accidents", "Share of the municipality's accidents (100+ accidents)"], key="rank_by6")
    by = "accidents" if by_label.startswith("Number") else "share"
    period = st.sidebar.selectbox("Period", tb.PERIODS, format_func=tb.PERIOD_LABELS.get, key="muni_period")
    region_label = st.sidebar.selectbox("Region", list(REGIONS), key="muni_region")
    map_kind = st.sidebar.radio("Map", ["Bubble map", "Choropleth"], key="muni_map")
    base = res["geo_a_cyclists_by_municipality"].set_index("municipality_nis_code")[["municipality", "region"]]
    table = tb.municipality_table(municipality_periods_f(), base, group, period, REGIONS[region_label])
    top20 = tb.top_municipalities(table, by)
    n_ranked = int((table["all accidents"] >= tb.MIN_ALL_FOR_SHARE).sum())
    selection_share = table["accidents"].sum() / table["all accidents"].sum() * 100
    st.subheader(f"Municipalities: accidents involving {many}, {region_label}, {tb.PERIOD_LABELS[period]}")
    st.caption(f"{n_ranked} of {len(table)} municipalities have {tb.MIN_ALL_FOR_SHARE} or more accidents of any kind and can be ranked by share"
               + (", so fewer than 20 can be shown." if by == "share" and n_ranked < 20 else ".") + " The gray line is the share in the whole selection.")
    plot(cf.fig_municipality_top(top20, group, by, selection_share))
    if table["accidents"].sum() == 0 or not ((table["accidents"] > 0) & (table["all accidents"] >= tb.MIN_ALL_FOR_SHARE)).any():
        st.info("Too few accidents in this selection to draw the map (a municipality needs 100 accidents of any kind to be coloured by share).")
    elif map_kind == "Bubble map":
        st.caption(f"Each bubble sits at the average position of the municipality's accidents (all years). Size = accidents involving {many}; colour = their share of the municipality's accidents (5 quantile classes, municipalities with 100+ accidents).")
        plot(cf.fig_group_bubble(tb.for_group_charts(table), outl, positions_f(), group))
    else:
        metric = "accidents" if by == "accidents" else "share of all accidents %"
        map_table = table.copy()
        if by == "share":  # a share is only coloured for municipalities with 100+ accidents (#161)
            map_table.loc[map_table["all accidents"] < tb.MIN_ALL_FOR_SHARE, "share of all accidents %"] = np.nan
        st.caption("Colour = " + ("the group's share of the municipality's accidents (100+ accidents)" if by == "share" else "accidents involving the group") + ", in five classes with about the same number of municipalities each. Municipalities outside the region stay light gray.")
        plot(cf.fig_municipality_map(map_table, outl, metric, group))
    with st.expander("The top 20 as a table"):
        show_table(top20[["rank", "municipality", "region", "accidents", "all accidents", "share of all accidents %", "severe", "severe %"]], f"municipalities_top20_{group.lower()}_{by}_{period}")
    with st.expander("All municipalities in the selection"):
        show_table(table.sort_values("accidents", ascending=False), f"municipalities_{group.lower()}_{period}")
    findings(fx.MUNICIPALITIES[group], note="Fixed text for all years 2017-2024 and all of Belgium; it does not change with the period and region filters.")
    st.caption("Read with care: counts favour big cities and the data has no population or traffic figures, so these are not rates per inhabitant or per road user. "
               "A share in a small municipality moves with a few accidents; one year alone has few accidents per municipality, so few qualify for the share ranking.")

# ================================================================ 7 residents: rates per municipality
elif view == VIEWS[6]:
    period = st.sidebar.radio("Period", charts.PERIODS, key="period")
    by_label = st.sidebar.radio("Rank by", ["Accidents per 100,000 residents per year", "Accidents per year (the count)"], key="rank_by")
    by = "rate" if by_label.startswith("Accidents per 100,000") else "count"
    st.header("7  Residents: accidents per 100,000 residents per year, by municipality")
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

# ================================================================ 8 regional severity and the province map (step 4a of the focused dashboard)
else:
    res = results_f()
    st.header("8  Regional severity")
    st.caption("Fixed results for all accidents 2017-2024; the severity class belongs to the whole accident. This view has no filters.")
    st.markdown("**Fatal and serious share per region and province** (dot = share, line = 95% interval, gray line = Belgium; Brussels has no province)")
    plot(cf.fig_regional_overview(res))
    st.markdown("**Province map**")
    plot(cf.fig_province_map(res, provinces_f()))
    findings(fx.STEP_4A)
    st.caption(fx.CARE_4)
    with st.expander("Table"):
        t = res["severity_regional_regions_provinces"]
        show_table(t[t["group"] == "All accidents"], "severity_regions_provinces_all_accidents")
