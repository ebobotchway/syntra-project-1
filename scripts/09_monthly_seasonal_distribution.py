"""
Step 09 - Analysis 1c: monthly and seasonal distributions per road-user group.

(Step d, urban vs rural, is NOT done: decision #55.)

Counting rules from step 07 still apply (#33-#35): an accident counts once for every road-user group
it involves (road user 1 OR road user 2); Unknown and Other road user stay as lines in the tables;
all 289,532 rows are used.

Decisions applied (see beslissingslogboek.md):
  #51 per road-user group, with "All accidents" as a reference row.
  #52 three measures: accidents and % share, average accidents per day, seasonal index.
        % share   = the month's (season's) accidents / the group's total accidents * 100
        per day   = accidents / number of days in that month (season), summed over the years in scope
        index     = % share / even share * 100, where the even share is 100/12 = 8.33% per month and 25% per season.
                    100 = average month, 130 = 30% more accidents than an average month.
  #53 meteorological seasons: winter = Dec, Jan, Feb; spring = Mar-May; summer = Jun-Aug; autumn = Sep-Nov.
  #54 pooled 8 years AND the three periods: pre 2017-2019, during 2020-2021, post 2022-2024 (names = my definition).
  #56 heatmap of the monthly seasonal index; #57 grouped bars of the seasonal share;
  #58 graphs show the 8 named groups only (+ the "All accidents" reference); #59 the period split is in the tables only.

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/09_monthly_seasonal_distribution.py OPENDATA_MAP_2017-2024_en_flagged.csv.gz reports
"""
import calendar
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to a file, not to a window
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

input_file = sys.argv[1]  # the flagged English dataset from step 05
output_dir = Path(sys.argv[2])  # the reports/ folder (also holds the step-07 result we check against)
output_dir.mkdir(exist_ok=True)

# --- 1. Read the data (code columns as text so "01" keeps its zero) ---
header = pd.read_csv(input_file, nrows=0).columns
df = pd.read_csv(input_file, dtype={c: str for c in header if c.endswith("_code")})
group_names = dict(zip(df["road_user_type1_code"], df["road_user_type1"]))  # code -> name
step7 = pd.read_csv(output_dir / "accidents_per_road_user.csv")  # totals per group, to check against
order = step7["road_user_group"].tolist()  # groups ranked by total accidents, as in step 07
rows_order = ["All accidents"] + order  # the reference row first

MONTH_NAMES = [calendar.month_abbr[m] for m in range(1, 13)]  # Jan ... Dec
SEASON_MONTHS = {"Winter": [12, 1, 2], "Spring": [3, 4, 5], "Summer": [6, 7, 8], "Autumn": [9, 10, 11]}  # decision #53
SCOPES = {  # name -> years in the scope (decision #54)
    "pooled_2017_2024": list(range(2017, 2025)),
    "pre_2017_2019": [2017, 2018, 2019],
    "during_2020_2021": [2020, 2021],
    "post_2022_2024": [2022, 2023, 2024],
}


def distributions(years_in_scope):
    """Return the monthly and seasonal tables (counts, % share, per day, index) for the given years."""
    sub = df[df["collision_year"].isin(years_in_scope)]

    # Accidents per group per month: a group counts if it is road user 1 OR road user 2 (once per accident).
    counts = {}
    for code, name in group_names.items():
        involved = (sub["road_user_type1_code"] == code) | (sub["road_user_type2_code"] == code)
        counts[name] = sub[involved].groupby("collision_month").size().reindex(range(1, 13), fill_value=0)
    monthly = pd.DataFrame(counts).T
    monthly.loc["All accidents"] = sub.groupby("collision_month").size().reindex(range(1, 13), fill_value=0)
    monthly = monthly.loc[rows_order]  # months are columns 1..12

    # Number of days per month in this scope (leap years have 29 days in February).
    days = pd.Series({m: sum(calendar.monthrange(y, m)[1] for y in years_in_scope) for m in range(1, 13)})

    # Seasons: add up the months that belong to each season.
    seasonal = pd.DataFrame({s: monthly[ms].sum(axis=1) for s, ms in SEASON_MONTHS.items()})
    season_days = pd.Series({s: days[ms].sum() for s, ms in SEASON_MONTHS.items()})

    result = {
        "monthly": {"accidents": monthly},
        "seasonal": {"accidents": seasonal},
    }
    for kind, table, day_counts, even_share in (("monthly", monthly, days, 100 / 12), ("seasonal", seasonal, season_days, 25.0)):
        share = table.div(table.sum(axis=1), axis=0) * 100  # % of the group's accidents in this month/season
        result[kind]["percent_share"] = share
        result[kind]["per_day"] = table.div(day_counts, axis=1)  # accidents per day
        result[kind]["index"] = share / even_share * 100  # 100 = even share
    result["days_total"] = int(days.sum())
    return result


