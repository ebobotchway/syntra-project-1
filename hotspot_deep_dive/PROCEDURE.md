# Step-by-step procedure: how the hotspot deep dive was made (version 2: step 1 first, 5 x 5 km squares, rate per square)

This file explains, in the order I did it, how the `hotspot_deep_dive/` folder was built, so you can repeat it, change it, or explain it in the no-AI conversation. Each step says **what**, **why**, **which file** and **how I checked it**. The calculations themselves are explained in `REPORT_how_the_output_was_calculated.md`. Decisions: `beslissingslogboek.md`, #169-#186.

## 0. What was asked and decided

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

### Version 2 (what changed after the first version, #180-#186)

You asked for three changes, so the folder was changed in these steps (they are described in the sections below, marked "version 2"):

1. **Step 1 first** (#181): 1a and 1b of the focused dashboard were added in front of the hotspot sections, in the Streamlit app (view 1) and on the HTML page (section 1), with their own filters (years and road-user groups).
2. **The 5 km2 cells were removed** (#182): only the 5 x 5 km squares remain, in the data, the charts, the apps, the pictures and the report. The cell-size filter is gone.
3. **A new measure: accidents per 100,000 residents of the square** (#183, #184): new script `01b` (residents per square) and new columns in `02`; the heat map, the three-period view and the top-20 table have it as a filter.

I asked before building: step 1 = 1a and 1b (not 1c); residents of a square from Statbel's sector residents of 2023 scaled to each year; a rate only from 1,000 residents and 30 accidents; and, for the rate measure, the marked squares follow the rate.

## 1. Prepare the folder

```bash
cd "Project 1"
mkdir -p hotspot_deep_dive/{scripts,data,results,images}
cp data/municipality_outlines.json hotspot_deep_dive/data/
```

Only the map outlines are copied. Everything else is made by the scripts. The large accident file stays in the main folder and is given to the scripts as an argument.

## 2. Get the residents: `scripts/01_prepare_population.py`

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

## 2b. Version 2: the residents of every 5 x 5 km square: `scripts/01b_cell_residents.py`

The municipality residents of step 2 cannot correct a square: a square can hold parts of several municipalities, and a city centre and its outskirts differ. So I used a finer source.

1. **Find the data.** Statbel publishes the residents per statistical sector (about 19,800 small areas) as `OPENDATA_SECTOREN_<year>`. I checked which years exist: 2018 and 2020-2024, not 2017 or 2019, and each year follows that year's sector boundaries. The sector map of the main project is the one of 2023, so I used the residents of 1 January 2023.
2. **Match sectors to the map.** The sector code of the file equals the code on the map (`CS01012023`). One row per municipality is "not to be located in a sector" (8,046 people in total, 0.07%): they are spread over the sectors of their municipality in proportion to the sector residents.
3. **Cut the sectors by the grid.** Each sector polygon is cut by the 5 x 5 km grid (`geopandas.overlay`) and the sector's residents are shared over the pieces by area (people are assumed evenly spread inside a sector).
4. **Scale to every year.** In script 02, the residents of each piece are multiplied for each year by the growth of its municipality (residents that year / residents in 2023), using the municipality table of step 2.
5. **Checks (in the scripts):** every sector of the map has residents; the pieces of a sector add up to its area; the squares add up to the Belgian total of 1 January 2023 (11,697,557); and the residents of all squares, added up over all years, equal the residents of all municipalities added up over all years.

```bash
python -I scripts/01b_cell_residents.py "../data/external/statbel_sectors_2023/sh_statbel_statistical_sectors_31370_20230101.shp/sh_statbel_statistical_sectors_31370_20230101.shp"
```

Result: `data/cell_residents_2023.csv` (residents of 2023 per square and municipality).

## 3. The analysis: `scripts/02_hotspot_analysis.py`

1. **Definitions copied from the main project:** an accident counts for a group if the group is road user 1 or 2 (#33); severe = classes 1 to 3 (#116); coordinates outside Belgium are missing (#90); Wilson intervals (#74); periods pre 2017-2019, during 2020-2021, post 2022-2024 (#38).
2. **Grid.** The squares have a side of 5,000 m; the square of an accident is `floor(x / 5000), floor(y / 5000)`. (Version 1 also had 5 km2 cells with a side of 2,236 m; they were removed in version 2, #182.)
3. **Per square** (for each group and period): accidents, accidents per year (divided by the number of years, because the periods are 3, 2 and 3 years long), severe, fatal and serious accidents, and (version 2) the residents of the square, the resident-years and the accidents per 100,000 residents per year (only for squares with 1,000+ residents and 30+ accidents).
4. **Hotspots:** the 20 busiest squares, with their municipality and severity; the severity of those 20 squares against all other squares; and (version 2) the 20 highest rates among the qualifying squares.
5. **Per municipality** (using all accidents, with or without coordinates): accidents divided by the residents of each year, per 100,000.
6. **Checks (in the script):** the totals equal the main project (289,532 accidents; 28,532 severe; 29,897 pedestrian, 71,881 cyclist, 19,792 motorcycle, 23,258 moped accidents); the square counts add up to the located accidents; the municipality counts add up to the accidents of the group.

```bash
python -I scripts/02_hotspot_analysis.py "../OPENDATA_MAP_2017-2024_en_flagged.csv.gz"
```

Results in `results/`: `grid_cells.csv`, `hotspots_top20.csv` (with a column `ranking`: by accidents or by rate), `hotspot_severity_summary.csv`, `coordinate_coverage.csv`, `municipality_rates.csv`.

## 4. What the first results showed, and what I did about it

Two things I noticed in the numbers before building any chart:

- **Coordinates are missing very unevenly over time:** 15% of the accidents lack coordinates before Covid-19, 17% during it and only 3.7% after it. Grid counts per year would therefore rise by 16% from the pre to the post period, while all accidents rise by only 2.5%. I did not "correct" the counts (a correction would assume that missing coordinates are random, and they are not: more in Wallonia). Instead, every grid view says it, and the resident rates use all accidents.
- **The strict small-number rule was too strict.** The rule I wrote down in #175 (a rate only with 100 accidents of the group in the period) leaves 3 to 8 municipalities for motorcycles and 6 for mopeds during Covid-19. I changed it (#177): full colour and ranking from 100 accidents, faded and flagged from 30 to 99, nothing under 30. This is the project's usual "hide under 30, flag under 100".

## 5. The charts: `charts.py`

One module builds every chart from the saved tables (nothing is recalculated):

- `fig_heatmap` and `fig_heatmap_periods`: the heat map of accidents per year or of accidents per 100,000 residents of the square (both on a log colour scale, because a few city squares have hundreds a year and most have less than one) or of the severe share (linear, squares with 30+ accidents), with the 20 busiest squares (or, for the rate, the 20 highest rates) marked; and the three periods side by side on the same grid and colour scale.
- `fig_hotspot_severity`: severe, fatal and serious share in the hotspot cells against the other cells, with 95% intervals.
- `fig_rate_map` and `fig_rate_ranking`: municipalities coloured by accidents per 100,000 residents per year (5 quantile classes), and the top 20 by rate or by number.

**Check:** I built every chart variant (groups x measures x periods) without errors.

## 6. The pictures: `scripts/03_plot_heatmaps.py`

Draws 20 PNGs in `images/` from the saved tables with matplotlib: for each group, the accidents-per-year heat maps, the rate-per-square heat maps and the severe-share heat maps (three periods side by side), and the municipality rate maps. I looked at them to check that nothing was cut off.

## 7. The Streamlit app: `app.py`

Design: one sidebar with the choice of view and the filters of that view; the main area shows one view.

| View | Filters in the sidebar |
|---|---|
| 1 Burden and annual change (1a, 1b) (version 2) | years, road-user groups, "also show Unknown and Other" |
| 2 Hotspot heat map | group, measure (accidents per year, per 100,000 residents of the square, severe share), period |
| 3 Compare the three periods | group, measure |
| 4 How severe are the hotspots? | group |
| 5 Residents: rates per municipality | group, period, rank by |

Every view has a table with a CSV download button, key findings (`findings.py`) and a "read with care" note. It reads the saved tables and needs no accident file.

```bash
python -m streamlit run app.py
```

(Use `python -m streamlit`, so the app runs in the active conda environment.)

**Test:** with Streamlit's `AppTest` I opened every view, every group, measure, period and ranking, and the step 1 filters (another year range, a single year, no groups, Unknown on): no errors.

## 8. The HTML page: `template.html` and `build_html.py`

The page uses the same design as the focused dashboard. `build_html.py` packs the saved tables as compact lists (the squares of each group and period, with their resident-years; the municipality numbers; the step 1 table) in one file, and the scripts in the page draw step 1, the heat maps and the rate maps in the browser, so every combination of buttons works without a server. The severity charts are built in Python and embedded. In version 2 the step 1 sections and script were taken from the focused dashboard's template, with their own status line and download buttons so they do not interfere with the hotspot sections.

```bash
python build_html.py
```

**Test:** I opened the page in headless Chrome, clicked through every control and looked at the screenshots: no console errors; the 20-cell table has 20 rows; the page shows the same numbers as the saved results (Brussel 383.8 and Knokke-Heist 367.6 accidents per 100,000 residents per year for all four groups).

## 9. The reports

- `scripts/04_build_report.py` writes `REPORT_how_the_output_was_calculated.md` (and the Word version). All tables and numbers come from the saved results; nothing is typed by hand.
- This file explains how the folder was made.

## 10. Publish the page on claude.ai

The page was published as a **new private** artifact (the earlier pages were not touched). Link: https://claude.ai/artifact/CDg8GqzbHpEPuQE7U2E9Jx (needs the `downloads` capability for the CSV buttons).

## 11. What you can change later

| You want to... | Change this | Then |
|---|---|---|
| Another square size | `CELL_SIZES` in `scripts/02_hotspot_analysis.py` and `charts.py`, and `SIDE` in `scripts/01b_cell_residents.py` | run scripts 01b, 02, 03, 04 and `build_html.py` |
| Another period | `PERIODS` in `scripts/02_hotspot_analysis.py` and `charts.py` | the same |
| A stricter or looser small-number rule | `MIN_SHARE`, `MIN_RATE` and `MIN_CELL_RESIDENTS` (script 02 and `charts.py`) | the same |
| Newer population | the years in `scripts/01_prepare_population.py` | run script 01, then the rest |
| Correct the grid counts for missing coordinates | add the correction in script 02 and say what it assumes | the same |

## Files in this folder

| File | Purpose |
|---|---|
| `scripts/01_prepare_population.py` | residents per municipality and year |
| `scripts/01b_cell_residents.py` | residents per 5 x 5 km square (version 2) |
| `scripts/02_hotspot_analysis.py` | cells, hotspots, severity, municipality rates |
| `scripts/03_plot_heatmaps.py` | the PNG heat maps |
| `scripts/04_build_report.py` | the calculation report |
| `charts.py`, `findings.py`, `app.py`, `step1_logic.py`, `step1_charts.py` | the Plotly charts, the texts, the Streamlit app, step 1 (copied from the focused dashboard) |
| `template.html`, `build_html.py`, `hotspot_deep_dive.html` | the HTML page |
| `data/`, `results/`, `images/` | inputs, saved results, pictures |
| `REPORT_how_the_output_was_calculated.md` / `.docx` | how every number was calculated |
| `PROCEDURE.md`, `README.md` | this file; the short version |
