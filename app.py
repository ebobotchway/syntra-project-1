"""
Interactive analysis tool: Belgian road accidents 2017-2024, who is most exposed and who suffers the most severe outcomes?
Run with:  streamlit run app.py

One consistent sidebar (decision #138): the analysis menu, then the filters for period, road users, place, and road and light conditions.
All filters apply to every analysis, and every number is calculated from the FILTERED accidents. The main area shows only the selected analysis.
Exports: the filtered accident data (sidebar) and, at the bottom of each analysis, its tables and charts (Excel, CSV, HTML, ZIP package).
The fixed results of the study (steps 1-5) are on the last page, "Study results".
The decisions behind the tool are in beslissingslogboek.md (#132-#144).
"""
import streamlit as st

import study_results
import tool_data as td
import tool_export as te
import tool_pages as tp

GITHUB = "https://github.com/ebobotchway/syntra-project-1"
ANALYSES = ["Overview and severity", "Compare groups", "Time: years, months, seasons", "Geography and hotspots", "Regions and concentration", "Statistical models", "Study results (fixed)"]

st.set_page_config(page_title="Road accident analysis tool", page_icon="🚦", layout="wide")
data = tp.get_data()
df = data["df"]
names = data["municipality_names"]

# --------------------------------------------------------------------------------------
# Sidebar: the analysis menu and the filters (the same for every analysis)
# --------------------------------------------------------------------------------------
DEFAULTS = {"f_years": (td.YEARS[0], td.YEARS[-1]), "f_groups": list(td.DEFAULT_COMPARE), "f_overlap": False, "f_regions": [], "f_provinces": [], "f_municipalities": [],
            "f_roadtypes": [], "f_intersections": [], "f_lightings": [], "f_weathers": [], "f_surfaces": []}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)


def reset_filters():
    for key, value in DEFAULTS.items():
        st.session_state[key] = value


def set_years(first, last):
    st.session_state["f_years"] = (first, last)


st.sidebar.title("Road accident analysis")
analysis = st.sidebar.radio("Analysis", ANALYSES, key="analysis")
st.sidebar.divider()
st.sidebar.subheader("Filters")
st.sidebar.button("Reset all filters", on_click=reset_filters, width="stretch")
if analysis == ANALYSES[-1]:
    st.sidebar.caption("The filters do not apply to the fixed study results.")

st.sidebar.markdown("**Period**")
st.sidebar.slider("Years", td.YEARS[0], td.YEARS[-1], key="f_years", label_visibility="collapsed")
cols = st.sidebar.columns(4)
cols[0].button("All", on_click=set_years, args=(2017, 2024), width="stretch", help="2017-2024")
cols[1].button("Pre", on_click=set_years, args=(2017, 2019), width="stretch", help="2017-2019")
cols[2].button("During", on_click=set_years, args=(2020, 2021), width="stretch", help="2020-2021")
cols[3].button("Post", on_click=set_years, args=(2022, 2024), width="stretch", help="2022-2024")

st.sidebar.markdown("**Road users**")
st.sidebar.multiselect("Groups to compare", td.GROUPS_ALL, key="f_groups",
                       help="An accident counts for every group it involves (road user 1 or 2). 'Unknown' and 'Other road user' are available but off by default.")
st.sidebar.checkbox("Exclude accidents involving more than one compared group", key="f_overlap",
                    help="For a cleaner comparison: a cyclist-pedestrian accident is then counted for neither group.")

st.sidebar.markdown("**Place**")
all_regions = sorted(df["region"].unique())
st.sidebar.multiselect("Region", all_regions, key="f_regions")
province_scope = df[df["region"].isin(st.session_state["f_regions"])] if st.session_state["f_regions"] else df
province_options = sorted(province_scope["province_label"].unique())
st.session_state["f_provinces"] = [p for p in st.session_state["f_provinces"] if p in province_options]
st.sidebar.multiselect("Province", province_options, key="f_provinces", help="Brussels has no province.")
municipality_scope = province_scope[province_scope["province_label"].isin(st.session_state["f_provinces"])] if st.session_state["f_provinces"] else province_scope
municipality_options = sorted(municipality_scope["municipality_nis_code"].unique(), key=lambda n: names[n])
st.session_state["f_municipalities"] = [m for m in st.session_state["f_municipalities"] if m in municipality_options]
st.sidebar.multiselect("Municipality", municipality_options, key="f_municipalities", format_func=lambda n: names[n], help="Type to search. Narrowed by the region and province above.")

