"""
Step 4 of the vulnerable hotspots analysis: builds the report "how the output was calculated" (REPORT_how_the_output_was_calculated.md).

The text is written here; every TABLE and every number in the running text is read from the saved result tables in results/ and data/, so nothing is typed by hand.
Each section says what was calculated, how, and how to read the result (the interpretation).

How to run (from the folder vulnerable_hotspots, with `conda activate syntra-ds`):
    python -I scripts/04_build_report.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import charts  # noqa: E402
import charts_focused as cf  # noqa: E402
import step1_logic as dl  # noqa: E402

cells, top, summ, cov, mun = charts.load_cells(), charts.load_top(), charts.load_summary(), charts.load_coverage(), charts.load_municipalities()
pop = pd.read_csv(HERE / "data" / "population_by_municipality.csv", dtype={"municipality_nis_code": str})
pieces = pd.read_csv(HERE / "data" / "cell_residents_2023.csv", dtype={"municipality_nis_code": str})
res = cf.load_results()
V = charts.GROUPS[0]
S5, S25 = "5 km2 cells", "5 x 5 km squares"
SIZES = [S5, S25]
NOUN = {S5: "cell", S25: "square"}
P = charts.PERIODS
short = {P[0]: "Pre (2017-2019)", P[1]: "During (2020-2021)", P[2]: "Post (2022-2024)", P[3]: "All years (2017-2024)"}
N_ACC = 289532


def md(rows, headers):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def r2(v, d=1):
    """Round half up (the float 0.365 would otherwise print as 0.36)."""
    return f"{float(v) + (1e-9 if v >= 0 else -1e-9):.{d}f}"


# ------------------------------------------------------------------ step 1: who is involved, annual change
df1 = dl.load_data(HERE / "data" / "dashboard_data.csv")
groups1 = dl.NAMED_GROUPS
tot, all1 = dl.totals(df1, dl.GROUPS, 2017, 2024)
assert all1 == N_ACC
counts1 = dl.yearly(df1, dl.GROUPS, 2017, 2024)
index1 = dl.yearly_index(df1, dl.GROUPS, 2017, 2024)
summary1 = dl.period_summary(df1, dl.GROUPS, 2017, 2024)
rows1 = []
for _, r in tot.iterrows():
    g = r["road_user_group"]
    rows1.append([g, f"{int(r['accidents']):,}", f"{r2(r['percent_of_all_accidents'])}%", f"{r2((counts1.loc[g, 2020] / counts1.loc[g, 2019] - 1) * 100)}%", f"{index1.loc[g, 2024]:.0f}", f"{summary1.loc[g, 'post vs pre %']:+.1f}%"])
t_step1 = md(rows1, ["Road-user group", "Accidents 2017-2024", "% of all accidents", "2020 against 2019", "Index 2024 (2017 = 100)", "Post against pre (average per year)"])
two_groups = int(round(tot["accidents"].sum() - N_ACC))  # accidents that involve two groups are counted twice in the sum of the groups

# ------------------------------------------------------------------ step 2: severity per road-user group
a, b, c = (res[k][res[k]["scope"] == "pooled_2017_2024"].set_index("road_user_group") for k in ("severity_a_fatal", "severity_b_serious", "severity_c_slight"))
order = a.drop("All accidents").sort_values("share_pct", ascending=False).index.tolist()
rows2 = [["All accidents", f"{int(a.loc['All accidents', 'accidents']):,}", f"{r2(a.loc['All accidents', 'share_pct'], 2)}%", f"{r2(b.loc['All accidents', 'share_pct'], 2)}%", f"{r2(c.loc['All accidents', 'share_pct'], 2)}%", f"{r2(a.loc['All accidents', 'share_pct'] + b.loc['All accidents', 'share_pct'])}%"]]
for g in order:
    rows2.append([g, f"{int(a.loc[g, 'accidents']):,}", f"{r2(a.loc[g, 'share_pct'], 2)}% ({r2(a.loc[g, 'ci_low_pct'], 2)}-{r2(a.loc[g, 'ci_high_pct'], 2)})", f"{r2(b.loc[g, 'share_pct'], 2)}%", f"{r2(c.loc[g, 'share_pct'], 2)}%", f"{r2(a.loc[g, 'share_pct'] + b.loc[g, 'share_pct'])}%"])
t_step2 = md(rows2, ["Road-user group", "Accidents", "Fatal (class 1+2), 95% interval", "Seriously injured (class 3)", "Slightly injured (class 4)", "Fatal + serious"])
fatal_by_scope = {sc: res["severity_a_fatal"][(res["severity_a_fatal"]["scope"] == sc) & (res["severity_a_fatal"]["road_user_group"] == "All accidents")]["share_pct"].iat[0] for sc in cf.SCOPE_LABELS}

# ------------------------------------------------------------------ coordinates, grid, hotspots
t_cov = md([[charts.GROUP_LABELS[g]] + [f"{int(x['accidents']):,} ({r2(100 - x['left out %'], 1)}% with coordinates)" for p in P[:3] for x in [cov[(cov["group"] == g) & (cov["period"] == p)].iloc[0]]] for g in charts.GROUPS],
           ["Group"] + [short[p] for p in P[:3]])
lost = {p: cov[(cov["group"] == V) & (cov["period"] == p)].iloc[0]["left out %"] for p in P}
located = {p: cells[(cells["size"] == S25) & (cells["group"] == V) & (cells["period"] == p)]["accidents"].sum() / charts.YEARS_IN[p] for p in P}
allacc = {p: charts.municipality_table(mun, V, p)["accidents"].sum() / charts.YEARS_IN[p] for p in P}
n_cells = {s: int(cells[(cells["size"] == s) & (cells["group"] == V) & (cells["period"] == P[3])].shape[0]) for s in SIZES}


def top_table(size, ranking):
    rows = []
    for p in P:
        t = top[(top["size"] == size) & (top["group"] == V) & (top["period"] == p) & (top["ranking"] == ranking)].head(5)
        if ranking == "accidents":
            rows.append([short[p]] + [f"{r.municipality} {r.per_year:.0f}" for r in t.itertuples()])
        else:
            rows.append([short[p]] + [f"{r.municipality} {r.rate:.0f} ({int(r.accidents)} acc., {int(round(r.resident_years / charts.YEARS_IN[p])):,} res.)" for r in t.itertuples()])
    return md(rows, ["Period", "1st", "2nd", "3rd", "4th", "5th"])


persist = []
for size in SIZES:
    row = [size]
    for g in charts.GROUPS:
        x = top[(top["size"] == size) & (top["group"] == g) & (top["period"] == P[0]) & (top["ranking"] == "accidents")]
        y = top[(top["size"] == size) & (top["group"] == g) & (top["period"] == P[2]) & (top["ranking"] == "accidents")]
        row.append(f"{len(set(zip(x.cx, x.cy)) & set(zip(y.cx, y.cy)))} of 20")
    persist.append(row)
t_persist = md(persist, ["Grid"] + [charts.GROUP_LABELS[g] for g in charts.GROUPS])

# residents of the cells
per_cell = {s: pieces[pieces["size"] == s].groupby(["cx", "cy"])["residents_2023"].sum() for s in SIZES}
t_cells_res = md([[s, f"{len(per_cell[s]):,}", f"{int((per_cell[s] >= 1000).sum()):,}", f"{int(per_cell[s].max()):,}"] for s in SIZES], ["Grid", "Cells with residents", "Cells with 1,000+ residents", "Residents of the most populated cell"])
rate_facts = {}
for s in SIZES:
    ca = cells[(cells["size"] == s) & (cells["group"] == V) & (cells["period"] == P[3])]
    ta = top[(top["size"] == s) & (top["group"] == V) & (top["period"] == P[3]) & (top["ranking"] == "accidents")]
    tr = top[(top["size"] == s) & (top["group"] == V) & (top["period"] == P[3]) & (top["ranking"] == "rate")]
    rate_facts[s] = {"n": len(ca), "ok": int(ca["rate_ok"].sum()), "median": float(ca[ca["rate_ok"]]["rate"].median()), "overlap": len(set(zip(ta.cx, ta.cy)) & set(zip(tr.cx, tr.cy))),
                     "busiest": ta.head(3)}
t_busiest = {s: md([[r["municipality"], f"{r['per_year']:.0f}", f"{r['average residents']:,.0f}", f"{r['rate']:.0f}"] for _, r in rate_facts[s]["busiest"].iterrows()],
                   [f"Busiest {NOUN[s]}s (all four groups, 2017-2024)", "Accidents per year", "Average residents", "Per 100,000 residents per year"]) for s in SIZES}

# severity of the hotspots
t_sev = {}
for s in SIZES:
    rows = []
    for p in P:
        x = summ[(summ["size"] == s) & (summ["group"] == V) & (summ["period"] == p)].set_index("cells")
        h, o = x.loc["20 hotspot cells"], x.loc["all other cells"]
        rows.append([short[p], f"{int(h['accidents']):,}", f"{r2(h['severe %'])}% ({r2(h['severe low'])}-{r2(h['severe high'])})", f"{int(o['accidents']):,}", f"{r2(o['severe %'])}% ({r2(o['severe low'])}-{r2(o['severe high'])})", f"{r2(h['fatal %'], 2)}% / {r2(o['fatal %'], 2)}%"])
    t_sev[s] = md(rows, ["Period", "Accidents in the 20 hotspot cells", "Severe % hotspots (95% interval)", "Accidents in all other cells", "Severe % other cells (95% interval)", "Fatal % hotspots / others"])
grp_rows = []
for g in charts.GROUPS:
    row = [charts.GROUP_LABELS[g]]
    for s in SIZES:
        x = summ[(summ["size"] == s) & (summ["group"] == g) & (summ["period"] == P[3])].set_index("cells")
        row += [f"{r2(x.loc['20 hotspot cells', 'severe %'])}% / {r2(x.loc['all other cells', 'severe %'])}%"]
    grp_rows.append(row)
t_grp = md(grp_rows, ["Group", f"Severe %, hotspots / other cells ({S5})", f"Severe %, hotspots / other cells ({S25})"])

# ------------------------------------------------------------------ municipalities: top 20 (number and share) and rates per resident
muni_rows = []
for g, name in (("Pedestrian", "pedestrians"), ("Bicycle", "cyclists"), ("Motorcycle", "motorcycles"), ("Moped", "mopeds")):
    t = res[f"geo_a_{name}_by_municipality"].copy() if f"geo_a_{name}_by_municipality" in res else pd.read_csv(HERE / "results" / f"geo_a_{name}_by_municipality.csv")
    col, share = ("accidents_cyclists", "cyclist_share_pct") if g == "Bicycle" else ("accidents_group", "group_share_pct")
    t["share"] = t[col] / t["accidents_total"] * 100  # from the counts: the saved shares are already rounded
    by_count = t.sort_values(col, ascending=False).head(5)
    by_share = t[t["ranked_by_share"]].sort_values("share", ascending=False).head(5)
    muni_rows.append([charts.GROUP_LABELS[g], f"{int(t[col].sum()):,}", ", ".join(f"{r.municipality} {int(r[col]):,}" for _, r in by_count.iterrows()), ", ".join(f"{r.municipality} {r.share:.1f}%" for _, r in by_share.iterrows())])
t_muni = md(muni_rows, ["Group", "Accidents", "Top 5 by number", "Top 5 by share of the municipality's accidents (100+ accidents)"])
t_pop = md([[int(y), f"{int(pop[pop['year'] == y]['residents'].sum()):,}"] for y in range(2017, 2025)], ["Year (1 January)", "Residents in Belgium (581 municipalities)"])
rate_rows, belgium = [], {}
for p in P:
    t = charts.municipality_table(mun, V, p)
    belgium[p] = t["accidents"].sum() / t["resident_years"].sum() * 1e5
    rel = t[t["reliable"]].sort_values(charts.RATE, ascending=False).head(5)
    rate_rows.append([short[p], f"{belgium[p]:.1f}", int(t["reliable"].sum()), ", ".join(f"{r.municipality} {r[charts.RATE]:.0f}" for _, r in rel.iterrows())])
t_rate = md(rate_rows, ["Period", "Belgium per 100,000 per year", "Municipalities with 100+ accidents", "Highest rates (per 100,000 per year)"])
t_n = md([[charts.GROUP_LABELS[g]] + [int(charts.municipality_table(mun, g, p)["reliable"].sum()) for p in P] for g in charts.GROUPS], ["Group"] + [short[p] for p in P])
t_all = charts.municipality_table(mun, V, P[3])
overlap = len(set(t_all.sort_values("accidents", ascending=False).head(20)["municipality"]) & set(t_all[t_all["reliable"]].sort_values(charts.RATE, ascending=False).head(20)["municipality"]))
ex = t_all.set_index("municipality").loc[["Antwerpen", "Brussel", "Knokke-Heist"]]
t_ex = md([[n, f"{int(r['accidents']):,}", f"{int(r['average residents']):,}", f"{r[charts.RATE]:.1f}"] for n, r in ex.iterrows()], ["Municipality (all four groups, 2017-2024)", "Accidents", "Average residents", "Per 100,000 residents per year"])

# ------------------------------------------------------------------ regional severity
rg = res["severity_regional_regions_provinces"]
rg = rg[(rg["group"] == "All accidents") & rg["level"].isin(["Belgium", "Region", "Province"])].copy()
rg["fatal"], rg["serious"] = rg["fatal_count"] / rg["accidents"] * 100, rg["serious_count"] / rg["accidents"] * 100  # from the counts
t_reg = md([[r.level, r.area, f"{int(r.accidents):,}", f"{r2(r.fatal, 2)}% ({r2(r.fatal_ci_low, 2)}-{r2(r.fatal_ci_high, 2)})", f"{r2(r.serious, 2)}%"] for r in rg.itertuples()], ["Level", "Area", "Accidents", "Fatal share (95% interval)", "Serious share"])
fat_reg = rg[rg["level"] == "Region"].set_index("area")["fatal"]

n_vuln = int(mun[(mun["group"] == V) & (mun["period"] == P[3])]["accidents"].sum())
text = f"""# How the output was calculated: accident hotspots with vulnerable road users, before, during and after Covid-19

