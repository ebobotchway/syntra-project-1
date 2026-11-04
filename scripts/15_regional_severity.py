"""
Step 15 - Analysis 4a: regional differences in accident severity.

Severity classes, indicators and the counting rule are those of step 12; the accident's region and province are the ones where it happened.
Limit as before: the accident class describes the WHOLE accident, not one road user.

Decisions applied (see beslissingslogboek.md):
  #91 the request.   #92 regions (3) and provinces (10; Brussels has no province and is its own line).
  #93 all accidents + cyclists, pedestrians, motorcycles and mopeds (an accident counts for a group if that group is road user 1 OR 2, #33).
  #94/#103 the same indicators per region within each road type (motorway, regional road, municipal road), also for the four groups;
           cells with fewer than 100 accidents are flagged. This controls for road type only.
  #95 per area: share of fatal / serious / slight accidents with a 95% Wilson interval, ratio to Belgium and percentage-point gap to Belgium.
  #99 graphs: interval charts, a group x region chart, a road-type chart and a province map.
  #71 fatal = class 1 + class 2.

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/15_regional_severity.py OPENDATA_MAP_2017-2024_en_flagged.csv.gz data/municipality_outlines.gpkg reports
"""
import math
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")  # draw to a file, not to a window
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

accidents_file = sys.argv[1]  # the flagged English dataset from step 05
outlines_file = sys.argv[2]   # municipality outlines from step 13
output_dir = Path(sys.argv[3])  # the reports/ folder
output_dir.mkdir(exist_ok=True)

# --- 1. Read the data (code columns as text so "03" keeps its zero) ---
header = pd.read_csv(accidents_file, nrows=0).columns
df = pd.read_csv(accidents_file, dtype={c: str for c in header if c.endswith("_code")})
df["province_label"] = df["province"].fillna("Brussels (no province)")  # Brussels-Capital Region has no province
step12 = pd.read_csv(output_dir / "severity_d_distribution.csv")  # severity counts of step 12, to check against
step12 = step12[step12["scope"] == "pooled_2017_2024"].set_index("road_user_group")

GROUPS = {"All accidents": None, "Bicycle": "03", "Pedestrian": "08", "Motorcycle": "07", "Moped": "06"}
masks = {}
for name, code in GROUPS.items():
    masks[name] = pd.Series(True, index=df.index) if code is None else (df["road_user_type1_code"] == code) | (df["road_user_type2_code"] == code)  # road user 1 OR 2
CLASS_OF = {"fatal": ["1", "2"], "serious": ["3"], "slight": ["4"]}
REGION_SHORT = {"Brussels-Capital Region": "Brussels", "Flemish Region": "Flanders", "Walloon Region": "Wallonia"}
ROAD_TYPES = ["Motorway", "Regional road", "Municipal road", "Unknown"]


def wilson(successes, n, z=1.96):
    """95% Wilson confidence interval for a share, in percent."""
    if n == 0:
        return float("nan"), float("nan")
    p = successes / n
    denominator = 1 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denominator
    return (center - half) * 100, (center + half) * 100


def counts(sub):
    """Accidents and how many are fatal / serious / slight."""
    classes = sub["accident_class_code"]
    return {"accidents": len(sub), **{label: int(classes.isin(codes).sum()) for label, codes in CLASS_OF.items()}}


def indicator_row(c, belgium):
    """One result row: for every indicator the count, share, 95% interval, ratio to Belgium and gap to Belgium (percentage points)."""
    row = {"accidents": c["accidents"], "few_accidents": c["accidents"] < 100}
    for label in CLASS_OF:
        share = c[label] / c["accidents"] * 100 if c["accidents"] else float("nan")
        low, high = wilson(c[label], c["accidents"])
        reference = belgium[label] / belgium["accidents"] * 100
        row.update({f"{label}_count": c[label], f"{label}_share_pct": share, f"{label}_ci_low": low, f"{label}_ci_high": high,
                    f"{label}_ratio_to_belgium": share / reference if reference else float("nan"), f"{label}_gap_points": share - reference})
    return row


# --- 2. Regions and provinces, per group ---
rows = []
belgium = {}
for group, mask in masks.items():
    belgium[group] = counts(df[mask])
    rows.append({"level": "Belgium", "area": "Belgium", "group": group, **indicator_row(belgium[group], belgium[group])})
    for level, column in (("Region", "region"), ("Province", "province_label")):
        for area in sorted(df.loc[mask, column].unique()):
            rows.append({"level": level, "area": area, "group": group, **indicator_row(counts(df[mask & (df[column] == area)]), belgium[group])})
