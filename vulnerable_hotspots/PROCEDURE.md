# Step-by-step procedure: how the vulnerable hotspots analysis was made

This file explains, in the order I did it, how the folder `vulnerable_hotspots/` was built, what each calculation does and **how to interpret it**, so you can repeat it, change it, or explain it in the no-AI conversation. Each step says **what**, **why**, **which file**, **how to interpret the result** and **how I checked it**. The calculations are explained in full in `REPORT_how_the_output_was_calculated.md`. Decisions: `beslissingslogboek.md`, #169-#192.

## 0. What was asked and decided

**Request (#187):** a new analysis in a new folder that has (a) step 1 of the focused dashboard (1a who is involved, 1b annual change), (b) step 2: a dive into the accident hotspots of vulnerable road users with filters for pre-Covid, during Covid, post-Covid and all years, with the severity of the accidents at the hotspots, on a grid of 5 km2 cells and 5 x 5 km squares instead of 500 m squares, as heat maps, corrected for the number of residents, and (c) in short: the focused dashboard's steps plus the whole of the `hotspot_deep_dive` analysis, with a procedure that interprets the calculations and a report on how the output was calculated.

**What I asked before building** (nothing was assumed):

| Question | Answer | Entry |
|---|---|---|
| Grid sizes? | Both: 5 km2 cells and 5 x 5 km squares (the 5 km2 cells I had removed from `hotspot_deep_dive` are back) | #188 |
| Which focused-dashboard parts besides 1a and 1b? | Step 2 (severity per group), the municipality top 20 of step 3b/3c, and step 4a (regional severity, province map) | #189 |
| What to deliver? | Streamlit app, HTML page (local + new private claude.ai page), scripts with tables and pictures, procedure and report (Markdown and Word) | #190 |
| Folder name? | `vulnerable_hotspots/`, self-contained | #191 |

## 1. Look at what already exists (no code yet)

Most of the work was **combining** two finished analyses:

- `focused_dashboard/`: step 1 (1a, 1b), step 2 (severity per group), municipality top 20, step 4a, built from saved results of the main project.
- `hotspot_deep_dive/` (version 2): step 1 first, hotspots per period, severity at the hotspots, residents per municipality and per 5 x 5 km square, heat maps, Streamlit app, HTML page, report. Version 2 had only the 5 x 5 km squares.

**Two things to decide while combining:** (1) bring back the 5 km2 cells next to the squares, so every part that had one grid now has two; (2) the focused dashboard's 500 m hotspot squares are **not** copied: they are replaced by the new grids.

## 2. Create the folder and copy what is needed

```bash
cd "Project 1"
mkdir -p vulnerable_hotspots/{scripts,data,results,images}
```

- From `hotspot_deep_dive/`: the four scripts, `charts.py`, `findings.py`, `app.py`, `build_html.py`, `template.html`, the step 1 modules, the map outlines, the resident tables and the downloaded Statbel files.
- From `focused_dashboard/`: `charts.py` (renamed `charts_focused.py`), `tables.py`, the municipality outline helper data, the saved results of step 2, 3b/3c and 4a (`severity_*.csv`, `geo_municipality_periods.csv`, `severity_regional_regions_provinces.csv`, the municipality tables), the province outlines and `template_extra.html` (renamed `template_focused.html`).

**Why copy and not point at the other folders?** The new folder keeps working on its own (the old folders are not changed). Two chart modules (`charts.py` for the hotspots and `charts_focused.py` for the focused parts) avoid name clashes between functions that have the same name in both.

## 3. Residents per municipality and year: `scripts/01_prepare_population.py` (unchanged)

Statbel's population on 1 January for each year 2017-2024, added up per municipality, with the 589 old municipality codes of 2017 and 2018 converted to the 581 current ones through the Statbel statistical sectors of 2023 (the 2019 mergers).

**Interpretation:** this is the denominator of every municipality rate. The yearly totals equal the Belgian totals (11,322,088 on 1 January 2017 up to 11,763,650 on 1 January 2024), which is the check that the merger conversion lost nobody.

## 4. Residents per grid cell, for both grids: `scripts/01b_cell_residents.py` (changed: two grids)

1. Statbel's residents per statistical sector (1 January 2023), 19,795 sectors; the 581 "not locatable in a sector" rows (8,046 people) are spread over the sectors of their municipality.
2. Each sector polygon is cut by the grid with `geopandas.overlay`, once for the 5 km2 cells (side 2,236 m) and once for the 5 x 5 km squares; the sector's residents are shared over the pieces by **area**.
3. Checks: the pieces of a sector add up to its area; the residents of all cells add up to the Belgian total of 11,697,557, for each grid.

```bash
python -I scripts/01b_cell_residents.py "../data/external/statbel_sectors_2023/sh_statbel_statistical_sectors_31370_20230101.shp/sh_statbel_statistical_sectors_31370_20230101.shp"
```

**Interpretation:** the residents of a cell are an estimate (people are assumed to be spread evenly inside a sector). They are only used as a denominator, so an error in one cell changes one rate, not the totals.

## 5. The hotspot analysis: `scripts/02_hotspot_analysis.py` (changed: two grids, again)

1. **Definitions copied from the main project:** an accident counts for a group if the group is road user 1 or 2, once per accident (#33); "all four" counts an accident with two of them once; severe = classes 1-3 (#116); coordinates outside Belgium are missing (#90); Wilson intervals (#74); periods pre 2017-2019, during 2020-2021, post 2022-2024 (#38), and all years.
2. **Grid cells:** the cell of an accident is `floor(x / side), floor(y / side)` for the side of each grid.
3. **Per cell** (group x period x grid): accidents, accidents per year (the periods are 3, 2 and 3 years long, so counts are divided by the years), severe, fatal and serious accidents, the residents of the cell for each year, and the rate per 100,000 residents per year (only for cells with 1,000+ residents and 30+ accidents).
4. **Hotspots:** the 20 busiest cells, with municipality and severity; the 20 highest rates; and the severity of the 20 busiest cells against all other cells.
5. **Per municipality:** accidents divided by the residents of each year, per 100,000.
6. **Checks (in the script):** the totals equal the main project (289,532 accidents; 28,532 severe; 29,897 pedestrian, 71,881 cyclist, 19,792 motorcycle, 23,258 moped accidents); the cell counts add up to the located accidents; the municipality counts add up to the accidents of the group; the residents of the cells over all years equal those of the municipalities.

```bash
python -I scripts/02_hotspot_analysis.py "../OPENDATA_MAP_2017-2024_en_flagged.csv.gz"
```

**How to interpret the results** (details in the report, sections 5 to 7):

- *The hotspots are the big cities and hardly move between the periods:* the pandemic lowered the counts everywhere but did not change where accidents concentrate.
- *Hotspots are much less often severe:* 6.4% severe in the 20 busiest 5 km2 cells against 13.4% elsewhere (7.6% against 14.3% in the 5 x 5 km squares). Accidents concentrate where speeds are low; severe accidents are spread over roads outside the cities. This is an association, speed is not in the data.
- *Per resident the busiest cells are not the highest:* Brussel's busiest 5 x 5 km square has 190 accidents per 100,000 residents a year; small towns on through roads (Stabroek 537) are higher.
- *Missing coordinates distort the comparison of the periods:* 15% of the accidents lack coordinates before Covid-19, 17% during it and 3.7% after it, so grid counts per year are understated in the first two periods. I did not "correct" this (a correction assumes that coordinates are missing at random; they are not): the apps say it, and the municipality rates use all accidents (#179).

## 6. A rule I changed while building (small numbers)

The rule I wrote down for municipality rates (a rate only with 100+ accidents of the group in the period) would leave 3 to 8 municipalities for motorcycles and 6 for mopeds during Covid-19. So: full colour and ranking from 100 accidents, faded and flagged from 30 to 99, nothing under 30 (#177). For cells: a rate needs 1,000 residents and 30 accidents (#184).

**Interpretation:** a rate or a share moves with a few accidents. The minimum numbers keep a village with 3 accidents out of the top of a ranking; "faded and flagged" keeps the information visible without pretending it is reliable.

## 7. The charts: `charts.py` and `charts_focused.py`

- `charts.py`: `fig_heatmap` and `fig_heatmap_periods` (heat map of accidents per year, of the rate per resident, or of the severe share, for the chosen grid; three periods side by side with the same colour scale), `fig_hotspot_severity` (hotspots against other cells with 95% intervals), `fig_rate_map` and `fig_rate_ranking` (municipality rates).
- `charts_focused.py`: `fig_severity_intervals` and `fig_severity_distribution` (step 2), the municipality top-20 bars, bubble map and choropleth, `fig_regional_overview` and `fig_province_map` (step 4a).
- Accidents per year and rates use a **log colour scale** (a few city cells have hundreds a year, most have less than one); the severe share a linear scale from 0 to 40%.

**Check:** I built every chart variant (groups x grids x measures x periods) without errors.

## 8. The pictures: `scripts/03_plot_heatmaps.py`

35 PNGs in `images/` with matplotlib, from the saved tables: for each of the five groups and each grid, the accidents-per-year, rate-per-resident and severe-share heat maps (three periods side by side), and the municipality rate maps. I looked at them to check that nothing was cut off.

## 9. The Streamlit app: `app.py`

One sidebar with the choice of view and the filters of that view; the main area shows one view.

| View | Filters in the sidebar |
|---|---|
| 1 Burden and annual change (1a, 1b) | years, road-user groups, "also show Unknown and Other" |
| 2 Severity per road-user group | period (all years, pre, during, post) |
| 3 Hotspot heat map | group, cell size, measure (accidents per year, per 100,000 residents of the cell, severe share), period |
| 4 Compare the three periods | group, cell size, measure |
| 5 How severe are the hotspots? | group, cell size |
| 6 Municipalities: top 20 | group, rank by (number or share), period, region, map type |
| 7 Residents: rates per municipality | group, period, rank by |
| 8 Regional severity and province map | none |

Every view has a table with a CSV download button, key findings (`findings.py`) and a "read with care" note.

```bash
python -m streamlit run app.py
```

(Use `python -m streamlit`, so the app runs in the active conda environment.)

**Test:** with Streamlit's `AppTest` I opened every view and ran every combination of group, grid, measure and period, the municipality top 20 for every group, ranking, map and a few regions and periods, the rate views for every group, period and ranking, and the step 1 filters.

## 10. The HTML page: `template.html`, `template_focused.html`, `build_html.py`

The page uses the design of the focused dashboard. `build_html.py` packs the saved tables as compact lists (the cells of each grid, group and period with their resident-years; the municipality numbers; the step 1 table) in one file; the scripts in the page draw the charts in the browser, so every combination of buttons works without a server. The severity charts are built in Python and embedded. The municipality borders are stored once and shared by all maps.

The page has the sections 1 Burden (1a, 1b), 2 Severity per group, 3 Heat map, 4 Three periods, 5 Severity of the hotspots, 6 Municipality top 20, 7 Residents, 8 Regional severity. Section 1 and the focused sections have their own filters; the left sidebar (group, cell size, measure) applies to the hotspot sections.

```bash
python build_html.py
```

**Test:** I opened the page in headless Chrome (a browser without a window that I control from a script), clicked through every control and looked at the screenshots: no console errors; the 20-cell table has 20 rows; the page shows the same numbers as the saved results (Brussel 383.8 and Knokke-Heist 367.6 accidents per 100,000 residents per year; Schoten 818.8 per 100,000 residents in the 5 km2 cells).

## 11. The report: `scripts/04_build_report.py`

Writes `REPORT_how_the_output_was_calculated.md` (and the Word version). All tables and numbers come from the saved results; nothing is typed by hand. Each section says what was calculated, how, and how to read it.

## 12. Publish the page on claude.ai

The page is published as a **new private** artifact (the earlier pages were not touched). Link: https://claude.ai/artifact/FPRzHKr2BvipQppZtLD3NG (needs the `downloads` capability for the CSV buttons).

## 13. What you can change later

| You want to... | Change this | Then |
|---|---|---|
| Another cell size | `CELL_SIZES` in `scripts/02_hotspot_analysis.py` and `charts.py`; `SIDES` in `scripts/01b_cell_residents.py` | run scripts 01b, 02, 03, 04 and `build_html.py` |
| Another period | `PERIODS` in `scripts/02_hotspot_analysis.py` and `charts.py` | the same |
| A stricter or looser small-number rule | `MIN_SHARE`, `MIN_RATE`, `MIN_CELL_RESIDENTS` (script 02 and `charts.py`) | the same |
| Newer population | the years in `scripts/01_prepare_population.py` | run scripts 01, 01b, 02, ... |
| Correct the grid counts for missing coordinates | add the correction in script 02 and say what it assumes | the same |

## Files in this folder

| File | Purpose |
|---|---|
| `scripts/01_prepare_population.py`, `01b_cell_residents.py` | residents per municipality and year; residents per cell |
| `scripts/02_hotspot_analysis.py` | cells, hotspots, severity, rates per cell and per municipality |
| `scripts/03_plot_heatmaps.py` | the PNG heat maps |
| `scripts/04_build_report.py` | the calculation report |
| `charts.py`, `charts_focused.py`, `step1_charts.py`, `step1_logic.py`, `tables.py`, `findings.py` | chart code, step 1 calculations, municipality calculations, texts |
| `app.py` | the Streamlit app |
| `template.html`, `template_focused.html`, `build_html.py`, `vulnerable_hotspots.html` | the HTML page |
| `data/`, `results/`, `images/` | inputs, saved results, pictures |
| `REPORT_how_the_output_was_calculated.md` / `.docx` | how every number was calculated and how to read it |
| `PROCEDURE.md`, `README.md` | this file; the short version |
