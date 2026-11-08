"""
Focused dashboard (Streamlit): step 1 (1a, 1b), step 2, step 3b/3c with a group filter, and step 4a with the province map.

It shows SAVED results (the tables in results/ and data/), so it needs no accident file; the filters change what is shown, not the analysis.
One sidebar holds the choice of analysis and the filters of the chosen analysis; the main area shows the selected analysis only.

How to run (from this folder, with `conda activate syntra-ds`):
    streamlit run app.py
"""
import numpy as np
import pandas as pd
import streamlit as st

import charts
import findings as fx
import step1_charts
import step1_logic as dl
import tables as tb

st.set_page_config(page_title="Belgian road accidents: focused dashboard", layout="wide")

ANALYSES = ["1  Burden and annual change (1a, 1b)", "2  Severity", "3  Vulnerable road users (3b/3c)", "4a  Regional severity and province map"]
GROUP_LABELS = {"Pedestrian": "Pedestrians", "Motorcycle": "Motorcycles", "Moped": "Mopeds", "Bicycle": "Cyclists"}
REGIONS = {"Belgium": None, "Flanders": "Flemish Region", "Wallonia": "Walloon Region", "Brussels": "Brussels-Capital Region"}


# ---------------------------------------------------------------- loading (cached, so a filter change does not read the files again)
@st.cache_data
def step1_table():
    return dl.load_data(charts.DATA / "dashboard_data.csv")


@st.cache_data
def results():
    return charts.load_results()


@st.cache_data
def outlines():
    return charts.load_outlines()


@st.cache_data
def provinces():
    return charts.load_provinces()


@st.cache_data
def hotspot_cells():
    return charts.load_hotspot_cells()


@st.cache_data
def positions():
    return charts.load_positions()


@st.cache_data
def municipality_periods():
    return charts.load_municipality_periods()


# ---------------------------------------------------------------- small helpers
def findings(lines, note=fx.FIXED_NOTE):
    with st.container(border=True):
        st.markdown(f"**Key findings**  \n*{note}*")
        for line in lines:
            st.markdown(f"- {line}")


def csv_button(df, name, index=False):
    st.download_button("Download as CSV", df.to_csv(index=index).encode("utf-8"), file_name=f"{name}.csv", mime="text/csv", key=f"download_{name}")


def show_table(df, name, decimals=2, index=False):
    st.dataframe(df.round(decimals), hide_index=not index, width="stretch")
    csv_button(df.round(decimals), name, index=index)


def plot(fig):
    st.plotly_chart(fig, width="stretch")


# ---------------------------------------------------------------- the sidebar: choice of analysis, then its filters
st.sidebar.title("Focused dashboard")
analysis = st.sidebar.radio("Analysis", ANALYSES, key="analysis")
st.sidebar.divider()
st.sidebar.subheader("Filters")

st.title("Belgian road accidents 2017-2024")
st.caption("289,532 accidents. An accident counts once for every road-user group it involves (road user 1 or 2), so one accident can count for two groups. These are counts and shares, not rates per amount of traffic.")

# ================================================================ 1a and 1b
if analysis == ANALYSES[0]:
    df = step1_table()
    first_year, last_year = st.sidebar.slider("Years", dl.YEARS[0], dl.YEARS[-1], (dl.YEARS[0], dl.YEARS[-1]), key="years")
    chosen = st.sidebar.multiselect("Road-user groups", dl.NAMED_GROUPS, default=dl.NAMED_GROUPS, key="groups")
    show_others = st.sidebar.checkbox("Also show Unknown and Other road user", value=False, key="others",
                                      help="Both are not a specific group. They are shown in gray and are off by default.")
    groups = [g for g in dl.GROUPS if g in chosen or (show_others and g in dl.NOT_A_GROUP)]
    st.header("Step 1: which road user bears the greatest accident burden?")
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
            summary = dl.period_summary(df, groups, first_year, last_year)
            st.caption(f"Index: {first_year} = 100 for every group. Shaded bands are the three periods (names are my own definition; the data does not state a cause). "
                       + ("Thin lines mark the average per year in the pre and post period." if summary is not None else "Select 2017-2024 to also see the pre and post averages and 'post vs pre'."))
            plot(step1_charts.annual_figure(groups, counts, index, summary, first_year, last_year))
            with st.expander("Tables"):
                st.markdown("**Accidents per year**")
                show_table(counts, "annual_accidents_by_group", index=True)
                st.markdown(f"**Index ({first_year} = 100)**")
                show_table(index, "annual_index", decimals=1, index=True)
                if summary is not None:
                    st.markdown("**Pre and post period**")
                    show_table(summary, "annual_pre_post", decimals=1, index=True)
        findings(fx.STEP_1A + fx.STEP_1B)
        st.caption(fx.CARE_1)

