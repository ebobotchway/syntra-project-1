"""
Analysis of accident hotspots for vulnerable road users (Streamlit): step 1 (who is involved, annual change; from the focused dashboard), then hotspots of accidents with vulnerable road users before, during and after Covid-19, their severity, and rates per resident.

It shows SAVED results (results/ and data/), made by scripts 01 and 02, so it needs no accident file. One sidebar holds the choice of view and the filters of that view.

How to run (from this folder, with `conda activate syntra-ds`):
    python -m streamlit run app.py
"""
import pandas as pd
import streamlit as st

import charts
import findings as fx
import step1_charts
import step1_logic as dl

st.set_page_config(page_title="Analysis of accident hotspots for vulnerable road users", layout="wide")
VIEWS = ["1  Burden and annual change (1a, 1b)", "2  Hotspot heat map", "3  Compare the three periods", "4  How severe are the hotspots?", "5  Residents: rates per 100,000"]
MEASURES = {"Accidents per year": "per_year", "Severe share (fatal + serious)": "severe"}


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
def summary(top_n):
    return charts.load_summary(top_n)


@st.cache_data
def coverage():
    return charts.load_coverage()


@st.cache_data
def municipalities():
    return charts.load_municipalities()


@st.cache_data
def outlines():
    return charts.load_outlines()


def top_filter():
    """The hotspot filter in the sidebar: the 20 or the 40 busiest cells (decision #213)."""
    return st.sidebar.radio("Hotspots", charts.TOP_NS, index=charts.TOP_NS.index(charts.TOP_DEFAULT), format_func=lambda n: f"Top {n}", key="top_n",
                            help="A hotspot is one of the 20 or 40 cells with the most accidents of a group in a period.")


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


st.sidebar.title("Analysis of accident hotspots for vulnerable road users")
view = st.sidebar.radio("View", VIEWS, key="view")
st.sidebar.divider()
st.sidebar.subheader("Filters")
if view != VIEWS[0]:
    group = st.sidebar.radio("Road-user group", charts.GROUPS, format_func=charts.GROUP_LABELS.get, key="group",
                             help="An accident counts for a group if the group is road user 1 or 2, once per accident. 'All four' counts an accident with two of them once.")
    words = charts.GROUP_WORDS[group]

st.title("Spatial and temporal patterns of road traffic accidents involving vulnerable road users in Belgium: A comparative analysis of accident hotspots, severity and municipalities")
st.caption("RQ: Are accidents occurring in identified hotspots more or less likely to result in fatal or serious injuries compared with accidents occurring elsewhere, after accounting for relevant environmental and road conditions?")

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

# ================================================================ 2 hotspot heat map
elif view == VIEWS[1]:
    size, top_n = charts.SIZE, top_filter()
    measure_label = st.sidebar.radio("Measure", list(MEASURES), key="measure", help="Severe share: only cells with 30 or more accidents are coloured.")
    period = st.sidebar.radio("Period", charts.PERIODS, key="period")
    measure = MEASURES[measure_label]
    st.header("2  Hotspot heat map")
    cov = coverage()
    cov = cov[(cov["group"] == group) & (cov["period"] == period)].iloc[0]
    st.caption(f"{measure_label} per 5 x 5 km square, {words}, {period}. {int(cov['with coordinates']):,} of {int(cov['accidents']):,} accidents involving {words} have usable coordinates "
               f"({100 - cov['left out %']:.1f}%); the others are not on the map. The squares mark the {top_n} busiest squares (hover for rank, municipality and severity); they are yellow (green on the severe-share map). Step 3 shows whether the same squares stay busy in all three periods.")
    plot(charts.fig_heatmap(cells(), top(), outlines(), size, measure, group, period, top_n))
    st.caption("Map: © OpenStreetMap contributors (openstreetmap.org/copyright); the tiles are loaded from the internet. Every square is drawn where it lies; its Lambert corners were converted to longitude and latitude (script 06), so it looks slightly tilted. The numbers do not change.")
    st.subheader(f"Ranking of the {top_n} busiest squares")
    st.caption("The same squares as the markers on the map, as bars of accidents per year. The bars are yellow, like the markers.")
    plot(charts.fig_hotspot_ranking(top(), size, group, period, top_n))
    t = top()
    t = t[(t["size"] == size) & (t["group"] == group) & (t["period"] == period) & (t["rank"] <= top_n)]
    with st.expander(f"The {top_n} busiest squares, with their severity", expanded=True):
        show_table(t[["rank", "municipality", "accidents", "per_year", "severe", "severe %", "severe low", "severe high", "fatal", "fatal %", "serious", "serious %", "share_of_located_pct", "centre_x_m", "centre_y_m"]],
                   f"hotspots_top{top_n}_{group}_{period}".replace(" ", "_"))
    findings(fx.heatmaps(top(), top_n), fx.TOP_NOTE)
    st.caption(fx.CARE)

