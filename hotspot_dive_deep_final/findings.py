"""
The fixed 'Key findings' texts of the hotspot deep dive. The numbers come from the saved results (scripts 01 and 02); the build script of the HTML page and app.py use these same texts.
"""
FIXED_NOTE = "Fixed text for all vulnerable groups together, calculated once by the scripts; it does not change with the filters."
TOP_NOTE = "Text for all vulnerable groups together; it follows the Hotspots filter (top 20 or top 40) but not the other filters."

STEP_1A = [
    "Passenger cars (70.2% of all accidents) and bicycles (24.8%) are involved most often. Pedestrians follow at 10.3%, vans 8.1%, mopeds 8.0%, motorcycles 6.8%, trucks 4.4%, buses 1.4%.",
    "'Unknown' is 10.7%: for about one accident in ten the road user is not recorded.",
    "Shares add up to more than 100% because one accident can involve two groups (136,144 accidents involve two different groups).",
]
STEP_1B = [
    "Almost every group drops in 2020 (bicycles only -5.5%; buses -37.7% and pedestrians -30.4% most) and rebounds in 2021-2022.",
    "By 2024 (2017 = 100): bicycles 115, mopeds 105, vans and buses 97, pedestrians 86, motorcycles 83, passenger cars 82, trucks 73.",
    "Post vs pre (average per year 2022-2024 against 2017-2019): trucks -17.2%, motorcycles -12.9%, cars -12.2%, pedestrians -10.4%, buses -6.4%, vans +1.5%, mopeds +7.3%, bicycles +14.6%.",
    "'Unknown' more than doubles (+113% from 2017 to 2024). Part of the decline of the named groups may be recording shifting into 'Unknown'; the data cannot show that.",
]
CARE_1 = "Read with care: these are raw counts and 'Covid-19' is my own label for the periods. A group that is common on the road appears often for that reason alone; severity and traffic volume are not part of these graphs."

COVERAGE_NOTE = ("During Covid-19 (2020-2021) the located accidents per year fall from 14,705 to 13,006 and rise to 17,083 afterwards. Part of that rise is better coordinates: 15% of the accidents lacked coordinates before Covid-19, 17% during it and only 3.7% after it.")
SQUARES = "5 x 5 km squares"
V = "Vulnerable (any of the four)"
PRE, DURING, POST = "Pre Covid-19 (2017-2019)", "During Covid-19 (2020-2021)", "Post Covid-19 (2022-2024)"
GROUP_NAMES = {"Pedestrian": "pedestrians", "Bicycle": "cyclists", "Motorcycle": "motorcycles", "Moped": "mopeds"}


def heatmaps(top, top_n):
    """The findings of the heat-map views for the top 20 or the top 40 squares; `top` is results/hotspots_top40.csv. The numbers are calculated here, so the text follows the hotspot filter."""
    t = top[(top["size"] == SQUARES) & (top["rank"] <= top_n)]

    def cell(group, period, rank):
        r = t[(t["group"] == group) & (t["period"] == period) & (t["rank"] == rank)].iloc[0]
        return r["municipality"], r["per_year"]

    def kept(group):
        pre, post = (set(zip(d["cx"], d["cy"])) for d in (t[(t["group"] == group) & (t["period"] == PRE)], t[(t["group"] == group) & (t["period"] == POST)]))
        return len(pre & post)

    pre1, post1 = cell(V, PRE, 1), cell(V, POST, 1)
    third_pre, third_post = cell(V, PRE, 3)[0], cell(V, POST, 3)[0]
    return [
        f"Hotspots are in the big cities. With 5 x 5 km squares, the busiest square for vulnerable road users is in {pre1[0]} before Covid-19 ({pre1[1]:.0f} accidents a year) and in {post1[0]} after it ({post1[1]:.0f} a year); "
        + (f"{third_pre} is third in both periods." if third_pre == third_post else f"{third_pre} is third before Covid-19 and {third_post} third after it."),
        f"The hotspots hardly move: {kept(V)} of the {top_n} busiest squares before Covid-19 are still among the {top_n} busiest after it, for all four groups together ("
        + ", ".join(f"{kept(g)} of {top_n} for {name}" for g, name in GROUP_NAMES.items()) + ").",
        COVERAGE_NOTE,
    ]


def severity(summary, top_n):
    """The findings of the severity view for the top 20 or the top 40 squares; `summary` is load_summary(top_n)."""
    s = summary[summary["size"] == SQUARES]

    def pair(group, period, column):
        d = s[(s["group"] == group) & (s["period"] == period)].set_index("cells")
        return d.loc[f"{top_n} hotspot cells", column], d.loc["all other cells", column]

    allv = "All years (2017-2024)"
    (sh, so), (fh, fo) = pair(V, allv, "severe %"), pair(V, allv, "fatal %")
    per = {p: pair(V, p, "severe %") for p in (PRE, DURING, POST)}
    grp = {g: pair(g, allv, "severe %") for g in GROUP_NAMES}
    return [
        f"Accidents in the {top_n} hotspot squares are much less often severe than accidents elsewhere: {sh:.1f}% against {so:.1f}% (5 x 5 km squares, 2017-2024); the fatal share is {fh:.2f}% against {fo:.2f}%.",
        f"The same holds in every period: severe share {per[PRE][0]:.1f}% (pre), {per[DURING][0]:.1f}% (during) and {per[POST][0]:.1f}% (post) in the hotspots against {per[PRE][1]:.1f}%, {per[DURING][1]:.1f}% and {per[POST][1]:.1f}% in all other squares.",
        "It holds for every group: severe share in the hotspots against other squares is " + ", ".join(f"{grp[g][0]:.1f}% against {grp[g][1]:.1f}% for {name}" for g, name in GROUP_NAMES.items()) + ".",
    ]