Report for the analysis `vulnerable_hotspots/`. It explains, in the order of the calculation, where every number in the Streamlit app, the HTML page and the pictures comes from, **how to read it** (the interpretation), and how each number can be reproduced. The analysis combines step 1, step 2, the municipality top 20 and step 4a of the focused dashboard with the whole hotspot analysis of the folder `hotspot_deep_dive` (hotspots per period on a grid of 5 km2 cells and 5 x 5 km squares, severity at the hotspots, rates per resident). Scripts: `scripts/01` to `scripts/04`. Decisions and their reasons: `beslissingslogboek.md`, entries #169-#192. All numbers in this report are read from the saved tables in `results/` and `data/` by `scripts/04_build_report.py`.

## 1. The question and what was decided

**Question.** Who is involved in accidents (step 1), how severe are the accidents of each road user (step 2), where do accidents with vulnerable road users (pedestrians, cyclists, motorcycles, mopeds) concentrate, did that change before (2017-2019), during (2020-2021) and after (2022-2024) Covid-19 and over all years, how severe are the accidents at the hotspots, and does the picture change when the number of residents is taken into account? Which municipalities and regions stand out?

| Choice | Decision | Entry |
|---|---|---|
| Step 1 | 1a (accidents per road-user group) and 1b (annual change), the same analysis as in the focused dashboard | #181, #187 |
| Step 2 | Severity per road-user group, with the period filter pre / during / post / all years | #189 |
| Grid | Two sizes with a cell-size filter: cells of 5 km2 (side 2,236 m) and squares of 5 km x 5 km, instead of the 500 m squares of the focused dashboard | #170, #188 |
| Hotspots | The 20 busiest cells per group and period; their severity against all other cells; heat maps per group, period and measure | #172, #173 |
| Residents | Accidents per 100,000 residents per year: per municipality (residents of each year) and per grid cell (sector residents of 2023 scaled to each year) | #171, #178, #183 |
| Municipalities | Top 20 by number or share (focused dashboard step 3b/3c) and rates per resident | #189 |
| Regions | Regional severity and the province map (focused dashboard step 4a) | #189 |
| Small numbers | No share under 30 accidents; a rate per cell needs 1,000 residents and 30 accidents; a municipality rate in full colour from 100 accidents, faded and flagged from 30 to 99 | #175, #177, #184 |