# ================================================================ 2 severity
elif analysis == ANALYSES[1]:
    res = results()
    scope = st.sidebar.radio("Period", list(charts.SCOPE_LABELS), format_func=charts.SCOPE_LABELS.get, key="severity_scope",
                             help="Pre, during and post Covid-19 are my own period names; the data states no cause.")
    st.header("Step 2: who experiences the most severe outcomes?")
    st.caption("The severity class belongs to the WHOLE accident, not to one road user: a car-pedestrian accident counts for both groups.")
    st.markdown("**Share of the group's accidents that are fatal, seriously injured or slightly injured** (dot = share, line = 95% interval, gray line = all accidents)")
    plot(charts.fig_severity_intervals(res, scope))
    st.markdown("**Severity distribution per group** (ordered by fatal share)")
    plot(charts.fig_severity_distribution(res, scope))
    findings(fx.STEP_2)
    st.caption(fx.CARE_2)
    with st.expander("Table"):
        a, b, c = (res[k][res[k]["scope"] == scope].set_index("road_user_group") for k in ("severity_a_fatal", "severity_b_serious", "severity_c_slight"))
        combined = a[["accidents", "count", "share_pct", "ci_low_pct", "ci_high_pct", "ratio_to_all", "gap_points"]].rename(
            columns={"count": "fatal", "share_pct": "fatal %", "ci_low_pct": "fatal low", "ci_high_pct": "fatal high", "ratio_to_all": "fatal ratio", "gap_points": "fatal gap"})
        combined["serious"], combined["serious %"] = b["count"], b["share_pct"]
        combined["slight"], combined["slight %"] = c["count"], c["share_pct"]
        show_table(combined.reset_index(), f"severity_{scope}")

