"""
Step 12 - Analysis 2: accident severity across road-user groups.

Question: who experiences the most severe outcomes as a result of accidents?
Indicators: a. fatal-accident share, b. serious-injury accident share, c. slight-injury accident share,
            d. severity distribution by road-user group.

IMPORTANT LIMIT: the accident class describes the WHOLE accident, not one road user. In a pedestrian-car accident the
same class counts for the pedestrian group and for the car group. So the numbers below show the severity of the accidents
a group is part of, NOT the harm to that group's own members.

Decisions applied (see beslissingslogboek.md):
  #70 the question and the four indicators.
  #71 fatal = class 1 "With fatalities" + class 2 "Fatally injured" together (the two classes are also shown separately in table d).
      serious = class 3 "With seriously injured"; slight = class 4 "With slightly injured".
  #72 an accident counts for every road-user group involved (road user 1 OR 2), once per group (as in #33); all 289,532 rows (#35).
  #73/#78 for each indicator: the share, the ratio to all accidents and the percentage-point gap to all accidents.
  #74 counts and a 95% Wilson confidence interval next to every share.
  #75 pooled 2017-2024 AND the three periods (pre 2017-2019, during 2020-2021, post 2022-2024; names = my definition).
  #76 interval charts for a-c and 100% stacked bars for d; #77 graphs show the 8 named groups + "All accidents".

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/12_severity_by_road_user.py OPENDATA_MAP_2017-2024_en_flagged.csv.gz reports
"""
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to a file, not to a window
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd

input_file = sys.argv[1]  # the flagged English dataset from step 05
output_dir = Path(sys.argv[2])  # the reports/ folder
output_dir.mkdir(exist_ok=True)

# --- 1. Read the data (code columns as text so "01" keeps its zero) ---
header = pd.read_csv(input_file, nrows=0).columns
df = pd.read_csv(input_file, dtype={c: str for c in header if c.endswith("_code")})
group_names = dict(zip(df["road_user_type1_code"], df["road_user_type1"]))  # code -> name
step7 = pd.read_csv(output_dir / "accidents_per_road_user.csv")  # totals per group (for checking and for the order)
order = step7["road_user_group"].tolist()
rows_order = ["All accidents"] + order

CLASSES = {  # decision #71: how the four accident classes form the three indicators
    "fatal": ["1", "2"],    # With fatalities + Fatally injured
    "serious": ["3"],       # With seriously injured
    "slight": ["4"],        # With slightly injured
}
INDICATORS = {"a_fatal": "fatal", "b_serious": "serious", "c_slight": "slight"}
SCOPES = {  # name -> years in the scope (decision #75)
    "pooled_2017_2024": range(2017, 2025),
    "pre_2017_2019": range(2017, 2020),
    "during_2020_2021": range(2020, 2022),
    "post_2022_2024": range(2022, 2025),
}


def wilson(successes, n, z=1.96):
    """95% Wilson confidence interval for a share (as percentages). It behaves better than the simple formula for small counts."""
    p = successes / n
    denominator = 1 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denominator
    return (center - half) * 100, (center + half) * 100


def counts_for(sub):
    """Accident counts per group and class for the given rows: columns = accidents, class1..class4."""
    table = {}
    classes = sub["accident_class_code"]
    for code, name in group_names.items():
        involved = (sub["road_user_type1_code"] == code) | (sub["road_user_type2_code"] == code)  # road user 1 OR 2
        table[name] = [int(involved.sum())] + [int((classes[involved] == c).sum()) for c in ["1", "2", "3", "4"]]
    table["All accidents"] = [len(sub)] + [int((classes == c).sum()) for c in ["1", "2", "3", "4"]]
    result = pd.DataFrame(table, index=["accidents", "class1", "class2", "class3", "class4"]).T.loc[rows_order]
    return result


