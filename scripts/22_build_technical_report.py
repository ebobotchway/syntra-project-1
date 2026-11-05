"""
Step 22 - Build the full technical report of steps 1-5 (reports/findings_technical_report_steps_1_5.md).

The text is written here; every TABLE is read from the saved result tables in reports/*.csv, so no number in a table is typed by hand.
Numbers in the running text were checked against these tables (see the checks at the end of this script, which stop the build if a quoted number differs).

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/22_build_technical_report.py reports
"""
import sys
from pathlib import Path

import pandas as pd

reports = Path(sys.argv[1])
read = lambda name: pd.read_csv(reports / f"{name}.csv")


def md(df, formats=None):
    """A DataFrame as a Markdown table; formats = {column: format string}."""
    formats = formats or {}
    lines = ["| " + " | ".join(df.columns) + " |", "|" + "|".join("---" for _ in df.columns) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in df.columns:
            v = r[c]
            if not pd.isna(v) and isinstance(v, float) and v == int(v) and c not in formats:
                v = int(v)  # iterrows turns whole numbers into floats when a row mixes types
            if not pd.isna(v) and c in formats and isinstance(v, float) and formats[c].endswith("f}"):
                v = v + (1e-9 if v >= 0 else -1e-9)  # round half up (the float 0.365 would otherwise print as 0.36)
            cells.append("" if pd.isna(v) else (formats[c].format(v) if c in formats else (f"{v:,}" if isinstance(v, int) else str(v))))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


T = {}
# --- step 1 ---
tot = read("accidents_per_road_user")
tot = tot.assign(percent_of_all_accidents=tot["accidents"] / 289532 * 100 + 1e-9)  # from the counts, so 12,595 / 289,532 = 4.35% rounds to 4.4% (the saved column is already rounded)
T["step1_totals"] = md(tot.rename(columns={"road_user_group": "Road-user group", "accidents": "Accidents", "percent_of_all_accidents": "% of all accidents"})[["Road-user group", "Accidents", "% of all accidents"]],
                       {"Accidents": "{:,.0f}", "% of all accidents": "{:.1f}%"})
ann = read("annual_accidents_by_group").set_index("road_user_group")
per = read("annual_periods").set_index("road_user_group")
years = [str(y) for y in range(2017, 2025)]
a1 = ann[years].copy()
a1["Index 2024 (2017 = 100)"] = a1["2024"] / a1["2017"] * 100
a1["Post vs pre (avg/yr)"] = per["avg_diff_pct_post_vs_pre"]
order = [g for g in tot["road_user_group"] if g in a1.index]
T["step1_annual"] = md(a1.loc[order].reset_index().rename(columns={"road_user_group": "Group"}), {**{y: "{:,.0f}" for y in years}, "Index 2024 (2017 = 100)": "{:.0f}", "Post vs pre (avg/yr)": "{:+.1f}%"})
# --- step 2 ---
d = read("severity_d_distribution")
d = d[d["scope"] == "pooled_2017_2024"].copy()
fa = read("severity_a_fatal")
fa = fa[fa["scope"] == "pooled_2017_2024"].set_index("road_user_group")
d["fatal 95% interval"] = [f"{fa.loc[g, 'ci_low_pct']:.2f}-{fa.loc[g, 'ci_high_pct']:.2f}%" for g in d["road_user_group"]]
d["Fatal + serious"] = d["fatal_total_pct"] + d["seriously_injured_class3_pct"]
t2 = d.rename(columns={"road_user_group": "Group", "accidents": "Accidents", "fatal_total_pct": "Fatal (class 1+2)", "seriously_injured_class3_pct": "Seriously injured (class 3)",
                       "slightly_injured_class4_pct": "Slightly injured (class 4)"})[["Group", "Accidents", "Fatal (class 1+2)", "fatal 95% interval", "Seriously injured (class 3)", "Slightly injured (class 4)", "Fatal + serious"]]
T["step2"] = md(t2, {"Accidents": "{:,.0f}", "Fatal (class 1+2)": "{:.2f}%", "Seriously injured (class 3)": "{:.2f}%", "Slightly injured (class 4)": "{:.2f}%", "Fatal + serious": "{:.1f}%"})
# --- step 3 ---
mu = read("geo_a_cyclists_by_municipality")
top = mu.sort_values("accidents_cyclists", ascending=False).head(10)[["municipality", "region", "accidents_total", "accidents_cyclists", "cyclist_share_pct"]]
T["step3_top"] = md(top.rename(columns={"municipality": "Municipality", "region": "Region", "accidents_total": "All accidents", "accidents_cyclists": "Involving cyclists", "cyclist_share_pct": "Cyclist share"}),
                    {"All accidents": "{:,.0f}", "Involving cyclists": "{:,.0f}", "Cyclist share": "{:.1f}%"})
share = mu[mu["ranked_by_share"]].sort_values("cyclist_share_pct", ascending=False).head(5)[["municipality", "region", "accidents_total", "cyclist_share_pct"]]
T["step3_share"] = md(share.rename(columns={"municipality": "Municipality", "region": "Region", "accidents_total": "All accidents", "cyclist_share_pct": "Cyclist share"}), {"All accidents": "{:,.0f}", "Cyclist share": "{:.1f}%"})
# --- step 4 ---
rp = read("severity_regional_regions_provinces")
rp = rp[(rp["group"] == "All accidents") & rp["level"].isin(["Belgium", "Region", "Province"])].copy()
rp["fatal_share_pct"], rp["serious_share_pct"] = rp["fatal_count"] / rp["accidents"] * 100, rp["serious_count"] / rp["accidents"] * 100  # from the counts: the saved shares are already rounded
T["step4_regions"] = md(rp[["level", "area", "accidents", "fatal_share_pct", "serious_share_pct"]].rename(columns={"level": "Level", "area": "Area", "accidents": "Accidents", "fatal_share_pct": "Fatal share", "serious_share_pct": "Serious share"}),
                        {"Accidents": "{:,.0f}", "Fatal share": "{:.2f}%", "Serious share": "{:.2f}%"})
sq = read("severity_by_square_concentration")
sq = sq[(sq["group"] == "All accidents") & (sq["scope"] == "2017-2024")].copy()
sq["fatal_share_pct"], sq["serious_share_pct"] = sq["fatal_count"] / sq["accidents"] * 100, sq["serious_count"] / sq["accidents"] * 100
T["step4_squares"] = md(sq[["square_class", "accidents", "fatal_share_pct", "serious_share_pct"]].rename(columns={"square_class": "Accidents in the 500 m square", "accidents": "Accidents", "fatal_share_pct": "Fatal share", "serious_share_pct": "Serious share"}),
                        {"Accidents": "{:,.0f}", "Fatal share": "{:.2f}%", "Serious share": "{:.2f}%"})
de = read("severity_by_municipality_density")
de = de[de["group"] == "All accidents"].copy()
de["fatal_share_pct"], de["serious_share_pct"] = de["fatal_count"] / de["accidents"] * 100, de["serious_count"] / de["accidents"] * 100
T["step4_density"] = md(de[["density_class", "municipalities", "accidents", "fatal_share_pct", "serious_share_pct"]].rename(columns={"density_class": "Density class (1 = least dense)", "municipalities": "Municipalities", "accidents": "Accidents", "fatal_share_pct": "Fatal share", "serious_share_pct": "Serious share"}),
                        {"Accidents": "{:,.0f}", "Fatal share": "{:.2f}%", "Serious share": "{:.2f}%"})
co = read("severity_density_correlation")
co = co[co["indicator"] == "fatal"]
T["step4_rho"] = md(co[["group", "municipalities_used", "spearman_rho"]].rename(columns={"group": "Group", "municipalities_used": "Municipalities (100+ accidents)", "spearman_rho": "Spearman rho (density vs fatal share)"}), {"spearman_rho" if False else "Spearman rho (density vs fatal share)": "{:.2f}"})
lg = read("severity_regions_logistic")
lg = lg[(lg["group"] == "All accidents") & (lg["term"] == "Wallonia vs Flanders")]
T["step4_logit"] = md(lg[["outcome", "model", "odds_ratio", "ci_low", "ci_high"]].rename(columns={"outcome": "Outcome", "model": "Model", "odds_ratio": "Odds ratio", "ci_low": "95% low", "ci_high": "95% high"}),
                      {"Odds ratio": "{:.2f}", "95% low": "{:.2f}", "95% high": "{:.2f}"})
# --- step 5 ---
fit = read("severity_logit_fit")
f5 = fit[fit["spec"] == "full"][["model", "accidents", "events", "event_rate_pct", "parameters", "mcfadden_r2", "aic", "auc", "icc_outcome", "icc_residual", "median_se_ratio_robust_to_ordinary", "max_se_ratio"]]
T["step5_fit"] = md(f5.rename(columns={"model": "Model", "accidents": "Accidents", "events": "Severe", "event_rate_pct": "Severe %", "parameters": "Parameters", "mcfadden_r2": "McFadden R2", "aic": "AIC", "auc": "AUC",
                                       "icc_outcome": "ICC outcome", "icc_residual": "ICC residual", "median_se_ratio_robust_to_ordinary": "Median SE ratio", "max_se_ratio": "Max SE ratio"}),
                    {"Accidents": "{:,.0f}", "Severe": "{:,.0f}", "Severe %": "{:.1f}", "Parameters": "{:.0f}", "McFadden R2": "{:.3f}", "AIC": "{:,.0f}", "AUC": "{:.3f}", "ICC outcome": "{:.3f}", "ICC residual": "{:.3f}", "Median SE ratio": "{:.2f}", "Max SE ratio": "{:.2f}"})
co5 = read("severity_logit_coefficients")
co5 = co5[co5["spec"] == "full"]
models = ["Baseline", "Cyclists", "Pedestrians", "Motorcyclists", "Mopeds"]
terms = ["Region: Brussels-Capital Region", "Region: Walloon Region", "Road type: Motorway", "Road type: Regional road", "Intersection: At intersection", "Lighting: Night, no public lighting",
         "Lighting: Night, public lighting present and lit", "Weather: Rain", "Road surface: Wet, puddles", "Year: 2020", "Year: 2024", "Month: Jun", "Month: Dec"]
rows = []
for t in terms:
    row = {"Term": t}
    for m in models:
        r = co5[(co5["model"] == m) & (co5["term"] == t)]
        row[m] = "-" if r.empty else f"{r.iloc[0]['odds_ratio']:.2f}{'*' if r.iloc[0]['p_value'] < 0.05 else ''} ({r.iloc[0]['or_ci_low']:.2f}-{r.iloc[0]['or_ci_high']:.2f})"
    rows.append(row)
T["step5_or"] = md(pd.DataFrame(rows))
base_users = [t for t in co5[(co5["model"] == "Baseline") & (co5["variable"] == "Group involved")]["term"]]
T["step5_users"] = md(pd.DataFrame([{"Group involved": t.split(": ", 1)[1], "Odds ratio (vs car-only)": f"{co5[(co5.model == 'Baseline') & (co5.term == t)].iloc[0]['odds_ratio']:.2f}",
                                     "95% interval": f"{co5[(co5.model == 'Baseline') & (co5.term == t)].iloc[0]['or_ci_low']:.2f}-{co5[(co5.model == 'Baseline') & (co5.term == t)].iloc[0]['or_ci_high']:.2f}"} for t in base_users]))
cps = sorted(set(co5[co5["variable"] == "Counterpart"]["term"]))
rows = []
for t in cps:
    row = {"Counterpart": t.split(": ", 1)[1]}
    for m in models[1:]:
        r = co5[(co5["model"] == m) & (co5["term"] == t)]
        row[m] = "-" if r.empty else f"{r.iloc[0]['odds_ratio']:.2f}{'*' if r.iloc[0]['p_value'] < 0.05 else ''}"
    rows.append(row)
T["step5_counterpart"] = md(pd.DataFrame(rows))
wd = read("severity_logit_interactions_tests")
T["step5_wald"] = md(wd.rename(columns={"spec": "Specification", "test": "Test", "terms": "Terms", "wald_chi2": "Wald chi-square", "p_value": "p-value"})[["Specification", "Test", "Terms", "Wald chi-square", "p-value"]],
                     {"Wald chi-square": "{:.1f}", "p-value": "{:.1e}"})  # the saved AIC columns are rounded to 5 significant digits, so the AIC values are quoted from the run in the text
pr = read("severity_logit_interactions_pairs")
pr = pr[pr["spec"] == "full"].pivot_table(index=["pair", "accidents", "severe_pct"], columns="version", values="odds_ratio_vs_car_only").reset_index().sort_values("accidents", ascending=False).head(10)
T["step5_pairs"] = md(pr.rename(columns={"pair": "Pair", "accidents": "Accidents", "severe_pct": "Severe %", "additive (baseline model)": "Additive (baseline)", "with the pair's own effect": "With pair effect", "interaction term (ratio of odds ratios)": "Pair term"})[["Pair", "Accidents", "Severe %", "Additive (baseline)", "With pair effect", "Pair term"]],
                      {"Accidents": "{:,.0f}", "Severe %": "{:.1f}", "Additive (baseline)": "{:.2f}", "With pair effect": "{:.2f}", "Pair term": "{:.2f}"})
sc = read("severity_logit_scenarios")
sc["text"] = [("n/a" if pd.isna(a) else f"{a:.1f}% ({b:.1f}-{c:.1f})") for a, b, c in zip(sc["predicted_pct"], sc["ci_low_pct"], sc["ci_high_pct"])]
sc["row"] = sc["model"] + " - " + sc["evaluated_as"]
sw = sc.pivot(index="row", columns="scenario", values="text").loc[list(dict.fromkeys(sc["row"]))].reset_index().rename(columns={"row": "Model - evaluated as"})
T["step5_scen"] = md(sw)
wo = read("severity_logit_roaduser_with_without_collision")
wo = wo[wo["model"] == "Baseline"][["term", "full", "no_collision", "change_pct"]].dropna()
T["step5_withwithout"] = md(wo.rename(columns={"term": "Term", "full": "With collision type", "no_collision": "Without", "change_pct": "Change"}), {"With collision type": "{:.2f}", "Without": "{:.2f}", "Change": "{:+.0f}%"})

# --- checks: numbers quoted in the text must match the tables ---
assert abs(tot.set_index("road_user_group").loc["Passenger car", "percent_of_all_accidents"] - 70.17) < 0.01
assert fit[(fit.spec == "full") & (fit.model == "Baseline")].iloc[0]["events"] == 28532
assert abs(co5[(co5.model == "Baseline") & (co5.term == "Group involved: Motorcycle")].iloc[0]["odds_ratio"] - 3.44) < 0.005
assert abs(co5[(co5.model == "Pedestrians") & (co5.term == "Counterpart: Truck")].iloc[0]["odds_ratio"] - 5.22) < 0.005
assert abs(lg[(lg["model"] == "+ density class + road type") & (lg["outcome"] == "fatal")].iloc[0]["odds_ratio"] - 1.35) < 0.005
assert abs(sq.iloc[0]["fatal_share_pct"] - 3.00) < 0.005 and abs(sq.iloc[-1]["fatal_share_pct"] - 0.37) < 0.01
assert abs(de.iloc[0]["fatal_share_pct"] - 3.66) < 0.005 and abs(de.iloc[-1]["fatal_share_pct"] - 0.80) < 0.005
assert abs(co.set_index("group").loc["All accidents", "spearman_rho"] + 0.66) < 0.005

text = open(Path(__file__).with_name("22_technical_report_text.md"), encoding="utf-8").read()
for key, table in T.items():
    assert f"{{{{{key}}}}}" in text, f"placeholder {key} missing in the text"
    text = text.replace(f"{{{{{key}}}}}", table)
assert "{{" not in text, "an unfilled placeholder remains"
(reports / "findings_technical_report_steps_1_5.md").write_text(text, encoding="utf-8")
print(f"Saved reports/findings_technical_report_steps_1_5.md: {len(text.split()):,} words, {len(T)} tables from the saved results.")
