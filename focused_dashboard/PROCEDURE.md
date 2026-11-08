# Step-by-step procedure: how the focused dashboard was made

This file explains, in the order I did it, how the `focused_dashboard/` folder was built from the main project, so you can repeat it, change it, or explain it in the no-AI conversation. Each step says **what** I did, **why**, **which file** it touches, and **how I checked** it. Decisions are in `beslissingslogboek.md` (#163-#167).

## 0. What was asked and what was decided

**Request (#163):** a new Streamlit app and a new HTML output that show only:

| Part | Content |
|---|---|
| Step 1 | 1a (who is involved) and 1b (annual change), no 1c |
| Step 2 | Severity per road-user group |
| Step 3b/3c | Hotspots and municipalities, with a filter for pedestrians, motorcycles, mopeds **and cyclists** |
| Step 4a | Regional severity and the province map |

plus this step-by-step procedure, and everything in a new folder.

**Decisions I asked you about before building (nothing was assumed):**

| # | Question | Answer |
|---|---|---|
| 164 | What does 3b/3c contain? | Both views (500 m hotspot squares and the municipality top 20), one group filter |
| 165 | How interactive is Streamlit? | Saved results with page filters (no accident file needed) |
| 166 | What about the HTML? | A local file **and** a new private claude.ai page; the existing page stays |
| 167 | How is the folder set up? | `focused_dashboard/`, self-contained |

## 1. Look at what already exists (no code yet)

Before writing anything I listed what the main project already had, because most of the work was **reusing** it:

- Step 1 (1a, 1b, 1c) was built in `dashboard_template.html` (browser) and `dashboard_logic.py` + `dashboard_charts.py` (Streamlit).
- Steps 2 and 4a charts were in `dashboard_extra.py`, built from saved result tables in `reports/`.
- The municipality top 20 was in `dashboard_extra.py` (generic `fig_group_*` functions), `tool_charts.py` and `scripts/24_municipalities_other_groups.py`.
- The hotspot squares existed for pedestrians, motorcycles and mopeds, **not for cyclists**. That was the one missing analysis (step 2 below).

## 2. Create the folder and copy the small input files

```bash
cd "Project 1"
mkdir -p focused_dashboard/data focused_dashboard/results
```

I copied only what the dashboard needs, so the folder runs on its own (3 MB in total, no accident file needed):

- `data/`: `dashboard_data.csv` (accidents per group, year and month), `municipality_outlines.json`, `province_outlines.json` (the map shapes), `hotspot_cells.csv` (accidents per 500 m square), `municipality_positions.csv` (bubble positions).
- `results/`: the saved result tables of steps 2, 3 and 4a (`severity_*.csv`, `geo_*.csv`, `severity_regional_regions_provinces.csv`, `accidents_per_road_user.csv`).

**Why copy and not point at the main folder?** (#167) The new folder keeps working if you move it, zip it, or put it on GitHub on its own.

## 3. The missing analysis: hotspot squares for cyclists

File: `make_cyclist_hotspots.py` (needs the big accident file, once).

1. It repeats the method of the main project's script 14 exactly: for each accident that has usable coordinates, find its 500 m square (`x // 500`, `y // 500`), count accidents per square, rank the 20 busiest squares, name the municipality that holds most accidents of each square (#83, #86, #87, #90).
2. **First it recalculates the pedestrians and checks that the result equals the saved pedestrian numbers** (top 20 and coverage). Only then does it do the cyclists. If the method differed from the earlier one, the script would stop with an error.
3. It writes `results/geo_hotspots_bicycle.csv`, adds two rows to `results/geo_coverage.csv` and the cyclist squares to `data/hotspot_cells.csv`.

```bash
cd focused_dashboard
python -I make_cyclist_hotspots.py "../OPENDATA_MAP_2017-2024_en_flagged.csv.gz"
```

Result: 71,881 accidents involve cyclists, 89.0% have coordinates (96.4% in 2022-2024); the busiest square is in Antwerpen (113 accidents); 9 of the 20 busiest squares are in Antwerpen.

## 4. The chart code: `charts.py`, `step1_charts.py`, `step1_logic.py`

I did **not** rewrite the charts; I made trimmed copies so the folder is standalone:

- `charts.py`: the functions for steps 2, 3b/3c and 4a, cut out of `dashboard_extra.py` (severity, group ranked/bubble/choropleth, hotspots, regional overview, province map) plus the municipality map and top-20 bars from `tool_charts.py`. Paths now point to the folder's own `results/` and `data/`.
- `step1_logic.py` and `step1_charts.py`: copies of `dashboard_logic.py` and `dashboard_charts.py`; the 1c functions (monthly heat map, seasons) were removed.
- Cyclists were added as a fourth group (`GROUPS4`), so the same functions work for all four.

**Checks:** the modules import without errors; a small script lists names that are used but never defined (none left); the Streamlit test in step 7 caught one constant I had forgotten to copy (`NAMED`), which I then added.

## 5. The calculations of the municipality view: `tables.py`

The top 20 can be filtered by group, period, region and by number/share, so it is calculated from `results/geo_municipality_periods.csv` (accidents and severe accidents per municipality, group and period).

Rules (all written in the file): an accident counts for a group if the group is road user 1 or 2 (#33); a share is only ranked for municipalities with at least 100 accidents of any kind in the chosen period and region (#88, #161); a "severe %" is only shown from 30 accidents of the group.

## 6. The Streamlit app: `app.py`

Design (from your instruction in the main project that filters belong in one sidebar):

- Sidebar: first the choice of analysis (4 options), then the filters of that analysis. The main area shows only the chosen analysis.
- 1a/1b: years, road-user groups, an "also show Unknown and Other" switch.
- Step 2: the period (all years, pre, during, post).
- 3b/3c: group (pedestrians, motorcycles, mopeds, cyclists), view (hotspots or municipalities); hotspots add the years; municipalities add rank by (number/share), period, region and map type (bubble/choropleth).
- 4a: no filters (the results are fixed), with a table.
- Every analysis shows the key findings, a "read with care" note, a table and a CSV download button.
- `@st.cache_data` loaders read each file once, so changing a filter is fast.

```bash
pip install -r requirements.txt    # inside the syntra-ds environment, only if something is missing
streamlit run app.py
```

## 7. Test the Streamlit app

I used Streamlit's `AppTest` (it runs the app without a browser and lets a script change widgets):

- Opened all four analyses, then changed every filter: step 1 with a different year range, a single year, no groups chosen and Unknown on; step 2 with each period; step 3 with all 4 groups x both views x rank by x map type, and region/period combinations such as Wallonia 2022-2024, Brussels 2019 (few municipalities qualify) and Flanders 2017.
- Result: no exceptions. (The one failure at first was the missing `NAMED` constant.)
- Number check: for all four groups the top 5 by number and by share equal the top 5 in the main project's saved tables, and the totals are 29,897 pedestrians, 19,792 motorcycles, 23,258 mopeds and 71,881 cyclists.

## 8. The HTML page: `template_page.html`, `template_extra.html`, `build_html.py`

The page works like the main project's page: the charts are built **in Python** from the saved results and embedded in the HTML as Plotly figures; a small script in the page draws them and switches between them with buttons. Step 1 and the municipality view are calculated in the browser (so buttons can be combined freely).

How the two templates were made (I cut them out of the main project's templates, with a check after each cut):

1. `template_page.html` = `dashboard_template.html` without: section 1c, the "Measure" buttons, the 1c drawing code, the unused 1c calculation helpers, and the navigation links of the removed steps. The sidebar filters now say they apply to section 1.
2. `template_extra.html` = the main page's extra sections, reduced to: step 2 (period buttons), step 3b/3c, step 4a (the regional overview and the province map).
3. **One group filter for step 3b/3c.** The two views share one row of buttons (pedestrians, motorcycles, mopeds, cyclists); changing it redraws the hotspots and the municipality view. The key findings change with the group.
4. `build_html.py` makes the figures with `charts.py`, packs the numbers per municipality, group and period for the browser code, and writes `focused_dashboard.html` (2.1 MB; the chart library comes from the internet).

```bash
python build_html.py
```

## 9. Test the HTML page

I opened the page in headless Chrome (a browser without a window that I control from a script), clicked through every control and took screenshots:

- No console errors or warnings.
- Step 1 shows 1a and 1b only; the page has no 1c, no step 5 and no 3a.
- Switching the group to Cyclists redraws the hotspot map and the text ("63,938 of 71,881 ... 89.0%").
- Municipality view in the browser gives the same numbers as the saved results: cyclists by number Antwerpen 7,405, Gent 4,229, Brussel 2,478; motorcycles by share Stoumont 32.7% (37 accidents), Froidchapelle 32.6%, Cerfontaine 29.4%.

## 10. Publish the page on claude.ai

The page is published as a **new private** artifact (#166), https://claude.ai/artifact/Y7KZ7Xysy4ai6hH8BBVeob (needs the `downloads` capability for the CSV buttons); the existing page was not touched. Only you can open it until you share it with someone (the sharing menu of the page).

## 11. What you can change later

| You want to... | Change this | Then |
|---|---|---|
| Update the numbers after a new analysis | the CSV files in `results/` and `data/` | run `python build_html.py`; restart Streamlit |
| Change a finding text | `findings.py` (Streamlit) and `template_extra.html` / `template_page.html` (HTML) | run `python build_html.py` |
| Add another group to 3b/3c | `GROUPS4` in `charts.py`, the cell/top/coverage files, the group buttons in `template_extra.html` | rebuild |
| Add a step back (for example 1c) | take it from the main project's templates and `dashboard_charts.py` | rebuild |

## 12. Limits (the same as in the main project)

- Counts and shares, not rates: there are no traffic or population figures.
- 10-13% of accidents have no coordinates (3-5% in 2022-2024), more in Wallonia; hotspots there may be understated.
- A share in a small municipality moves with a few accidents, which is why it needs 100 accidents to be ranked.
- Associations, not causes.

## Files in this folder

| File | Purpose |
|---|---|
| `app.py` | the Streamlit app |
| `charts.py`, `step1_charts.py`, `step1_logic.py`, `tables.py`, `findings.py` | chart code, step 1 calculations, municipality calculations, texts |
| `build_html.py`, `template_page.html`, `template_extra.html` | the HTML builder and its two templates |
| `focused_dashboard.html` | the output page |
| `make_cyclist_hotspots.py` | the one new analysis (cyclist hotspots) |
| `data/`, `results/` | the copied input files (small) |
| `requirements.txt` | what to install |
| `README.md` | the short version: how to run |
