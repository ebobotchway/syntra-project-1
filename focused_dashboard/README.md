# Focused dashboard: Belgian road accidents 2017-2024

A smaller version of the project's dashboard with only:

- **Step 1**: 1a (who is involved) and 1b (annual change)
- **Step 2**: severity per road-user group
- **Step 3b/3c**: hotspots (500 m squares) and the municipality top 20, with a filter for pedestrians, motorcycles, mopeds and cyclists
- **Step 4a**: regional severity and the province map

It shows saved results (no accident file needed). The steps of how it was made are in [PROCEDURE.md](PROCEDURE.md).

## Run the Streamlit app

```bash
conda activate syntra-ds
cd focused_dashboard
streamlit run app.py
```

## Open or rebuild the HTML page

Open `focused_dashboard.html` in a browser (it needs internet for the chart library). To rebuild it after changing a result file:

```bash
python build_html.py
```

## Rebuild the cyclist hotspots (needs the big accident file once)

```bash
python -I make_cyclist_hotspots.py "../OPENDATA_MAP_2017-2024_en_flagged.csv.gz"
```

Counts and shares, not rates: there are no traffic or population figures. Associations, not causes.
