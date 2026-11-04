"""
Step 07 - Analysis 1a: total accidents involving each road-user group.

Question: which road user bears the greatest accident burden?
This step answers part a: how many accidents involve each road-user group?

Decisions applied (see beslissingslogboek.md):
  #32 all years 2017-2024 combined; the groups as they exist in the data.
  #33 an accident counts for a group if that group is road user 1 OR road user 2,
      counted ONCE per accident (car vs car = one accident for "Passenger car").
      So the group totals add up to more than the number of accidents.
  #34 "Unknown" and "Other road user" get their own lines. The type-2 values
      "Single road user..." (codes 10 and 11) are not road users: no line, but we report how many rows they cover.
  #35 all 289,532 rows are used, including the 32 flagged possible duplicates.
      One row = one accident (the data has no ID to prove it).
  #36 output: table, CSV, bar chart.

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/07_accidents_per_road_user.py OPENDATA_MAP_2017-2024_en_flagged.csv.gz reports
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to a file, not to a window
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd

input_file = sys.argv[1]  # the flagged English dataset from step 05
output_dir = Path(sys.argv[2])  # the reports/ folder
output_dir.mkdir(exist_ok=True)

# --- 1. Read the data (code columns as text so "01" keeps its zero) ---
header = pd.read_csv(input_file, nrows=0).columns
df = pd.read_csv(input_file, dtype={c: str for c in header if c.endswith("_code")})
n_rows = len(df)  # decision #35: all rows
print(f"Rows used: {n_rows:,} (one row = one accident)\n")

# --- 2. The road-user groups: code -> English name ---
# Road user 1 holds exactly the group codes (01-09 and 99), so we read the names from there.
group_names = dict(zip(df["road_user_type1_code"], df["road_user_type1"]))

# --- 3. Count the accidents involving each group (decision #33) ---
# "|" means OR: the group is road user 1 OR road user 2. Each row is counted at most once per group.
rows = []
for code, name in group_names.items():
    involved = (df["road_user_type1_code"] == code) | (df["road_user_type2_code"] == code)
    rows.append((name, code, int(involved.sum())))

result = pd.DataFrame(rows, columns=["road_user_group", "code", "accidents"])
result["percent_of_all_accidents"] = (result["accidents"] / n_rows * 100).round(2)
result = result.sort_values("accidents", ascending=False).reset_index(drop=True)  # pure ranking by count
result.insert(0, "rank", result.index + 1)

# --- 4. Checks ---
# (a) Independent method: stack both columns under each other, drop "single road user" values (10, 11),
#     drop repeats of the same group inside one accident, then count. Must give the same numbers.
stacked = pd.concat([
    pd.DataFrame({"accident": df.index, "code": df["road_user_type1_code"]}),
    pd.DataFrame({"accident": df.index, "code": df["road_user_type2_code"]}),
])
stacked = stacked[~stacked["code"].isin(["10", "11"])].drop_duplicates()
independent = stacked["code"].value_counts()
for code, accidents in zip(result["code"], result["accidents"]):
    assert independent[code] == accidents, f"code {code}: methods disagree"

# (b) The totals must add up: every accident counts once, plus once more if it has TWO different groups.
single_user = df["road_user_type2_code"].isin(["10", "11"])
two_different_groups = (df["road_user_type1_code"] != df["road_user_type2_code"]) & ~single_user
assert result["accidents"].sum() == n_rows + two_different_groups.sum(), "totals do not add up"

# --- 5. Print and save ---
print("Accidents involving each road-user group, 2017-2024:")
print(result.drop(columns="code").to_string(index=False))
print(f"\nSum of the lines: {result['accidents'].sum():,} (more than {n_rows:,} because one accident can involve two groups)")
print(f"Accidents with two different groups: {two_different_groups.sum():,}")
print(f"Accidents with the same group twice: {((df['road_user_type1_code'] == df['road_user_type2_code'])).sum():,}")
print(f"Rows with a 'Single road user' in type 2 (no line, decision #34): {single_user.sum():,}")
print("Checks passed: two independent counting methods agree, and the totals add up.")
result.drop(columns="code").to_csv(output_dir / "accidents_per_road_user.csv", index=False)

# --- 6. Bar chart (horizontal bars, sorted by count) ---
SURFACE, INK, INK_2, MUTED, GRID, BASELINE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, GRAY = "#2a78d6", "#898781"  # blue = a named group, gray = not a specific group
not_a_group = {"Unknown", "Other road user"}

plt.rcParams["font.family"] = ["Helvetica Neue", "Arial", "DejaVu Sans"]  # a plain system sans
fig, ax = plt.subplots(figsize=(9, 5.6), dpi=200, facecolor=SURFACE)
ax.set_facecolor(SURFACE)

plot = result.iloc[::-1]  # reversed so the biggest bar ends up at the top
colors = [GRAY if g in not_a_group else BLUE for g in plot["road_user_group"]]
ax.barh(plot["road_user_group"], plot["accidents"], height=0.5, color=colors, zorder=3)

# Value at the tip of every bar (for bars the tip is where the value goes).
for y, n in enumerate(plot["accidents"]):
    pct = n / n_rows * 100  # exact share; rounding the already-rounded 2-decimal column could round the wrong way (4.3501 -> 4.35 -> 4.3)
    ax.text(n + result["accidents"].max() * 0.015, y, f"{n:,} ({pct:.1f}%)", va="center", ha="left", fontsize=9, color=INK)

# Quiet axes: hairline vertical grid, a baseline on the left, no box.
ax.set_xlim(0, result["accidents"].max() * 1.32)
ax.xaxis.set_major_formatter(lambda v, _: "0" if v == 0 else f"{v / 1000:.0f}K")  # compact ticks: 0 / 50K / 100K
ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
ax.set_axisbelow(True)
for side in ("top", "right", "bottom"):
    ax.spines[side].set_visible(False)
ax.spines["left"].set_color(BASELINE)
ax.tick_params(axis="both", length=0, labelsize=9, labelcolor=INK_2)
ax.tick_params(axis="x", labelcolor=MUTED)

# Title and subtitle in text colours (never in the bar colour).
fig.text(0.04, 0.955, "Accidents involving each road-user group, 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.04, 0.905, f"Share of all {n_rows:,} accidents. A group counts if it is road user 1 or 2, so one accident can count twice and shares add up to more than 100%.",
         fontsize=8, color=INK_2, ha="left", va="top", wrap=True)

# Key for the two colours (the chart has one series; the key explains blue vs gray).
fig.legend(handles=[Patch(color=BLUE, label="Named road-user group"), Patch(color=GRAY, label="Not a specific group (Unknown, Other road user)")],
           loc="lower left", bbox_to_anchor=(0.04, 0.01), ncol=2, frameon=False, fontsize=8, labelcolor=INK_2, handlelength=1, handleheight=1)

fig.subplots_adjust(left=0.17, right=0.97, top=0.84, bottom=0.12)
fig.savefig(output_dir / "accidents_per_road_user.png", facecolor=SURFACE)
print(f"\nSaved accidents_per_road_user.csv and accidents_per_road_user.png in {output_dir}/")
