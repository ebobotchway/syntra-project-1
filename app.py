"""
Dashboard: Belgian road accidents 2017-2024, which road users bear the greatest accident burden?
Run with:  streamlit run app.py

It shows the four graphs of analysis 1 (steps a, b, c) and lets you filter years and road-user groups.
The calculations are in dashboard_logic.py, the graphs in dashboard_charts.py, and the data is the summary table
data/dashboard_data.csv (accidents per road-user group, per year, per month; built by scripts/10_build_dashboard_data.py).
The decisions behind it are in beslissingslogboek.md (#60-#68).
"""
from pathlib import Path

import streamlit as st

import dashboard_charts as charts
import dashboard_logic as dl

GITHUB = "https://github.com/ebobotchway/syntra-project-1"

st.set_page_config(page_title="Road accidents in Belgium 2017-2024", page_icon="🚦", layout="wide")


@st.cache_data
def get_data():
    return dl.load_data(Path(__file__).parent / "data" / "dashboard_data.csv")


df = get_data()

# --------------------------------------------------------------------------------------
# Sidebar: the controls (decision #62)
# --------------------------------------------------------------------------------------
if "years" not in st.session_state:
    st.session_state["years"] = (dl.YEARS[0], dl.YEARS[-1])


def set_years(first, last):
    st.session_state["years"] = (first, last)  # used by the preset buttons


st.sidebar.header("Filters")
st.sidebar.slider("Years", dl.YEARS[0], dl.YEARS[-1], key="years")
st.sidebar.caption("Quick choice:")
columns = st.sidebar.columns(2)
columns[0].button("All years", on_click=set_years, args=(2017, 2024), width="stretch")
columns[1].button("Pre 2017-19", on_click=set_years, args=(2017, 2019), width="stretch")
columns[0].button("During 2020-21", on_click=set_years, args=(2020, 2021), width="stretch")
columns[1].button("Post 2022-24", on_click=set_years, args=(2022, 2024), width="stretch")
first_year, last_year = st.session_state["years"]

chosen = st.sidebar.multiselect("Road-user groups", dl.NAMED_GROUPS, default=dl.NAMED_GROUPS)
show_others = st.sidebar.checkbox("Also show Unknown and Other road user", value=False,
                                  help="Both are not a specific group. They are in gray and off by default, like in the static graphs.")
groups = [g for g in dl.GROUPS if g in chosen or (show_others and g in dl.NOT_A_GROUP)]  # keep the ranking order

measure = st.sidebar.radio("Measure (monthly and seasonal graphs)", dl.MEASURES, index=3,
                           help="Accidents = counts; % share = share of the group's accidents; Per day = accidents divided by the number of days; "
                                "Seasonal index = % share divided by the even share (100 = average month or season).")

st.title("Which road user bears the greatest accident burden?")
st.caption(f"Belgian road accidents, years {first_year}-{last_year}. An accident counts once for every road-user group it involves "
           "(road user 1 or 2), so one accident can count for two groups. These are counts, not rates per amount of traffic.")

if not groups:
    st.warning("Choose at least one road-user group in the sidebar.")
    st.stop()


def csv_button(table, name, label="Download as CSV"):
    st.download_button(label, table.to_csv().encode("utf-8"), file_name=f"{name}.csv", mime="text/csv", key=f"download_{name}")


def findings(title, lines):
    with st.container(border=True):
        st.markdown(f"**{title}**  \n*Fixed text for all years 2017-2024; it does not change with the filters.*")
        for line in lines:
            st.markdown(f"- {line}")


tab_a, tab_b, tab_c, tab_about = st.tabs(["1a  Who is involved", "1b  Annual change", "1c  Months and seasons", "About and caveats"])