def indicators(counts):
    """For one scope: per indicator the count, share, 95% interval, ratio and gap to all accidents."""
    out = {}
    overall = counts.loc["All accidents"]
    for key, label in INDICATORS.items():
        n_class = counts[[f"class{c}" for c in CLASSES[label]]].sum(axis=1)
        share = n_class / counts["accidents"] * 100
        overall_share = share["All accidents"]
        intervals = [wilson(x, n) for x, n in zip(n_class, counts["accidents"])]
        out[key] = pd.DataFrame({
            "accidents": counts["accidents"], "count": n_class, "share_pct": share,
            "ci_low_pct": [i[0] for i in intervals], "ci_high_pct": [i[1] for i in intervals],
            "ratio_to_all": share / overall_share, "gap_points": share - overall_share,
        })
    return out


results = {}
for scope, years in SCOPES.items():
    counts = counts_for(df[df["collision_year"].isin(years)])
    results[scope] = {"counts": counts, "indicators": indicators(counts)}
pooled = results["pooled_2017_2024"]

# --- 2. Checks ---
assert abs(wilson(10, 100)[0] - 5.5) < 0.1 and abs(wilson(10, 100)[1] - 17.4) < 0.1, "Wilson interval gives an unexpected result"
counts = pooled["counts"]
assert (counts[["class1", "class2", "class3", "class4"]].sum(axis=1) == counts["accidents"]).all(), "classes do not add up to the accidents"
assert (counts.drop(index="All accidents")["accidents"].values == step7["accidents"].values).all(), "group totals differ from step 07"
assert counts.loc["All accidents", "accidents"] == len(df), "All accidents differs from the number of rows"
assert counts.loc["All accidents", ["class1", "class2", "class3", "class4"]].tolist() == [3077, 1064, 24391, 261000], "class totals differ from the earlier look"
# Independent method: stack both road-user columns, drop "single road user" (10, 11), drop repeats inside one accident, count per code and class.
stacked = pd.concat([
    pd.DataFrame({"accident": df.index, "code": df["road_user_type1_code"], "cls": df["accident_class_code"]}),
    pd.DataFrame({"accident": df.index, "code": df["road_user_type2_code"], "cls": df["accident_class_code"]}),
])
stacked = stacked[~stacked["code"].isin(["10", "11"])].drop_duplicates()
independent = stacked.groupby(["code", "cls"]).size()
for code, name in group_names.items():
    for i, c in enumerate(["1", "2", "3", "4"], start=1):
        assert independent.get((code, c), 0) == counts.loc[name, f"class{i}"], f"{name} class {c}: methods disagree"
# The three periods must add up to the pooled table.
period_sum = sum(results[s]["counts"] for s in ("pre_2017_2019", "during_2020_2021", "post_2022_2024"))
assert (period_sum == counts).all().all(), "periods do not add up to the pooled table"
print("Checks passed: classes add up, totals match step 07, an independent method agrees, periods add up, Wilson interval verified.\n")

# --- 3. Save the tables (one CSV per indicator, with a 'scope' column) ---
for key in INDICATORS:
    stacked_scopes = pd.concat({scope: results[scope]["indicators"][key] for scope in SCOPES}, names=["scope", "road_user_group"]).reset_index()
    stacked_scopes.to_csv(output_dir / f"severity_{key}.csv", index=False, float_format="%.3f")
# Table d: counts and shares of the severity classes (fatal shown in its two classes)
distribution_parts = {}
for scope in SCOPES:
    c = results[scope]["counts"]
    d = pd.DataFrame({"accidents": c["accidents"]})
    for label, column in (("with_fatalities_class1", "class1"), ("fatally_injured_class2", "class2"), ("seriously_injured_class3", "class3"), ("slightly_injured_class4", "class4")):
        d[f"{label}_count"] = c[column]
        d[f"{label}_pct"] = c[column] / c["accidents"] * 100
    d["fatal_total_pct"] = (c["class1"] + c["class2"]) / c["accidents"] * 100
    distribution_parts[scope] = d
pd.concat(distribution_parts, names=["scope", "road_user_group"]).reset_index().to_csv(output_dir / "severity_d_distribution.csv", index=False, float_format="%.3f")