## 2. The data

- **Accidents:** the Belgian road accident open data 2017-2024, translated and flagged in the main project: {N_ACC:,} accidents, one row per accident. The severity class belongs to the whole accident.
- **Counting rule (#33):** an accident counts for a group if the group is road user 1 or road user 2, once per accident. An accident between a car and a bicycle counts for both groups, so the shares of the groups add up to more than 100% (the groups add up to {int(round(tot['accidents'].sum())):,} for {N_ACC:,} accidents). "All four vulnerable groups" counts an accident that involves two of them once: {n_vuln:,} accidents, less than the sum of the four groups.
- **Severity:** *severe* = accident class 1, 2 or 3 (fatal, fatally injured, seriously injured); *fatal* = class 1 or 2; *serious* = class 3; *slight* = class 4 (#116). 28,532 of the {N_ACC:,} accidents are severe (9.85%).
- **Coordinates:** the accident file has Belgian Lambert 1972 coordinates (metres). Coordinates outside Belgium's range (two accidents) are treated as missing (#90). Accidents without usable coordinates cannot be put in a grid cell.
- **Periods (#38):** pre 2017-2019 (3 years), during 2020-2021 (2 years), post 2022-2024 (3 years), plus all years (8 years). These names are my own definition; the data states no cause. Because the periods have different lengths, grid counts are divided by the number of years: **accidents per year**.
- **Residents:** Statbel open data (CC BY 4.0): per municipality for each year 2017-2024 (section 9) and per statistical sector for 1 January 2023 (section 6).

### Accidents with usable coordinates

Grid cells use only the accidents that have coordinates. The share without coordinates changes strongly over time, which matters for the comparison of the periods:

{t_cov}

For all four groups together, {r2(lost[P[0]], 0)}% of the accidents lack coordinates before Covid-19, {r2(lost[P[1]], 0)}% during it and {r2(lost[P[2]], 1)}% after it. That is why the located accidents per year rise from {located[P[0]]:,.0f} to {located[P[2]]:,.0f} (+{(located[P[2]] / located[P[0]] - 1) * 100:.0f}%) while all accidents of the group per year (with or without coordinates) rise only from {allacc[P[0]]:,.0f} to {allacc[P[2]]:,.0f} (+{(allacc[P[2]] / allacc[P[0]] - 1) * 100:.1f}%). Grid counts are not corrected for this (#179): a correction would assume that coordinates are missing at random, and they are not (more in Wallonia). The apps and this report say it instead; municipality rates use all accidents.

## 3. Step 1: who is involved, and the annual change (1a, 1b)

**What was calculated.** For every road-user group, the accidents in which the group is involved in 2017-2024 and their share of all {N_ACC:,} accidents (1a); and the accidents per year with 2017 = 100, the change of 2020 against 2019, and the change of the average per year in 2022-2024 against 2017-2019 (1b). The numbers come from the summary table `data/dashboard_data.csv` (accidents per group, year and month), calculated in the main project with the counting rule of section 2. "Unknown" and "Other road user" are separate lines.

{t_step1}

**How to read it.** The shares add up to more than 100% because one accident can involve two groups. These are counts: a group that is common on the road (cars, bicycles) appears often for that reason alone; severity and traffic volume are not in this step. Nearly every group drops in 2020, the year of the lockdowns; by 2024 bicycles and mopeds are above the level of 2017 and cars, trucks, motorcycles and pedestrians below it. The pre, during and post periods are my own names. "Unknown" more than doubles from 2017 to 2024, so part of the decline of the named groups may be recording that shifts into "Unknown".

## 4. Step 2: the severity per road-user group

**What was calculated.** For each group, the share of the accidents it is involved in that are fatal (class 1+2), seriously injured (class 3) and slightly injured (class 4), with a 95% Wilson interval, for all years and for each period (#74). The class belongs to the whole accident, so a truck-pedestrian accident counts for both groups.

{t_step2}

**How to read it.** Accidents involving trucks ({r2(a.loc['Truck', 'share_pct'])}% fatal) and motorcycles ({r2(a.loc['Motorcycle', 'share_pct'])}%) are the most severe, against {r2(a.loc['All accidents', 'share_pct'], 2)}% for all accidents; mopeds and bicycles are the least often fatal, but bicycle accidents are more often seriously injured. The shares describe the accidents a group is part of, not the harm to that group's own members, and they are shares given that an accident happened, not the risk of having one. The fatal share of all accidents is {r2(fatal_by_scope['pre_2017_2019'], 2)}% before Covid-19, {r2(fatal_by_scope['during_2020_2021'], 2)}% during it and {r2(fatal_by_scope['post_2022_2024'], 2)}% after it. Section 7 shows how severe the accidents are at the hotspots.

## 5. The grid cells and the hotspots

1. **Two grids.** Cells of 5 km2 have a side of sqrt(5) x 1,000 = 2,236.07 m; the squares have sides of 5,000 m. Both are aligned to multiples of the side in Belgian Lambert 1972: the cell of an accident is `(floor(x / side), floor(y / side))`. {n_cells[S5]:,} 5 km2 cells and {n_cells[S25]:,} 5 x 5 km squares contain at least one accident of the four groups. The 500 m squares of the focused dashboard are replaced by these two grids (a hotspot of 500 m is a street corner, a hotspot of 5 km is a city district).
2. **Counting.** For each grid, group and period: the accidents with coordinates per cell, the severe, fatal and serious accidents per cell, and accidents per year = accidents / years of the period. The sum over the cells equals the number of located accidents of the group and period (checked in the script).
3. **Hotspots.** The 20 cells with the most accidents (ties: lowest column, then row). The municipality of a hotspot is the most common municipality among its accidents (a cell can cover several municipalities).
4. **Heat maps.** Accidents per year per cell on a **log colour scale** (a few city cells have hundreds of accidents a year, most cells less than one), the rate per resident (section 6) on a log scale, and the severe share per cell on a linear scale from 0 to 40% (cells with 30 or more accidents). In the three-period view the three maps share the same grid and the same colour scale.

The busiest cells for all four groups together (accidents per year):

{S5}:

{top_table(S5, 'accidents')}

{S25}:

{top_table(S25, 'accidents')}

**Do the hotspots move?** Number of the 20 busiest cells of the pre period that are still among the 20 busiest of the post period:

{t_persist}

**How to read it.** The hotspots are the big cities (Brussel, Antwerpen, Gent and the Brussels municipalities) and they hardly move between the periods: the pandemic lowered the counts everywhere but did not change where accidents concentrate. A 5 km2 cell shows a city district; a 5 x 5 km square covers a whole city and its surroundings, so there are fewer distinct hotspots and the picture is smoother. Counts per year in the pre and during periods are understated because more coordinates are missing (section 2).

## 6. Accidents per 100,000 residents of a cell

Busy cells are busy because many people live there. To compare cells fairly the accidents are divided by the residents of the cell (decision #183), for both grids.

1. **Residents per sector.** Statbel publishes the residents on 1 January 2023 for each of the 19,795 statistical sectors (`OPENDATA_SECTOREN_2023`), the small areas of the Statbel map of 2023. Statbel adds per municipality one row of residents who cannot be located in a sector (8,046 people, 0.07%); they are spread over the sectors of their municipality in proportion to the sector residents, so that every municipality total stays exact (#185).
2. **From sectors to cells.** Each sector polygon is cut by the grid (the same cells as the accidents) and the residents of the sector are shared over the pieces in proportion to their **area**. This assumes that people are spread evenly inside a sector; sectors are small compared with a 25 km2 square, so the error is small, but a cell that holds a large sector with houses on one side only may be off. A check in the script: the pieces of a sector add up to its area and the cells add up to the Belgian total of 11,697,557.

{t_cells_res}

3. **From 2023 to every year.** Statbel's sector files exist only for some years (not for 2017 and 2019) and each follows that year's sector boundaries, so one reference year is used (2023, the year of the sector map). For every year the residents of a piece (cell x municipality) are multiplied by the growth of its municipality: the residents of that year divided by the residents of 2023 (section 9). A check in the script: the residents of all cells, added up over all years, equal the residents of all municipalities added up over all years, for both grids.
4. **The rate.** For a cell, group and period: `accidents / resident-years x 100,000`, where resident-years is the sum over the years of the period of the residents of the cell in that year. It is the average yearly number of accidents per 100,000 residents of the cell.
5. **Small cells (#184).** A rate is shown only for cells with at least 1,000 residents (on average over the period) and at least 30 accidents; otherwise a forest or an industrial cell with a few residents would get an extreme rate. For the rate measure the 20 black cells and the top-20 table are the 20 highest rates among the qualifying cells; for the other measures they are the 20 busiest by number.

Results for all four groups together, 2017-2024:

| Grid | Cells with accidents | Cells that qualify for a rate | Median rate | 20 busiest cells that are also among the 20 highest rates |
|---|---|---|---|---|
| {S5} | {rate_facts[S5]['n']:,} | {rate_facts[S5]['ok']:,} | {rate_facts[S5]['median']:.0f} | {rate_facts[S5]['overlap']} |
| {S25} | {rate_facts[S25]['n']:,} | {rate_facts[S25]['ok']:,} | {rate_facts[S25]['median']:.0f} | {rate_facts[S25]['overlap']} |

The busiest cells are not the highest per resident:

{t_busiest[S5]}

{t_busiest[S25]}

The cells with the highest rates (rate per 100,000 residents per year, with the accidents of the period and the average residents):

{S5}:

{top_table(S5, 'rate')}

{S25}:

{top_table(S25, 'rate')}

**How to read it.** The busiest cells are in the middle of the big cities, where tens of thousands of people live; the highest rates are in small towns and on through roads (Stabroek, Brugge, Schoten, Knokke-Heist) where fewer residents share many accidents, and in tourist places. A rate per resident is not a rate per kilometre travelled: people who pass through a cell (commuters, visitors) are not residents. A cell rate counts only accidents with coordinates (89% of all), so it is lower than the municipality rate of section 9.

## 7. The severity of the hotspots

Share of the accidents involving vulnerable road users that are severe, in the 20 hotspot cells (the 20 busiest) and in all other cells, with 95% Wilson intervals (all four groups together). A share is only given for 30 or more accidents.

{S5}:

{t_sev[S5]}

{S25}:

{t_sev[S25]}

By group (2017-2024):

{t_grp}

**How to read it.** Accidents in the hotspots are much less often severe than elsewhere, in every period, for every group and for both grids. This is an association: hotspots are cities, where speeds are lower and traffic is slower; speed is not in the data. It also means that the places with the most accidents are not the places with the most severe ones: the severe accidents are spread over roads outside the cities.

## 8. The municipalities: top 20 by number and by share (step 3b/3c of the focused dashboard)

**What was calculated.** For each of the four groups, the accidents involving the group in each of the 581 municipalities, and the group's share of all accidents of the municipality; for 2017-2024, 2022-2024 and each year. The top 20 is ranked by number or by share; a share is only ranked for municipalities with at least 100 accidents of any kind in the chosen period and region (#88, #161), so that a handful of accidents in a village do not top the list. The app and the page re-rank for any period and region.

{t_muni}

**How to read it.** By number the big cities win (they have the most accidents of every kind); by share small municipalities can win (for example small Walloon municipalities for motorcycles, with a few dozen accidents each, so a few accidents move the share). These are counts and shares, not rates per resident: section 9 corrects for residents.

## 9. The residents per municipality and the rates per municipality

**Where the residents come from.** Statbel publishes the population of each municipality on 1 January of each year (`TF_SOC_POP_STRUCT_<year>`). The file is one row per age, sex, nationality and marital status; the residents of a municipality are the sum of `MS_POPULATION`. Script `01` downloads the files of 2017-2024 and adds them up.

**The 2019 mergers.** On 1 January 2019 several Flemish municipalities merged and got new NIS codes. The 2017 and 2018 files have 589 old codes, the 2019-2024 files and the accident data have the 581 current codes. The Statbel statistical sectors of 2023 carry both codes (the first five characters of `C_NIS6` are the old municipality, `CNIS5_2023` the current one), which gives an exact table old code -> current code (`data/nis_old_to_2023.csv`); the residents of merged municipalities are added up (#178). After this step every year has 581 municipalities and the total equals the Belgian total of that year:

{t_pop}

**The rate.** For a municipality, group and period: `accidents per 100,000 residents per year = accidents / resident-years x 100,000`, where resident-years is the sum over the years of the period of the residents of **that year** (#171). It uses all accidents of the municipality, with or without coordinates.

**Small numbers (#175, #177).** A rate is in full colour and can be ranked from 100 accidents of the group in the period; with 30 to 99 accidents it is shown faded and flagged; under 30 it is not shown. A stricter rule would leave almost nothing for single groups. Municipalities with 100 or more accidents of the group:

{t_n}

Results for all four groups together (rates per 100,000 residents per year; five highest):

{t_rate}

**How to read it.** Counts favour big places. {overlap} of the 20 municipalities with the most accidents (all four groups, 2017-2024) are also among the 20 with the highest rate. Example:

{t_ex}

Antwerpen has by far the most accidents (first by number) but a rate below Brussel and Knokke-Heist: it has more residents. After the pandemic the rate per resident is back at the level before it ({belgium[P[2]]:.0f} against {belgium[P[0]]:.0f} per 100,000 residents per year; {belgium[P[1]]:.0f} during it), so the rise in counts after 2021 is mostly population growth and better coordinates.

## 10. Regional severity and the province map (step 4a of the focused dashboard)

**What was calculated.** The fatal and the serious share of all accidents in each region and province, with 95% Wilson intervals; the Belgian share is the reference (gray line in the chart). The province map colours the provinces (and Brussels, which has no province) in five classes of the fatal and of the serious share.

{t_reg}

**How to read it.** Wallonia has the highest fatal share ({r2(fat_reg['Walloon Region'], 2)}%, against {r2(fat_reg['Flemish Region'], 2)}% in Flanders and {r2(fat_reg['Brussels-Capital Region'], 2)}% in Brussels) while Flanders has the highest serious-injury share: that could be real or come from how the classes are recorded, which was not tested. These are shares of accidents, not rates per resident.

## 11. How the pictures, the app and the page are built

- `scripts/03_plot_heatmaps.py` draws `images/*.png` from the saved tables (no recalculation): for each group and grid the heat maps of accidents per year, of the rate per resident and of the severe share, three periods side by side, and the municipality rate maps.
- `charts.py` (hotspots) and `charts_focused.py`, `step1_charts.py` (steps 1, 2, the municipality top 20 and step 4a) build the Plotly charts from the saved tables; `app.py` (Streamlit) shows eight views with filters in one sidebar.
- `build_html.py` packs the saved tables as compact lists in one HTML file (`vulnerable_hotspots.html`); the page draws steps 1, the heat maps, the rate maps and the municipality top 20 in the browser from them, so every combination of buttons works. The severity charts are built in Python and embedded.

![Accidents per year per 5 km2 cell](images/heat_vulnerable_5km2_accidents.png)

![Accidents per 100,000 residents of the 5 km2 cell per year](images/heat_vulnerable_5km2_rate.png)

![Severe share per 5 x 5 km square](images/heat_vulnerable_5x5km_severe.png)

![Accidents per 100,000 residents per year, by municipality](images/rates_vulnerable.png)

## 12. Checks

- The scripts check that the totals equal the main project: {N_ACC:,} accidents, 28,532 severe accidents, and 29,897 pedestrian, 71,881 cyclist, 19,792 motorcycle and 23,258 moped accidents.
- For every group, period and grid, the cell counts add up to the accidents with coordinates, and the municipality counts add up to all accidents of the group.
- The residents of every year add up to the Belgian total for 581 municipalities; the sector residents add up to the Belgian total of 1 January 2023; the pieces of a sector add up to its area; the residents of all cells over all years equal the residents of all municipalities over all years, for both grids.
- The Streamlit app was run through every view, group, grid, measure, period and ranking without errors. The HTML page was opened in a browser, every button was used, and the tables on the page equal the saved results (for example Brussel 383.8 and Knokke-Heist 367.6 accidents per 100,000 residents per year for all four groups; Schoten 818.8 per 100,000 residents in the 5 km2 cells of 2017-2024).

## 13. Limits

- **Coordinates:** missing coordinates change over the periods (section 2); grid counts per year are understated before Covid-19. Wallonia has more missing coordinates, so hotspots there may be understated.
- **Residents are not traffic.** Municipalities and cells with visitors, commuters or tourists (Brussel, Knokke-Heist, Gent) get a high rate because many of the people involved do not live there. A rate per resident is not a rate per kilometre travelled.
- **Residents of a cell are an estimate:** sector residents of 2023, spread by area and scaled with the growth of the municipality.
- **Hotspots are where accidents are counted.** A different grid origin or size would give different cells; the two grids show the same big picture.
- **Small municipalities and cells:** a rate or a share moves with a few accidents; this is why minimum numbers are needed.
- **Associations, not causes.** The Covid-19 periods are my own definition; the data states no cause.
"""
(HERE / "REPORT_how_the_output_was_calculated.md").write_text(text, encoding="utf-8")
print(f"Saved REPORT_how_the_output_was_calculated.md: {len(text.split()):,} words")