# --------------------------------------------------------------------------------------
# 1a: accidents involving each road-user group
# --------------------------------------------------------------------------------------
with tab_a:
    result, all_accidents = dl.totals(df, groups, first_year, last_year)
    st.subheader("Accidents involving each road-user group")
    st.caption(f"Share of all {all_accidents:,} accidents in {first_year}-{last_year}. Blue = a named road-user group. Gray = not a specific group (Unknown, Other road user).")
    st.plotly_chart(charts.totals_figure(result), width="stretch")
    findings("Key findings", [
        "Passenger cars (70.2% of all accidents) and bicycles (24.8%) are involved most often. Pedestrians follow at 10.3%, vans 8.1%, mopeds 8.0%, motorcycles 6.8%, trucks 4.4%, buses 1.4%.",
        "'Unknown' is 10.7%: for about one accident in ten the road user is not recorded.",
        "Shares add up to more than 100% because one accident can involve two groups (136,144 accidents involve two different groups).",
    ])
    st.caption("Read with care: these are raw counts. A group that is common on the road appears often for that reason alone; severity and traffic volume are not part of this graph.")
    with st.expander("Table"):
        st.dataframe(result.rename(columns={"road_user_group": "Road-user group", "accidents": "Accidents", "percent_of_all_accidents": "% of all accidents"}),
                     hide_index=True, width="stretch")
        csv_button(result.set_index("road_user_group"), "accidents_per_road_user")

# --------------------------------------------------------------------------------------
# 1b: annual change, small multiples indexed to the first selected year (decision #66)
# --------------------------------------------------------------------------------------
with tab_b:
    st.subheader("Annual change in accidents involving each group")
    if first_year == last_year:
        st.info("Select at least two years in the sidebar to see the annual change.")
    else:
        counts = dl.yearly(df, groups, first_year, last_year)
        index = dl.yearly_index(df, groups, first_year, last_year)
        summary = dl.period_summary(df, groups, first_year, last_year)
        st.caption(f"Index: {first_year} = 100 for every group. Shaded bands are the three periods (names are my own definition; the data does not state a cause). "
                   + ("Thin lines mark the average per year in the pre and post period." if summary is not None else
                      "Select 2017-2024 to also see the pre and post averages and 'post vs pre'."))
        st.plotly_chart(charts.annual_figure(groups, counts, index, summary, first_year, last_year), width="stretch")
        findings("Key findings", [
            "Almost every group drops in 2020 (bicycles only -5.5%; buses -37.7% and pedestrians -30.4% most) and rebounds in 2021-2022.",
            "By 2024 (2017 = 100): bicycles 115, mopeds 105, vans and buses 97, pedestrians 86, motorcycles 83, passenger cars 82, trucks 73.",
            "Post vs pre (average per year 2022-2024 against 2017-2019): trucks -17.2%, motorcycles -12.9%, cars -12.2%, pedestrians -10.4%, buses -6.4%, vans +1.5%, mopeds +7.3%, bicycles +14.6%.",
            "'Unknown' more than doubles (+113% from 2017 to 2024). Part of the decline of the named groups may be recording shifting into 'Unknown'; the data cannot show that.",
        ])
        st.caption("Read with care: 'Covid-19' is my own label for the periods. These are accident counts, not rates, so fewer accidents could also mean less traffic.")
        with st.expander("Tables"):
            st.markdown("**Accidents per year**")
            st.dataframe(counts, width="stretch")
            csv_button(counts, "annual_accidents_by_group")
            st.markdown(f"**Index ({first_year} = 100)**")
            st.dataframe(index.round(1), width="stretch")
            csv_button(index.round(2), "annual_index")
            if summary is not None:
                st.markdown("**Pre and post period**")
                st.dataframe(summary.round(1), width="stretch")
                csv_button(summary.round(2), "annual_pre_post")

