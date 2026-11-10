"""
Step 4 of the hotspot deep dive: builds the report "how the output was calculated" (REPORT_how_the_output_was_calculated.md).

The text is written here; every TABLE and every number in the running text is read from the saved result tables in results/ and data/, so nothing is typed by hand.

How to run (from the folder hotspot_deep_dive, with `conda activate syntra-ds`):
    python -I scripts/04_build_report.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import charts  # noqa: E402

cells, top, summ, cov, mun = charts.load_cells(), charts.load_top(), charts.load_summary(), charts.load_coverage(), charts.load_municipalities()
pop = pd.read_csv(HERE / "data" / "population_by_municipality.csv", dtype={"municipality_nis_code": str})
V, SIZE = charts.GROUPS[0], "5 x 5 km squares"
P = charts.PERIODS
short = {P[0]: "Pre (2017-2019)", P[1]: "During (2020-2021)", P[2]: "Post (2022-2024)", P[3]: "All years (2017-2024)"}


def md(rows, headers):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def r2(v, d=1):
    """Round half up (the float 0.365 would otherwise print as 0.36)."""
    return f"{float(v) + (1e-9 if v >= 0 else -1e-9):.{d}f}"


# --- numbers ---
cell_counts = {s: int(cells[(cells["size"] == s) & (cells["group"] == V) & (cells["period"] == P[3])].shape[0]) for s in charts.CELL_SIZES}
t_cov = md([[charts.GROUP_LABELS[g]] + [f"{int(c['accidents']):,} ({r2(100 - c['left out %'], 1)}% with coordinates)" for p in P[:3] for c in [cov[(cov["group"] == g) & (cov["period"] == p)].iloc[0]]] for g in charts.GROUPS],
           ["Group"] + [short[p] for p in P[:3]])
t_pop = md([[int(y), f"{int(pop[pop['year'] == y]['residents'].sum()):,}"] for y in range(2017, 2025)], ["Year (1 January)", "Residents in Belgium (581 municipalities)"])
tops = []
for size in charts.CELL_SIZES:
    for p in P[:3]:
        t = top[(top["size"] == size) & (top["group"] == V) & (top["period"] == p) & (top["ranking"] == "accidents")].head(5)
        tops.append([short[p]] + [f"{r.municipality} {r.per_year:.0f}" for r in t.itertuples()])
t_top = md(tops, ["Period", "1st", "2nd", "3rd", "4th", "5th"])
tops_rate = []
for p in P[:3] + [P[3]]:
    t = top[(top["size"] == SIZE) & (top["group"] == V) & (top["period"] == p) & (top["ranking"] == "rate")].head(5)
    tops_rate.append([short[p]] + [f"{r.municipality} {r.rate:.0f} ({int(r.accidents)} acc., {int(round(r.resident_years / charts.YEARS_IN[p])):,} res.)" for r in t.itertuples()])
t_top_rate = md(tops_rate, ["Period", "1st", "2nd", "3rd", "4th", "5th"])
sev_rows = []
for size in charts.CELL_SIZES:
    for p in P[:3] + [P[3]]:
        s = summ[(summ["size"] == size) & (summ["group"] == V) & (summ["period"] == p)].set_index("squares")
        sev_rows.append([short[p], f"{int(s.loc['20 hotspot squares', 'accidents']):,}", f"{r2(s.loc['20 hotspot squares', 'severe %'])}% ({r2(s.loc['20 hotspot squares', 'severe low'])}-{r2(s.loc['20 hotspot squares', 'severe high'])})",
                         f"{int(s.loc['all other squares', 'accidents']):,}", f"{r2(s.loc['all other squares', 'severe %'])}% ({r2(s.loc['all other squares', 'severe low'])}-{r2(s.loc['all other squares', 'severe high'])})",
                         f"{r2(s.loc['20 hotspot squares', 'fatal %'], 2)}% / {r2(s.loc['all other squares', 'fatal %'], 2)}%"])
t_sev = md(sev_rows, ["Period", "Accidents in 20 hotspot squares", "Severe % hotspots (95% interval)", "Accidents in all other squares", "Severe % other squares (95% interval)", "Fatal % hotspots / others"])
grp_rows = []
for g in charts.GROUPS:
    s = summ[(summ["size"] == SIZE) & (summ["group"] == g) & (summ["period"] == P[3])].set_index("squares")
    grp_rows.append([charts.GROUP_LABELS[g], f"{r2(s.loc['20 hotspot squares', 'severe %'])}%", f"{r2(s.loc['all other squares', 'severe %'])}%", f"{r2(s.loc['20 hotspot squares', 'fatal %'], 2)}%", f"{r2(s.loc['all other squares', 'fatal %'], 2)}%"])
t_grp = md(grp_rows, ["Group", "Severe % hotspots", "Severe % other squares", "Fatal % hotspots", "Fatal % other squares"])
persist = []
for size in charts.CELL_SIZES:
    row = [size]
    for g in charts.GROUPS:
        a = top[(top["size"] == size) & (top["group"] == g) & (top["period"] == P[0]) & (top["ranking"] == "accidents")]; b = top[(top["size"] == size) & (top["group"] == g) & (top["period"] == P[2]) & (top["ranking"] == "accidents")]
        row.append(f"{len(set(zip(a.cx, a.cy)) & set(zip(b.cx, b.cy)))} of 20")
    persist.append(row)
t_persist = md(persist, ["Grid"] + [charts.GROUP_LABELS[g] for g in charts.GROUPS])
rate_rows, belgium = [], {}
for p in P:
    t = charts.municipality_table(mun, V, p)
    belgium[p] = t["accidents"].sum() / t["resident_years"].sum() * 1e5
    rel = t[t["reliable"]].sort_values(charts.RATE, ascending=False).head(5)
    rate_rows.append([short[p], f"{belgium[p]:.1f}", int(t["reliable"].sum()), ", ".join(f"{r.municipality} {r[charts.RATE]:.0f}" for _, r in rel.iterrows())])
t_rate = md(rate_rows, ["Period", "Belgium per 100,000 per year", "Municipalities with 100+ accidents", "Highest rates (per 100,000 per year)"])
n_by_group = []
for g in charts.GROUPS:
    n_by_group.append([charts.GROUP_LABELS[g]] + [int(charts.municipality_table(mun, g, p)["reliable"].sum()) for p in P])
t_n = md(n_by_group, ["Group"] + [short[p] for p in P])
t_all = charts.municipality_table(mun, V, P[3])
count_top = t_all.sort_values("accidents", ascending=False).head(20)["municipality"]
rate_top = t_all[t_all["reliable"]].sort_values(charts.RATE, ascending=False).head(20)["municipality"]
overlap = len(set(count_top) & set(rate_top))
ex = t_all.set_index("municipality").loc[["Antwerpen", "Brussel", "Knokke-Heist"]]
t_ex = md([[n, f"{int(r['accidents']):,}", f"{int(r['average residents']):,}", f"{r[charts.RATE]:.1f}"] for n, r in ex.iterrows()], ["Municipality (all four groups, 2017-2024)", "Accidents", "Average residents", "Per 100,000 residents per year"])
lost = {p: 100 - cov[(cov["group"] == V) & (cov["period"] == p)].iloc[0]["with coordinates"] / cov[(cov["group"] == V) & (cov["period"] == p)].iloc[0]["accidents"] * 100 for p in P}
located = {p: cells[(cells["size"] == SIZE) & (cells["group"] == V) & (cells["period"] == p)]["accidents"].sum() / charts.YEARS_IN[p] for p in P}
allacc = {p: t["accidents"].sum() / charts.YEARS_IN[p] for p in P for t in [charts.municipality_table(mun, V, p)]}

pieces = pd.read_csv(HERE / "data" / "cell_residents_2023.csv", dtype={"municipality_nis_code": str})
per_square = pieces.groupby(["cx", "cy"])["residents_2023"].sum()
ca = cells[(cells["size"] == SIZE) & (cells["group"] == V) & (cells["period"] == P[3])]
ta = top[(top["size"] == SIZE) & (top["group"] == V) & (top["period"] == P[3]) & (top["ranking"] == "accidents")].head(3)
ta_rows = md([[r["municipality"], f"{r['per_year']:.0f}", f"{r['average residents']:,.0f}", f"{r['rate']:.0f}"] for _, r in ta.iterrows()], ["Busiest squares (all four groups, 2017-2024)", "Accidents per year", "Average residents", "Per 100,000 residents per year"])
rate_overlap = [len(set(zip(a.cx, a.cy)) & set(zip(b.cx, b.cy))) for p_ in P[:3] + [P[3]] for a, b in [(top[(top["group"] == V) & (top["period"] == p_) & (top["ranking"] == "accidents")], top[(top["group"] == V) & (top["period"] == p_) & (top["ranking"] == "rate")])]]

text = f"""# How the output was calculated: hotspots of accidents with vulnerable road users, before, during and after Covid-19

