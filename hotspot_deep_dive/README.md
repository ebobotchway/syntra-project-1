# Hotspot deep dive: accidents with vulnerable road users before, during and after Covid-19 (version 2)

Step 1 first (who is involved, annual change), then where accidents with pedestrians, cyclists, motorcycles and mopeds concentrate on a 5 x 5 km grid, how severe they are at the hotspots, and what the picture looks like per resident (per square and per municipality). Heat maps for the periods 2017-2019, 2020-2021 and 2022-2024.

- How it was made: [PROCEDURE.md](PROCEDURE.md)
- How every number was calculated: [REPORT_how_the_output_was_calculated.md](REPORT_how_the_output_was_calculated.md) (also as Word)
- Pictures: `images/`; saved results: `results/`
- Page on claude.ai (private): https://claude.ai/artifact/CDg8GqzbHpEPuQE7U2E9Jx

## Run the Streamlit app

```bash
conda activate syntra-ds
cd hotspot_deep_dive
python -m streamlit run app.py
```

## Open or rebuild the HTML page

Open `hotspot_deep_dive.html` in a browser (it needs internet for the chart library). After changing a result file: `python build_html.py`.

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
