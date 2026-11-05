"""
The Streamlit pages for steps 2-4 (decisions #109-#113). They show SAVED results (#110): the figures come from dashboard_extra.py, which reads the
CSV files written by scripts 12-18. The years filter in the sidebar does not apply here, and every page says so.
"""
import streamlit as st

import dashboard_extra as extra

FIXED_NOTE = ("Fixed results from my analysis scripts, not recalculated here. The years filter in the sidebar does not apply to this tab; "
              "periods are chosen in the controls on this page where they exist.")


@st.cache_data
def results():
    return extra.load_results()


@st.cache_data
def outlines():
    return extra.load_outlines()


@st.cache_data
def provinces():
    return extra.load_provinces()


@st.cache_data
def hotspot_cells():
    return extra.load_hotspot_cells()


@st.cache_data
def positions():
    return extra.load_positions()


def plot(fig):
    st.plotly_chart(fig, width="stretch")


def findings(lines):
    with st.container(border=True):
        st.markdown("**Key findings**  \n*Fixed text for all years 2017-2024; it does not change with the controls.*")
        for line in lines:
            st.markdown(f"- {line}")


def table(df, name, caption=None):
    """A table with a CSV download button."""
    if caption:
        st.caption(caption)
    st.dataframe(df, hide_index=True, width="stretch")
    st.download_button("Download as CSV", df.to_csv(index=False).encode("utf-8"), file_name=f"{name}.csv", mime="text/csv", key=f"download_{name}")


# --------------------------------------------------------------------------------------
# Step 2
# --------------------------------------------------------------------------------------
def render_severity(tab):
    res = results()
    with tab:
        st.subheader("Who experiences the most severe outcomes?")
        st.caption(FIXED_NOTE + " The severity class belongs to the WHOLE accident, not to one road user: a car-pedestrian accident counts for both groups.")
        scope = st.radio("Period", list(extra.SCOPE_LABELS), format_func=extra.SCOPE_LABELS.get, horizontal=True, key="severity_scope",
                         help="Pre, during and post Covid-19 are my own period names; the data states no cause.")
        st.markdown("**Share of the group's accidents that are fatal, seriously injured or slightly injured** (dot = share, line = 95% interval, gray line = all accidents)")
        plot(extra.fig_severity_intervals(res, scope))
        st.markdown("**Severity distribution per group** (ordered by fatal share)")
        plot(extra.fig_severity_distribution(res, scope))
        findings([
            "Accidents involving trucks and motorcycles are the most severe: fatal plus serious makes up 17.3% (trucks) and 18.9% (motorcycles) of their accidents, against 9.9% for all accidents.",
            "The fatal share is 5.1% for trucks (3.6 times the 1.4% of all accidents), 2.8% for motorcycles and 2.0% for pedestrians. It is lowest for mopeds (0.6%), bicycles (0.9%) and passenger cars (1.3%).",
            "Bicycle accidents are less often fatal but more often seriously injured (10.0% against 8.4% overall); motorcycles have the highest serious share (16.2%).",
            "The fatal share of all accidents falls from 1.54% (2017-2019) to 1.47% (2020-2021) and 1.29% (2022-2024).",
        ])
        st.caption("Read with care: these are the severity of the accidents a group is part of, not the harm to that group's own members. A truck accident may be fatal mostly for the other party. "
                   "They are shares given that an accident happened, not the risk of having one. Intervals assume independent accidents, which is slightly optimistic because one accident can count for two groups.")
        with st.expander("Table"):
            a, b, c = (res[k][res[k]["scope"] == scope].set_index("road_user_group") for k in ("severity_a_fatal", "severity_b_serious", "severity_c_slight"))
            combined = a[["accidents", "count", "share_pct", "ci_low_pct", "ci_high_pct", "ratio_to_all", "gap_points"]].rename(columns={"count": "fatal", "share_pct": "fatal %", "ci_low_pct": "fatal low", "ci_high_pct": "fatal high", "ratio_to_all": "fatal ratio", "gap_points": "fatal gap"})
            combined["serious"], combined["serious %"] = b["count"], b["share_pct"]
            combined["slight"], combined["slight %"] = c["count"], c["share_pct"]
            table(combined.reset_index().round(2), f"severity_{scope}")