Report for the hotspot deep dive (`hotspot_deep_dive/`). It explains, in the order of the calculation, where every number in the Streamlit app, the HTML page and the pictures comes from, so that each number can be reproduced and explained. Scripts: `scripts/01` to `scripts/04`. Decisions and their reasons: `beslissingslogboek.md`, entries #169-#186. All numbers in this report are read from the saved tables in `results/` and `data/` by `scripts/04_build_report.py`.

## 1. The question and what was decided

**Question.** Who is involved in accidents, where do accidents with vulnerable road users (pedestrians, cyclists, motorcycles, mopeds) concentrate, did that change before (2017-2019), during (2020-2021) and after (2022-2024) Covid-19, how severe are the accidents at the hotspots, and does the picture change when the number of residents is taken into account?

| Choice | Decision | Entry |
|---|---|---|
| Step 1 | 1a (accidents per road-user group) and 1b (annual change) come first, as in the focused dashboard; no 1c | #181 |
| Grid | Squares of 5 km x 5 km (25 km2), instead of the 500 m squares of the earlier analysis; the 5 km2 cells of the first version were removed | #170, #182 |
| Residents | Rates per municipality and, new, per 5 x 5 km square: accidents per 100,000 residents per year, using the residents of each year | #171, #178, #183 |
| Severity | Severe share (classes 1-3) per square, with fatal and serious shares and 95% intervals in tables | #172 |
| Groups | Pedestrians, cyclists, motorcycles, mopeds, and all four together | #173 |
| Small numbers | No share under 30 accidents; a rate per square needs 1,000 residents and 30 accidents; a municipality rate in full colour from 100 accidents, faded and flagged from 30 to 99 | #175, #177, #184 |