# ================================================================ 3 compare the three periods
elif view == VIEWS[2]:
    size, top_n = charts.SIZE, top_filter()
    measure_label = st.sidebar.radio("Measure", list(MEASURES), key="measure")
    measure = MEASURES[measure_label]
    st.header("3  Compare the three periods")
    st.caption(f"{measure_label}, {words}. The three maps use the same grid and the same colour scale. The squares mark the {top_n} busiest squares of each period, in the same colour when the same square is in the top {top_n} of all 3 periods (red), of 2 periods (orange) or of 1 period (black).")
    plot(charts.fig_heatmap_periods(cells(), top(), outlines(), size, measure, group, top_n))
    st.caption("Map: © OpenStreetMap contributors (openstreetmap.org/copyright); the tiles are loaded from the internet. Every square is drawn where it lies; its Lambert corners were converted to longitude and latitude (script 06), so it looks slightly tilted. The numbers do not change.")
    st.subheader(f"Ranking of the {top_n} busiest squares per period")
    st.caption("The squares of the three maps as bars of accidents per year, rank 1 at the top. Same colours as the markers: red = the square is in the top of all 3 periods, orange = 2, black = 1.")
    plot(charts.fig_hotspot_ranking_periods(top(), size, group, top_n))
    c = cells()
    c = c[(c["size"] == size) & (c["group"] == group) & c["period"].isin(charts.THREE)]
    cov = coverage()
    cov = cov[(cov["group"] == group) & cov["period"].isin(charts.THREE)].set_index("period")
    table = pd.DataFrame({"period": charts.THREE,
                          "located accidents per year": [c[c["period"] == p]["accidents"].sum() / charts.YEARS_IN[p] for p in charts.THREE],
                          "accidents without coordinates %": [cov.loc[p, "left out %"] for p in charts.THREE],
                          "cells with 30+ accidents": [int((c[c["period"] == p]["accidents"] >= 30).sum()) for p in charts.THREE]})
    show_table(table, f"periods_{group}".replace(" ", "_"), decimals=1)
    st.caption("Many more accidents lack coordinates before Covid-19 than after it, so counts per year in the first two maps are understated compared with the third. The severe-share view and the resident rates (view 5) do not have this problem to the same degree.")
    findings(fx.heatmaps(top(), top_n), fx.TOP_NOTE)

