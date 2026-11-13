# How the five steps of the final analysis were modeled: the technical underpinnings

Plain-language method report for the analysis in `hotspot_dive_deep_final/`: accident hotspots with vulnerable road users in Belgium, 2017-2024 (289,532 accidents), with step 1 of the focused dashboard in front. It explains, for each of the five steps, **what kind of model or calculation was used, what it assumes, how it works inside, how it was checked, and where it stops being reliable**. It does not repeat the findings or the numbers of every table (see `REPORT_how_the_output_was_calculated.md`); it explains the machinery behind them, so that every number can be defended without AI. `#n` points to an entry in `beslissingslogboek.md`, where the decision and its reason are written down; `scripts/NN` points to the code.

**What "model" means here.** All five steps are *descriptive models*: carefully defined counts, grids, shares, rates and comparisons that turn accident rows into results, with uncertainty added where it matters. There is no regression in this analysis; the only inferential tool is the confidence interval of a share.

| Step | Question | Kind of model | Where |
|---|---|---|---|
| 1 | Who is involved in accidents, and how did it change? (1a, 1b) | Counts, shares, an index over time | `step1_logic.py`, `step1_charts.py` |
| 2 | Where do accidents with vulnerable road users concentrate? | Grid-cell counts, a hotspot ranking and heat maps (two grid sizes) | `scripts/02`, `charts.py` |
| 3 | Did that change before, during and after Covid-19? | The same grid and colour scale for three periods, in accidents per year | `scripts/02`, `charts.py` |
| 4 | How severe are the accidents at the hotspots? | A two-group comparison of shares (hotspot cells against all other cells) with Wilson intervals | `scripts/02`, `charts.py` |
| 5 | Does the picture change per resident? | Rates per 100,000 residents per year per municipality, with minimum-number rules | `scripts/01`, `02` |

## 0. The foundations shared by all five steps

### 0.1 The unit of analysis: one row is one accident