# --- 4. Print the pooled tables ---
LABELS = {"a_fatal": "a. Fatal accidents (class 1 + 2)", "b_serious": "b. Seriously injured accidents (class 3)", "c_slight": "c. Slightly injured accidents (class 4)"}
print("=== Pooled 2017-2024 ===\n")
for key, table in pooled["indicators"].items():
    show = table.copy()
    show["95% interval"] = [f"{lo:.1f}-{hi:.1f}%" for lo, hi in zip(show["ci_low_pct"], show["ci_high_pct"])]
    print(LABELS[key])
    print(show[["accidents", "count", "share_pct", "95% interval", "ratio_to_all", "gap_points"]].to_string(
        formatters={"accidents": "{:,.0f}".format, "count": "{:,.0f}".format, "share_pct": "{:.2f}%".format, "ratio_to_all": "{:.2f}".format, "gap_points": "{:+.2f}".format}), "\n")
print("d. Severity distribution (% of the group's accidents)")
print(distribution_parts["pooled_2017_2024"][["accidents", "with_fatalities_class1_pct", "fatally_injured_class2_pct", "seriously_injured_class3_pct", "slightly_injured_class4_pct"]].rename(
    columns={"with_fatalities_class1_pct": "With fatalities", "fatally_injured_class2_pct": "Fatally injured", "seriously_injured_class3_pct": "Seriously", "slightly_injured_class4_pct": "Slightly"}).to_string(
    formatters={"accidents": "{:,.0f}".format, "With fatalities": "{:.2f}".format, "Fatally injured": "{:.2f}".format, "Seriously": "{:.2f}".format, "Slightly": "{:.2f}".format}), "\n")
print("Fatal-accident share (%) by period (the full period tables are in the CSV files)")
period_fatal = pd.DataFrame({scope.split("_")[0]: results[scope]["indicators"]["a_fatal"]["share_pct"] for scope in SCOPES})
print(period_fatal.to_string(float_format=lambda v: f"{v:.2f}"), "\n")

# --- 5. Graphs (decisions #76, #77): the 8 named groups + the reference ---
SURFACE, INK, INK_2, MUTED, GRID, BASELINE, BLUE, GRAY = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#2a78d6", "#898781"
plt.rcParams["font.family"] = ["Helvetica Neue", "Arial", "DejaVu Sans"]  # a plain system sans
named = [g for g in order if g not in ("Unknown", "Other road user")]

# 5a. Interval charts for a, b, c
fig, axes = plt.subplots(1, 3, figsize=(13, 5.4), dpi=200, facecolor=SURFACE)
for ax, (key, table) in zip(axes, pooled["indicators"].items()):
    ax.set_facecolor(SURFACE)
    data = table.loc[named].sort_values("share_pct", ascending=False)  # highest share at the top
    y = np.arange(len(data))[::-1]
    overall = table.loc["All accidents", "share_pct"]
    ax.axvline(overall, color=GRAY, linewidth=1.5, zorder=1)
    ax.hlines(y, data["ci_low_pct"], data["ci_high_pct"], color=BLUE, linewidth=2, zorder=2)  # the 95% interval
    ax.plot(data["share_pct"], y, "o", color=BLUE, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)  # the share
    span = data["ci_high_pct"].max() - data["ci_low_pct"].min()
    for yi, (share, low, high) in zip(y, zip(data["share_pct"], data["ci_low_pct"], data["ci_high_pct"])):
        # The value label goes on the side of the dot AWAY from the gray reference line, so the line never cuts through it.
        if share >= overall:
            ax.text(high + span * 0.03, yi, f"{share:.1f}%", va="center", ha="left", fontsize=9, color=INK)
        else:
            ax.text(low - span * 0.03, yi, f"{share:.1f}%", va="center", ha="right", fontsize=9, color=INK)
    ax.set_yticks(y, data.index)
    ax.set_xlim(min(data["ci_low_pct"].min(), overall) - span * 0.3, max(data["ci_high_pct"].max(), overall) + span * 0.28)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))  # whole-number ticks only, so a label never rounds a tick like 7.5 to "8%"
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(length=0, labelsize=9, labelcolor=INK_2)
    ax.set_title(LABELS[key], fontsize=10.5, fontweight="bold", color=INK, loc="left", pad=22)
    ax.text(0, 1.015, f"all accidents: {overall:.1f}% (gray line)", transform=ax.transAxes, fontsize=8, color=MUTED, ha="left", va="bottom")
