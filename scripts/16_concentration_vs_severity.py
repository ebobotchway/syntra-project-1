"""
Step 16 - Analysis 4b: does accident concentration go with accident severity?

Part 1: 500 m squares (as in step 3) grouped into classes by the number of accidents in the square; the severity of the accidents in each class.
Part 2: municipalities in five density classes (accidents per km2 per year); the severity of the accidents in each class, and the correlation.
Limit as before: the accident class describes the WHOLE accident, not one road user; and concentration is where accidents are COUNTED, not a rate per traffic.

Decisions applied (see beslissingslogboek.md):
  #91 the request.   #96 squares AND municipalities.   #97 all accidents + cyclists, pedestrians, motorcycles, mopeds; for a group the concentration is
  that group's own accidents per square (or per km2) and the severity is that of those accidents (an accident counts for a group if road user 1 OR 2, #33).
  #98 squares: all years 2017-2024 AND 2022-2024, accidents with usable coordinates (#90); municipalities: all accidents.
  #100 classes of squares: 1, 2-4, 5-9, 10-19, 20-49, 50-99, 100+ accidents.   #101 municipalities in five equal-sized density classes (quintiles).
  #102 correlation (Spearman): municipalities with at least 100 accidents; for a group at least 30 accidents of that group.
  #99 graphs.   #95/#74 shares with 95% Wilson intervals.   #71 fatal = class 1 + 2.

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/16_concentration_vs_severity.py OPENDATA_MAP_2017-2024_en_flagged.csv.gz data/municipality_outlines.gpkg reports
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
from scipy.stats import spearmanr

accidents_file = sys.argv[1]  # the flagged English dataset from step 05
outlines_file = sys.argv[2]   # municipality outlines from step 13
output_dir = Path(sys.argv[3])  # the reports/ folder
output_dir.mkdir(exist_ok=True)

# --- 1. Read the data ---
header = pd.read_csv(accidents_file, nrows=0).columns
df = pd.read_csv(accidents_file, dtype={c: str for c in header if c.endswith("_code")})
usable = df["x_coord"].between(20_000, 300_000) & df["y_coord"].between(20_000, 250_000)  # decision #90: impossible coordinates are not used
step12 = pd.read_csv(output_dir / "severity_d_distribution.csv")
step12 = step12[step12["scope"] == "pooled_2017_2024"].set_index("road_user_group")

GROUPS = {"All accidents": None, "Bicycle": "03", "Pedestrian": "08", "Motorcycle": "07", "Moped": "06"}
masks = {name: (pd.Series(True, index=df.index) if code is None else (df["road_user_type1_code"] == code) | (df["road_user_type2_code"] == code)) for name, code in GROUPS.items()}
CLASS_OF = {"fatal": ["1", "2"], "serious": ["3"], "slight": ["4"]}
CELL = 500
SQUARE_BINS = [1, 2, 5, 10, 20, 50, 100, np.inf]  # decision #100
SQUARE_LABELS = ["1", "2-4", "5-9", "10-19", "20-49", "50-99", "100+"]
SCOPES = {"2017-2024": range(2017, 2025), "2022-2024": range(2022, 2025)}
N_YEARS = 8


def wilson(successes, n, z=1.96):
    """95% Wilson confidence interval for a share, in percent."""
    if n == 0:
        return float("nan"), float("nan")
    p = successes / n
    denominator = 1 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denominator
    return (center - half) * 100, (center + half) * 100


def indicators(sub):
    """Accidents, and for fatal / serious / slight: the count, share and 95% interval."""
    n = len(sub)
    row = {"accidents": n, "few_accidents": n < 100}
    for label, codes in CLASS_OF.items():
        k = int(sub["accident_class_code"].isin(codes).sum())
        low, high = wilson(k, n)
        row.update({f"{label}_count": k, f"{label}_share_pct": k / n * 100 if n else float("nan"), f"{label}_ci_low": low, f"{label}_ci_high": high})
    return row


# =====================================================================
# Part 1: severity by square concentration
# =====================================================================
rows = []
for scope, years in SCOPES.items():
    for group, mask in masks.items():
        sub = df[mask & df["collision_year"].isin(years) & usable].copy()
        sub["cx"], sub["cy"] = (sub["x_coord"] // CELL).astype(int), (sub["y_coord"] // CELL).astype(int)
        sub["square_accidents"] = sub.groupby(["cx", "cy"])["x_coord"].transform("size")  # how many of the group's accidents are in the same square
        sub["square_class"] = pd.cut(sub["square_accidents"], bins=SQUARE_BINS, right=False, labels=SQUARE_LABELS)
        n_squares = sub.groupby(["cx", "cy"]).size().rename("n").reset_index()
        n_squares["square_class"] = pd.cut(n_squares["n"], bins=SQUARE_BINS, right=False, labels=SQUARE_LABELS)
        assert n_squares["n"].sum() == len(sub), "square counts do not add up"
        reference = indicators(sub)
        for label in SQUARE_LABELS:
            part = sub[sub["square_class"] == label]
            rows.append({"scope": scope, "group": group, "square_class": label, "squares": int((n_squares["square_class"] == label).sum()), **indicators(part),
                         **{f"overall_{k}_share_pct": reference[f"{k}_share_pct"] for k in CLASS_OF}})
squares_table = pd.DataFrame(rows)
for (scope, group), part in squares_table.groupby(["scope", "group"]):  # the classes must add up to all located accidents of that group in that scope
    expected = int((masks[group] & df["collision_year"].isin(SCOPES[scope]) & usable).sum())
    assert part["accidents"].sum() == expected, f"{scope} {group}: classes do not add up to {expected}"
squares_table.to_csv(output_dir / "severity_by_square_concentration.csv", index=False, float_format="%.3f")
print("Checks passed for part 1: the concentration classes add up to all located accidents of every group and scope.\n")

print("PART 1. Severity by number of accidents in the 500 m square, 2017-2024 (accidents with coordinates)")
for group in GROUPS:
    part = squares_table[(squares_table["scope"] == "2017-2024") & (squares_table["group"] == group) & (squares_table["accidents"] > 0)].set_index("square_class")
    overall = part.iloc[0]
    print(f"\n{group}: overall fatal {overall['overall_fatal_share_pct']:.2f}%, serious {overall['overall_serious_share_pct']:.2f}%")
    show = part[["squares", "accidents", "fatal_share_pct", "serious_share_pct", "slight_share_pct"]].copy()
    show["fatal 95% interval"] = [f"{lo:.1f}-{hi:.1f}%" for lo, hi in zip(part["fatal_ci_low"], part["fatal_ci_high"])]
    print(show.to_string(formatters={"squares": "{:,.0f}".format, "accidents": "{:,.0f}".format, "fatal_share_pct": "{:.2f}%".format, "serious_share_pct": "{:.2f}%".format, "slight_share_pct": "{:.2f}%".format}))
print()

# =====================================================================
# Part 2: severity by municipality density
# =====================================================================
outlines = gpd.read_file(outlines_file)
area = outlines.set_index("nis_code").geometry.area / 1e6  # km2
names = df.groupby("municipality_nis_code")[["municipality", "region"]].first()
municipal_rows, class_rows, correlation_rows = [], [], []
for group, mask in masks.items():
    per = pd.DataFrame({"municipality": names["municipality"], "region": names["region"], "area_km2": area.reindex(names.index)})
    per["accidents"] = df[mask].groupby("municipality_nis_code").size().reindex(per.index, fill_value=0)
    per["fatal"] = df[mask & df["accident_class_code"].isin(CLASS_OF["fatal"])].groupby("municipality_nis_code").size().reindex(per.index, fill_value=0)
    per["serious"] = df[mask & df["accident_class_code"].isin(CLASS_OF["serious"])].groupby("municipality_nis_code").size().reindex(per.index, fill_value=0)
    assert per["area_km2"].notna().all(), "a municipality has no area"
    assert per["accidents"].sum() == mask.sum() and per["fatal"].sum() == step12.loc[group, "with_fatalities_class1_count"] + step12.loc[group, "fatally_injured_class2_count"], f"{group}: municipality totals differ from step 12"
    per["density_per_km2_per_year"] = per["accidents"] / per["area_km2"] / N_YEARS
    per["fatal_share_pct"] = per["fatal"] / per["accidents"] * 100
    per["serious_share_pct"] = per["serious"] / per["accidents"] * 100
    per["density_class"] = pd.qcut(per["density_per_km2_per_year"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)  # five equal-sized classes (decision #101)
    for k, part in per.groupby("density_class"):
        total, fatal, serious = int(part["accidents"].sum()), int(part["fatal"].sum()), int(part["serious"].sum())
        f_low, f_high = wilson(fatal, total)
        s_low, s_high = wilson(serious, total)
        class_rows.append({"group": group, "density_class": k, "municipalities": len(part), "density_min": part["density_per_km2_per_year"].min(), "density_max": part["density_per_km2_per_year"].max(),
                           "accidents": total, "fatal_count": fatal, "fatal_share_pct": fatal / total * 100, "fatal_ci_low": f_low, "fatal_ci_high": f_high,
                           "serious_count": serious, "serious_share_pct": serious / total * 100, "serious_ci_low": s_low, "serious_ci_high": s_high})
    minimum = 100 if group == "All accidents" else 30  # decision #102
    eligible = per[per["accidents"] >= minimum]
    for label in ("fatal", "serious"):
        rho, p = spearmanr(eligible["density_per_km2_per_year"], eligible[f"{label}_share_pct"])
        correlation_rows.append({"group": group, "indicator": label, "municipalities_used": len(eligible), "minimum_accidents": minimum, "spearman_rho": rho, "p_value": p})
    per.insert(0, "group", group)
    per["used_in_correlation"] = per["accidents"] >= minimum
    municipal_rows.append(per.reset_index())
municipal_table = pd.concat(municipal_rows)
class_table = pd.DataFrame(class_rows)
correlations = pd.DataFrame(correlation_rows)
assert (class_table.groupby("group")["accidents"].sum().values == municipal_table.groupby("group")["accidents"].sum().values).all(), "density classes do not add up"
municipal_table.to_csv(output_dir / "severity_municipality_density_table.csv", index=False, float_format="%.4f")
class_table.to_csv(output_dir / "severity_by_municipality_density.csv", index=False, float_format="%.4f")
correlations.to_csv(output_dir / "severity_density_correlation.csv", index=False, float_format="%.4f")
print("Checks passed for part 2: municipality counts match step 12 and the density classes add up for every group.\n")

print("PART 2. Severity by municipality density (accidents per km2 per year), five equal-sized classes")
for group in GROUPS:
    part = class_table[class_table["group"] == group].set_index("density_class")
    print(f"\n{group}")
    show = part[["municipalities", "density_min", "density_max", "accidents", "fatal_share_pct", "serious_share_pct"]].copy()
    show["fatal 95% interval"] = [f"{lo:.2f}-{hi:.2f}%" for lo, hi in zip(part["fatal_ci_low"], part["fatal_ci_high"])]
    print(show.to_string(formatters={"density_min": "{:.2f}".format, "density_max": "{:.2f}".format, "accidents": "{:,.0f}".format, "fatal_share_pct": "{:.2f}%".format, "serious_share_pct": "{:.2f}%".format}))
print("\nSpearman correlation between municipality density and severity share (rho: -1 = lower where denser, +1 = higher where denser)")
print(correlations.to_string(index=False, formatters={"spearman_rho": "{:+.2f}".format, "p_value": "{:.3g}".format}), "\n")

# =====================================================================
# Graphs (decision #99)
# =====================================================================
SURFACE, INK, INK_2, MUTED, GRID, BASELINE, BLUE, ORANGE, GRAY = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#2a78d6", "#eb6834", "#898781"
plt.rcParams["font.family"] = ["Helvetica Neue", "Arial", "DejaVu Sans"]  # a plain system sans


def style(ax):
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}%")  # :g keeps 0.5% as 0.5%
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(length=0, labelsize=8.5, labelcolor=INK_2)


# E. Squares: severity by concentration class, two scopes
fig, axes = plt.subplots(2, 5, figsize=(15, 6.8), dpi=200, facecolor=SURFACE)
for col, group in enumerate(GROUPS):
    part_all = squares_table[(squares_table["group"] == group) & (squares_table["accidents"] > 0)]
    classes = [c for c in SQUARE_LABELS if c in set(part_all["square_class"])]
    for row, label in enumerate(("fatal", "serious")):
        ax = axes[row, col]
        ax.set_facecolor(SURFACE)
        tops = []
        for scope, colour, shift in (("2017-2024", BLUE, -0.13), ("2022-2024", ORANGE, 0.13)):
            part = squares_table[(squares_table["group"] == group) & (squares_table["scope"] == scope)].set_index("square_class")
            for i, c in enumerate(classes):
                r = part.loc[c]
                if r["accidents"] == 0:
                    continue
                ax.vlines(i + shift, r[f"{label}_ci_low"], r[f"{label}_ci_high"], color=colour, linewidth=1.8, zorder=2)
                ax.plot(i + shift, r[f"{label}_share_pct"], "o", markersize=6.5, markeredgecolor=colour, markeredgewidth=1.5, markerfacecolor=SURFACE if r["few_accidents"] else colour, zorder=3)
                if not r["few_accidents"]:
                    tops.append(r[f"{label}_ci_high"])
        overall = part_all[f"overall_{label}_share_pct"].iloc[0]
        ax.axhline(overall, color=GRAY, linewidth=1.3, zorder=1)
        ax.set_ylim(0, max(tops + [overall]) * 1.12)
        ax.set_xlim(-0.6, len(classes) - 0.4)
        ax.set_xticks(range(len(classes)), classes, fontsize=7.5, rotation=35, ha="right")  # rotated so neighbouring class labels never run into each other
        style(ax)
        if row == 0:
            ax.set_title(group, fontsize=10, fontweight="bold", color=INK, loc="left", pad=6)
        if row == 1:
            ax.set_xlabel("accidents in the square", fontsize=8.5, color=MUTED)
        if col == 0:
            ax.set_ylabel("fatal share" if label == "fatal" else "serious share", fontsize=9, color=INK_2)
fig.legend(handles=[Line2D([0], [0], marker="o", color=BLUE, markerfacecolor=BLUE, markersize=7, linewidth=0, label="2017-2024"), Line2D([0], [0], marker="o", color=ORANGE, markerfacecolor=ORANGE, markersize=7, linewidth=0, label="2022-2024"),
                    Line2D([0], [0], marker="o", color=INK_2, markerfacecolor=SURFACE, markersize=7, linewidth=0, label="hollow = fewer than 100 accidents (may run off the panel)"), Line2D([0], [0], color=GRAY, linewidth=1.3, label="overall share of that group")],
           loc="lower center", bbox_to_anchor=(0.5, 0.005), ncol=4, frameon=False, fontsize=8.5, labelcolor=INK_2)
fig.text(0.02, 0.975, "Are accidents in busier 500 m squares more or less severe? 2017-2024 and 2022-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.935, "Each accident is put in the class of its square (how many of that group's accidents lie in the square). Dot = share of the accidents in the class; line = 95% interval. Only accidents with coordinates.",
         fontsize=8, color=INK_2, ha="left", va="top")
fig.subplots_adjust(left=0.05, right=0.99, top=0.80, bottom=0.14, wspace=0.35, hspace=0.38)
fig.savefig(output_dir / "severity_by_square_concentration.png", facecolor=SURFACE)
plt.close(fig)

# F. Municipality density classes
fig, axes = plt.subplots(2, 5, figsize=(15, 6.6), dpi=200, facecolor=SURFACE)
for col, group in enumerate(GROUPS):
    part = class_table[class_table["group"] == group].set_index("density_class")
    for row, label in enumerate(("fatal", "serious")):
        ax = axes[row, col]
        ax.set_facecolor(SURFACE)
        for k in range(1, 6):
            r = part.loc[k]
            ax.vlines(k, r[f"{label}_ci_low"], r[f"{label}_ci_high"], color=BLUE, linewidth=2, zorder=2)
            ax.plot(k, r[f"{label}_share_pct"], "o", color=BLUE, markersize=7.5, markeredgecolor=SURFACE, markeredgewidth=1.6, zorder=3)
            ax.text(k, r[f"{label}_ci_high"] + part[f"{label}_ci_high"].max() * 0.04, f"{r[f'{label}_share_pct']:.1f}%", ha="center", va="bottom", fontsize=8, color=INK)
        overall = part[f"{label}_count"].sum() / part["accidents"].sum() * 100
        ax.axhline(overall, color=GRAY, linewidth=1.3, zorder=1)
        ax.set_ylim(0, part[f"{label}_ci_high"].max() * 1.22)
        ax.set_xlim(0.4, 5.6)
        ax.set_xticks(range(1, 6), ["1\nlowest", "2", "3", "4", "5\nhighest"], fontsize=8)
        style(ax)
        if row == 0:
            ax.set_title(group, fontsize=10, fontweight="bold", color=INK, loc="left", pad=6)
        if row == 1:
            ax.set_xlabel("accident density class of the municipality", fontsize=8.5, color=MUTED)
        if col == 0:
            ax.set_ylabel("fatal share" if label == "fatal" else "serious share", fontsize=9, color=INK_2)
fig.text(0.02, 0.975, "Are accidents in denser municipalities more or less severe? 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.935, "581 municipalities in five equal-sized classes by accidents per km2 per year (of that group). Dot = share of the accidents in the class; line = 95% interval; gray line = overall share of that group.",
         fontsize=8, color=INK_2, ha="left", va="top")
fig.subplots_adjust(left=0.05, right=0.99, top=0.80, bottom=0.10, wspace=0.35, hspace=0.42)
fig.savefig(output_dir / "severity_by_municipality_density.png", facecolor=SURFACE)
plt.close(fig)

# G. Municipality scatter: density against fatal share
fig, axes = plt.subplots(2, 5, figsize=(15, 6.8), dpi=200, facecolor=SURFACE)
for col, group in enumerate(GROUPS):
    per = municipal_table[(municipal_table["group"] == group) & municipal_table["used_in_correlation"] & (municipal_table["density_per_km2_per_year"] > 0)]
    for row, label in enumerate(("fatal", "serious")):
        ax = axes[row, col]
        ax.set_facecolor(SURFACE)
        ax.scatter(per["density_per_km2_per_year"], per[f"{label}_share_pct"], s=np.sqrt(per["accidents"]) * 1.6, color=BLUE, alpha=0.55, edgecolors=SURFACE, linewidths=0.4, zorder=3)
        ax.set_xscale("log")
        ax.set_ylim(0, None)
        rho = correlations[(correlations["group"] == group) & (correlations["indicator"] == label)].iloc[0]
        ax.text(0.97, 0.95, f"rho = {rho['spearman_rho']:+.2f}\n{int(rho['municipalities_used'])} municipalities", transform=ax.transAxes, ha="right", va="top", fontsize=8.5, color=INK,
                bbox=dict(boxstyle="round,pad=0.25", fc=SURFACE, ec="none", alpha=0.85))
        style(ax)
        ax.xaxis.set_major_formatter(lambda v, _: f"{v:g}")
        if row == 0:
            ax.set_title(group, fontsize=10, fontweight="bold", color=INK, loc="left", pad=6)
        if row == 1:
            ax.set_xlabel("accidents per km2 per year (log scale)", fontsize=8.5, color=MUTED)
        if col == 0:
            ax.set_ylabel("fatal share" if label == "fatal" else "serious share", fontsize=9, color=INK_2)
fig.text(0.02, 0.975, "Density and severity across municipalities, 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.935, "One dot per municipality (bigger = more accidents). Only municipalities with at least 100 accidents (for a group: at least 30 of its accidents). rho = Spearman rank correlation.",
         fontsize=8, color=INK_2, ha="left", va="top")
fig.subplots_adjust(left=0.05, right=0.99, top=0.80, bottom=0.10, wspace=0.35, hspace=0.42)
fig.savefig(output_dir / "severity_density_scatter.png", facecolor=SURFACE)
plt.close(fig)
print(f"Saved 5 CSV files and 3 graphs (severity_by_square_concentration.png, severity_by_municipality_density.png, severity_density_scatter.png) in {output_dir}/")