regional = pd.DataFrame(rows)
regional.to_csv(output_dir / "severity_regional_regions_provinces.csv", index=False, float_format="%.3f")

# --- 3. Region x road type, per group (decision #94/#103) ---
rows = []
for group, mask in masks.items():
    for road_type in ROAD_TYPES:
        type_mask = mask & (df["road_type"] == road_type)
        belgium_type = counts(df[type_mask])
        for region in sorted(df["region"].unique()):
            rows.append({"group": group, "road_type": road_type, "region": region, **indicator_row(counts(df[type_mask & (df["region"] == region)]), belgium_type)})
roadtype = pd.DataFrame(rows)
roadtype.to_csv(output_dir / "severity_regional_roadtype.csv", index=False, float_format="%.3f")

# --- 4. Checks ---
for group in GROUPS:
    name = group
    reference = step12.loc[name] if name in step12.index else None
    parts = regional[(regional["group"] == group) & (regional["level"] == "Region")]
    assert parts["accidents"].sum() == belgium[group]["accidents"], f"{group}: regions do not add up to Belgium"
    provinces = regional[(regional["group"] == group) & (regional["level"] == "Province")]
    assert provinces["accidents"].sum() == belgium[group]["accidents"], f"{group}: provinces (+Brussels) do not add up to Belgium"
    assert roadtype[roadtype["group"] == group]["accidents"].sum() == belgium[group]["accidents"], f"{group}: road types do not add up"
    if reference is not None:  # independent check against the step-12 tables
        assert belgium[group]["fatal"] == reference["with_fatalities_class1_count"] + reference["fatally_injured_class2_count"], f"{group}: fatal differs from step 12"
        assert belgium[group]["serious"] == reference["seriously_injured_class3_count"], f"{group}: serious differs from step 12"
        assert belgium[group]["accidents"] == reference["accidents"], f"{group}: accident total differs from step 12"
assert belgium["All accidents"]["accidents"] == 289532 and belgium["All accidents"]["fatal"] == 4141, "overall counts differ from step 12"
print("Checks passed: regions, provinces and road types add up to Belgium for every group, and the Belgian counts match step 12.\n")

# --- 5. Print ---
def show(table, columns):
    return table[columns].to_string(formatters={"accidents": "{:,.0f}".format, **{c: "{:.2f}%".format for c in columns if c.endswith("_share_pct")},
                                               **{c: "{:.2f}".format for c in columns if c.endswith("_ratio_to_belgium")}, **{c: "{:+.2f}".format for c in columns if c.endswith("_gap_points")}})


for level in ("Region", "Province"):
    table = regional[(regional["group"] == "All accidents") & (regional["level"].isin([level, "Belgium"]))].set_index("area")
    table = table.sort_values("fatal_share_pct", ascending=False)
    table["fatal 95% interval"] = [f"{lo:.2f}-{hi:.2f}%" for lo, hi in zip(table["fatal_ci_low"], table["fatal_ci_high"])]
    print(f"{level}s, all accidents (sorted by fatal share)")
    print(show(table, ["accidents", "fatal_share_pct", "fatal 95% interval", "fatal_ratio_to_belgium", "fatal_gap_points", "serious_share_pct", "serious_ratio_to_belgium", "slight_share_pct"]), "\n")

print("Fatal share (%) by region and group (accidents in brackets)")
fatal_pivot = regional[regional["level"] == "Region"].pivot(index="group", columns="area", values="fatal_share_pct").loc[list(GROUPS)]
n_pivot = regional[regional["level"] == "Region"].pivot(index="group", columns="area", values="accidents").loc[list(GROUPS)]
print(pd.DataFrame({region: [f"{fatal_pivot.loc[g, region]:.2f}% ({n_pivot.loc[g, region]:,.0f})" for g in GROUPS] for region in fatal_pivot.columns}, index=list(GROUPS)).to_string(), "\n")
print("Serious share (%) by region and group")
serious_pivot = regional[regional["level"] == "Region"].pivot(index="group", columns="area", values="serious_share_pct").loc[list(GROUPS)]
print(serious_pivot.to_string(float_format=lambda v: f"{v:.2f}%"), "\n")
print("Fatal share (%) by region and road type, ALL accidents ('*' = fewer than 100 accidents)")
sub = roadtype[roadtype["group"] == "All accidents"]
print(sub.assign(cell=[f"{s:.2f}%{'*' if few else ''} ({n:,.0f})" for s, few, n in zip(sub["fatal_share_pct"], sub["few_accidents"], sub["accidents"])]).pivot(index="region", columns="road_type", values="cell")[ROAD_TYPES].to_string(), "\n")
print("Cells with fewer than 100 accidents in the road-type split:", int(roadtype["few_accidents"].sum()), "of", len(roadtype), "(all groups, incl. empty cells)\n")