fig.text(0.02, 0.975, "How severe are the accidents each road-user group is part of? 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.93, "Dot = share of the group's accidents in that class; line = 95% interval (Wilson), wider for groups with fewer accidents. Severity belongs to the whole accident, so a car-pedestrian accident counts for both groups.",
         fontsize=8, color=INK_2, ha="left", va="top")
fig.subplots_adjust(left=0.085, right=0.985, top=0.80, bottom=0.08, wspace=0.55)
fig.savefig(output_dir / "severity_intervals.png", facecolor=SURFACE)
plt.close(fig)

# 5b. 100% stacked bars: the severity distribution (d), ordered by fatal share
dist = distribution_parts["pooled_2017_2024"]
share_fatal = dist["fatal_total_pct"]
share_serious, share_slight = dist["seriously_injured_class3_pct"], dist["slightly_injured_class4_pct"]
bar_order = sorted(named, key=lambda g: share_fatal[g], reverse=True)
labels = ["All accidents"] + bar_order
RAMP = {"fatal": "#184f95", "serious": "#3987e5", "slight": "#86b6ef"}  # one blue ramp, dark = more severe (ordinal)
fig, ax = plt.subplots(figsize=(11, 5.6), dpi=200, facecolor=SURFACE)
ax.set_facecolor(SURFACE)
y = np.arange(len(labels))[::-1]
for yi, g in zip(y, labels):
    f, s, l = share_fatal[g], share_serious[g], share_slight[g]
    ax.barh(yi, f, height=0.55, color=RAMP["fatal"], zorder=3)
    ax.barh(yi, s, height=0.55, left=f + 0.0, color=RAMP["serious"], zorder=3, linewidth=0)
    ax.barh(yi, l, height=0.55, left=f + s, color=RAMP["slight"], zorder=3, linewidth=0)
    # Thin surface-coloured gaps between the segments
    for edge in (f, f + s):
        ax.plot([edge, edge], [yi - 0.275, yi + 0.275], color=SURFACE, linewidth=1.6, zorder=4)
    ax.text(f + s + l / 2, yi, f"{l:.1f}% slight", ha="center", va="center", fontsize=9, color=INK, zorder=5)
    ax.text(101.5, yi, f"fatal {f:.1f}%  ·  serious {s:.1f}%", ha="left", va="center", fontsize=9, color=INK)
ax.set_xlim(0, 100)
ax.set_yticks(y, labels)
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
ax.set_axisbelow(True)
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
ax.spines["bottom"].set_color(BASELINE)
ax.tick_params(length=0, labelsize=9.5, labelcolor=INK_2)
fig.text(0.04, 0.965, "Severity distribution of the accidents each road-user group is part of, 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.04, 0.915, "100% of the group's accidents. Fatal = with fatalities + fatally injured. Ordered by fatal share. Severity belongs to the whole accident, not to one road user.",
         fontsize=8, color=INK_2, ha="left", va="top")
fig.legend(handles=[Patch(color=RAMP["fatal"], label="Fatal"), Patch(color=RAMP["serious"], label="Seriously injured"), Patch(color=RAMP["slight"], label="Slightly injured")],
           loc="lower left", bbox_to_anchor=(0.04, 0.005), ncol=3, frameon=False, fontsize=8.5, labelcolor=INK_2, handlelength=1.2, handleheight=1.2)
fig.subplots_adjust(left=0.14, right=0.78, top=0.86, bottom=0.14)
fig.savefig(output_dir / "severity_distribution.png", facecolor=SURFACE)
plt.close(fig)
print(f"Saved 4 CSV files and 2 graphs (severity_intervals.png, severity_distribution.png) in {output_dir}/")