The data are *accident-level*, not person-level: one row per accident, with the road-user type of up to two parties (road user 1 and road user 2), the conditions, the place (municipality and, for about 89%, coordinates), the year, and one **accident class** for the whole accident. There is no identifier to prove that a row is a unique accident (#20), so possible duplicates were flagged and kept. Nothing was filled in or removed for empty cells; "Unknown" stays a category (#18, #22).

**Consequence for every step:** the severity belongs to the accident, not to a person. In a car-pedestrian accident the same class is attached to the pedestrian group and to the car group, so all results describe *the accidents a group is part of*, not the harm to that group's own members.

### 0.2 The counting rule (#33, #173)

An accident counts for a road-user group if that group is road user 1 **or** road user 2, once per accident. Technical consequences:

- Group counts add up to more than the number of accidents (136,144 accidents involve two different groups), and shares of groups add up to more than 100% (step 1).
- The group "**vulnerable (any of the four)**" (pedestrians, cyclists, motorcycles, mopeds) is a logical OR over the four: an accident with, say, a cyclist and a pedestrian counts **once** (136,627 accidents), which is less than the sum of the four groups.
- The meaning of "road user 1" versus "road user 2" is not documented, so the order is never interpreted.

### 0.3 The severity coding (#71, #116)

| Name | Accident classes | Share of all accidents |
|---|---|---|
| Fatal | class 1 (with fatalities) + class 2 (fatally injured) | 1.43% |
| Serious | class 3 (with seriously injured) | 8.42% |
| Slight | class 4 (with slightly injured) | 90.15% |
| Severe | classes 1 + 2 + 3 | 9.85% (28,532 accidents) |

Step 4 uses *severe* as its headline measure (the same definition as the logistic models of the main project) and gives fatal and serious next to it.

### 0.4 Uncertainty: the 95% Wilson interval (#74)

A share such as "6.4% of the accidents in the hotspots are severe" is a *sample proportion*, so it carries uncertainty. The interval used is the **Wilson score interval**. In words: it asks "which true shares are still plausible given k events out of n accidents?" and returns the range of those shares at the 95% level. Compared with the simple textbook interval (share ± 1.96 standard errors) it behaves well for small counts and for shares near 0%, and it never leaves the 0-100% range, which matters because many fatal shares are around 1%.

*Assumption:* accidents are independent draws. This is slightly optimistic: accidents in the same city resemble each other, and one accident can count for two groups.

### 0.5 The small-number rules (#175, #177)

Shares and rates built on few accidents jump around, so the analysis uses minimum numbers:

| Quantity | Rule |
|---|---|
| A severity share (per cell or per group of cells) | shown only from **30** accidents |
| A municipality rate per 100,000 residents | **full colour and ranked from 100** accidents of the group in the period; **faded and flagged from 30 to 99**; **not shown under 30** |

The first version of the rate rule (rate only from 100 accidents) was changed after the first results: for single groups it would have left only 3 to 8 municipalities for motorcycles in a period (#177). "Faded and flagged" keeps the information visible without pretending that it is reliable.

### 0.6 Coordinates and the missing ones (#90)

Coordinates are Belgian Lambert 1972 (EPSG:31370, metres), so a grid of "5 km" is a real 5 km. Two impossible coordinates (values around 10^16) are treated as missing. **Every grid step (2 to 4) can only use the accidents that have usable coordinates**: 121,379 of the 136,627 accidents of vulnerable road users (88.8%). The share without coordinates is very uneven over time (section 3.3), which is the main technical weakness of the period comparison. Step 5 does not have this problem: every accident has a municipality code, so rates use all accidents.

### 0.7 The three periods (#38)

Pre Covid-19 = 2017-2019 (3 years), during = 2020-2021 (2 years), post = 2022-2024 (3 years), plus all years (8 years). The names and the cut-offs are my own definition; the data state no cause for any change. Because the periods have different lengths, grid counts are always **divided by the number of years** (accidents per year).

### 0.8 How correctness was protected

- Every analysis is a script with the decision numbers in its header, runnable from the command line.
- The scripts contain checks that stop the run if a total is wrong (289,532 accidents; 28,532 severe; 29,897 pedestrian, 71,881 cyclist, 19,792 motorcycle and 23,258 moped accidents; the cell counts and the municipality counts add up).
- The Streamlit app, the HTML page, the pictures and the report are all built from the saved result tables, never recalculated differently; every tool was checked against those tables.

## 1. Step 1: who is involved in accidents, and the annual change (1a, 1b)

**Question.** How many accidents involve each road-user group, and how did that change from year to year?

**The model.** Counting, followed by two transformations that make groups and years comparable. The calculations are those of the focused dashboard (`step1_logic.py`) on a summary table of accidents per road-user group, year and month.

1. **Count and share (1a).** For each group, the number of accidents it is involved in, and that number divided by all 289,532 accidents.
2. **Index over time (1b).** Accidents per year for each group, divided by the group's accidents in the first selected year and multiplied by 100 (2017 = 100). The index removes the different sizes of the groups, so a small group (buses) and a large one (cars) can be compared by their *change*. The three periods of section 0.7 are drawn as bands, and the **average per year in the post period is compared with the pre period** (a percentage change). A period is only used when the selected years cover it completely.

**Assumptions and choices.** The counting rule of section 0.2. "Unknown" and "Other road user" are separate lines, in gray, and hidden by default (they are not specific groups). The filters (years, groups) only choose which rows of the summary table are added up.

**Checked.** The totals per group equal the first count; the browser version on the HTML page recalculates 1a and 1b in JavaScript from the same summary table and was compared with the Python calculation to 10^-6 in several scenarios.

**Limits.** These are counts, not rates: a road user that is common on the road appears often for that reason alone. "Unknown" more than doubles between 2017 and 2024, so part of the decline of the named groups may be recording that moves into "Unknown". Explanations of the change (lockdowns, weather) are not tested.

## 2. Step 2: where do accidents with vulnerable road users concentrate? (the heat map)

**Question.** In which places are the accidents with pedestrians, cyclists, motorcycles and mopeds concentrated?

**The model.** A **grid-cell count**, drawn as a heat map.

1. **Two grids (#170).** The map of Belgium is divided into square cells aligned to the Belgian Lambert 1972 coordinate system: *5 km2 cells* (side = sqrt(5) x 1,000 m = 2,236.07 m) and *5 x 5 km squares* (side 5,000 m). The cell of an accident is `(floor(x / side), floor(y / side))`, so each accident falls in exactly one cell. Two sizes are used on purpose: they show how much the result depends on the size of the cell.
2. **Counting.** For each group (pedestrians, cyclists, motorcycles, mopeds, and the combined group), each period and each grid: the number of accidents with coordinates in each cell, plus the severe, fatal and serious accidents in it. Cells without accidents are simply absent. 5,013 5 km2 cells and 1,274 5 x 5 km squares contain at least one accident of the combined group in 2017-2024.
3. **Accidents per year.** The count divided by the number of years of the period (section 0.7). This is the quantity that is coloured.
4. **Hotspots.** The **20 cells with the most accidents** (ties: lowest column, then lowest row). Each hotspot is named after the municipality that holds most of its accidents (a cell can cover several municipalities). The 20 hotspot cells of the combined group hold 20,733 accidents in 5 km2 cells (17% of the located accidents) and 38,228 in 5 x 5 km squares (31%).
5. **The colour scale.** The number of accidents per cell is extremely skewed: a few city cells have more than 250 accidents a year, most cells have less than one. A straight colour scale would show only the cities. So the colour follows the **logarithm** of the accidents per year (a floor of 0.1 a year; ticks at 0.1, 0.3, 1, 3, 10, 30, 100, 300): each step in colour means "about three times as many accidents". The second measure, the **severe share per cell**, uses a linear scale from 0% to 40% and is only drawn for cells with 30 or more accidents (section 0.5).
6. **Why heat maps and not smoothing.** The first alternatives considered for hotspots were a smoothed density surface and clustering (#85). A grid count has no tuning parameters other than the cell size, gives exact counts per cell, and can be reproduced and explained. The price: the result depends on the cell size and on where the grid starts (a concentration that is split across two cells looks weaker; this is the "modifiable areal unit problem" of all grid maps).

**Checked.** The counts of the cells add up to the located accidents of the group and period (the script stops if not); the totals equal the main project's totals; the heat maps on the HTML page are built in the browser from the same cell lists as the Python figures and the Streamlit app, and the top-20 table has 20 rows and the same numbers.

**Limits.** Hotspots are where accidents are *counted*, which is mostly where many people and vehicles are; a hotspot is not a place of high risk (step 5 and the report discuss this). Only accidents with coordinates are shown (88.8%); a different grid origin or cell size would give different cells, although the two sizes tell the same big story (the big cities).

## 3. Step 3: before, during and after Covid-19

**Question.** Did the places where accidents concentrate change over the three periods?

**The model.** The step 2 calculation repeated for each period, with three things kept identical so that the pictures are comparable:

1. **The same grid** (same cell boundaries) in all three periods.
2. **The same colour scale** in the three maps (the upper end is the maximum over the three periods), so the same colour means the same number of accidents a year in every panel.
3. **Accidents per year**, not totals, because the periods are 3, 2 and 3 years long.

**Persistence of the hotspots.** To summarise "do the hotspots move?" in one number, the 20 hotspot cells of the pre period are compared with the 20 of the post period: **how many cells are in both lists**. For the combined group this is 17 of 20 for the 5 km2 cells and 18 of 20 for the 5 x 5 km squares. The hotspots hardly move: the pandemic lowered counts everywhere but did not change where accidents concentrate.

### 3.3 The weakness of this step: coordinates are missing unevenly over time

| Period | Accidents of vulnerable road users | With usable coordinates | Share without coordinates |
|---|---|---|---|
| Pre (2017-2019) | 51,917 | 44,116 | 15.0% |
| During (2020-2021) | 31,473 | 26,013 | 17.4% |
| Post (2022-2024) | 53,237 | 51,250 | 3.7% |

Because far fewer accidents lack coordinates after 2021, the **located** accidents per year rise from 14,705 (pre) to 17,083 (post), +16%, while **all** accidents of the group per year (with or without coordinates) rise only from 17,306 to 17,746, +2.5%. The grid counts per year of the first two periods are therefore *understated* compared with the third.

**Why it was not corrected.** The obvious correction is to divide each period's counts by its share with coordinates. That assumes that coordinates are missing *at random*, which is not true (they are missing more often in Wallonia and before 2022), so the correction could create a false picture of where accidents happen (#179). Instead the page and the report say it next to every grid view, and two views are not affected by it as much: the *shares* of step 4 (a share is computed inside the cells that have coordinates) and the *municipality rates* of step 5 (which use all accidents).

**Limits.** The period names are my own; the comparison is descriptive; a change in a single cell between periods may be noise (a cell with 3 accidents a year).

## 4. Step 4: how severe are the accidents at the hotspots?

**Question.** Are the accidents in the busiest places more or less severe than elsewhere?

**The model.** A **comparison of two shares**.

1. **Two groups of cells.** For each group, period and grid, the located accidents are divided into those in the **20 hotspot cells** (the 20 busiest) and those in **all other cells**.
2. **The share.** In each group of cells the share of accidents that are severe (classes 1-3), fatal (1-2) and serious (3): `k / n`, with its 95% Wilson interval (section 0.4). A share is only given for 30 or more accidents (always met here).
3. **The comparison.** The two shares and their intervals are drawn next to each other for each period; the intervals do not overlap when the difference is clear.

**Result in words.** In 2017-2024 for the combined group, **6.44%** of the accidents in the 20 hotspot 5 km2 cells are severe (interval 6.11-6.78%) against **13.42%** (13.21-13.63%) in all other cells; for the 5 x 5 km squares it is 7.63% against 14.34%. Fatal: 0.40% against 1.56% (5 km2 cells). The same pattern holds in each period and for each group.

**Why the comparison is fair (and where it is not).**

- The hotspots are chosen by the *number* of accidents, not by their severity, so there is no selection on the outcome: the hotspots are not "the places with few severe accidents" by construction.
- It is a comparison of shares *given that an accident happened*; it says nothing about the chance of having an accident.
- It is an **association**: the hotspots are in city centres where speeds are lower and traffic is slower, but speed is not in the data, so the report does not claim that speed is the reason.
- The accident class belongs to the whole accident (section 0.1).
- The accidents of a hotspot cell are not independent (they share the same streets), so the Wilson intervals are somewhat too narrow; the differences are large enough (about double) not to depend on that.
- The 20 hotspot cells are few cells with many accidents; "all other cells" is thousands of cells with few accidents each. The comparison is between *accidents in busy places* and *accidents in the rest*, not between cells.

**Checked.** The two groups of cells together are all the located accidents of the group and period (by construction, the "all cells" line of the table is the sum); the table and chart on the page and in the app show the same numbers as the saved table.

**Limits.** No correction for road type or speed (a comparison that controlled for those would need a regression, as in the main project's step 5). The result does not mean that cities are "safe": the hotspots have the most severe accidents in absolute numbers simply because they have the most accidents.

## 5. Step 5: accidents per resident (rates per municipality)

**Question.** Counts favour big places. Which places stand out when the number of residents is taken into account?

**The model.** A **rate**: accidents of the group in the municipality divided by the residents of the municipality, per 100,000 and per year.

### 5.1 The denominator: residents of every municipality and year

1. **Source.** Statbel open data (CC BY 4.0), "population by place of residence": one file per year, the population on 1 January of 2017 to 2024. The file has one row per age, sex, nationality and marital status; the residents of a municipality are the **sum** of the population column (script `01`).
2. **The 2019 mergers (#178).** On 1 January 2019 several Flemish municipalities merged and got new NIS codes. The 2017 and 2018 files still use 589 old codes, while the accident data and the outlines use the 581 current codes. The Statbel statistical sectors of 2023 solve this exactly: every sector carries the code of its old municipality (the first five characters of its `C_NIS6` code) and the current code of the municipality it now belongs to. That gives a table old code -> current code (`data/nis_old_to_2023.csv`), and the residents of merged municipalities are added up. Matching by name would not be exact for merged municipalities.
3. **Checks (in the script).** Every year has exactly 581 municipalities, all with residents; the yearly total changes by less than 2%; and the yearly totals equal the Belgian totals (11,322,088 on 1 January 2017 up to 11,763,650 on 1 January 2024), which proves that the conversion lost nobody.

### 5.2 The rate

For a municipality *m*, a group *g* and a period:

`rate = accidents of g in m / resident-years x 100,000`

where **resident-years** is the sum, over the years of the period, of the residents of *m* **in that year** (#171). It is the average yearly number of accidents per 100,000 residents. Using each year's own residents (not one fixed year) follows population growth. The numerator uses **all** accidents of the municipality (with or without coordinates).

### 5.3 Minimum numbers and the map

- Full colour and ranking from **100** accidents of the group in the period; **faded and flagged** from 30 to 99; **no rate** under 30 (section 0.5).
- The colour classes are **five quantile classes** computed on the municipalities that qualify for full colour: the class limits are chosen so that each class holds about the same number of municipalities, which keeps a very skewed distribution readable. The faded municipalities get the colour of the class their rate falls in, at lower opacity.
- For the combined group in 2017-2024, 302 municipalities qualify for full colour and 199 are faded.

### 5.4 What it shows, and how to read it

Belgium's rate for the combined group is 152 accidents per 100,000 residents per year before Covid-19, 137 during it and 152 after it: after the pandemic the rate per resident is back at its earlier level, so the rise in counts after 2021 is mostly population growth (and, for the grid, better coordinates). A municipality can be first by number and not by rate (a big city with many residents), and a small municipality can top the rate list. A comparison of the 20 municipalities with the most accidents and the 20 with the highest rate shows only a partial overlap, which is the reason for this step.

**Checked.** The municipality counts add up to all accidents of the group and period (the script stops if not); the tables on the page equal the saved results (for example Brussel 383.8 and Knokke-Heist 367.6 per 100,000 residents per year for the combined group).

**Limits.**

- **Residents are not traffic.** A tourist town or a city with many commuters (Brussel, Knokke-Heist, Gent) gets a high rate because many of the people involved do not live there. A rate per resident is not a rate per kilometre travelled.
- A rate in a small municipality moves with a few accidents, which is what the minimum numbers are for.
- Rates per resident are shown per municipality only; the grid steps (2 to 4) are not corrected for residents (a later version of the analysis did that per cell).

## 6. How the pictures, the app and the page compute

- **Pictures** (`scripts/03`): matplotlib, drawn from the saved tables with no recalculation.
- **Streamlit app** (`app.py`): builds Plotly charts from the saved tables with `charts.py` and `step1_charts.py`; filters only select rows of those tables.
- **HTML page** (`template.html`, `build_html.py`): the saved tables are packed as compact lists (the cells of each grid, group and period; the municipality numbers; the step 1 table) into one file, and the scripts in the page redraw the charts in the browser, so every combination of buttons works without a server. The severity charts are built in Python and embedded. The page needs internet only for the chart library.

## 7. How each step was verified

| Step | Check | Result |
|---|---|---|
| All | Script totals stop the run if wrong (289,532 accidents; 28,532 severe; group totals) | passed |
| 1 | Browser calculation of 1a and 1b against the Python tables | equal to 10^-6 in several scenarios |
| 2 | Cell counts add up to the located accidents; top-20 table has 20 rows and the same numbers in Python, the app and the page | passed |
| 3 | Same grid and colour scale in the three panels; persistence counted from the saved top-20 lists | passed |
| 4 | The two groups of cells together equal the "all cells" line (the located accidents); page and app show the saved table | passed |
| 5 | Resident totals equal the Belgian totals per year; municipality counts add up to the accidents of the group; page equals the saved table | passed |
| App and page | The Streamlit app was run through every view, group, grid, measure, period and ranking (155 combinations) and the step 1 filters; the HTML page was opened in a browser and every control was used | no errors |

## 8. What was deliberately not modeled

- **Causes.** Every result is an association; the Covid-19 periods are my own definition.
- **Exposure.** Residents are used as the denominator, not traffic or distance travelled (the data have neither).
- **A correction of the grid counts for missing coordinates** (section 3.3) and **rates per grid cell** (later versions of the analysis do the second).
- **Adjustment for road type, speed or conditions in step 4** (that would be the logistic models of the main project's step 5).
- **Smoothing** (kernel density) or **clustering** of the hotspots.

## 9. Glossary

- **Grid cell:** one square of the map grid; an accident belongs to exactly one cell.
- **Hotspot:** here, one of the 20 cells with the most accidents; where accidents are counted, not a risk measure.
- **Accidents per year:** the count of a period divided by the number of years of the period.
- **Log colour scale:** a colour scale where equal steps mean equal *ratios*, used because a few cells have hundreds of accidents and most have less than one.
- **Wilson interval:** a 95% interval for a share that stays valid for small counts and for shares near 0%.
- **Severe / fatal / serious:** accident classes 1-3 / 1-2 / 3.
- **Resident-years:** the residents of a place added up over the years of a period.
- **Rate per 100,000 residents per year:** accidents divided by resident-years, times 100,000.
- **Quantile classes:** map classes chosen so that each holds about the same number of areas.
- **Modifiable areal unit problem:** the result of a grid map depends on the size and the starting point of the cells.
- **Association:** two things go together; it does not show that one causes the other.

## Where to find things

- Decisions and reasons: `beslissingslogboek.md` (#169-#179, #193-#196).
- Code: `scripts/01` (residents), `02` (cells, hotspots, severity, rates), `03` (pictures), `04` (report); `charts.py`, `step1_logic.py`, `step1_charts.py`, `app.py`, `build_html.py`, `template.html`.
- Results: `results/`; pictures: `images/`; how every number was calculated: `REPORT_how_the_output_was_calculated.md`; how the folder was made: `PROCEDURE.md`.