# --- 6. Graphs (decision #99) ---
SURFACE, INK, INK_2, MUTED, GRID, BASELINE, BLUE, GRAY = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#2a78d6", "#898781"
REGION_COLOURS = {"Brussels-Capital Region": "#2a78d6", "Flemish Region": "#eb6834", "Walloon Region": "#1baf7a"}  # categorical slots 1-3 (validated for all pairs)
RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]
plt.rcParams["font.family"] = ["Helvetica Neue", "Arial", "DejaVu Sans"]  # a plain system sans

# 6a. Regions and provinces, all accidents: fatal and serious share
all_rows = regional[regional["group"] == "All accidents"].set_index(["level", "area"])
fig, axes = plt.subplots(1, 2, figsize=(12.5, 6.2), dpi=200, facecolor=SURFACE)
for ax, label, title in zip(axes, ("fatal", "serious"), ("Fatal accidents (class 1 + 2)", "Seriously injured accidents (class 3)")):
    ax.set_facecolor(SURFACE)
    blocks = [("Regions", all_rows.loc["Region"].sort_values(f"{label}_share_pct", ascending=False)),
              ("Provinces", all_rows.loc["Province"].sort_values(f"{label}_share_pct", ascending=False))]
    labels, ypos, y = [], [], 0
    for block_name, table in blocks:
        labels.append(block_name); ypos.append(y); y -= 1  # a header line for the block
        for area, r in table.iterrows():
            share, low, high = r[f"{label}_share_pct"], r[f"{label}_ci_low"], r[f"{label}_ci_high"]
            ax.hlines(y, low, high, color=BLUE, linewidth=2, zorder=2)
            ax.plot(share, y, "o", color=BLUE, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
            labels.append(area); ypos.append(y); y -= 1
        y -= 0.4
    ref = all_rows.loc[("Belgium", "Belgium"), f"{label}_share_pct"]
    ax.axvline(ref, color=GRAY, linewidth=1.5, zorder=1)
    all_share = all_rows[f"{label}_share_pct"]
    span = all_rows[f"{label}_ci_high"].max() - all_rows[f"{label}_ci_low"].min()
    for (block_name, table) in blocks:
        pass
    ax.set_yticks(ypos, labels)
    for tick, name in zip(ax.get_yticklabels(), labels):
        if name in ("Regions", "Provinces"):
            tick.set_fontweight("bold"); tick.set_color(INK)
    # value labels on the side of the dot away from the gray line
    for (level, area), r in all_rows.iterrows():
        if level == "Belgium":
            continue
        idx = labels.index(area)
        share = r[f"{label}_share_pct"]
        if share >= ref:
            ax.text(r[f"{label}_ci_high"] + span * 0.015, ypos[idx], f"{share:.1f}%", va="center", ha="left", fontsize=8.5, color=INK)
        else:
            ax.text(r[f"{label}_ci_low"] - span * 0.015, ypos[idx], f"{share:.1f}%", va="center", ha="right", fontsize=8.5, color=INK)
    ax.set_xlim(max(0, all_rows[f"{label}_ci_low"].min() - span * 0.14), all_rows[f"{label}_ci_high"].max() + span * 0.14)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:g}%")  # :g keeps 0.5% as 0.5%, instead of rounding it to 0% or 1%
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(length=0, labelsize=9, labelcolor=INK_2)
    ax.set_title(title, fontsize=10.5, fontweight="bold", color=INK, loc="left", pad=22)
    ax.text(0, 1.015, f"Belgium: {ref:.1f}% (gray line)", transform=ax.transAxes, fontsize=8, color=MUTED, ha="left", va="bottom")
