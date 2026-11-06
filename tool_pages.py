"""
The analysis pages of the interactive tool (decisions #132-#144). Each page works on the FILTERED accidents chosen in the sidebar and registers its tables and charts
so that the "Export" panel at the bottom can offer them as CSV, Excel, HTML and one ZIP package. The main area shows only the selected analysis.
"""
import dataclasses

import numpy as np
import pandas as pd
import streamlit as st

import dashboard_extra as dx
import logit_live as ll
import tool_charts as tc
import tool_data as td
import tool_export as te
import tool_stats as ts

GITHUB = "https://github.com/ebobotchway/syntra-project-1"
MIN_MODEL_TEXT = f"A model needs at least {ll.MIN_ACCIDENTS:,} accidents and {ll.MIN_EVENTS} severe accidents."


# --------------------------------------------------------------------------------------
# Shared data (loaded once and shared by all users of the app)
# --------------------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading 289,532 accidents ...")
def get_data():
    df = td.load_accidents()
    names = dict(zip(df["road_user_type1_code"], df["road_user_type1"]))
    return {"df": df, "gmaps": ll.global_merge_maps(df), "group_names": names, "group_codes": {v: k for k, v in names.items()},
            "municipality_names": df.groupby("municipality_nis_code")["municipality"].first().to_dict(), "areas": td.load_areas(),
            "outlines": dx.load_outlines(), "provinces": dx.load_provinces()}


@dataclasses.dataclass
class Context:
    """Everything a page needs: the full data, the filter selection and the filtered accidents."""
    data: dict
    f: td.Filters
    sub: pd.DataFrame

    @property
    def df(self):
        return self.data["df"]


def plot_config(name):
    """Every chart has a camera button that saves a PNG in the browser (no extra package needed)."""
    return {"displaylogo": False, "toImageButtonOptions": {"format": "png", "filename": te.safe_name(name), "scale": 2}}


