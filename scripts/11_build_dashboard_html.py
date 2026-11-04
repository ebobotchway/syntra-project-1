"""
Step 11 - Build the self-contained HTML dashboard (decisions #61 and #69).

It takes the page design in dashboard_template.html and puts the summary table (data/dashboard_data.csv:
accidents per road-user group, per year, per month) into it, so the finished page needs no data file.
Result: dashboard.html, the page that is published as a private page on claude.ai.

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/11_build_dashboard_html.py dashboard_template.html data/dashboard_data.csv reports/accidents_per_road_user.csv dashboard.html
"""
import json
import sys

import pandas as pd

template_file, data_file, ranking_file, output_file = sys.argv[1:5]

# --- 1. Read the summary table and the ranking of the groups (step 07) ---
table = pd.read_csv(data_file)
ranking = pd.read_csv(ranking_file)["road_user_group"].tolist()  # groups ranked by total accidents
names = ["All accidents"] + ranking  # index 0 = the reference line, 1..10 = the groups
assert set(table["road_user_group"]) == set(names), "the groups in the data differ from the ranking"

# --- 2. Turn it into compact rows: [group index, year, month, accidents] ---
index_of = {name: i for i, name in enumerate(names)}
rows = [[index_of[g], int(y), int(m), int(n)] for g, y, m, n in zip(table["road_user_group"], table["year"], table["month"], table["accidents"])]
data = {"names": names, "years": sorted(int(y) for y in table["year"].unique()), "rows": rows}
assert len(rows) == 11 * 8 * 12, "unexpected number of rows"

# --- 3. Put it in the template ---
template = open(template_file, encoding="utf-8").read()
assert template.count("/*__DATA__*/null") == 1, "the data placeholder was not found exactly once"
page = template.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
open(output_file, "w", encoding="utf-8").write(page)
print(f"Saved {output_file}: {len(page) / 1024:.0f} KB, {len(rows)} data rows")