## 2. The data

- **Accidents:** the Belgian road accident open data 2017-2024, translated and flagged in the main project: 289,532 accidents, one row per accident. The severity class belongs to the whole accident.
- **Step 1 (1a, 1b):** the accidents per road-user group, year and month (`data/dashboard_data.csv`, from step 1 of the main project): accidents per group, and the annual change with 2017 = 100. Same numbers and counting rule as in the earlier analysis.
- **Counting rule (#33):** an accident counts for a group if the group is road user 1 or road user 2, once per accident. "All four vulnerable groups" counts an accident that involves two of them once: {int(mun[(mun['group'] == V) & (mun['period'] == P[3])]['accidents'].sum()):,} accidents, less than the sum of the four groups.
- **Severity:** *severe* = accident class 1, 2 or 3 (fatal, fatally injured, seriously injured); *fatal* = class 1 or 2; *serious* = class 3 (#116). 28,532 of the 289,532 accidents are severe (9.85%).
- **Coordinates:** the accident file has Belgian Lambert 1972 coordinates (metres). Coordinates outside Belgium's range (two accidents) are treated as missing (#90). Accidents without usable coordinates cannot be put in a grid square.
- **Periods (#38):** pre 2017-2019 (3 years), during 2020-2021 (2 years), post 2022-2024 (3 years), plus all years (8 years). These names are my own definition; the data states no cause. Because the periods have different lengths, counts are divided by the number of years: **accidents per year**.
- **Residents:** Statbel open data (CC BY 4.0): per municipality for each year 2017-2024 (section 6) and per statistical sector for 1 January 2023 (section 4).

### Accidents with usable coordinates

Grid squares use only the accidents that have coordinates. The share without coordinates changes strongly over time, which matters for the comparison of the periods:

{t_cov}

For all four groups together, {r2(lost[P[0]], 0)}% of the accidents lack coordinates before Covid-19, {r2(lost[P[1]], 0)}% during it and {r2(lost[P[2]], 1)}% after it. That is why the located accidents per year rise from {located[P[0]]:,.0f} to {located[P[2]]:,.0f} (+{(located[P[2]] / located[P[0]] - 1) * 100:.0f}%) while all accidents of the group per year (with or without coordinates) rise only from {allacc[P[0]]:,.0f} to {allacc[P[2]]:,.0f} (+{(allacc[P[2]] / allacc[P[0]] - 1) * 100:.1f}%). Grid counts are not corrected for this (#179); the report and the apps say so. Municipality rates use all accidents.

## 3. The grid squares and the hotspots (script `02`, parts A and B)

1. **Squares.** The grid has sides of 5,000 m, aligned to multiples of 5,000 m in Belgian Lambert 1972: the square of an accident is `(floor(x / 5000), floor(y / 5000))`. {cell_counts[SIZE]:,} squares contain at least one accident of the four groups.
2. **Counting.** For each group and period: the accidents with coordinates per square, the severe, fatal and serious accidents per square, and accidents per year = accidents / years of the period. The sum over the squares equals the number of located accidents of the group and period (checked in the script).
3. **Hotspots.** The 20 squares with the most accidents (ties: lowest column, then row). The municipality of a hotspot is the most common municipality among its accidents (a square can cover several municipalities).
4. **Severity of the hotspots.** For each group and period the severity of the 20 hotspot squares is compared with all other squares together: severe, fatal and serious shares with 95% Wilson intervals (the same method as step 2 of the main project, #74). A share is only given for 30 or more accidents.
5. **Heat maps.** Accidents per year per square on a **log colour scale** (a few city squares have hundreds of accidents a year, most squares less than one), and the severe share per square on a linear scale from 0 to 40% (squares with 30 or more accidents). In the three-period view the three maps share the same grid and the same colour scale.

The busiest squares for all four groups together (accidents per year):

{t_top}

**Do the hotspots move?** Number of the 20 busiest squares of the pre period that are still among the 20 busiest of the post period:

{t_persist}

## 4. Accidents per 100,000 residents of a square (scripts `01b` and `02`)

The question: busy squares are busy because many people live there. To compare squares fairly the accidents are divided by the residents of the square (decision #183).

1. **Residents per sector.** Statbel publishes the residents on 1 January 2023 for each of the 19,795 statistical sectors (`OPENDATA_SECTOREN_2023`); the sectors are the small areas of the Statbel map of 2023. Statbel adds per municipality one row of residents who cannot be located in a sector (8,046 people, 0.07%); they are spread over the sectors of their municipality in proportion to the sector residents, so that every municipality total stays exact. The residents add up to the Belgian total of {int(pieces['residents_2023'].sum()):,} (rounding).
2. **From sectors to squares.** Each sector polygon is cut by the 5 x 5 km grid (the same squares as the accidents) and the residents of the sector are shared over the pieces in proportion to their **area**. This assumes that people are spread evenly inside a sector; sectors are small compared with a 25 km2 square, so the error is small, but a square that holds a large sector with houses on only one side may be off. {len(per_square):,} squares contain residents; {int((per_square >= 1000).sum()):,} have 1,000 or more; the most populated square (Brussels) has {int(per_square.max()):,} residents. A check in the script: the pieces of a sector add up to its area.
3. **From 2023 to every year.** Statbel's sector files exist only for some years (not for 2017 and 2019) and each follows that year's sector boundaries, so one reference year is used (2023, the year of the sector map). For every year the residents of a piece (square x municipality) are multiplied by the growth of its municipality: the residents of that year divided by the residents of 2023 (from the municipality table of section 6). A check in the script: the residents of all squares, added up over all years, equal the residents of all municipalities added up over all years.
4. **The rate.** For a square, group and period: `accidents / resident-years x 100,000`, where resident-years is the sum over the years of the period of the residents of the square in that year. It is the average yearly number of accidents per 100,000 residents of the square.
5. **Small squares (#184).** A rate is shown only for squares with at least 1,000 residents (on average over the period) and at least 30 accidents; otherwise a forest or an industrial square with a few residents would get an extreme rate. {int(ca['rate_ok'].sum())} of the {len(ca):,} squares with accidents of the four groups (2017-2024) qualify.
6. **Marked squares.** For the rate measure the 20 black squares and the top-20 table are the 20 highest rates among the qualifying squares; for the other measures they are the 20 busiest by number.

The squares with the highest rates (all four groups; rate per 100,000 residents per year, with accidents in the period and average residents):

{t_top_rate}

The busiest squares are not the highest per resident:

{ta_rows}

Only {rate_overlap[3]} of the 20 busiest squares (2017-2024) are also among the 20 highest rates ({rate_overlap[0]}, {rate_overlap[1]} and {rate_overlap[2]} in the pre, during and post period). The highest rates are in squares of 2,000 to 6,000 residents on a through road or in a tourist town, and in Gent and Leuven. Median rate of the qualifying squares: {ca[ca['rate_ok']]['rate'].median():.0f} per 100,000 residents per year.

Limits of the rate per square: it counts only accidents with coordinates (89% of all), so it is lower than the municipality rate; people who pass through a square (commuters, visitors) are not residents; and the residents are spread by area inside sectors.

## 5. The severity of the hotspots

Share of the accidents involving vulnerable road users that are severe, in the 20 hotspot squares (the 20 busiest) and in all other squares, with 95% Wilson intervals (all four groups together):

{t_sev}

By group (2017-2024):

{t_grp}

Accidents in the hotspots are much less often severe than elsewhere, in every period and for every group. This is an association: hotspots are in cities, where speeds are lower; speed is not in the data.

## 6. The residents per municipality and the rates per municipality (scripts `01` and `02`, part C)

**Where the residents come from.** Statbel publishes the population of each municipality on 1 January of each year (`TF_SOC_POP_STRUCT_<year>`). The file is one row per age, sex, nationality and marital status; the residents of a municipality are the sum of `MS_POPULATION`. Script `01` downloads the files of 2017-2024 and adds them up.

**The 2019 mergers.** On 1 January 2019 several Flemish municipalities merged and got new NIS codes. The 2017 and 2018 files have 589 old codes, the 2019-2024 files and the accident data have the 581 current codes. The Statbel statistical sectors of 2023 carry both codes (the first five characters of `C_NIS6` are the old municipality, `CNIS5_2023` the current one), which gives an exact table old code -> current code (`data/nis_old_to_2023.csv`); the residents of merged municipalities are added up. After this step every year has 581 municipalities and the total equals the Belgian total of that year:

{t_pop}

**The rate.** For a municipality, group and period:

`accidents per 100,000 residents per year = accidents / resident-years x 100,000`, where resident-years is the sum over the years of the period of the residents of **that year** (#171). It uses all accidents of the municipality, with or without coordinates.

**Small numbers (#175, #177).** A rate is in full colour and can be ranked from 100 accidents of the group in the period; with 30 to 99 accidents it is shown faded and flagged; under 30 it is not shown. A stricter rule (100 accidents for any display) would leave almost nothing for single groups. Municipalities with 100 or more accidents of the group:

{t_n}

**Results for all four groups together** (rates per 100,000 residents per year; five highest):

{t_rate}

**Why residents matter.** Counts favour big places. {overlap} of the 20 municipalities with the most accidents (all four groups, 2017-2024) are also among the 20 with the highest rate. Example:

{t_ex}

Antwerpen has by far the most accidents (first by number) but a rate below Brussel and Knokke-Heist: it has more residents.

## 7. How the pictures, the app and the page are built

- `scripts/03_plot_heatmaps.py` draws `images/*.png` from the saved tables (no recalculation).
- `charts.py` builds the Plotly charts from the saved tables; `app.py` (Streamlit) shows step 1 first and then the hotspot views with filters (view, group, measure, period, rank by).
- `build_html.py` packs the saved tables as compact lists in one HTML file (`hotspot_deep_dive.html`); the page draws step 1, the heat maps and the rate maps in the browser from them, so every combination of buttons works. The severity charts are built in Python and embedded.

![Accidents per year per 5 x 5 km square](images/heat_vulnerable_5x5km_accidents.png)

![Accidents per 100,000 residents of the square per year](images/heat_vulnerable_5x5km_rate.png)

![Severe share per 5 x 5 km square](images/heat_vulnerable_5x5km_severe.png)

![Accidents per 100,000 residents per year, by municipality](images/rates_vulnerable.png)

## 8. Checks

- The script checks that its totals equal the main project: 289,532 accidents, 28,532 severe accidents, and 29,897 pedestrian, 71,881 cyclist, 19,792 motorcycle and 23,258 moped accidents.
- For every group and period, the square counts add up to the accidents with coordinates, and the municipality counts add up to all accidents of the group.
- The residents of every year add up to the Belgian total for 581 municipalities; the sector residents add up to the Belgian total of 1 January 2023; the pieces of a sector add up to its area; the residents of all squares over all years equal the residents of all municipalities over all years.
- The Streamlit app was run through every view, group, period, measure and ranking without errors. The HTML page was opened in a browser, every button was used, and the tables on the page equal the saved results (for example Brussel 383.8 and Knokke-Heist 367.6 accidents per 100,000 residents per year for all four groups; Stabroek 835.6 per 100,000 residents in the squares of 2022-2024).

## 9. Limits

- **Coordinates:** missing coordinates change over the periods (section 2); grid counts per year are understated before Covid-19. Wallonia has more missing coordinates, so hotspots there may be understated.
- **Residents are not traffic.** Municipalities and squares with visitors, commuters or tourists (Brussel, Knokke-Heist, Gent) get a high rate because many of the people involved do not live there. A rate per resident is not a rate per kilometre travelled.
- **Residents of a square are an estimate:** sector residents of 2023, spread by area and scaled with the growth of the municipality.
- **Hotspots are where accidents are counted.** A different grid origin or size would give different squares.
- **Small municipalities and squares:** a rate or a share moves with a few accidents; this is why minimum numbers are needed.
- **Associations, not causes.** The Covid-19 periods are my own definition; the data states no cause.
"""
(HERE / "REPORT_how_the_output_was_calculated.md").write_text(text, encoding="utf-8")
print(f"Saved REPORT_how_the_output_was_calculated.md: {len(text.split()):,} words")