def logit(lg):
    """The findings of the logistic regression for the top 20 or the top 40; `lg` is charts.load_logit(top_n)."""
    m, fit, adj, desc = lg["severity_model"].set_index("term"), lg["severity_fit"].iloc[0], lg["hotspot_adjusted"].iloc[0], lg["severity_descriptives"]

    def odds(term, ci=True):
        r = m.loc[term]
        return f"{r['odds ratio']:.2f} ({r['OR low']:.2f} to {r['OR high']:.2f})" if ci else f"{r['odds ratio']:.2f}"

    def clear(term):
        return m.loc[term, "p value"] < 0.05

    raw = desc[desc["variable"] == "Hotspot"].set_index("category")["severe %"]
    post, during, dawn = "period=" + POST, "period=" + DURING, "light=Dawn, dusk"
    return [
        f"Being in a hotspot square {'lowers' if m.loc['hotspot', 'odds ratio'] < 1 else 'raises'} the odds of a severe accident: odds ratio {m.loc['hotspot', 'odds ratio']:.2f} (95% interval {m.loc['hotspot', 'OR low']:.2f} to {m.loc['hotspot', 'OR high']:.2f}), with period, group, built-up area and light condition held equal. "
        f"Raw: {raw['Hotspot square']:.1f}% severe in hotspot squares against {raw['Not a hotspot square']:.1f}% elsewhere.",
        f"As percentage points: if every accident were in a hotspot square the model gives {adj['severe % if all in a hotspot']:.1f}% severe, if none were {adj['severe % if none in a hotspot']:.1f}%: "
        f"{abs(adj['difference (percentage points)']):.1f} points lower (95% interval {abs(adj['difference high']):.1f} to {abs(adj['difference low']):.1f}).",
        f"Outside built-up areas the odds of a severe accident are {odds('built_up=outside', False)} times those inside ({m.loc['built_up=outside', 'OR low']:.2f} to {m.loc['built_up=outside', 'OR high']:.2f}); "
        f"at night (public lighting or not) they are {odds('light=Night', False)} times those in daylight ({m.loc['light=Night', 'OR low']:.2f} to {m.loc['light=Night', 'OR high']:.2f}); "
        f"dawn and dusk {'differ from' if clear(dawn) else 'do not differ from'} daylight ({m.loc[dawn, 'odds ratio']:.2f}, {m.loc[dawn, 'OR low']:.2f} to {m.loc[dawn, 'OR high']:.2f}).",
        f"Against cyclists, motorcycles have {odds('group=Motorcycle', False)} times the odds ({m.loc['group=Motorcycle', 'OR low']:.2f} to {m.loc['group=Motorcycle', 'OR high']:.2f}), pedestrians {odds('group=Pedestrian')} and mopeds {odds('group=Moped')}. "
        f"After Covid-19 the odds are {odds(post, False)} times those before it ({m.loc[post, 'OR low']:.2f} to {m.loc[post, 'OR high']:.2f}); during Covid-19 they "
        f"{'differ' if clear(during) else 'do not differ clearly'} ({m.loc[during, 'odds ratio']:.2f}, {m.loc[during, 'OR low']:.2f} to {m.loc[during, 'OR high']:.2f}).",
        f"The model is simple and only moderately predictive (AUC {fit['AUC']:.2f}, McFadden R2 {fit['McFadden R2']:.3f}): it describes differences between groups of accidents and cannot say which single accident will be severe.",
    ]


def logit_care(top_n):
    return (f"Read with care: an odds ratio is not a risk ratio (severe accidents are 12% of the rows, so odds ratios look further from 1 than risk ratios). 'Hotspot' means a top-{top_n} square of the accident's own group and period, so it is a busy place, not a dangerous one. "
            "Speed, traffic volume and road layout are not in the data; the hotspot effect probably carries the lower speeds of city centres. One accident with two vulnerable groups is a row in both groups; standard errors are cluster-robust by municipality. Associations, not causes.")


RATES = [
    "Per resident, the picture changes: for all four groups the highest rates (per 100,000 residents per year, 2017-2024) are Brussel 384, Knokke-Heist 368, Wijnegem 349, Eeklo 321, Wommelgem 306 and Gent 304, against 148 for Belgium; Antwerpen, first by number of accidents (12,043), has 284.",
    "Only 9 of the 20 municipalities with most accidents are also among the 20 with the highest rate (15 for pedestrians, 9 for cyclists, 19 for motorcycles, 12 for mopeds).",
    "Cyclists: Knokke-Heist 233, Eeklo 222, Leuven 217, Sint-Niklaas 212 (Belgium 78). Pedestrians: Brussel 110, Sint-Gillis 88, Koekelberg 84 (Belgium 32). Motorcycles: Brussel 91, far above Elsene 42 (Belgium 22). Mopeds: Knokke-Heist 75, Brugge 64, Sint-Niklaas 61 (Belgium 25).",
    "The rate for all four groups together is 152 per 100,000 residents per year before Covid-19, 137 during it and 152 after it: after the pandemic the rate per resident is back to the level before it, so the 2022-2024 rise in counts is mostly population growth and better coordinates.",
]
CARE = ("Read with care: residents are not traffic. Municipalities that attract many visitors, commuters or tourists (Brussel, Knokke-Heist, Gent) get a high rate because the people involved do not all live there. "
        "Grid cells use only accidents with coordinates (89% of all, 85% before Covid-19, 96% after it, fewer in Wallonia); municipality rates use all accidents. Associations, not causes.")