# --------------------------------------------------------------------------------------
# Step 3
# --------------------------------------------------------------------------------------
def render_geography(tab):
    res, outl = results(), outlines()
    with tab:
        st.subheader("Where are vulnerable road users most exposed?")
        st.caption(FIXED_NOTE + " Municipality outlines: Statbel statistical sectors 2023, CC BY 4.0 (outlines joined and simplified).")
        part_a, part_b = st.tabs(["3a  Cyclists by municipality", "3b/3c  Hotspots: pedestrians, motorcycles, mopeds"])
        with part_a:
            st.markdown("**Accidents involving cyclists, 2017-2024**")
            plot(extra.fig_cyclists_ranked(res))
            kind = st.radio("Map", ["Bubble map", "Choropleth (two maps)"], horizontal=True, key="cyclist_map")
            if kind == "Bubble map":
                st.caption("Each bubble sits at the average position of the municipality's accidents. Size = accidents involving cyclists; colour = cyclist share of all its accidents (5 quantile classes, municipalities with 100+ accidents).")
                plot(extra.fig_cyclists_bubble(res, outl, positions()))
            else:
                st.caption("Five classes with about the same number of municipalities each; the legend gives the exact limits. Gray = fewer than 100 accidents, not ranked by share.")
                plot(extra.fig_cyclists_choropleth(res, outl))
            findings([
                "71,881 accidents involve cyclists, in 577 of the 581 municipalities; cyclists are in 24.8% of all accidents.",
                "By count: Antwerpen 7,405 (37% of its accidents), Gent 4,229 (42%), Brussel 2,478 (25%), Leuven 1,773 (54%), Brugge 1,598 (37%).",
                "By share (municipalities with 100+ accidents): Haacht 56.2%, Mortsel 54.4%, Leuven 54.3%, Hove 50.4%, Keerbergen 49.0%.",
                "Cyclist share by region: Flanders 33.5%, Brussels 21.8%, Wallonia 7.0%. Wherever cyclists make up more than a third of the accidents, the municipality is in Flanders.",
            ])
            st.caption("Read with care: counts favour big cities and the data has no population or cycling-traffic figures, so these are not rates per inhabitant or per cyclist.")
            with st.expander("Table (all 581 municipalities)"):
                table(res["geo_a_cyclists_by_municipality"].round(2), "geo_cyclists_by_municipality")
        with part_b:
            c1, c2 = st.columns(2)
            group = c1.radio("Group", ["Pedestrian", "Motorcycle", "Moped"], horizontal=True, key="hotspot_group")
            scope = c2.radio("Years", ["2017-2024", "2022-2024"], horizontal=True, key="hotspot_scope", help="2022-2024 has the fewest missing coordinates.")
            cov = res["geo_coverage"]
            cov = cov[(cov["group"] == group) & (cov["scope"] == scope)].iloc[0]
            st.caption(f"{cov['with_coordinates']:,.0f} of {cov['accidents']:,.0f} accidents involving {group.lower()}s have usable coordinates ({100 - cov['left_out_pct']:.1f}%); the other {cov['left_out']:,.0f} are not on the map. "
                       "Heat map of accidents per 500 m square: zoom and pan; the 20 busiest squares are marked (hover for rank, municipality and counts).")
            plot(extra.fig_hotspots(res, hotspot_cells(), outl, group, scope))
            top = res[f"geo_hotspots_{group.lower()}"]
            top = top[top["scope"] == scope].drop(columns=["scope"]).round(2)
            findings([
                "Pedestrians: 17 of the top 20 squares are in the Brussels area, 2 in Antwerp and 1 in Liège; the busiest square (Antwerp) has 82 accidents, only 0.31% of all located pedestrian accidents.",
                "Motorcycles: all 20 busiest squares are in the Brussels area (busiest: 41 accidents).",
                "Mopeds: 12 of the top 20 squares are in Antwerp, 4 in Gent, 2 in Brussels, 1 in Charleroi and 1 in Knokke-Heist (busiest: 45 accidents).",
                "About two thirds of the hotspot squares come back in 2022-2024 (12, 16 and 12 of 20 for pedestrians, motorcycles and mopeds).",
            ])
            st.caption("Read with care: hotspots are where accidents are COUNTED, which is mostly where many people and vehicles are; there are no traffic or population figures. "
                       "10-13% of accidents have no coordinates (3-5% in 2022-2024), more in Wallonia, so Walloon hotspots may be understated. Different square sizes would give different ranks.")
            with st.expander(f"The 20 busiest squares: {group.lower()}s, {scope}"):
                table(top, f"hotspots_{group.lower()}_{scope}", "Rank = by accidents involving the group in the square. 'Municipality' = the most common municipality among the square's accidents.")