# ================================================================ 3b / 3c vulnerable road users
elif analysis == ANALYSES[2]:
    res, outl = results(), outlines()
    group = st.sidebar.radio("Road-user group", charts.GROUPS4, format_func=GROUP_LABELS.get, key="group")
    view = st.sidebar.radio("View", ["Hotspots (500 m squares)", "Municipalities (top 20)"], key="view")
    many = charts.GROUP_WORDS[group][1]
    st.header("Step 3b/3c: where are vulnerable road users most exposed?")
    if view.startswith("Hotspots"):
        scope = st.sidebar.radio("Years", ["2017-2024", "2022-2024"], key="hotspot_years", help="2022-2024 has the fewest missing coordinates.")
        cov = res["geo_coverage"]
        cov = cov[(cov["group"] == group) & (cov["scope"] == scope)].iloc[0]
        st.subheader(f"Hotspots: accidents involving {many}, {scope}")
        st.caption(f"{cov['with_coordinates']:,.0f} of {cov['accidents']:,.0f} accidents involving {many} have usable coordinates ({100 - cov['left_out_pct']:.1f}%); the other {cov['left_out']:,.0f} are not on the map. "
                   "Heat map of accidents per 500 m square: zoom and pan; the 20 busiest squares are marked (hover for rank, municipality and counts).")
        plot(charts.fig_hotspots(res, hotspot_cells(), outl, group, scope))
        top = res[f"geo_hotspots_{group.lower()}"]
        top = top[top["scope"] == scope].drop(columns=["scope"])
        with st.expander(f"The 20 busiest squares: {many}, {scope}"):
            st.caption("Rank = by accidents involving the group in the square. 'Municipality' = the most common municipality among the square's accidents.")
            show_table(top, f"hotspots_{group.lower()}_{scope}")
        findings(fx.HOTSPOTS[group])
        st.caption(fx.CARE_3 + " Different square sizes would give different ranks.")
    else:
        by_label = st.sidebar.radio("Top 20 by", ["Number of accidents", "Share of the municipality's accidents (100+ accidents)"], key="rank_by")
        by = "accidents" if by_label.startswith("Number") else "share"
        period = st.sidebar.selectbox("Period", tb.PERIODS, format_func=tb.PERIOD_LABELS.get, key="muni_period")
        region_label = st.sidebar.selectbox("Region", list(REGIONS), key="muni_region")
        map_kind = st.sidebar.radio("Map", ["Bubble map", "Choropleth"], key="muni_map")
        base = res["geo_a_cyclists_by_municipality"].set_index("municipality_nis_code")[["municipality", "region"]]
        table = tb.municipality_table(municipality_periods(), base, group, period, REGIONS[region_label])
        top = tb.top_municipalities(table, by)
        n_ranked = int((table["all accidents"] >= tb.MIN_ALL_FOR_SHARE).sum())
        selection_share = table["accidents"].sum() / table["all accidents"].sum() * 100
        st.subheader(f"Municipalities: accidents involving {many}, {region_label}, {tb.PERIOD_LABELS[period]}")
        st.caption(f"{n_ranked} of {len(table)} municipalities have {tb.MIN_ALL_FOR_SHARE} or more accidents of any kind and can be ranked by share"
                   + (", so fewer than 20 can be shown." if by == "share" and n_ranked < 20 else ".") + " The gray line is the share in the whole selection.")
        plot(charts.fig_municipality_top(top, group, by, selection_share))
        if table["accidents"].sum() == 0 or not ((table["accidents"] > 0) & (table["all accidents"] >= tb.MIN_ALL_FOR_SHARE)).any():
            st.info("Too few accidents in this selection to draw the map (a municipality needs 100 accidents of any kind to be coloured by share).")
        elif map_kind == "Bubble map":
            st.caption(f"Each bubble sits at the average position of the municipality's accidents (all years). Size = accidents involving {many}; colour = their share of the municipality's accidents (5 quantile classes, municipalities with 100+ accidents).")
            plot(charts.fig_group_bubble(tb.for_group_charts(table), outl, positions(), group))
        else:
            metric = "accidents" if by == "accidents" else "share of all accidents %"
            map_table = table.copy()
            if by == "share":  # a share is only coloured for municipalities with 100+ accidents (#161)
                map_table.loc[map_table["all accidents"] < tb.MIN_ALL_FOR_SHARE, "share of all accidents %"] = np.nan
            st.caption("Colour = " + ("the group's share of the municipality's accidents (100+ accidents)" if by == "share" else "accidents involving the group") + ", in five classes with about the same number of municipalities each. Municipalities outside the region stay light gray.")
            plot(charts.fig_municipality_map(map_table, outl, metric, group))
        with st.expander("The top 20 as a table"):
            show_table(top[["rank", "municipality", "region", "accidents", "all accidents", "share of all accidents %", "severe", "severe %"]], f"municipalities_top20_{group.lower()}_{by}_{period}")
        with st.expander("All municipalities in the selection"):
            show_table(table.sort_values("accidents", ascending=False), f"municipalities_{group.lower()}_{period}")
        findings(fx.MUNICIPALITIES[group], note="Fixed text for all years 2017-2024 and all of Belgium; it does not change with the period and region filters.")
        st.caption("Read with care: counts favour big cities and the data has no population or traffic figures, so these are not rates per inhabitant or per road user. "
                   "A share in a small municipality moves with a few accidents; one year alone has few accidents per municipality, so few qualify for the share ranking.")

# ================================================================ 4a regional severity and the province map
else:
    res = results()
    st.header("Step 4a: regional severity")
    st.caption("Fixed results for all accidents 2017-2024; the severity class belongs to the whole accident. This analysis has no filters.")
    st.markdown("**Fatal and serious share per region and province** (dot = share, line = 95% interval, gray line = Belgium; Brussels has no province)")
    plot(charts.fig_regional_overview(res))
    st.markdown("**Province map**")
    plot(charts.fig_province_map(res, provinces()))
    findings(fx.STEP_4A)
    st.caption(fx.CARE_4)
    with st.expander("Table"):
        t = res["severity_regional_regions_provinces"]
        show_table(t[t["group"] == "All accidents"], "severity_regions_provinces_all_accidents")