results = {scope: distributions(years_in_scope) for scope, years_in_scope in SCOPES.items()}
pooled = results["pooled_2017_2024"]

# --- 2. Checks ---
# (a) Each row of the pooled monthly table must add up to the step-07 total for that group.
assert (pooled["monthly"]["accidents"].drop(index="All accidents").sum(axis=1).values == step7["accidents"].values).all(), "monthly totals differ from step 07"
assert pooled["monthly"]["accidents"].loc["All accidents"].sum() == len(df), "All accidents does not add up to the number of rows"
# (b) Seasons must add up to the same totals.
assert (pooled["seasonal"]["accidents"].sum(axis=1) == pooled["monthly"]["accidents"].sum(axis=1)).all(), "seasons do not add up to months"
# (c) The three periods must add up to the pooled table.
period_sum = sum(results[s]["monthly"]["accidents"] for s in ("pre_2017_2019", "during_2020_2021", "post_2022_2024"))
assert (period_sum == pooled["monthly"]["accidents"]).all().all(), "periods do not add up to the pooled table"
# (d) Independent method: stack both road-user columns, drop "single road user" (10, 11), drop repeats inside one accident, count per month.
stacked = pd.concat([
    pd.DataFrame({"accident": df.index, "month": df["collision_month"], "code": df["road_user_type1_code"]}),
    pd.DataFrame({"accident": df.index, "month": df["collision_month"], "code": df["road_user_type2_code"]}),
])
stacked = stacked[~stacked["code"].isin(["10", "11"])].drop_duplicates()
independent = stacked.groupby(["code", "month"]).size()
for code, name in group_names.items():
    assert (independent[code].reindex(range(1, 13), fill_value=0).values == pooled["monthly"]["accidents"].loc[name].values).all(), f"{name}: methods disagree"
# (e) Shares add up to 100, the average index is 100, and 2017-2024 has 2,922 days.
assert np.allclose(pooled["monthly"]["percent_share"].sum(axis=1), 100) and np.allclose(pooled["seasonal"]["percent_share"].sum(axis=1), 100)
assert np.allclose(pooled["monthly"]["index"].mean(axis=1), 100)
assert pooled["days_total"] == 2922, "unexpected number of days"
print("Checks passed: totals match step 07, seasons and periods add up, an independent method agrees.\n")

# --- 3. Save the tables as wide CSV files: one file per measure, with a 'scope' column ---
for kind in ("monthly", "seasonal"):
    for measure in ("accidents", "percent_share", "per_day", "index"):
        stacked_scopes = pd.concat({scope: results[scope][kind][measure] for scope in SCOPES}, names=["scope", "road_user_group"]).reset_index()
        if kind == "monthly":
            stacked_scopes = stacked_scopes.rename(columns=dict(zip(range(1, 13), MONTH_NAMES)))
        stacked_scopes.to_csv(output_dir / f"distribution_{kind}_{measure}.csv", index=False, float_format="%.2f")


def month_names(table):
    return table.rename(columns=dict(zip(range(1, 13), MONTH_NAMES)))