fig.text(0.02, 0.975, "How severe are accidents in each region and province? 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.935, "Dot = share of the accidents in that area; line = 95% interval (Wilson). Brussels has no province. The class belongs to the whole accident.", fontsize=8, color=INK_2, ha="left", va="top")
fig.subplots_adjust(left=0.15, right=0.985, top=0.83, bottom=0.07, wspace=0.55)
fig.savefig(output_dir / "severity_regional_overview.png", facecolor=SURFACE)
plt.close(fig)

# 6b. Groups x regions: two rows (fatal, serious) x five groups
fig, axes = plt.subplots(2, 5, figsize=(14.5, 6.6), dpi=200, facecolor=SURFACE)
region_rows = regional[regional["level"] == "Region"].set_index(["group", "area"])
for col, group in enumerate(GROUPS):
    for row, label in enumerate(("fatal", "serious")):
        ax = axes[row, col]
        ax.set_facecolor(SURFACE)
        for i, region in enumerate(REGION_COLOURS):
            r = region_rows.loc[(group, region)]
            ax.vlines(i, r[f"{label}_ci_low"], r[f"{label}_ci_high"], color=REGION_COLOURS[region], linewidth=2, zorder=2)
            ax.plot(i, r[f"{label}_share_pct"], "o", color=REGION_COLOURS[region], markersize=8, markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
            ax.text(i + 0.12, r[f"{label}_share_pct"], f"{r[f'{label}_share_pct']:.1f}%", fontsize=8, color=INK, va="center", ha="left")
        ref = regional[(regional["group"] == group) & (regional["level"] == "Belgium")][f"{label}_share_pct"].iat[0]
        ax.axhline(ref, color=GRAY, linewidth=1.3, zorder=1)
        ax.set_xlim(-0.5, 2.9)
        top = max(region_rows.loc[group][f"{label}_ci_high"].max(), ref)
        ax.set_ylim(0, top * 1.15)
        ax.set_xticks(range(3), [REGION_SHORT[r] for r in REGION_COLOURS])
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}%")
        ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(BASELINE)
        ax.tick_params(length=0, labelsize=8.5, labelcolor=INK_2)
        if row == 0:
            ax.set_title(f"{group}\n({belgium[group]['accidents']:,} accidents)", fontsize=10, fontweight="bold", color=INK, loc="left", pad=6)
        if col == 0:
            ax.set_ylabel("fatal share" if label == "fatal" else "serious share", fontsize=9, color=INK_2)
fig.text(0.02, 0.975, "Regional differences in severity, by road-user group, 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.935, "Dot = share of the group's accidents; line = 95% interval; gray line = Belgium for that group. An accident counts once for every group it involves. Each panel has its own scale.",
         fontsize=8, color=INK_2, ha="left", va="top")
fig.subplots_adjust(left=0.05, right=0.99, top=0.80, bottom=0.07, wspace=0.35, hspace=0.35)
fig.savefig(output_dir / "severity_regional_groups.png", facecolor=SURFACE)
plt.close(fig)

# 6c. Road type: the same, within motorway / regional / municipal road
fig, axes = plt.subplots(2, 5, figsize=(14.5, 6.8), dpi=200, facecolor=SURFACE)
type_rows = roadtype.set_index(["group", "road_type", "region"])
types3 = ROAD_TYPES[:3]
for col, group in enumerate(GROUPS):
    for row, label in enumerate(("fatal", "serious")):
        ax = axes[row, col]
        ax.set_facecolor(SURFACE)
        tops = []
        for t, road_type in enumerate(types3):
            belgium_share = None
            for k, region in enumerate(REGION_COLOURS):
                r = type_rows.loc[(group, road_type, region)]
                if r["accidents"] == 0:
                    continue
                x = t + (k - 1) * 0.22
                colour = REGION_COLOURS[region]
                ax.vlines(x, r[f"{label}_ci_low"], r[f"{label}_ci_high"], color=colour, linewidth=1.8, zorder=2)
                ax.plot(x, r[f"{label}_share_pct"], "o", markersize=7, markeredgecolor=colour, markeredgewidth=1.6,
                        markerfacecolor=SURFACE if r["few_accidents"] else colour, zorder=3)  # hollow = fewer than 100 accidents
                if not r["few_accidents"]:
                    tops.append(r[f"{label}_ci_high"])  # only cells with 100+ accidents set the scale; hollow cells may run off the panel
            sub = df[masks[group] & (df["road_type"] == road_type)]
            ref = counts(sub)[label] / max(len(sub), 1) * 100
            ax.hlines(ref, t - 0.4, t + 0.4, color=GRAY, linewidth=1.4, zorder=1)  # Belgium within this road type
        ax.set_xlim(-0.5, 2.5)
        ax.set_ylim(0, max(tops) * 1.12)
        ax.set_xticks(range(3), ["Motorway", "Regional", "Municipal"])
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}%")
        ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(BASELINE)
        ax.tick_params(length=0, labelsize=8.5, labelcolor=INK_2)
        if row == 0:
            ax.set_title(group, fontsize=10, fontweight="bold", color=INK, loc="left", pad=6)
        if col == 0:
            ax.set_ylabel("fatal share" if label == "fatal" else "serious share", fontsize=9, color=INK_2)