# --------------------------------------------------------------------------------------
# Step 4
# --------------------------------------------------------------------------------------
def render_regions(tab):
    res, prov = results(), provinces()
    with tab:
        st.subheader("Regional differences, concentration and severity")
        st.caption(FIXED_NOTE + " The severity class belongs to the whole accident. Concentration is where accidents are counted, not traffic.")
        part_a, part_b, part_c = st.tabs(["4a  Regional severity", "4b  Concentration vs severity", "4c  Regions within density"])
        with part_a:
            st.markdown("**Fatal and serious share per region and province, all accidents**")
            plot(extra.fig_regional_overview(res))
            st.markdown("**Province map**")
            plot(extra.fig_province_map(res, prov))
            st.markdown("**By road-user group**")
            plot(extra.fig_regional_groups(res))
            st.markdown("**Within each road type** (hollow dots = fewer than 100 accidents; they can run off the panel)")
            plot(extra.fig_regional_roadtype(res))
            findings([
                "Fatal share: Wallonia 2.26% (1.6 times Belgium), Flanders 1.23%, Brussels 0.42%. Serious-injury share goes the other way: Flanders 9.67%, Wallonia 7.16%, Brussels 4.45%.",
                "By province, the fatal share is highest in Luxembourg (3.37%), Namur (2.95%) and Hainaut (2.17%) and lowest in Antwerp (1.04%) and Brussels (0.42%); the serious share is highest in West Flanders (11.5%).",
                "The order Brussels < Flanders < Wallonia in fatal share holds for cyclists, pedestrians, motorcycles and mopeds.",
                "Wallonia has the higher fatal share on every road type: motorways 4.01% against 2.39% in Flanders, regional roads 2.54% against 1.22%, municipal roads 1.52% against 1.02%.",
            ])
            st.caption("Read with care: Flanders has more serious but fewer fatal accidents than Wallonia. That could be real or come from how the classes are recorded; I have not tested it. Matching road type controls for road type only.")
            with st.expander("Tables"):
                table(res["severity_regional_regions_provinces"].round(3), "severity_regions_provinces")
                table(res["severity_regional_roadtype"].round(3), "severity_regions_roadtype")
        with part_b:
            st.markdown("**By the number of accidents in the 500 m square** (accidents with coordinates; two periods)")
            plot(extra.fig_squares(res))
            st.markdown("**By municipality density** (five equal-sized classes of accidents per km2 per year)")
            plot(extra.fig_density_classes(res))
            st.markdown("**One dot per municipality** (rho = Spearman rank correlation between density and severity share)")
            plot(extra.fig_density_scatter(res))
            findings([
                "The busier the square, the less severe the accidents: for all accidents the fatal share falls from 3.00% in squares with one accident to 0.37% in squares with 100 or more; the serious share from 12.5% to 5.1%.",
                "The same direction holds for cyclists (fatal 1.93% to 0.17%), pedestrians (4.29% to 0.70%), motorcycles and mopeds, and in 2022-2024 as well.",
                "By municipality: the fatal share falls from 3.66% in the least dense fifth to 0.80% in the densest; Spearman rho is -0.66 for all accidents, -0.52 for motorcycles, -0.36 for pedestrians, -0.22 for cyclists and -0.15 for mopeds.",
                "The accident hotspots are therefore not the deadliest places: an isolated pedestrian accident is fatal in 4.3% of cases, one in a busy square in under 1%.",
            ])
            st.caption("Read with care: this is an association, not a cause. Dense places have lower speeds, other roads and more minor accidents, and density is accidents per km2, not per vehicle.")
            with st.expander("Tables"):
                table(res["severity_by_square_concentration"].round(3), "severity_by_square_concentration")
                table(res["severity_by_municipality_density"].round(3), "severity_by_municipality_density")
                table(res["severity_density_correlation"].round(4), "severity_density_correlation")
        with part_c:
            st.markdown("**Regions within the same density class, all accidents**")
            plot(extra.fig_within_density(res))
            st.markdown("**Per road-user group** (each group has its own density classes)")
            plot(extra.fig_within_density(res, extra.GROUPS5))
            st.markdown("**Within the same density class AND road type, all accidents**")
            plot(extra.fig_within_density_roadtype(res))
            st.markdown("**How much of the Wallonia-Flanders gap remains**")
            st.caption("Above 1 = Wallonia higher. Standardised ratio: Wallonia's share if it had Flanders' mix of strata. Odds ratio: logistic regression with bootstrap intervals (1,000 repetitions).")
            plot(extra.fig_gap_adjusted(res))
            findings([
                "At the same accident density Wallonia's fatal share stays 36-48% higher than Flanders' in every density class (ratio 1.48, 1.36, 1.36, 1.37 and 1.44); overall the ratio is 1.84.",
                "Adjusted odds ratio Wallonia vs Flanders, fatal: 1.86 (region only), 1.39 (same density class), 1.35 (also same road type; 95% interval 1.25-1.44). Density and road type explain more than half of the excess; roughly 40% of it remains.",
                "The serious-injury gap goes the other way and widens when matched: odds ratio 0.72 crude and 0.60 at the same density and road type.",
                "By group (fatal, density + road type): mopeds 1.70 (gap remains), pedestrians 1.23 and motorcycles 1.21 (borderline), cyclists 0.69 (no gap; the standardised ratio's interval includes 1, so I treat it as 'no clear gap').",
            ])
            st.caption("Read with care: density and road type are the only things matched; speed limits, vehicle mix, enforcement, emergency response and how classes are recorded are not. Brussels is only in the densest class.")
            with st.expander("Tables"):
                table(res["severity_regions_standardised"].round(3), "severity_regions_standardised")
                table(res["severity_regions_logistic"].round(3), "severity_regions_logistic")
                table(res["severity_regions_within_density"].round(3), "severity_regions_within_density")