# --- 4. Print the pooled tables (all 8 years) ---
print("=== Pooled 2017-2024 ===\n")
print("Monthly: accidents involving each group")
print(month_names(pooled["monthly"]["accidents"]).to_string(float_format=lambda v: f"{v:,.0f}"), "\n")
print("Monthly: % of the group's accidents in each month (even share = 8.33%)")
print(month_names(pooled["monthly"]["percent_share"]).to_string(float_format=lambda v: f"{v:.1f}"), "\n")
print("Monthly: average accidents per day")
print(month_names(pooled["monthly"]["per_day"]).to_string(float_format=lambda v: f"{v:.1f}"), "\n")
print("Monthly: seasonal index (100 = average month; not corrected for month length)")
print(month_names(pooled["monthly"]["index"]).to_string(float_format=lambda v: f"{v:.0f}"), "\n")
print("Seasonal: accidents")
print(pooled["seasonal"]["accidents"].to_string(float_format=lambda v: f"{v:,.0f}"), "\n")
print("Seasonal: % of the group's accidents per season (even share = 25%)")
print(pooled["seasonal"]["percent_share"].to_string(float_format=lambda v: f"{v:.1f}"), "\n")
print("Seasonal: average accidents per day")
print(pooled["seasonal"]["per_day"].to_string(float_format=lambda v: f"{v:.1f}"), "\n")
print("Seasonal: index (100 = even share of 25%)")
print(pooled["seasonal"]["index"].to_string(float_format=lambda v: f"{v:.0f}"), "\n")

# --- 5. Print the seasonal % share for the three periods (the monthly period tables are only in the CSV files) ---
for scope in ("pre_2017_2019", "during_2020_2021", "post_2022_2024"):
    print(f"=== Seasonal % share, {scope} ===")
    print(results[scope]["seasonal"]["percent_share"].to_string(float_format=lambda v: f"{v:.1f}"), "\n")

# --- 6. Graphs (only the 8 named groups + the 'All accidents' reference, decision #58) ---
SURFACE, INK, INK_2, MUTED, GRID, BASELINE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
plt.rcParams["font.family"] = ["Helvetica Neue", "Arial", "DejaVu Sans"]  # a plain system sans
graph_rows = ["All accidents"] + [g for g in order if g not in ("Unknown", "Other road user")]

# 6a. Heatmap of the monthly seasonal index (decision #56)
index = pooled["monthly"]["index"].loc[graph_rows]
limit = max(30, math.ceil(np.abs(index.values - 100).max() / 10) * 10)  # symmetric colour range around 100
norm = TwoSlopeNorm(vmin=100 - limit, vcenter=100, vmax=100 + limit)
cmap = LinearSegmentedColormap.from_list("blue_gray_red", ["#2a78d6", "#f0efec", "#e34948"])  # blue = fewer than average, red = more

# One empty row between the reference row and the groups, so "All accidents" reads as a separate reference.
values = np.vstack([index.iloc[[0]].values, np.full((1, 12), np.nan), index.iloc[1:].values])
labels = [graph_rows[0], ""] + graph_rows[1:]
fig, ax = plt.subplots(figsize=(11, 6), dpi=200, facecolor=SURFACE)
ax.set_facecolor(SURFACE)
mesh = ax.pcolormesh(np.ma.masked_invalid(values), cmap=cmap, norm=norm, edgecolors=SURFACE, linewidth=2)  # 2px gap between cells
ax.set_xlim(0, 12)
ax.set_ylim(len(labels), 0)  # first row at the top
ax.set_xticks(np.arange(12) + 0.5, MONTH_NAMES)
ax.set_yticks(np.arange(len(labels)) + 0.5, labels)
ax.xaxis.tick_top()
ax.tick_params(length=0, labelsize=9, labelcolor=INK_2)
for side in ax.spines.values():
    side.set_visible(False)
for r, row in enumerate(values):
    for c, v in enumerate(row):
        if np.isnan(v):
            continue
        strong = abs(v - 100) / limit > 0.55  # dark cell -> white text, light cell -> near-black text
        ax.text(c + 0.5, r + 0.5, f"{v:.0f}", ha="center", va="center", fontsize=9, color="#ffffff" if strong else INK)
fig.text(0.04, 0.965, "When do accidents happen? Seasonal index by month and road-user group, 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.04, 0.92, "Index = the month's share of the group's accidents divided by the even share of 8.33%, x 100. 100 = an average month; 130 = 30% more accidents than an average month.",
         fontsize=8, color=INK_2, ha="left", va="top")
