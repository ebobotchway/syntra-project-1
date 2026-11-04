"""
Step 08 - Analysis 1b: annual changes in accident involvement by road-user group.

Counting rules from step 07 still apply (#33-#35): an accident counts once for every road-user
group it involves (road user 1 OR road user 2); Unknown and Other road user stay as lines;
all 289,532 rows are used.

Decisions applied (see beslissingslogboek.md):
  #38 measures: year-over-year % change, total change 2017 -> 2024, and a three-period comparison:
      pre Covid-19 (2017-2019), during Covid-19 (2020-2021), post Covid-19 (2022-2024).
      The period names are my own definition; the data does not state a cause for 2020.
  #39 graph: small multiples, one line panel per group, indexed 2017 = 100 on a shared scale.
  #40 tables: wide (groups as rows, years as columns), printed and saved as CSV.
  #41/#44 no adjustments to the calculations; the graph shows only the 8 named groups (no Unknown, no Other road user);
      the tables keep all 10 lines.
  #42 change within a period = average yearly % change (compound) and average accidents per year.
  #43 the graph shows the three periods as light shaded bands.
  #45 period averages are compared with the period before (during vs pre, post vs during).
  #46/#47 added on request: "post vs pre" = % difference between the average accidents per year in 2022-2024 and 2017-2019.
  #48 the graph shows the pre and post averages as thin lines in every panel, with a "post vs pre" label.

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/08_annual_change_per_road_user.py OPENDATA_MAP_2017-2024_en_flagged.csv.gz reports
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to a file, not to a window
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import pandas as pd

input_file = sys.argv[1]  # the flagged English dataset from step 05
output_dir = Path(sys.argv[2])  # the reports/ folder (also holds the step-07 result we check against)
output_dir.mkdir(exist_ok=True)

# --- 1. Read the data (code columns as text so "01" keeps its zero) ---
header = pd.read_csv(input_file, nrows=0).columns
df = pd.read_csv(input_file, dtype={c: str for c in header if c.endswith("_code")})
years = sorted(df["collision_year"].unique())  # 2017 ... 2024
group_names = dict(zip(df["road_user_type1_code"], df["road_user_type1"]))  # code -> name (type 1 holds all group codes)

# Keep the same order as the step-07 table (ranked by total accidents).
step7 = pd.read_csv(output_dir / "accidents_per_road_user.csv")
order = step7["road_user_group"].tolist()

# --- 2. Accidents per group per year (an accident counts once per group, as in step 07) ---
rows = {}
for code, name in group_names.items():
    involved = (df["road_user_type1_code"] == code) | (df["road_user_type2_code"] == code)
    rows[name] = df[involved].groupby("collision_year").size().reindex(years, fill_value=0)
counts = pd.DataFrame(rows).T.loc[order]  # rows = groups, columns = years
counts.loc["All accidents"] = df.groupby("collision_year").size()  # reference row: every accident once

# --- 3. Checks on the counts ---
# (a) The yearly counts must add up to the step-07 totals.
assert (counts.drop(index="All accidents").sum(axis=1).values == step7["accidents"].values).all(), "totals differ from step 07"
# (b) Independent method: stack both columns, drop "single road user" (10, 11), drop repeats inside one accident, count per year and code.
stacked = pd.concat([
    pd.DataFrame({"accident": df.index, "year": df["collision_year"], "code": df["road_user_type1_code"]}),
    pd.DataFrame({"accident": df.index, "year": df["collision_year"], "code": df["road_user_type2_code"]}),
])
stacked = stacked[~stacked["code"].isin(["10", "11"])].drop_duplicates()
independent = stacked.groupby(["code", "year"]).size()
for code, name in group_names.items():
    assert (independent[code].reindex(years, fill_value=0).values == counts.loc[name].values).all(), f"{name}: methods disagree"
print("Checks passed: yearly counts add up to step 07 and match an independent counting method.\n")

# --- 4. Table 1: accidents per year ---
counts.index.name = "road_user_group"
counts.to_csv(output_dir / "annual_accidents_by_group.csv")
print("1. Accidents involving each group, per year:")
print(counts.to_string(float_format=lambda v: f"{v:,.0f}"), "\n")

# --- 5. Table 2: year-over-year % change ---
# pct_change(axis=1) compares every year with the year before (left neighbour).
yoy = (counts.pct_change(axis=1) * 100).drop(columns=years[0])  # 2017 has no previous year
yoy.to_csv(output_dir / "annual_yoy_pct_change.csv", float_format="%.2f")
print("2. Year-over-year % change (each year vs the year before):")
print(yoy.to_string(float_format=lambda v: f"{v:+.1f}%"), "\n")

# --- 6. Table 3: total change 2017 -> 2024 ---
first, last = years[0], years[-1]
total_change = pd.DataFrame({
    str(first): counts[first],
    str(last): counts[last],
    "change_accidents": counts[last] - counts[first],
    "change_pct": (counts[last] / counts[first] - 1) * 100,
})
total_change.to_csv(output_dir / "annual_total_change_2017_2024.csv", float_format="%.2f")
print(f"3. Total change {first} -> {last}:")
print(total_change.to_string(formatters={str(first): "{:,.0f}".format, str(last): "{:,.0f}".format,
                                         "change_accidents": "{:+,.0f}".format, "change_pct": "{:+.1f}%".format}), "\n")

# --- 7. Table 4: the three periods (decisions #38, #42, #45) ---
PERIODS = {  # name -> (first year, last year); the names are my own definition
    "pre_2017_2019": (2017, 2019),
    "during_2020_2021": (2020, 2021),
    "post_2022_2024": (2022, 2024),
}
periods = pd.DataFrame(index=counts.index)
for name, (start, end) in PERIODS.items():
    in_period = [y for y in years if start <= y <= end]
    # average number of accidents per year in the period
    periods[f"avg_per_year_{name}"] = counts[in_period].mean(axis=1)
    # average yearly % change: (end / start) ** (1 / number of yearly steps) - 1  (compound rate)
    steps = end - start
    periods[f"avg_yearly_change_pct_{name}"] = ((counts[end] / counts[start]) ** (1 / steps) - 1) * 100
# % difference between period averages, each period vs the one before (decision #45)
periods["avg_diff_pct_during_vs_pre"] = (periods["avg_per_year_during_2020_2021"] / periods["avg_per_year_pre_2017_2019"] - 1) * 100
periods["avg_diff_pct_post_vs_during"] = (periods["avg_per_year_post_2022_2024"] / periods["avg_per_year_during_2020_2021"] - 1) * 100
# decisions #46/#47: post vs pre, i.e. 2022-2024 against 2017-2019 (skips the "during" period)
periods["avg_diff_pct_post_vs_pre"] = (periods["avg_per_year_post_2022_2024"] / periods["avg_per_year_pre_2017_2019"] - 1) * 100
periods.to_csv(output_dir / "annual_periods.csv", float_format="%.2f")

avg_cols = [c for c in periods.columns if c.startswith("avg_per_year") or c.startswith("avg_diff")]
chg_cols = [c for c in periods.columns if c.startswith("avg_yearly_change")]
print("4a. Average accidents per year in each period, and % difference with the period before:")
print(periods[avg_cols].to_string(formatters={**{c: "{:,.0f}".format for c in avg_cols if c.startswith("avg_per")},
                                              **{c: "{:+.1f}%".format for c in avg_cols if c.startswith("avg_diff")}}), "\n")
print("4b. Average yearly % change within each period (2017->2019, 2020->2021, 2022->2024):")
print(periods[chg_cols].to_string(float_format=lambda v: f"{v:+.1f}%"), "\n")

# --- 8. Graph: small multiples, indexed 2017 = 100 (decisions #39, #41, #43) ---
SURFACE, INK, INK_2, MUTED, GRID, BASELINE, BLUE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#2a78d6"
BANDS = {"pre": "#f7f6f3", "during": "#dfddd5", "post": "#ecebe6"}  # three light washes behind the lines: lightest, darkest, in between
band_edges = {"pre": (years[0] - 0.5, 2019.5), "during": (2019.5, 2021.5), "post": (2021.5, years[-1] + 0.5)}

named = [g for g in order if g not in ("Unknown", "Other road user")]  # 8 panels (decision #41)
index = counts.loc[named].div(counts.loc[named, first], axis=0) * 100  # 2017 = 100 for every group

plt.rcParams["font.family"] = ["Helvetica Neue", "Arial", "DejaVu Sans"]  # a plain system sans
fig, axes = plt.subplots(2, 4, figsize=(11, 6.4), dpi=200, sharex=True, sharey=True, facecolor=SURFACE)
for ax, group in zip(axes.flat, named):
    ax.set_facecolor(SURFACE)
    for key, (left, right) in band_edges.items():
        ax.axvspan(left, right, color=BANDS[key], zorder=0, linewidth=0)
    ax.axhline(100, color=BASELINE, linewidth=0.8, zorder=1)  # the 2017 level
    # Thin lines at the average of the pre and the post period, on the same index scale (decision #48).
    for key, column in (("pre", "avg_per_year_pre_2017_2019"), ("post", "avg_per_year_post_2022_2024")):
        average_index = periods.loc[group, column] / counts.loc[group, first] * 100
        ax.plot(band_edges[key], [average_index, average_index], color=INK_2, linewidth=1.4, zorder=2, solid_capstyle="butt")
    ax.text(0.04, 0.04, f"post vs pre: {periods.loc[group, 'avg_diff_pct_post_vs_pre']:+.0f}%", transform=ax.transAxes, fontsize=8, color=INK_2, ha="left", va="bottom")
    ax.plot(years, index.loc[group], color=BLUE, linewidth=2, solid_capstyle="round", solid_joinstyle="round", zorder=3)
    ax.plot([years[-1]], [index.loc[group, years[-1]]], marker="o", markersize=7, color=BLUE, markeredgecolor=SURFACE, markeredgewidth=2, zorder=4)
    end_value = index.loc[group, years[-1]]
    post_average = periods.loc[group, "avg_per_year_post_2022_2024"] / counts.loc[group, first] * 100
    # Put the 2024 label on the side of the dot that does NOT have the post-average line, so they never overlap.
    above = end_value >= post_average
    ax.annotate(f"{end_value:.0f}", (years[-1], end_value), xytext=(0, 7 if above else -7), textcoords="offset points",
                ha="center", va="bottom" if above else "top", fontsize=8.5, color=INK)
    ax.set_title(f"{group}", fontsize=9.5, color=INK, loc="left", pad=14, fontweight="bold")
    ax.text(0, 1.015, f"{counts.loc[group, first]:,} accidents in {first}", transform=ax.transAxes, fontsize=7.5, color=MUTED, ha="left", va="bottom")
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(length=0, labelsize=8, labelcolor=MUTED)
    ax.set_xlim(years[0] - 0.5, years[-1] + 0.5)
    ax.set_xticks([years[0], 2020, years[-1]])
axes[0, 0].set_ylim(50, 140)
axes[0, 0].set_yticks([60, 80, 100, 120, 140])
for ax in axes[:, 0]:
    ax.set_ylabel("Index (2017 = 100)", fontsize=8, color=INK_2)

fig.text(0.04, 0.965, "Annual change in accidents involving each road-user group (index, 2017 = 100)", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.04, 0.925, "The 8 named groups. An accident counts once for each group it involves. The number at the end of each line is the 2024 index; Unknown and Other road user are in the tables only.",
         fontsize=8, color=INK_2, ha="left", va="top")
fig.legend(handles=[Patch(facecolor=BANDS["pre"], edgecolor=BASELINE, label="2017-2019 pre Covid-19"),
                    Patch(facecolor=BANDS["during"], edgecolor=BASELINE, label="2020-2021 during Covid-19"),
                    Patch(facecolor=BANDS["post"], edgecolor=BASELINE, label="2022-2024 post Covid-19"),
                    Line2D([0], [0], color=INK_2, linewidth=1.4, label="Average per year in the pre and post period")],
           loc="lower left", bbox_to_anchor=(0.04, 0.028), ncol=4, frameon=False, fontsize=8, labelcolor=INK_2, handlelength=1.4, handleheight=1.2)
fig.text(0.04, 0.012, "Period names are my own definition; the data does not state a cause.", fontsize=7.5, color=MUTED, ha="left", va="bottom")
fig.subplots_adjust(left=0.07, right=0.98, top=0.84, bottom=0.14, wspace=0.12, hspace=0.34)
fig.savefig(output_dir / "annual_change_per_road_user.png", facecolor=SURFACE)
print(f"Saved 4 CSV files and annual_change_per_road_user.png in {output_dir}/")