# --------------------------------------------------------------------------------------
# Step 5: the saved logistic models
# --------------------------------------------------------------------------------------
def render_models(tab):
    res = results()
    with tab:
        st.subheader("Logistic models of accident severity (saved study results)")
        st.caption(FIXED_NOTE + " Severe = fatal, fatally injured or seriously injured. Standard errors are clustered by municipality. The models are fixed; to estimate a model on your own selection use 'Statistical models' in the analysis menu.")
        fit = res["severity_logit_fit"]
        fit = fit[fit["spec"] == "full"].set_index("model")[["accidents", "events", "event_rate_pct", "parameters", "mcfadden_r2", "aic", "auc", "icc_outcome", "icc_residual", "median_se_ratio_robust_to_ordinary"]].round(3)
        st.dataframe(fit.rename(columns={"event_rate_pct": "severe %", "mcfadden_r2": "McFadden R2", "auc": "AUC (in-sample)", "icc_outcome": "ICC outcome", "icc_residual": "ICC residuals",
                                         "median_se_ratio_robust_to_ordinary": "robust / ordinary SE"}), width="stretch")
        view = st.radio("Show", ["Region, road type, intersection, lighting", "Weather and road surface", "Year and month", "Collision type", "The road users in the accident",
                                 "Predicted probabilities", "Four typical situations", "Calibration", "Interactions between road users"], key="study_models_view")
        if view.startswith("Region"):
            plot(extra.fig_logit_forest(res, ["Region", "Road type", "Intersection", "Lighting"]))
        elif view.startswith("Weather"):
            plot(extra.fig_logit_forest(res, ["Weather", "Road surface"]))
        elif view.startswith("Year"):
            plot(extra.fig_logit_forest(res, ["Year", "Month"]))
        elif view.startswith("Collision"):
            plot(extra.fig_logit_forest(res, ["Collision type"]))
        elif view.startswith("The road users"):
            plot(extra.fig_logit_roadusers(res))
        elif view.startswith("Predicted"):
            plot(extra.fig_logit_predicted(res))
        elif view.startswith("Four"):
            plot(extra.fig_logit_scenarios(res))
        elif view.startswith("Calibration"):
            plot(extra.fig_logit_calibration(res))
        else:
            plot(extra.fig_logit_interactions(res))
        findings([
            "Baseline model (289,532 accidents, 28,532 severe): odds of a severe accident are 3.44 times higher with a motorcycle involved and 3.32 times higher with a pedestrian (against a car-only accident), 2.94 with a truck and 1.77 with a bicycle.",
            "Night without public lighting raises the odds (1.78 in the baseline; 2.04 for pedestrians and 2.01 for motorcyclists); Brussels has much lower odds than Flanders in every model (0.29 to 0.41), Wallonia somewhat lower (0.74 to 0.81).",
            "In the group models a truck as counterpart is the strongest risk factor (odds 5.22 for pedestrians, 4.26 for cyclists, 2.63 for mopeds, 2.26 for motorcyclists, against a passenger car).",
            "Accidents in the same municipality are correlated (ICC 0.016 in the baseline); the cluster-robust standard errors are on average 11% larger in the baseline and up to 3.8 times larger for region-level terms.",
            "The road users in one accident do not simply add up: 22 pairs were tested jointly (p < 10^-180). Bicycle + pedestrian is far less severe than the two effects added (0.33), car + motorcycle more severe (1.48); the order of road user 1 and 2 also matters (p = 2 x 10^-9), but their meaning is undocumented.",
            "Predicted probabilities in a daytime urban situation in 2024: car-only accident 5.1%, bicycle against a car 8.6%, pedestrian 15.0%, motorcycle 15.5%.",
        ])
        st.caption("Read with care: these are associations, not causes; speed, traffic, vehicle type and helmet use are not in the data. The class belongs to the whole accident. AUC is in-sample. "
                   "'With a pedestrian' (collision type) is 99% the same as the pedestrian road-user term and is left out of the models; without collision type the pedestrian odds ratio is 2.54 instead of 3.32.")
        with st.expander("Tables"):
            coef = res["severity_logit_coefficients"]
            model = st.selectbox("Model", extra.MODELS5, key="study_models_table")
            table(coef[(coef["model"] == model) & (coef["spec"] == "full")][["term", "odds_ratio", "or_ci_low", "or_ci_high", "p_value", "accidents", "events"]].round(4), f"logit_{model.lower()}_odds_ratios")
            table(res["severity_logit_interactions_tests"].round(4), "logit_interaction_tests")