# --------------------------------------------------------------------------------------
# 1c: months and seasons
# --------------------------------------------------------------------------------------
with tab_c:
    tables = dl.distributions(df, groups, first_year, last_year)
    monthly, seasonal = tables["monthly"], tables["seasonal"]
    st.subheader("When do accidents happen?")
    st.caption(f"Years {first_year}-{last_year}, measure: {measure}. Meteorological seasons: winter = Dec-Feb, spring = Mar-May, summer = Jun-Aug, autumn = Sep-Nov (whole months).")

    st.markdown("**Months (heatmap)**")
    st.plotly_chart(charts.heatmap_figure(monthly, measure, groups), width="stretch")
    st.caption("Colour = seasonal index (blue below an average month, red above; 100 = average). Numbers = the measure chosen in the sidebar. "
               "The index is not corrected for month length: February has 28 or 29 days; use 'Per day' to correct for that.")

    st.markdown("**Seasons (grouped bars)**")
    st.plotly_chart(charts.seasonal_figure(seasonal, measure, groups), width="stretch")
    st.caption("The number marks each group's highest season. Winter, spring, summer, autumn have 90-92 days, so an even share of 25% is approximate.")

    findings("Key findings", [
        "Motorcycles, bicycles and mopeds peak in the warm months and nearly vanish in winter: motorcycles have 13.0% of their accidents in winter and 32.6% in summer.",
        "Pedestrians are the reverse: highest share in winter (28.0%), lowest in summer (21.3%), with a peak in December (index 123).",
        "Passenger cars, vans and trucks are fairly even, with a mild autumn peak (about 27%).",
        "Per day, January is the quietest month for all accidents (84.8 a day), not February (91.2); February's low index is partly its length.",
        "In 2020-2021 the spring share is lower for every group (all accidents 20.6% against 25.1% before); from 2022 the pattern looks like before again. The data states no cause.",
    ])
    st.caption("Read with care: shares and indexes describe WHEN a group's accidents happen, not how many there are, and not rates per amount of traffic. "
               "The seasonal hypotheses (riding in good weather, darker months for pedestrians) are not tested.")
    file_name = measure.replace(" ", "_").replace("%", "pct")
    with st.expander("Tables"):
        st.markdown(f"**Months: {measure}**")
        st.dataframe(monthly[measure].round(2), width="stretch")
        csv_button(monthly[measure].round(2), f"monthly_{file_name}")
        st.markdown(f"**Seasons: {measure}**")
        st.dataframe(seasonal[measure].round(2), width="stretch")
        csv_button(seasonal[measure].round(2), f"seasonal_{file_name}")

# --------------------------------------------------------------------------------------
# About
# --------------------------------------------------------------------------------------
with tab_about:
    st.subheader("About this dashboard and what to be careful with")
    st.markdown(
        "- **Data:** Belgian road-accident open data 2017-2024 (289,532 accidents), translated to English. One row = one accident (the data has no ID to prove it).\n"
        "- **Counting:** an accident counts for a road-user group if that group is road user 1 or road user 2, once per accident. 'Single road user' is not a road user.\n"
        "- **Unknown** (about 10% of accidents, growing over the years) and **Other road user** are separate lines and hidden by default.\n"
        "- **Periods:** pre (2017-2019), during (2020-2021) and post (2022-2024) 'Covid-19' are my own definition; the data states no cause.\n"
        "- **Counts, not rates:** traffic volume is not in the data, so more accidents does not mean more risk per kilometre.\n"
        "- **Seasons:** meteorological, whole months only (the data has no day). December, January and February of the same calendar year are grouped.\n"
        "- **Open questions:** why empty coordinates jump in Brussels in 2024; the difference between accident classes 'with fatalities' and 'fatally injured'.\n"
        "- **Not done:** urban vs rural. The data has only 'built-up area', no official urban/rural classification (decision #55)."
    )
    st.markdown(f"Decisions and reasons: [decision log]({GITHUB}/blob/main/beslissingslogboek.md) · Code: [scripts]({GITHUB}/tree/main/scripts) · "
                f"Summary of the missing-value work: [report]({GITHUB}/blob/main/reports/missing_values_summary.md)")

st.divider()
st.caption(f"Decisions behind this dashboard: [decision log]({GITHUB}/blob/main/beslissingslogboek.md), entries #60-#68. Code: [GitHub]({GITHUB}).")
