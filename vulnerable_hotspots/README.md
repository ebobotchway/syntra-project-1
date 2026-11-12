# Vulnerable hotspots: accident hotspots with vulnerable road users, before, during and after Covid-19

One analysis that combines:

- **Step 1** (focused dashboard): who is involved in accidents (1a) and the annual change (1b)
- **Step 2** (focused dashboard): severity per road-user group, for all years and each period
- **The whole hotspot analysis** (`hotspot_deep_dive`): heat maps of accident hotspots with pedestrians, cyclists, motorcycles and mopeds on **5 km2 cells and 5 x 5 km squares**, for pre-Covid, during Covid, post-Covid and all years; the severity at the hotspots; accidents per 100,000 residents (per cell and per municipality)
- **Municipality top 20** and **regional severity with the province map** (focused dashboard)

- How it was made, step by step, with the interpretation of each calculation: [PROCEDURE.md](PROCEDURE.md)
- How every number was calculated and how to read it: [REPORT_how_the_output_was_calculated.md](REPORT_how_the_output_was_calculated.md) (also as Word)
- Pictures: `images/`; saved results: `results/`
- Page on claude.ai (private): https://claude.ai/artifact/FPRzHKr2BvipQppZtLD3NG

## Run the Streamlit app

```bash
conda activate syntra-ds
cd vulnerable_hotspots
python -m streamlit run app.py
```

## Open or rebuild the HTML page

Open `vulnerable_hotspots.html` in a browser (it needs internet for the chart library). After changing a result file: `python build_html.py`.

## Rebuild everything from the accident file

```bash
python -I scripts/01_prepare_population.py "../data/external/statbel_sectors_2023/sh_statbel_statistical_sectors_31370_20230101.shp/sh_statbel_statistical_sectors_31370_20230101.shp"
python -I scripts/01b_cell_residents.py "../data/external/statbel_sectors_2023/sh_statbel_statistical_sectors_31370_20230101.shp/sh_statbel_statistical_sectors_31370_20230101.shp"
python -I scripts/02_hotspot_analysis.py "../OPENDATA_MAP_2017-2024_en_flagged.csv.gz"
python -I scripts/03_plot_heatmaps.py
python -I scripts/04_build_report.py
python build_html.py
```

Counts and rates, not causes. Residents are not traffic. Residents: Statbel open data (CC BY 4.0); outlines: Statbel statistical sectors 2023 (CC BY 4.0).
