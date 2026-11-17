# Step-by-step procedure: how the analysis of accident hotspots for vulnerable road users with step 1 was made

This file explains, in the order I did it, how the `hotspot_dive_deep_osm_4steps/` folder was built (the analysis of accident hotspots for vulnerable road users plus step 1 of the focused dashboard), so you can repeat it, change it, or explain it in the no-AI conversation. Each step says **what**, **why**, **which file** and **how I checked it**. The calculations themselves are explained in `REPORT_how_the_output_was_calculated.md`. Decisions: `beslissingslogboek.md`, #169-#178.

## 0b. The OpenStreetMap version of this folder (#225)

**Request (#225):** "create the same analysis for me using the open source map for the analysis for the hotspots. create a new folder for me". I asked three questions first (#225): what the open source map is used for, how the tiles are loaded, and how much to copy. Answers: a basemap under the squares (hotspots stay the 5 x 5 km squares), live OpenStreetMap tiles, a full copy.

1. **Copy.** `hotspot_dive_deep_osm/` was copied to `hotspot_dive_deep_osm/` (scripts, results, docs); the HTML page was rebuilt as `hotspot_deep_dive_osm.html`.
2. **Convert the squares.** Accidents and squares are in Belgian Lambert 1972 (metres); OpenStreetMap needs longitude and latitude. `scripts/06_grid_lonlat.py` converts the four corners of every square with `pyproj` (EPSG:31370 to EPSG:4326) into `data/grid_lonlat.csv`. Check: Brussels comes out at 4.350 E, 50.850 N. No accident is moved; the counts in `results/` do not change.
3. **Draw on the map.** In `charts.py` (app) and `template.html` (page) the heat map changed from a Plotly `heatmap` on a metre grid to a `choroplethmap`: one polygon per square, 70% opaque so streets show through, on the `open-street-map` style. The colours, the log scale, the severe-share scale, the hover texts and the top 20 / top 40 filter are the same.
4. **Mark the hotspots.** A map has no hollow square markers, and the border of a map polygon fades with its fill (I saw invisible borders in the first test), so each marked square is a coloured line around the square (yellow, or green on the severe-share map, in step 2; red, orange, black in step 3) plus an almost invisible point at its centre that carries the hover text.
5. **Unchanged:** the ranking bar charts, steps 1, 4, 4b and 5, and the step 5 municipality map.
6. **Checked:** the Streamlit app was run for steps 2 and 3, for all groups, top 20 and top 40, without errors; the page was opened in headless Chrome with software WebGL (maps need WebGL) and the screenshots of step 2 (counts and severe share) and step 3 were looked at; the browser console showed no errors.
7. **Limits.** The maps need internet for the tiles. The pictures in `images/` (script 03, used in the report) are still the plain grid maps without OpenStreetMap, because a printed picture cannot load map tiles from the internet. The pictures in the report and the older description of the maps in sections below still talk about the plain grid.

## 0c. Severity inside the step 5 ranking bars (#226)

**Request (#226):** "combine the severity with the analysis in step 5 so the result will not be only top accident per 100,000 residents per year but also the severity with the graph for the severity per 100,000 residents per year embeded in the top accident per 100,000 residents per year bars". I asked three questions first: which folder (answer: both, `hotspot_dive_deep_final` and `hotspot_dive_deep_osm`), what the severity part shows (severe per 100,000 residents per year) and whether the ranking changes (no: same ranking by all accidents).

1. **Calculation.** Severe accidents per 100,000 residents per year = severe (fatal + serious) / resident-years x 100,000, from `results/municipality_rates.csv` (columns `severe` and `resident_years`); the same denominator as the rate.
2. **Chart.** In `charts.py` (`fig_rate_ranking`) and `template.html` (`rateRank`) the bars are drawn with `barmode="overlay"`: a wide light-blue bar for all accidents per 100,000 and a narrower orange bar (the severity colour of the app) inside it for the severe ones. The label next to the bar reads "384 per 100,000, severe 24 (715 a year)". Ranking by the count is unchanged.
3. **Texts.** Two new key findings (severe rate for Belgium; Brussel versus Eeklo, Heuvelland, Kaprijke) and a care note on small severe counts; the captions of step 5 explain the dark bar. The numbers in the findings were calculated from the saved table (Belgium 18.0; Brussel 24, 111th of 302; Eeklo 54).
4. **Checked.** The Streamlit step 5 was run for all groups, all periods and both ranking options without errors; the page was opened in headless Chrome and the new chart was looked at.

## 0d. The four-step version of this folder (#227)

**Request (#227):** "remove step 2 and re number the panel, it is redundant when you present it with step 3, create new folder". I asked three questions first: which version to copy (the OpenStreetMap version), what happens to the parts only step 2 had (dropped: the 'All years' map, the single-period severe-share map, its ranking bars and the table of the busiest squares) and how to number (1, 2, 3, 3b, 4).

1. **Copy.** `hotspot_dive_deep_osm/` was copied to `hotspot_dive_deep_osm_4steps/`.
2. **App and page.** The step 2 view (app) and section 2 (page) were removed, with the Period buttons and the single-period functions; the Key findings and the care note of that section moved under the three-period maps. The views are numbered 1, 2 (three periods), 3 (severity, 3b regression), 4 (residents); the page navigation, the section tags and the filter note use the same numbers. The page no longer carries the all-years cell data (the all-years period stays on the residents step).
3. **Charts.** `fig_heatmap` and `fig_hotspot_ranking` (only the removed step used them) were deleted from `charts.py`; nothing in `scripts/` changed, so the numbers are identical.
4. **Docs.** In `TECHNICAL_UNDERPINNINGS.md` the grid, the counts and the hotspot method (formerly step 2) are kept as section 2.1 of the new step 2, followed by 2.2 (the periods) and 2.3 (the weakness); the later steps and the checks table are renumbered. The report keeps its section order (it follows the scripts) and states the new step numbers.
5. **Checked.** The Streamlit app was run through all four views with every group and both Hotspot settings without errors; the page was opened in headless Chrome: the navigation reads 1 to 4, the section headings are numbered 1, 1a, 1b, 2, 3, 4 and the console shows no errors.

## 0. What was asked and decided

**Request for this folder (#193):** take the hotspot deep dive and add step 1 of the focused dashboard as its step 1, change nothing else, in a new folder, with the procedure and the report on how the output was calculated.

| Question for this folder | Answer | Entry |
|---|---|---|
| Which version of the hotspot deep dive is the base? | The original version 1 (both grids, rates per municipality), restored from git, without the later changes of version 2 | #194 |
| Which parts of step 1? | 1a and 1b, as in the focused dashboard | #195 |
| Folder and outputs? | `hotspot_dive_deep_osm_4steps/`, with the app, the page, the pictures, this procedure and the report; no new claude.ai page unless asked | #196 |

**The rest of this file** describes the hotspot deep dive itself (its request #169 and the questions I asked then), because that part is unchanged. The only new part is section 2.


**Request (#169):** a new analysis in a new folder: hotspots of accidents with vulnerable road users before, during and after Covid-19; the severity of the accidents at the hotspots (step 2 integrated); a 5 km2 grid instead of 500 m squares; results as heat maps; and, so that the results are not biased, the number of residents of the municipalities.

**What I asked before building** (nothing was assumed):

| Question | Answer | Entry |
|---|---|---|
| What does "5km2" mean? | Both: cells of 5 km2 in area and squares of 5 km x 5 km | #170 |
| How are residents used? | Rates per municipality, plus the grid counts | #171 |
| Which residents figure? | The residents of each year | #171 |
| How is severity shown? | Severe share per cell, fatal and serious in tables | #172 |
| Which groups? | The four groups plus a combined view | #173 |
| What is delivered? | Scripts, tables and PNGs; Streamlit app; HTML page plus a new private claude.ai page; this procedure; and a calculation report | #174 |
| Small numbers? | The project rules (adapted in #177, see step 5) | #175, #177 |
| Folder? | `hotspot_deep_dive/`, self-contained | #176 |

## 1. Prepare the folder

(This describes how the original hotspot deep dive folder was prepared. For this folder the base was restored from git instead and step 1 was added, see section 2.)

```bash
cd "Project 1"
mkdir -p hotspot_deep_dive/{scripts,data,results,images}
cp data/municipality_outlines.json hotspot_deep_dive/data/
```

Only the map outlines are copied. Everything else is made by the scripts. The large accident file stays in the main folder and is given to the scripts as an argument.

## 2. Add step 1 of the focused dashboard (the only change)

Step 1 of the focused dashboard has two parts: 1a "who is involved" (accidents per road-user group) and 1b "annual change" (accidents per year, index with 2017 = 100, pre and post period). It was added without touching the hotspot analysis:

1. **Restore the base.** `git archive ef10089 hotspot_deep_dive | tar -x -C hotspot_dive_deep_osm_4steps --strip-components=1` copies the original version 1 into the new folder (the commit with the first delivery), so nothing of version 2 is in it.
2. **Copy the step 1 code and data** from the focused dashboard: `step1_logic.py` (the calculations: totals, yearly counts, index, pre and post averages), `step1_charts.py` (the 1a bars and the 1b small multiples), `data/dashboard_data.csv` (accidents per road-user group, year and month) and `results/accidents_per_road_user.csv` (the order of the groups).
3. **Streamlit app (`app.py`):** a new first view "1 Burden and annual change (1a, 1b)" with its own sidebar filters (years, road-user groups, "also show Unknown and Other"); the group filter of the other views is hidden in this view; the hotspot views are renumbered 2 to 5. The key findings texts of step 1 were added to `findings.py`.
4. **HTML page (`template.html`, `build_html.py`):** the step 1 sections (1a, 1b) and their script were taken from the focused dashboard's page; they have their own filter card inside section 1, their own status line and download buttons, so they do not interfere with the hotspot sections; the hotspot sections are renumbered 2 to 5. `build_html.py` packs the step 1 table in the page.
5. **Report (`scripts/04_build_report.py`):** a new section "Step 1" with a table calculated from the saved step 1 table; the later sections are renumbered.

**Interpretation of step 1:** the shares add up to more than 100% because one accident can involve two groups; these are counts, not rates; nearly every group drops in 2020 and bicycles and mopeds end above their 2017 level; "Unknown" more than doubles, so part of the decline of the named groups may be recording that moves into "Unknown".

**How I checked it:** the step 1 table adds up to 289,532 accidents (checked in the report script); the Streamlit app was run through every view and every filter of the hotspot views (the same combinations as for version 1) and the step 1 filters (another year range, a single year, no groups chosen, Unknown on); the HTML page was opened in headless Chrome and every control was used: no errors. The only error I saw came from my own test clicking two filters in the same millisecond, which a person cannot do; with a pause between clicks there are none.

**What did not change:** the scripts 01 to 03, `charts.py`, the saved results, the pictures and the findings of the hotspot analysis are exactly those of version 1.

## 2b. Change made later: persistence colours of the hotspot markers (#202-#204)

In the three-period heat maps (and in the single-period heat map) the 40 marked cells are coloured by **how many of the three periods the same cell is among the 40 busiest**: red = all 3, orange = 2, black = 1 (gray = none of the three, only possible in the all-years view). Steps: (1) `persistence()` in `charts.py` counts for every cell in how many of the three periods' top-40 lists it appears (a cell is its grid column and row); (2) `hotspot_markers()` draws one trace per class, so each colour has a legend entry; (3) the same logic is in `template.html` (`persistence()`, `markerTraces()`, keyed on the cell centre) and in `scripts/03_plot_heatmaps.py`, which also draws a legend; (4) captions in `app.py`, the page and the report explain the colours. Nothing else changed: the scripts 01 and 02, the saved results and all numbers are the same.

## 3. Get the residents: `scripts/01_prepare_population.py`

1. **Find the data.** The earlier analysis had no population figures. Statbel (the Belgian statistical office) publishes the population of every municipality on 1 January, one file per year (CC BY 4.0). I checked that the files for 2017 to 2024 exist with the same address pattern.
2. **Download and add up.** The script downloads the 8 zip files (to `raw_population/`, not part of the repository, 21 MB) and adds the residents per municipality (the file has one row per age, sex, nationality and marital status).
3. **Two traps, both handled:**
   - The 2022 file is in another text encoding (Windows-1252) and the 2017 and 2018 files use other column names.
   - **The 2019 mergers:** the 2017 and 2018 files still use 589 old municipality codes, while the accident data uses the 581 current codes. The Statbel statistical sectors of 2023 (already in the main project) carry both codes, which gives an exact table old code -> current code (`data/nis_old_to_2023.csv`). Matching by name would not be exact for merged municipalities (#178).
4. **Checks (in the script):** every year has exactly 581 municipalities, all with residents, the yearly total changes by less than 2%, and the totals equal the official Belgian totals (11,322,088 on 1 January 2017 up to 11,763,650 on 1 January 2024).

```bash
python -I scripts/01_prepare_population.py "../data/external/statbel_sectors_2023/sh_statbel_statistical_sectors_31370_20230101.shp/sh_statbel_statistical_sectors_31370_20230101.shp"
```

Result: `data/population_by_municipality.csv` (581 municipalities x 8 years).

## 4. The analysis: `scripts/02_hotspot_analysis.py`

1. **Definitions copied from the main project:** an accident counts for a group if the group is road user 1 or 2 (#33); severe = classes 1 to 3 (#116); coordinates outside Belgium are missing (#90); Wilson intervals (#74); periods pre 2017-2019, during 2020-2021, post 2022-2024 (#38).
2. **Grid.** Cell side = sqrt(5) x 1,000 m = 2,236 m for the 5 km2 cells and 5,000 m for the squares; the cell of an accident is `floor(x / side), floor(y / side)`.
3. **Per cell** (for each size, group and period): accidents, accidents per year (divided by the number of years, because the periods are 3, 2 and 3 years long), severe, fatal and serious accidents.
4. **Hotspots:** the 40 busiest cells, with their municipality and severity; and the severity of those 40 cells against all other cells.
5. **Per municipality** (using all accidents, with or without coordinates): accidents divided by the residents of each year, per 100,000.
6. **Checks (in the script):** the totals equal the main project (289,532 accidents; 28,532 severe; 29,897 pedestrian, 71,881 cyclist, 19,792 motorcycle, 23,258 moped accidents); the cell counts add up to the located accidents; the municipality counts add up to the accidents of the group.

```bash
python -I scripts/02_hotspot_analysis.py "../OPENDATA_MAP_2017-2024_en_flagged.csv.gz"
```

Results in `results/`: `grid_cells.csv`, `hotspots_top40.csv`, `hotspot_severity_summary.csv`, `coordinate_coverage.csv`, `municipality_rates.csv`.

> **Change #213:** the app and the HTML page no longer have a cell-size filter (only the 5 x 5 km squares are shown) and have a new filter 'Hotspots: top 20 / top 40'. Scripts 02, 03 and 04 still calculate both cell sizes; script 02 and 05 write results for the top 20 and the top 40 (column `top_n`), the written findings are calculated from them (`findings.py`).

> **Change #218:** the regression (script 05, step 4b) now separates three kinds of night (public lighting lit / present but not lit / none, reference daylight) and has a road-surface term (reference dry or clean; wet, dirty, ice or snow; a combination takes its worst part, unknown surface left out). Rows with an unknown surface drop out of the model, so it uses fewer rows than before.

> **Change #216:** in step 2 (single-period map and its ranking bars) all marked squares and bars are yellow; the persistence colours (red/orange/black) are only used in step 3 (`single=True` in `hotspot_markers` and `ranking_bars`).

## 4b. Change made later: a logistic regression for severity in step 4 (`scripts/05_logistic_model.py`, #205-#209)

You asked for a binary logistic regression in step 4: severity (fatal + serious injury) = 1, otherwise 0, explained by hotspot, period, group and two more variables. Choices (all asked first): extra variables **built-up area** (inside/outside) and **light condition** (daylight, dawn/dusk, night); hotspot = the accident is in one of the **40 busiest 5 x 5 km squares of its own group and period**; group = the four groups, an accident counts in a group if road user 1 or 2 is of that group, so an accident with two groups is a row in both.

1. **Script:** `python -I scripts/05_logistic_model.py "../OPENDATA_MAP_2017-2024_en_flagged.csv.gz"` reads the accidents, links each accident to its 5 x 5 km square, marks the hotspot squares from `results/hotspots_top40.csv`, leaves out accidents without coordinates or with unknown built-up area or light, builds the design matrix (reference categories: pre Covid-19, cyclists, inside built-up area, daylight) and fits the model.
2. **Standard errors:** cluster-robust by municipality (not by accident as first proposed: municipality clusters also cover the double rows and the resemblance of accidents in one municipality).
3. **Results** in `results/`: `logit_severity_model.csv` (coefficients and odds ratios), `logit_severity_fit.csv`, `logit_hotspot_adjusted.csv` (hotspot effect in percentage points), `logit_severity_descriptives.csv`, `logit_selection.csv`.
4. **Shown in:** block 4b of view 4 of the Streamlit app (forest plot, table, the percentage-point effect, the selection and the plain shares) and the same block in section 3 of the HTML page; the report (section 5b) and the technical underpinnings (section 4b) explain the calculation. The block does not follow the group filter (it is one model for the four groups) but it does follow the hotspots filter: script 05 fits the model once with the top 20 and once with the top 40 as the definition of a hotspot (#213). A term that is not significant at 5% (p of 0.05 or more) is drawn as a hollow gray dot (#210).
5. **Result:** the odds of a severe accident in a hotspot square are 0.59 times those elsewhere (95% interval 0.53 to 0.65) with the other variables held equal; 9.2% against 14.6% severe in percentage points. (Top 20 at first: 0.55; the hotspot lists were enlarged to 40 later, #211.)

## 5. What the first results showed, and what I did about it

Two things I noticed in the numbers before building any chart:

- **Coordinates are missing very unevenly over time:** 15% of the accidents lack coordinates before Covid-19, 17% during it and only 3.7% after it. Grid counts per year would therefore rise by 16% from the pre to the post period, while all accidents rise by only 2.5%. I did not "correct" the counts (a correction would assume that missing coordinates are random, and they are not: more in Wallonia). Instead, every grid view says it, and the resident rates use all accidents.
- **The strict small-number rule was too strict.** The rule I wrote down in #175 (a rate only with 100 accidents of the group in the period) leaves 3 to 8 municipalities for motorcycles and 6 for mopeds during Covid-19. I changed it (#177): full colour and ranking from 100 accidents, faded and flagged from 30 to 99, nothing under 30. This is the project's usual "hide under 30, flag under 100".

## 6. The charts: `charts.py`

One module builds every chart from the saved tables (nothing is recalculated):

- `fig_heatmap` and `fig_heatmap_periods`: the heat map of accidents per year (log colour scale, because a few city cells have hundreds a year and most have less than one) or of the severe share (linear, cells with 30+ accidents), with the 40 busiest cells marked; and the three periods side by side on the same grid and colour scale.
- `fig_hotspot_severity`: severe, fatal and serious share in the hotspot cells against the other cells, with 95% intervals.
- `fig_rate_map` and `fig_rate_ranking`: municipalities coloured by accidents per 100,000 residents per year (5 quantile classes), and the top 20 by rate or by number.

**Check:** I built all 170 chart variants (sizes x groups x measures x periods) without errors.

## 7. The pictures: `scripts/03_plot_heatmaps.py`

Draws 25 PNGs in `images/` from the saved tables with matplotlib: for each group, the accidents-per-year heat maps and the severe-share heat maps (both cell sizes, three periods side by side), and the municipality rate maps. I looked at them and fixed nothing was cut off.

## 8. The Streamlit app: `app.py`

Design: one sidebar with the choice of view and the filters of that view; the main area shows one view.

| View | Filters in the sidebar |
|---|---|
| 1 Burden and annual change (1a, 1b) (added, step 1 of the focused dashboard) | years, road-user groups, "also show Unknown and Other" |
| 2 Hotspot heat map | group, hotspots (top 20 / top 40), measure, period |
| 3 Compare the three periods | group, hotspots (top 20 / top 40), measure |
| 4 How severe are the hotspots? | group, hotspots (top 20 / top 40; also steers the regression 4b) |
| 5 Residents: rates per 100,000 | group, period, rank by |

Every view has a table with a CSV download button, key findings (`findings.py`) and a "read with care" note. It reads the saved tables and needs no accident file.

```bash
python -m streamlit run app.py
```

(Use `python -m streamlit`, so the app runs in the active conda environment.)

**Test:** with Streamlit's `AppTest` I opened every view, every group, every cell size, measure, period and ranking, 100+ combinations: no errors.

## 9. The HTML page: `template.html` and `build_html.py`

The page uses the same design as the focused dashboard. `build_html.py` packs the saved tables as compact lists (the cells of each size, group and period; the municipality numbers; the residents) in one file, and the script in the page draws the heat maps and the rate maps in the browser, so every combination of buttons works without a server. The severity charts are built in Python and embedded.

```bash
python build_html.py
```

**Test:** I opened the page in headless Chrome, clicked through every control and looked at the screenshots: no console errors; the 40-cell table has 40 rows; the page shows the same numbers as the saved results (Brussel 383.8 and Knokke-Heist 367.6 accidents per 100,000 residents per year for all four groups).

## 10. The reports

- `scripts/04_build_report.py` writes `REPORT_how_the_output_was_calculated.md` (and the Word version). All tables and numbers come from the saved results; nothing is typed by hand.
- This file explains how the folder was made.

## 11. Publish the page on claude.ai

The page of this folder is **not published** (you did not ask for it). The page published earlier, https://claude.ai/artifact/CDg8GqzbHpEPuQE7U2E9Jx, is the hotspot deep dive version 1 without step 1 and is unchanged. Say if you want this page published as a new private artifact.

## 12. What you can change later

| You want to... | Change this | Then |
|---|---|---|
| Another cell size | `CELL_SIZES` in `scripts/02_hotspot_analysis.py` and in `charts.py` | run scripts 02, 03, 04 and `build_html.py` |
| Another period | `PERIODS` in `scripts/02_hotspot_analysis.py` and `charts.py` | the same |
| A stricter or looser small-number rule | `MIN_SHARE` and `MIN_RATE` (script 02 and `charts.py`) | the same |
| Newer population | the years in `scripts/01_prepare_population.py` | run script 01, then the rest |
| Correct the grid counts for missing coordinates | add the correction in script 02 and say what it assumes | the same |

## Files in this folder

| File | Purpose |
|---|---|
| `scripts/01_prepare_population.py` | residents per municipality and year |
| `scripts/02_hotspot_analysis.py` | cells, hotspots, severity, municipality rates |
| `scripts/03_plot_heatmaps.py` | the PNG heat maps |
| `scripts/05_logistic_model.py` | The logistic regression of severity (step 4b); run after script 02 |
| `scripts/05_logistic_model.py` | the logistic regression of severity (step 4b); run before script 04 |
| `scripts/04_build_report.py` | the calculation report (with the step 1 section and 5b) |
| `charts.py`, `findings.py`, `app.py`, `step1_logic.py`, `step1_charts.py` | the Plotly charts, the texts, the Streamlit app, step 1 (copied from the focused dashboard) |
| `template.html`, `build_html.py`, `hotspot_deep_dive.html` | the HTML page |
| `data/`, `results/`, `images/` | inputs, saved results, pictures |
| `REPORT_how_the_output_was_calculated.md` / `.docx` | how every number was calculated |
| `PROCEDURE.md`, `README.md` | this file; the short version |