fig.legend(handles=[Line2D([0], [0], marker="o", color=REGION_COLOURS[r], markerfacecolor=REGION_COLOURS[r], markersize=7, linewidth=0, label=REGION_SHORT[r]) for r in REGION_COLOURS] +
           [Line2D([0], [0], marker="o", color=INK_2, markerfacecolor=SURFACE, markersize=7, linewidth=0, label="hollow = fewer than 100 accidents"),
            Line2D([0], [0], color=GRAY, linewidth=1.4, label="Belgium, same road type")],
           loc="lower center", bbox_to_anchor=(0.5, 0.005), ncol=5, frameon=False, fontsize=8.5, labelcolor=INK_2)
fig.text(0.02, 0.975, "Regional differences in severity within each road type, 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.935, "Dot = share of the accidents on that road type in that region; line = 95% interval. This accounts for road type only, not for speed, traffic or other differences. Each panel has its own scale; hollow cells (fewer than 100 accidents) may run off it.",
         fontsize=8, color=INK_2, ha="left", va="top")
fig.subplots_adjust(left=0.05, right=0.99, top=0.80, bottom=0.12, wspace=0.35, hspace=0.35)
fig.savefig(output_dir / "severity_regional_roadtype.png", facecolor=SURFACE)
plt.close(fig)

# 6d. Province map: fatal and serious share, all accidents (5 quantile classes)
outlines = gpd.read_file(outlines_file)
province_of = df.groupby("municipality_nis_code")["province_label"].first()
outlines["province_label"] = outlines["nis_code"].map(province_of)
assert outlines["province_label"].notna().all(), "a municipality has no province"
provinces_map = outlines.dissolve(by="province_label").reset_index()
provinces_map["geometry"] = provinces_map.geometry.buffer(100).buffer(-100)  # closes the tiny gaps between the separately simplified municipality outlines
prov_rows = all_rows.loc["Province"]
fig, axes = plt.subplots(1, 2, figsize=(13, 6.2), dpi=200, facecolor=SURFACE)
for ax, label, title in zip(axes, ("fatal", "serious"), ("Fatal share of accidents", "Serious-injury share of accidents")):
    ax.set_facecolor(SURFACE)
    values = provinces_map["province_label"].map(prov_rows[f"{label}_share_pct"])
    edges = np.unique(np.quantile(values, np.linspace(0, 1, 6)))
    classes = np.clip(np.digitize(values, edges[1:-1], right=True), 0, len(edges) - 2)
    provinces_map.plot(ax=ax, color=[RAMP[c] for c in classes], edgecolor=SURFACE, linewidth=0.8)
    for geom, name, value, c in zip(provinces_map.geometry, provinces_map["province_label"], values, classes):
        point = geom.representative_point()
        ax.annotate(f"{name.replace(' (no province)', '')}\n{value:.1f}%", (point.x, point.y), ha="center", va="center", fontsize=7.5, color="#ffffff" if c >= 2 else INK, fontweight="bold")
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for side in ax.spines.values():
        side.set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=RAMP[i]) for i in range(len(edges) - 1)]
    ax.legend(handles, [f"{edges[i]:.1f}-{edges[i + 1]:.1f}%" for i in range(len(edges) - 1)], loc="lower left", frameon=False, fontsize=8, labelcolor=INK_2, title="5 quantile classes", title_fontsize=8)
    ax.set_title(title, fontsize=10.5, fontweight="bold", color=INK, loc="left")
fig.text(0.02, 0.975, "Accident severity by province, 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.935, "Brussels is shown as its own area (no province). Province outlines are made from the municipality outlines of Statbel, CC BY 4.0.", fontsize=8, color=INK_2, ha="left", va="top")
fig.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.01, wspace=0.03)
fig.savefig(output_dir / "severity_regional_province_map.png", facecolor=SURFACE)
plt.close(fig)
print(f"Saved 2 CSV files and 4 graphs (severity_regional_*.png) in {output_dir}/")
