# Step-by-step procedure: how the hotspot deep dive was made

This file explains, in the order I did it, how the `hotspot_deep_dive/` folder was built, so you can repeat it, change it, or explain it in the no-AI conversation. Each step says **what**, **why**, **which file** and **how I checked it**. The calculations themselves are explained in `REPORT_how_the_output_was_calculated.md`. Decisions: `beslissingslogboek.md`, #169-#178.

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

## 3. The analysis: `scripts/02_hotspot_analysis.py`

1. **Definitions copied from the main project:** an accident counts for a group if the group is road user 1 or 2 (#33); severe = classes 1 to 3 (#116); coordinates outside Belgium are missing (#90); Wilson intervals (#74); periods pre 2017-2019, during 2020-2021, post 2022-2024 (#38).
2. **Grid.** Cell side = sqrt(5) x 1,000 m = 2,236 m for the 5 km2 cells and 5,000 m for the squares; the cell of an accident is `floor(x / side), floor(y / side)`.
3. **Per cell** (for each size, group and period): accidents, accidents per year (divided by the number of years, because the periods are 3, 2 and 3 years long), severe, fatal and serious accidents.
4. **Hotspots:** the 20 busiest cells, with their municipality and severity; and the severity of those 20 cells against all other cells.
5. **Per municipality** (using all accidents, with or without coordinates): accidents divided by the residents of each year, per 100,000.
6. **Checks (in the script):** the totals equal the main project (289,532 accidents; 28,532 severe; 29,897 pedestrian, 71,881 cyclist, 19,792 motorcycle, 23,258 moped accidents); the cell counts add up to the located accidents; the municipality counts add up to the accidents of the group.

```bash
python -I scripts/02_hotspot_analysis.py "../OPENDATA_MAP_2017-2024_en_flagged.csv.gz"
```

Results in `results/`: `grid_cells.csv`, `hotspots_top20.csv`, `hotspot_severity_summary.csv`, `coordinate_coverage.csv`, `municipality_rates.csv`.

## 4. What the first results showed, and what I did about it

Two things I noticed in the numbers before building any chart:

- **Coordinates are missing very unevenly over time:** 15% of the accidents lack coordinates before Covid-19, 17% during it and only 3.7% after it. Grid counts per year would therefore rise by 16% from the pre to the post period, while all accidents rise by only 2.5%. I did not "correct" the counts (a correction would assume that missing coordinates are random, and they are not: more in Wallonia). Instead, every grid view says it, and the resident rates use all accidents.
- **The strict small-number rule was too strict.** The rule I wrote down in #175 (a rate only with 100 accidents of the group in the period) leaves 3 to 8 municipalities for motorcycles and 6 for mopeds during Covid-19. I changed it (#177): full colour and ranking from 100 accidents, faded and flagged from 30 to 99, nothing under 30. This is the project's usual "hide under 30, flag under 100".

## 5. The charts: `charts.py`

One module builds every chart from the saved tables (nothing is recalculated):

- `fig_heatmap` and `fig_heatmap_periods`: the heat map of accidents per year (log colour scale, because a few city cells have hundreds a year and most have less than one) or of the severe share (linear, cells with 30+ accidents), with the 20 busiest cells marked; and the three periods side by side on the same grid and colour scale.
- `fig_hotspot_severity`: severe, fatal and serious share in the hotspot cells against the other cells, with 95% intervals.
- `fig_rate_map` and `fig_rate_ranking`: municipalities coloured by accidents per 100,000 residents per year (5 quantile classes), and the top 20 by rate or by number.

**Check:** I built all 170 chart variants (sizes x groups x measures x periods) without errors.

## 6. The pictures: `scripts/03_plot_heatmaps.py`

Draws 25 PNGs in `images/` from the saved tables with matplotlib: for each group, the accidents-per-year heat maps and the severe-share heat maps (both cell sizes, three periods side by side), and the municipality rate maps. I looked at them and fixed nothing was cut off.

## 7. The Streamlit app: `app.py`

Design: one sidebar with the choice of view and the filters of that view; the main area shows one view.

| View | Filters in the sidebar |
|---|---|
| 1 Hotspot heat map | group, cell size, measure, period |
| 2 Compare the three periods | group, cell size, measure |
| 3 How severe are the hotspots? | group, cell size |
| 4 Residents: rates per 100,000 | group, period, rank by |

Every view has a table with a CSV download button, key findings (`findings.py`) and a "read with care" note. It reads the saved tables and needs no accident file.

```bash
python -m streamlit run app.py
```

(Use `python -m streamlit`, so the app runs in the active conda environment.)

**Test:** with Streamlit's `AppTest` I opened every view, every group, every cell size, measure, period and ranking, 100+ combinations: no errors.

## 8. The HTML page: `template.html` and `build_html.py`

The page uses the same design as the focused dashboard. `build_html.py` packs the saved tables as compact lists (the cells of each size, group and period; the municipality numbers; the residents) in one file, and the script in the page draws the heat maps and the rate maps in the browser, so every combination of buttons works without a server. The severity charts are built in Python and embedded.

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
| `scripts/04_build_report.py` | the calculation report |
| `charts.py`, `findings.py`, `app.py` | the Plotly charts, the texts, the Streamlit app |
| `template.html`, `build_html.py`, `hotspot_deep_dive.html` | the HTML page |
| `data/`, `results/`, `images/` | inputs, saved results, pictures |
| `REPORT_how_the_output_was_calculated.md` / `.docx` | how every number was calculated |
| `PROCEDURE.md`, `README.md` | this file; the short version |