with st.sidebar.expander("Road and light conditions"):
    st.multiselect("Road type", sorted(df["road_type"].unique()), key="f_roadtypes")
    st.multiselect("Intersection", sorted(df["crossway"].unique()), key="f_intersections")
    st.multiselect("Lighting", sorted(df["light_condition"].unique()), key="f_lightings")
    st.multiselect("Weather", sorted(df["weather"].unique()), key="f_weathers")
    st.multiselect("Road surface", sorted(df["road_condition"].unique()), key="f_surfaces")
    st.caption("No selection = all categories.")

f = td.Filters(years=tuple(st.session_state["f_years"]), groups=tuple(st.session_state["f_groups"]), exclude_overlap=st.session_state["f_overlap"],
               regions=tuple(st.session_state["f_regions"]), provinces=tuple(st.session_state["f_provinces"]), municipalities=tuple(st.session_state["f_municipalities"]),
               road_types=tuple(st.session_state["f_roadtypes"]), intersections=tuple(st.session_state["f_intersections"]), lightings=tuple(st.session_state["f_lightings"]),
               weathers=tuple(st.session_state["f_weathers"]), surfaces=tuple(st.session_state["f_surfaces"]))
mask = td.base_mask(df, f)
sub = df[mask]

# --------------------------------------------------------------------------------------
# Sidebar: the filtered data download (built only when you click, #142)
# --------------------------------------------------------------------------------------
export_mask = mask & td.selected_group_mask(df, f) if f.groups else mask & False
st.sidebar.divider()
st.sidebar.markdown("**Export filtered data**")
st.sidebar.caption(f"{int(export_mask.sum()):,} accidents pass the filters and involve at least one selected group.")


def filtered_csv():
    return te.csv_bytes(df.loc[export_mask, tp.filtered_columns(df)])


st.sidebar.download_button("Download filtered accident data (CSV)", data=filtered_csv, file_name="filtered_accidents.csv", mime="text/csv", width="stretch", disabled=not export_mask.any())
st.sidebar.caption("All 32 columns of the dataset plus analysis columns (severe, one 0/1 column per group involved, ...). Analysis tables, charts and results: see 'Export' at the bottom of each analysis.")

# --------------------------------------------------------------------------------------
# Main area: only the selected analysis
# --------------------------------------------------------------------------------------
st.title(analysis)
if analysis == ANALYSES[-1]:
    study_results.render()
    st.stop()

severe_share = sub["severe"].mean() * 100 if len(sub) else float("nan")
st.caption("Active filters: " + td.describe_filters(f, names))
k1, k2, k3 = st.columns(3)
k1.metric("Accidents in the selection", f"{len(sub):,}", help=f"of {len(df):,} in total")
k2.metric("Severe share (fatal + serious)", f"{severe_share:.1f}%" if len(sub) else "-")
k3.metric("Fatal share", f"{sub['fatal'].mean() * 100:.2f}%" if len(sub) else "-")
if len(sub) == 0:
    st.warning("No accidents pass these filters. Widen the selection or press 'Reset all filters'.")
    st.stop()
if len(sub) < 100:
    st.warning(f"Only {len(sub)} accidents pass these filters: shares will be unstable or hidden (fewer than 30 accidents per group).")

ctx = tp.Context(data=data, f=f, sub=sub)
page = {"Overview and severity": tp.page_overview, "Compare groups": tp.page_compare, "Time: years, months, seasons": tp.page_time, "Geography and hotspots": tp.page_geography,
        "Regions and concentration": tp.page_regions, "Statistical models": tp.page_models}[analysis](ctx)
page.export_panel()
st.divider()
st.caption(f"Belgian road accident open data 2017-2024, translated to English. Counts and shares, not rates per traffic. Decisions behind the tool: [decision log]({GITHUB}/blob/main/beslissingslogboek.md) (#132-#144) · Code: [GitHub]({GITHUB}).")
