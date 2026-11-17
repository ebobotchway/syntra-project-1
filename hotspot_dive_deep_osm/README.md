# Analysis of accident hotspots for vulnerable road users on OpenStreetMap, with step 1: accidents with vulnerable road users before, during and after Covid-19

This is the analysis of accident hotspots for vulnerable road users (the `hotspot_dive_deep_final/` version) with the **maps of steps 2 and 3 drawn on top of OpenStreetMap** (#225). The squares, numbers, hotspots, regression and rates are the same; only the map behind and under the squares is new. Each square is drawn where it lies on the ground (its Lambert corners converted to longitude and latitude by `scripts/06_grid_lonlat.py`). The step 5 municipality map is unchanged. The pictures in `images/` (script 03, used in the report) are still the plain grid maps without OpenStreetMap, because a printed picture cannot load map tiles from the internet.

Where accidents with pedestrians, cyclists, motorcycles and mopeds concentrate (5 km2 cells and 5 x 5 km squares), how severe they are at the hotspots, and what the picture looks like per resident. Heat maps for the periods 2017-2019, 2020-2021 and 2022-2024.

- How it was made: [PROCEDURE.md](PROCEDURE.md)
- How every number was calculated: [REPORT_how_the_output_was_calculated.md](REPORT_how_the_output_was_calculated.md) (also as Word)
- The technical underpinnings of the five steps, in plain language: [TECHNICAL_UNDERPINNINGS.md](TECHNICAL_UNDERPINNINGS.md) (also as Word)
- Pictures: `images/`; saved results: `results/`
- This page is not published. The maps load OpenStreetMap tiles from the internet (© OpenStreetMap contributors).

## Run the Streamlit app

```bash
conda activate syntra-ds
cd hotspot_dive_deep_osm
python -m streamlit run app.py
```

## Open or rebuild the HTML page

Open `hotspot_deep_dive_osm.html` in a browser (it needs internet for the chart library and the map tiles). After changing a result file: `python build_html.py`.

## Rebuild everything from the accident file

```bash
python -I scripts/01_prepare_population.py "../data/external/statbel_sectors_2023/sh_statbel_statistical_sectors_31370_20230101.shp/sh_statbel_statistical_sectors_31370_20230101.shp"
python -I scripts/02_hotspot_analysis.py "../OPENDATA_MAP_2017-2024_en_flagged.csv.gz"
python -I scripts/03_plot_heatmaps.py
python -I scripts/06_grid_lonlat.py                         # corners of the squares in longitude/latitude (needs pyproj), for the OpenStreetMap maps
python -I scripts/05_logistic_model.py "../OPENDATA_MAP_2017-2024_en_flagged.csv.gz"   # logistic regression of severity (step 4b); run before script 04
python -I scripts/04_build_report.py
python build_html.py
```

Counts and rates, not causes. Residents are not traffic. Residents: Statbel open data (CC BY 4.0); outlines: Statbel statistical sectors 2023 (CC BY 4.0).