fig.text(0.04, 0.893, "An accident counts once for each group it involves.", fontsize=8, color=INK_2, ha="left", va="top")
fig.text(0.04, 0.025, "Not corrected for month length: February has 28 or 29 days, so its index is lower partly for that reason (see the per-day table).",
         fontsize=7.5, color=MUTED, ha="left", va="bottom")
cax = fig.add_axes([0.62, 0.035, 0.30, 0.018])  # slim colour scale at the bottom right
cbar = fig.colorbar(mesh, cax=cax, orientation="horizontal", ticks=[100 - limit, 100, 100 + limit])
cbar.outline.set_visible(False)
cax.tick_params(length=0, labelsize=7.5, labelcolor=MUTED)
fig.subplots_adjust(left=0.13, right=0.97, top=0.82, bottom=0.12)
fig.savefig(output_dir / "monthly_seasonal_index_heatmap.png", facecolor=SURFACE)
plt.close(fig)

# 6b. Grouped bars: seasonal share per group (decision #57)
share = pooled["seasonal"]["percent_share"].loc[graph_rows]
SEASON_COLORS = {"Winter": "#2a78d6", "Spring": "#eb6834", "Summer": "#1baf7a", "Autumn": "#eda100"}  # categorical slots 1-4 in the validated order
fig, ax = plt.subplots(figsize=(11, 5.6), dpi=200, facecolor=SURFACE)
ax.set_facecolor(SURFACE)
bar_width, step = 0.17, 0.19  # step > width leaves a gap of surface colour between touching bars
x = np.arange(len(graph_rows))
for i, season in enumerate(SEASON_COLORS):
    ax.bar(x + (i - 1.5) * step, share[season].values, width=bar_width, color=SEASON_COLORS[season], zorder=3)
# Label only the highest season of every group (never a number on every bar).
for g, group in enumerate(graph_rows):
    top_season = share.loc[group].idxmax()
    i = list(SEASON_COLORS).index(top_season)
    ax.text(g + (i - 1.5) * step, share.loc[group, top_season] + 0.5, f"{share.loc[group, top_season]:.0f}%", ha="center", va="bottom", fontsize=8.5, color=INK)
ax.axhline(25, color=INK_2, linewidth=1.2, zorder=4)  # the even share
ax.set_xlim(-0.6, len(graph_rows) + 0.6)  # extra room on the right for the label of the reference line
ax.text(len(graph_rows) - 0.55, 25.6, "even share 25%", ha="left", va="bottom", fontsize=8, color=INK_2)
ax.set_xticks(x, graph_rows)
ax.set_ylim(0, math.ceil(share.values.max() / 5) * 5 + 3)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
ax.set_axisbelow(True)
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
ax.spines["bottom"].set_color(BASELINE)
ax.tick_params(length=0, labelsize=9, labelcolor=INK_2)
ax.tick_params(axis="y", labelcolor=MUTED)
fig.text(0.04, 0.965, "How each road-user group's accidents spread over the seasons, 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.04, 0.92, "Share of the group's accidents per season. Meteorological seasons, whole months. An accident counts once for each group it involves. The number marks each group's highest season.",
         fontsize=8, color=INK_2, ha="left", va="top")
fig.legend(handles=[Patch(color=SEASON_COLORS["Winter"], label="Winter (Dec-Feb)"), Patch(color=SEASON_COLORS["Spring"], label="Spring (Mar-May)"),
                    Patch(color=SEASON_COLORS["Summer"], label="Summer (Jun-Aug)"), Patch(color=SEASON_COLORS["Autumn"], label="Autumn (Sep-Nov)")],
           loc="lower left", bbox_to_anchor=(0.04, 0.005), ncol=4, frameon=False, fontsize=8.5, labelcolor=INK_2, handlelength=1.2, handleheight=1.2)
fig.subplots_adjust(left=0.06, right=0.98, top=0.84, bottom=0.17)
fig.savefig(output_dir / "seasonal_share_per_group.png", facecolor=SURFACE)
plt.close(fig)
print(f"Saved 8 CSV files and 2 graphs (monthly_seasonal_index_heatmap.png, seasonal_share_per_group.png) in {output_dir}/")