# ================================================================ 4 severity of the hotspots
elif view == VIEWS[3]:
    size, top_n = charts.SIZE, top_filter()
    st.header("4  How severe are the hotspots?")
    st.caption(f"Share of the accidents involving {words} that are severe (fatal + serious injury), fatal, or serious, in the {top_n} hotspot squares against all other squares. Dot = share, line = 95% Wilson interval.")
    plot(charts.fig_hotspot_severity(summary(top_n), size, group, top_n))
    s = summary(top_n)
    s = s[(s["size"] == size) & (s["group"] == group)]
    with st.expander("Table", expanded=True):
        show_table(s[["period", "cells", "number of cells", "accidents", "severe", "severe %", "severe low", "severe high", "fatal", "fatal %", "serious", "serious %"]], f"hotspot_severity_top{top_n}_{group}".replace(" ", "_"))
    findings(fx.severity(summary(top_n), top_n), fx.TOP_NOTE)
    st.caption("Read with care: severity is the class of the whole accident, not the harm to one road user. Hotspot cells are cities with lower speeds and more stop-and-go traffic, but speed is not in the data: an association, not a cause.")

    # ---- 4b logistic regression (script 05): always the 5 x 5 km squares, all four groups in one model
    st.divider()
    st.subheader("4b  Logistic regression: what goes with a severe accident?")
    lg = charts.load_logit(top_n)
    fit, adj, sel = lg["severity_fit"].iloc[0], lg["hotspot_adjusted"].iloc[0], lg["selection"]
    st.caption(f"One model for the four groups together (it does not follow the group filter; it does follow the hotspot filter). Dependent variable: severe (fatal + serious injury) = 1, otherwise 0. Explanatory variables: hotspot (accident in one of the {top_n} busiest 5 x 5 km squares of its own group and period), period, group, built-up area, light condition (daylight, dawn or dusk, and night with public lighting lit, present but not lit, or none) and road surface (dry or clean, wet, dirty, ice or snow). "
               f"{int(fit['rows']):,} rows ({int(fit['different accidents']):,} accidents; an accident with two groups is a row in both), {int(fit['severe accidents']):,} severe ({fit['severe %']:.1f}%). Standard errors are cluster-robust by municipality ({int(fit['clusters (municipalities)'])} clusters)." + " Filled dots are significant at the 5% level (p below 0.05); a hollow gray dot is not significant (its interval includes 1).")
    plot(charts.fig_logit_forest(lg["severity_model"]))
    show_table(charts.odds_ratio_table(lg["severity_model"]), "logit_severity_odds_ratios", decimals=3)
    c1, c2, c3 = st.columns(3)
    c1.metric("Severe % if none in a hotspot", f"{adj['severe % if none in a hotspot']:.1f}%")
    c2.metric("Severe % if all in a hotspot", f"{adj['severe % if all in a hotspot']:.1f}%")
    c3.metric("Difference (95% interval)", f"{adj['difference (percentage points)']:.1f} points", f"{adj['difference low']:.1f} to {adj['difference high']:.1f}", delta_color="off")
    st.caption(f"Fit: AUC {fit['AUC']:.2f}, McFadden R2 {fit['McFadden R2']:.3f}, highest VIF {fit['highest VIF']:.2f}. The average adjusted prediction sets the hotspot term to 1 and to 0 for every row (other variables as observed) and averages the predicted probabilities; the interval uses 1,000 simulated coefficient sets.")
    with st.expander("Which accidents were used", expanded=False):
        show_table(sel, "logit_severity_selection")
        st.caption("Accidents without usable coordinates (the square is unknown) and accidents with unknown built-up area, light condition or road surface are left out.")
    with st.expander("Plain severe share per category (no model)", expanded=False):
        show_table(lg["severity_descriptives"], "logit_severity_descriptives")
    findings(fx.logit(lg), fx.TOP_NOTE)
    st.caption(fx.logit_care(top_n))

# ================================================================ 5 residents: rates per 100,000
else:
    period = st.sidebar.radio("Period", charts.PERIODS, key="period")
    by_label = st.sidebar.radio("Rank by", ["Accidents per 100,000 residents per year", "Accidents per year (the count)"], key="rank_by")
    by = "rate" if by_label.startswith("Accidents per 100,000") else "count"
    st.header("5  Residents: accidents per 100,000 residents per year")
    t = charts.municipality_table(municipalities(), group, period)
    belgium = t["accidents"].sum() / t["resident_years"].sum() * 100_000
    st.caption(f"{words.capitalize()}, {period}. Rate = accidents of the group in the municipality divided by its residents, using the residents of each year (Statbel, 1 January), per 100,000. Belgium: {belgium:.1f}. "
               + (f"{int(t['reliable'].sum())} of {len(t)} municipalities have 100 or more accidents of the group (full colour); {int(t['flagged'].sum())} have 30-99 (faded: flagged as unreliable); the rest stay gray. The map is coloured by the rate."
               if by == "rate" else f"The map is coloured by the number of accidents per year (5 classes with equal numbers of municipalities); {int((t['accidents'] > 0).sum())} of {len(t)} municipalities have at least one accident, the rest stay gray."))
    plot(charts.fig_rate_map(t, outlines(), group, by))
    plot(charts.fig_rate_ranking(t, group, by))
    with st.expander("All municipalities with 30 or more accidents", expanded=False):
        d = t[t["accidents"] >= charts.MIN_SHARE].sort_values(charts.RATE, ascending=False)
        show_table(d[["municipality", "region", "accidents", "accidents per year", "average residents", charts.RATE, "reliable", "severe", "severe %", "fatal", "fatal %"]], f"rates_{group}_{period}".replace(" ", "_"), decimals=1)
    findings(fx.RATES)
    st.caption(fx.CARE)