class Page:
    """Shows tables and charts and remembers them for the export panel."""

    def __init__(self, ctx, name):
        self.ctx, self.name = ctx, name
        self.tables, self.figs = {}, {}

    def chart(self, title, fig):
        st.plotly_chart(fig, width="stretch", config=plot_config(f"{self.name}_{title}"), key=f"{self.name}-{title}")
        self.figs[title] = fig

    def table(self, title, df, caption=None, decimals=2, show=True, keep_all_rows=True):
        if caption:
            st.caption(caption)
        if show:
            shown = df.round(decimals)
            for column in shown.columns:  # tiny p-values would show as 0
                if "p-value" in str(column):
                    shown[column] = [("<0.001" if p < 0.001 else f"{p:.3f}") if pd.notna(p) else "" for p in df[column]]
            st.dataframe(shown, hide_index=True, width="stretch")
        self.tables[title] = df

    def export_panel(self):
        """The export panel at the bottom of a page: Excel, ZIP package, and single tables or charts."""
        ctx = self.ctx
        filters_text = td.describe_filters(ctx.f, ctx.data["municipality_names"])
        with st.expander("Export this analysis (tables, charts, statistical results)"):
            if not self.tables and not self.figs:
                st.caption("Nothing to export for this selection.")
                return
            st.caption("Charts: use the camera button on a chart for a PNG. The files below are built when you click.")
            tables, figs, name = dict(self.tables), dict(self.figs), self.name
            c1, c2 = st.columns(2)
            c1.download_button("Statistical results as one Excel workbook", data=lambda: te.excel_bytes(tables, filters_text, name), file_name=f"{te.safe_name(name)}_results.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"xlsx-{name}")
            include_data = c2.checkbox("Include the filtered accident data in the package", value=False, key=f"pkg-data-{name}")
            n = len(ctx.sub)
            readme = te.readme_text(name, filters_text, n)
            f, df = ctx.f, ctx.df

            def package():
                data_csv = None
                if include_data:
                    mask = td.base_mask(df, f) & td.selected_group_mask(df, f)
                    data_csv = te.csv_bytes(df.loc[mask, filtered_columns(df)])
                return te.zip_bytes(tables, figs, readme, data_csv)
            c2.download_button("Analysis package (ZIP: tables, charts, README)", data=package, file_name=f"{te.safe_name(name)}_package.zip", mime="application/zip", key=f"zip-{name}")
            if tables:
                pick = st.selectbox("Single table as CSV", list(tables), key=f"pick-table-{name}")
                st.download_button("Download the table", data=lambda: te.csv_bytes(tables[pick]), file_name=f"{te.safe_name(pick)}.csv", mime="text/csv", key=f"csv-{name}")
            if figs:
                pick_fig = st.selectbox("Single chart as interactive HTML", list(figs), key=f"pick-chart-{name}")
                st.download_button("Download the chart", data=lambda: te.chart_html(figs[pick_fig], pick_fig), file_name=f"{te.safe_name(pick_fig)}.html", mime="text/html", key=f"html-{name}")


def filtered_columns(df):
    """The columns of the data download (#142): the 32 columns of the English dataset plus the analysis columns."""
    original = list(pd.read_csv(td.ACCIDENTS_FILE, nrows=0).columns)
    extra = ["severe", "fatal", "serious", "slight"] + [f"ind_{g}" for g in td.GROUPS_ALL if f"ind_{g}" in df.columns] + ["single_road_user", "province_label", "usable_xy"]
    return original + [c for c in extra if c in df.columns]


def need_groups(ctx):
    if not ctx.f.groups:
        st.warning("Choose at least one road-user group in the sidebar.")
        return False
    return True


def interpretation(table, key="severe"):
    """One plain sentence about the highest and lowest share among the shown groups (no causal claims)."""
    d = table[(table["group"] != tc.REFERENCE_NAME) & table[f"{key} %"].notna()]
    if len(d) < 2:
        return ""
    hi, lo = d.loc[d[f"{key} %"].idxmax()], d.loc[d[f"{key} %"].idxmin()]
    return (f"Among the shown groups the {key} share is highest for **{hi['group']}** ({hi[f'{key} %']:.1f}% of {hi['accidents']:,} accidents) and lowest for **{lo['group']}** "
            f"({lo[f'{key} %']:.1f}% of {lo['accidents']:,}). The class belongs to the whole accident, not to one road user, and these are shares given an accident, not risks per amount of traffic.")


# --------------------------------------------------------------------------------------
# 1. Overview and severity
# --------------------------------------------------------------------------------------
def page_overview(ctx):
    page = Page(ctx, "Overview and severity")
    if not need_groups(ctx):
        return page
    groups = list(ctx.f.groups)
    masks = td.group_masks(ctx.sub, groups, ctx.f.exclude_overlap)
    table = ts.severity_by_group(ctx.sub, masks)
    n_over, pairs = td.overlap_count(ctx.sub, groups)
    if n_over:
        st.info(f"{n_over:,} accidents involve more than one of the compared groups" + (" and are excluded from every group." if ctx.f.exclude_overlap else " and count for each of them (the groups overlap).") + " Pairs: " + "; ".join(f"{k}: {v:,}" for k, v in pairs.items()))
    st.markdown("**Accidents involving each compared group**")
    page.chart("Accidents per group", tc.fig_accidents_per_group(table))
    outcome = st.radio("Outcome to compare", list(tc.OUTCOME_KEYS), horizontal=True, key="ov_outcome")
    st.markdown(f"**{outcome}: share of each group's accidents** (dot = share, line = 95% interval, gray line = all accidents of the selection; hollow = fewer than 100 accidents)")
    page.chart("Severity by group", tc.fig_severity_intervals(table, outcome))
    st.markdown("**Severity distribution**")
    page.chart("Severity distribution", tc.fig_severity_distribution(table))
    text = interpretation(table, tc.OUTCOME_KEYS[outcome])
    if text:
        st.markdown(text)
    columns = ["group", "accidents", "fatal", "fatal %", "serious", "serious %", "slight", "slight %", "severe", "severe %", "severe low", "severe high", "note"]
    with st.expander("Table", expanded=True):
        page.table("Severity by group", table[columns])
    return page


# --------------------------------------------------------------------------------------
# 2. Compare two groups
# --------------------------------------------------------------------------------------
@st.cache_data(show_spinner="Estimating the adjusted comparison ...", max_entries=40)
def adjusted_pair(fkey, a, b):
    """The adjusted comparison of group B against group A on the filtered accidents (#143), as light tables."""
    data = get_data()
    f = td.Filters(*fkey)
    sub = data["df"][td.base_mask(data["df"], f)]
    try:
        design = ll.fit_pair(sub, sub[f"ind_{a}"].to_numpy(), sub[f"ind_{b}"].to_numpy(), data["gmaps"])
    except ll.ModelNotAvailable as e:
        return {"error": str(e)}
    coef = ll.coefficient_table(design)
    row = coef[coef["term"] == "Group B (versus group A)"].iloc[0]
    return {"odds ratio": float(row["odds ratio"]), "low": float(row["OR low"]), "high": float(row["OR high"]), "p": float(row["p-value"]), "fit": design.fit, "notes": design.notes,
            "accidents": design.fit["accidents"], "events": design.fit["severe accidents"]}


def page_compare(ctx):
    page = Page(ctx, "Compare groups")
    f = ctx.f
    default_a = f.groups[0] if f.groups else "Bicycle"
    c1, c2 = st.columns([1, 2])
    a = c1.selectbox("Group A (the reference)", td.GROUPS_ALL, index=td.GROUPS_ALL.index(default_a), key="cmp_a")
    others = [g for g in f.groups if g != a] or [g for g in ("Pedestrian", "Motorcycle") if g != a]
    b_list = c2.multiselect("Compared with (one or more groups)", [g for g in td.GROUPS_ALL if g != a], default=others, key="cmp_b")
    if not b_list:
        st.warning("Choose at least one group to compare group A with.")
        return page
    masks = td.group_masks(ctx.sub, [a] + b_list, f.exclude_overlap)
    raw = td.group_masks(ctx.sub, [a] + b_list, False)
    overlap_rows = [(b, int((raw[a] & raw[b]).sum())) for b in b_list]
    if any(n for _, n in overlap_rows):
        st.info("Accidents involving both groups: " + "; ".join(f"{a} + {b}: {n:,}" for b, n in overlap_rows if n) + (" (excluded from the crude comparison)." if f.exclude_overlap else " (counted for both in the crude comparison; left out of the adjusted comparison)."))
    st.markdown(f"**Crude comparison: the share of {a}'s accidents that are severe against each compared group** (dot = share, line = 95% interval)")
    results = [r for r in (ts.compare_two(ctx.sub, masks, a, b) for b in b_list) if r]
    page.chart("Severe share by group", tc.fig_compare_groups(results))
    if not results:
        st.warning("Too few accidents (under 30) in one of the groups for a comparison. Widen the filters.")
    else:
        table = pd.DataFrame(results)
        show = table[["group B", "accidents A", "severe share A %", "accidents B", "severe share B %", "difference B - A (points)", "difference low", "difference high",
                      "odds ratio B / A", "odds ratio low", "odds ratio high", "chi-square p-value", "accidents in both groups"]]
        page.table("Crude comparison", show, caption="Difference in points with a Newcombe-Wilson 95% interval; odds ratio with a 95% interval (Woolf). Where the groups overlap and are not excluded, the two samples are not independent and the test is only indicative.")
        for r in results:
            word = "higher" if r["difference B - A (points)"] > 0 else "lower"
            sig = "the 95% interval excludes 0" if (r["difference low"] > 0 or r["difference high"] < 0) else "the 95% interval includes 0, so the difference is not clear"
            st.markdown(f"- **{r['group B']} against {a}:** the severe share is {abs(r['difference B - A (points)']):.1f} points {word} ({r['severe share B %']:.1f}% against {r['severe share A %']:.1f}%); {sig}.")
    st.markdown("**Adjusted comparison: the same, at the same road, light, weather, place and time conditions**")
    st.caption("A logistic model on the accidents of the two groups with region, road type, intersection, lighting, weather, road surface, year and month; standard errors clustered by municipality. "
               + MIN_MODEL_TEXT)
    fkey = dataclasses.astuple(f)
    rows, notes = [], []
    for b in b_list:
        res = adjusted_pair(fkey, a, b)
        if "error" in res:
            notes.append(f"{b} against {a}: {res['error']}")
        else:
            rows.append((f"{b} vs {a}", res["odds ratio"], res["low"], res["high"], res))
    if rows:
        page.chart("Adjusted odds ratios", tc.fig_odds_ratios([r[:4] for r in rows], f"adjusted odds ratio of a severe accident, compared group against {a} (log scale)"))
        adj = pd.DataFrame([{"comparison": r[0], "adjusted odds ratio": r[1], "low": r[2], "high": r[3], "p-value": r[4]["p"], "accidents": r[4]["accidents"], "severe accidents": r[4]["events"]} for r in rows])
        page.table("Adjusted comparison", adj, decimals=3)
        notes_all = [f"{r[0]}: {n}" for r in rows for n in r[4]["notes"]]
        if notes_all:
            with st.expander(f"Notes on the adjusted models ({len(notes_all)})"):
                for n in notes_all:
                    st.caption(n)
    for n in notes:
        st.warning(n)
    st.caption("Read with care: associations, not causes. The class belongs to the whole accident; conditions not in the data (speed, traffic, vehicle) are not adjusted for.")
    return page


# --------------------------------------------------------------------------------------
# 3. Time
# --------------------------------------------------------------------------------------
def page_time(ctx):
    page = Page(ctx, "Time")
    if not need_groups(ctx):
        return page
    groups = list(ctx.f.groups)
    masks = td.group_masks(ctx.sub, groups, ctx.f.exclude_overlap)
    st.markdown("**Annual change**")
    metric = st.radio("Show", ["Accidents", "Index (first selected year = 100)", "Severe share %"], horizontal=True, key="time_metric")
    annual = ts.annual_table(ctx.sub, masks)
    if ctx.f.years[0] == ctx.f.years[1]:
        st.info("One year is selected: the annual change needs at least two years.")
    page.chart("Annual change", tc.fig_annual(annual, metric))
    st.markdown("**Months and seasons**")
    measure = st.radio("Measure", ["seasonal index", "share of group's accidents %", "accidents per day", "accidents"], horizontal=True, key="time_measure",
                       help="Seasonal index: the month's share divided by the even share (100 = an average month); per day corrects for month length.")
    monthly = ts.monthly_table(ctx.sub, masks, ctx.f.years)
    seasonal = ts.seasonal_table(monthly)
    st.caption("Colour = seasonal index (blue below an average month, red above); numbers = the chosen measure. Meteorological seasons, whole months (the data has no day).")
    page.chart("Months", tc.fig_monthly_heatmap(monthly, measure))
    page.chart("Seasons", tc.fig_seasonal(seasonal, measure if measure != "accidents per day" else "accidents"))
    st.caption("Shares and indexes describe WHEN a group's accidents happen, not how many there are, and not rates per amount of traffic.")
    with st.expander("Tables"):
        page.table("Annual table", annual, decimals=2)
        page.table("Monthly table", monthly, decimals=2)
        page.table("Seasonal table", seasonal, decimals=2)
    return page


# --------------------------------------------------------------------------------------
# 4. Geography
# --------------------------------------------------------------------------------------
def page_geography(ctx):
    page = Page(ctx, "Geography")
    f, sub = ctx.f, ctx.sub
    default = f.groups[0] if f.groups else "Bicycle"
    c1, c2 = st.columns([1, 2])
    group = c1.selectbox("Road-user group", td.GROUPS_ALL, index=td.GROUPS_ALL.index(default), key="geo_group")
    view = c2.radio("View", ["Municipalities", "Provinces and regions", "Hotspots (500 m squares)"], horizontal=True, key="geo_view")
    mask = sub[f"ind_{group}"].to_numpy()
    if not mask.any():
        st.warning(f"No accidents involve {group.lower()}s in this selection.")
        return page
    data = ctx.data
    if view == "Municipalities":
        table = ts.municipality_table(sub, mask)
        metric_label = st.selectbox("Colour the map by", ["Accidents involving the group", "The group's share of all the municipality's accidents (%)", "Severe share of the group's accidents (%, 30+ accidents)"], key="geo_metric")
        metric = {"Accidents involving the group": "accidents", "The group's share of all the municipality's accidents (%)": "share of all accidents %",
                  "Severe share of the group's accidents (%, 30+ accidents)": "severe %"}[metric_label]
        st.caption("Five classes with about the same number of municipalities each; gray = outside the selection or too few accidents for a share (a share map needs 100+ accidents in the municipality, a severe share 30+ accidents of the group). Municipality outlines: Statbel, CC BY 4.0.")
        map_table = table.copy()
        if metric == "share of all accidents %":  # the same rule as the ranking: a share needs 100+ accidents in the municipality (#161)
            map_table.loc[map_table["all accidents"] < ts.MIN_ALL_FOR_SHARE, "share of all accidents %"] = np.nan
        page.chart("Municipality map", tc.fig_municipality_map(map_table, data["outlines"], metric, group))
        by_label = st.radio("Top 20 by", ["Number of accidents", "Share of the municipality's accidents (100+ accidents)"], horizontal=True, key="geo_top_by")
        by = "accidents" if by_label.startswith("Number") else "share"
        top = ts.top_municipalities(table, by)
        n_ranked = int((table["all accidents"] >= ts.MIN_ALL_FOR_SHARE).sum())
        selection_share = table["accidents"].sum() / table["all accidents"].sum() * 100
        st.markdown(f"**Top 20 municipalities by {'number of accidents' if by == 'accidents' else 'share'}: {group.lower()}s**")
        if by == "share":
            st.caption(f"Only municipalities with at least {ts.MIN_ALL_FOR_SHARE} accidents of any kind in the selection are ranked by share: {n_ranked} of {len(table)} qualify"
                       + (f", so fewer than 20 can be shown." if n_ranked < 20 else ".") + " The gray line is the share in the whole selection.")
        page.chart("Top 20 municipalities", tc.fig_municipality_top(top, group, by, selection_share))
        with st.expander("The top 20 as a table", expanded=False):
            page.table("Top 20 municipalities", top[["rank", "municipality", "region", "accidents", "all accidents", "share of all accidents %", "severe", "severe %", "note"]])
        ranking = table[table["accidents"] > 0].sort_values(metric if metric in table else "accidents", ascending=False)
        with st.expander("All municipalities in the selection", expanded=False):
            page.table("Municipality table", ranking[["municipality", "region", "accidents", "all accidents", "share of all accidents %", "severe", "severe %", "severe low", "severe high", "note"]])
        st.caption("Counts favour big municipalities, and there are no population or traffic figures: these are not rates per inhabitant or per road user.")
    elif view == "Provinces and regions":
        level = st.radio("Level", ["Region", "Province"], horizontal=True, key="geo_level")
        outcome = st.radio("Outcome", list(tc.OUTCOME_KEYS), horizontal=True, key="geo_outcome")
        column = "region" if level == "Region" else "province_label"
        masks = {group: mask}
        table = ts.by_area(sub, masks, column)
        if table.empty:
            st.warning("No accidents to show.")
            return page
        page.chart("Severity by area", tc.fig_area_severity(table, outcome))
        if level == "Province":
            page.chart("Province map", tc.fig_province_map(table, data["provinces"], outcome, group))
        with st.expander("Table", expanded=False):
            page.table("Area table", table)
    else:
        cells, top, n_all, n_located = ts.hotspot_cells(sub, mask)
        st.caption(f"{n_located:,} of {n_all:,} accidents involving {group.lower()}s have usable coordinates ({n_located / max(n_all, 1) * 100:.1f}%); the rest are not on the map. "
                   "Zoom and pan; the 20 busiest squares are marked (hover for rank, municipality and counts).")
        page.chart("Hotspot map", tc.fig_hotspot_map(cells, top, data["outlines"], group))
        with st.expander("The 20 busiest squares", expanded=True):
            page.table("Top 20 squares", top[["rank", "municipality", "accidents", "severe", "severe share %", "centre x (m)", "centre y (m)"]])
        st.caption("Hotspots are where accidents are COUNTED, which is mostly where many people and vehicles are; coordinates are missing for 10-13% of accidents (more in Wallonia and before 2022).")
    return page


# --------------------------------------------------------------------------------------
# 5. Regions and concentration
# --------------------------------------------------------------------------------------
def page_regions(ctx):
    page = Page(ctx, "Regions and concentration")
    if not need_groups(ctx):
        return page
    groups = list(ctx.f.groups)
    masks = td.group_masks(ctx.sub, groups, ctx.f.exclude_overlap)
    view = st.radio("View", ["Regional severity", "Severity by 500 m square concentration", "Severity by municipality density"], horizontal=True, key="reg_view")
    outcome = st.radio("Outcome", list(tc.OUTCOME_KEYS), horizontal=True, key="reg_outcome")
    key = tc.OUTCOME_KEYS[outcome]
    if view == "Regional severity":
        level = st.radio("Level", ["Region", "Province"], horizontal=True, key="reg_level")
        table = ts.by_area(ctx.sub, masks, "region" if level == "Region" else "province_label")
        page.chart("Severity by area", tc.fig_area_severity(table, outcome) if not table.empty else tc.empty_figure("No accidents to show."))
        if not table.empty:
            with st.expander("Table"):
                page.table("Area table", table)
        st.caption("Shares given an accident, per area; the class belongs to the whole accident. Areas with fewer than 30 accidents of a group show no share.")
    elif view == "Severity by 500 m square concentration":
        table = ts.concentration_squares(ctx.sub, masks)
        st.caption("Each accident is put in the class of its 500 m square: how many of the group's accidents lie in the same square. Accidents with usable coordinates only.")
        page.chart("Square concentration", tc.fig_square_concentration(table, outcome if key != "slight" else "Fatal (class 1 + 2)") if not table.empty else tc.empty_figure("No accidents with coordinates."))
        if not table.empty:
            with st.expander("Table"):
                page.table("Square concentration table", table)
        st.caption("An association: busier squares also differ in speed, road type and the mix of accidents. Not a cause.")
    else:
        table, corr, per_m = ts.concentration_density(ctx.sub, masks, ctx.data["areas"], ctx.f.years)
        st.caption("Municipalities of the selection in five equal-sized classes by accidents per km2 per year (of the group); the density is calculated from the filtered accidents.")
        page.chart("Density classes", tc.fig_density_classes(table, outcome if key != "slight" else "Fatal (class 1 + 2)") if not table.empty else tc.empty_figure("Too few municipalities for density classes."))
        if not table.empty:
            with st.expander("Tables"):
                page.table("Density class table", table)
                if not corr.empty:
                    page.table("Spearman correlations", corr, decimals=3, caption="Spearman rank correlation between municipality density and severe share (municipalities with at least 100 accidents).")
        st.caption("Density is accidents per km2, not per vehicle. An association, not a cause.")
    return page


# --------------------------------------------------------------------------------------
# 6. Statistical models
# --------------------------------------------------------------------------------------
@st.cache_data(show_spinner="Estimating the model (a few seconds) ...", max_entries=20)
def live_model(fkey, model, spec, with_prediction):
    """A study model estimated on the filtered accidents (#137); returns light tables only."""
    data = get_data()
    f = td.Filters(*fkey)
    sub = data["df"][td.base_mask(data["df"], f)]
    try:
        design = ll.fit_study_model(sub, model, spec, data["gmaps"], data["group_names"], data["group_codes"])
    except ll.ModelNotAvailable as e:
        return {"error": str(e)}
    out = {"coef": ll.coefficient_table(design), "fit": design.fit, "notes": design.notes, "calibration": ll.calibration_table(design)}
    if with_prediction:
        out["predicted"] = ll.predicted_by_category(design, ["Region", "Road type", "Intersection", "Lighting", "Year", "Month"])
    return out


def page_models(ctx):
    page = Page(ctx, "Statistical models")
    c1, c2, c3 = st.columns([2, 2, 2])
    model = c1.selectbox("Model", ll.MODEL_CHOICES, index=0 if not ctx.f.groups else 0, key="mod_model",
                         help="The baseline covers all road users of the selection; the others cover the accidents involving that group.")
    spec_label = c2.radio("Specification", ["As specified (with collision type)", "Without collision type"], key="mod_spec",
                          help="Collision type overlaps strongly with the road users; the variant shows how much the road-user odds ratios depend on it.")
    with_prediction = c3.checkbox("Also compute predicted probabilities (takes longer)", value=False, key="mod_pred")
    spec = "full" if spec_label.startswith("As") else "no_collision"
    st.caption(f"Logistic model of Severe (fatal, fatally injured or seriously injured) on the filtered accidents, estimated live with standard errors clustered by municipality. {MIN_MODEL_TEXT} "
               "The five saved study models are on the 'Study results' page.")
    res = live_model(dataclasses.astuple(ctx.f), model, spec, with_prediction)
    if "error" in res:
        st.warning(res["error"])
        return page
    fit = res["fit"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Accidents", f"{fit['accidents']:,}")
    m2.metric("Severe accidents", f"{fit['severe accidents']:,} ({fit['severe share %']:.1f}%)")
    m3.metric("AUC (in-sample)", f"{fit['AUC (in-sample)']:.2f}")
    m4.metric("McFadden R2", f"{fit['McFadden R2']:.3f}")
    st.caption(f"Clustering: {fit['municipalities (clusters)']} municipalities; intraclass correlation of the outcome {fit['ICC of the outcome']:.3f} (of the residuals {fit['ICC of the residuals']:.3f}); "
               f"the cluster-robust standard errors are on median {fit['median robust / ordinary SE']:.2f} times the ordinary ones.")
    if res["notes"]:
        with st.expander(f"Notes on this model ({len(res['notes'])}): merged categories and left-out terms"):
            for n in res["notes"]:
                st.caption(n)
    coef = res["coef"]
    available = list(dict.fromkeys(coef["variable"]))
    main_vars = [v for v in ("Group involved", "Counterpart", "Group", "Region", "Road type", "Intersection", "Lighting") if v in available]
    shown_vars = st.multiselect("Variables to show in the chart", available, default=main_vars or available, key="mod_vars")
    st.markdown("**Adjusted odds ratios of a severe accident** (filled = significant at 5%; the reference category of each variable is 1)")
    page.chart("Odds ratios", tc.fig_forest(coef[coef["variable"].isin(shown_vars)] if shown_vars else coef))
    with st.expander("Odds ratio table", expanded=False):
        page.table("Odds ratios", coef[["term", "odds ratio", "OR low", "OR high", "p-value", "accidents", "events", "coefficient", "robust SE", "ordinary SE"]], decimals=3)
    if "predicted" in res:
        st.markdown("**Average adjusted predicted probability of a severe accident**")
        page.chart("Predicted probabilities", tc.fig_predicted(res["predicted"], list(dict.fromkeys(res["predicted"]["variable"]))[:4]))
        with st.expander("Predicted probability table"):
            page.table("Predicted probabilities", res["predicted"], decimals=2)
    st.markdown("**Calibration** (do predicted probabilities match what happened?)")
    page.chart("Calibration", tc.fig_calibration(res["calibration"], fit["AUC (in-sample)"]))
    page.table("Model fit", pd.DataFrame([fit]).T.reset_index().rename(columns={"index": "statistic", 0: "value"}), show=False)
    st.caption("Associations, not causes; speed, traffic, vehicle type and helmet use are not in the data. The class belongs to the whole accident. AUC is in-sample (the model was fitted on the same accidents).")
    return page
