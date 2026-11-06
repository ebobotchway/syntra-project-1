"""
Step 24 - Analysis 3b/3c, municipality view: the 3a analysis (cyclists by municipality) repeated for pedestrians, motorcycles and mopeds

For each of the three groups:
  - a table with all 581 municipalities (accidents with the group, all accidents, the group's share, ranks)
  - a ranked chart: top 20 by number of accidents and top 20 by share (municipalities with at least 100 accidents)
  - a bubble map and a choropleth, exactly like 3a
Also writes one table with the numbers per municipality for the periods the claude.ai page lets you choose (all years, 2022-2024 and each year),
for the four groups (cyclists too) with the severe accidents, so the page can re-rank in the browser.

Decisions applied (see beslissingslogboek.md): #158 the request. #159 same as 3a for each group, hotspots stay. #160 filters (here: the saved period table). #161 share ranking needs 100+ accidents.
Same rules as step 14: #33 counting (road user 1 OR 2), #81 counts and share (no rate per inhabitant), #82 bubble map and choropleth, #88 share ranking only with 100+ accidents,
#89 five quantile classes. Severe = accident class 1, 2 or 3 (#116).

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/24_municipalities_other_groups.py OPENDATA_MAP_2017-2024_en_flagged.csv.gz data/municipality_outlines.gpkg reports
"""
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")  # draw to a file, not to a window
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

accidents_file = sys.argv[1]    # the flagged English dataset from step 05
outlines_file = sys.argv[2]     # municipality outlines from step 13
output_dir = Path(sys.argv[3])  # the reports/ folder

header = pd.read_csv(accidents_file, nrows=0).columns
df = pd.read_csv(accidents_file, dtype={c: str for c in header if c.endswith("_code")})
outlines = gpd.read_file(outlines_file)
step7 = pd.read_csv(output_dir / "accidents_per_road_user.csv").set_index("road_user_group")["accidents"]
df["severe"] = df["accident_class_code"].isin(["1", "2", "3"])
assert int(df["severe"].sum()) == 28532, "severe count differs from step 5"

GROUPS = {"Bicycle": "03", "Pedestrian": "08", "Motorcycle": "07", "Moped": "06"}
NEW_GROUPS = ["Pedestrian", "Motorcycle", "Moped"]
mask = {name: (df["road_user_type1_code"] == code) | (df["road_user_type2_code"] == code) for name, code in GROUPS.items()}  # decision #33
for name in GROUPS:
    assert int(mask[name].sum()) == int(step7[name]), f"{name}: count differs from step 07"
usable = df["x_coord"].between(20_000, 300_000) & df["y_coord"].between(20_000, 250_000)  # decision #90

MIN_ACCIDENTS = 100  # decision #88 / #161
SURFACE, INK, INK_2, MUTED, GRID, BASELINE, BLUE, GRAY, LAND = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#2a78d6", "#898781", "#f1f0ec"
RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]
plt.rcParams["font.family"] = ["Helvetica Neue", "Arial", "DejaVu Sans"]
LOWER = {"Pedestrian": "pedestrian", "Motorcycle": "motorcycle", "Moped": "moped"}
PLURAL = {"Pedestrian": "pedestrians", "Motorcycle": "motorcycles", "Moped": "mopeds"}


def quantile_classes(values, n=5):
    edges = np.unique(np.quantile(values, np.linspace(0, 1, n + 1)))
    return edges, np.clip(np.digitize(values, edges[1:-1], right=True), 0, len(edges) - 2)


def style_map(ax):
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for side in ax.spines.values():
        side.set_visible(False)


located = df[usable]
centre = located.groupby("municipality_nis_code")[["x_coord", "y_coord"]].mean()  # average position of the municipality's accidents (#82)
base = df.groupby("municipality_nis_code").agg(municipality=("municipality", "first"), region=("region", "first"), province=("province", "first"), accidents_total=("collision_year", "size"))
assert base["accidents_total"].sum() == len(df)

for group in NEW_GROUPS:
    plural, key = PLURAL[group], LOWER[group]
    t = base.copy()
    t["accidents_group"] = df[mask[group]].groupby("municipality_nis_code").size().reindex(t.index, fill_value=0)
    t["group_share_pct"] = t["accidents_group"] / t["accidents_total"] * 100
    t["ranked_by_share"] = t["accidents_total"] >= MIN_ACCIDENTS
    t["rank_count"] = t["accidents_group"].rank(ascending=False, method="min").astype(int)
    t["rank_share"] = t.loc[t["ranked_by_share"], "group_share_pct"].rank(ascending=False, method="min")
    t = t.sort_values("rank_count")
    assert t["accidents_group"].sum() == int(mask[group].sum()), f"{group}: municipality counts do not add up"
    t.to_csv(output_dir / f"geo_a_{key}s_by_municipality.csv", float_format="%.2f")
    national = t["accidents_group"].sum() / len(df) * 100
    top_share = t[t["ranked_by_share"]].sort_values("group_share_pct", ascending=False)
    print(f"{group}: {t['accidents_group'].sum():,} accidents in {(t['accidents_group'] > 0).sum()} of {len(t)} municipalities; Belgium share {national:.1f}%; {int(t['ranked_by_share'].sum())} municipalities ranked by share")
    print("  Top 5 by count:", ", ".join(f"{r.municipality} {r.accidents_group:,}" for r in t.head(5).itertuples()))
    print("  Top 5 by share:", ", ".join(f"{r.municipality} {r.group_share_pct:.1f}%" for r in top_share.head(5).itertuples()))
    by_region = df.assign(g=mask[group]).groupby("region").agg(accidents=("g", "size"), n=("g", "sum"))
    print("  Share by region:", ", ".join(f"{k} {v:.1f}%" for k, v in (by_region["n"] / by_region["accidents"] * 100).items()), "\n")

    # --- graph 1: ranked charts ---
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.6), dpi=200, facecolor=SURFACE)
    panels = [(t.head(20), "accidents_group", f"Top 20 by number of accidents involving {plural}", False),
              (top_share.head(20), "group_share_pct", f"Top 20 by {key} share ({MIN_ACCIDENTS}+ accidents)", True)]
    for ax, (data, column, title, is_share) in zip(axes, panels):
        ax.set_facecolor(SURFACE)
        data = data.iloc[::-1]
        ax.barh(data["municipality"], data[column], height=0.6, color=BLUE, zorder=3)
        for y, (_, row) in enumerate(data.iterrows()):
            label = f"{row[column]:.1f}%  ({row['accidents_group']:,.0f} of {row['accidents_total']:,.0f})" if is_share else f"{row[column]:,.0f}  ({row['group_share_pct']:.0f}% of {row['accidents_total']:,.0f})"
            ax.text(row[column] + data[column].max() * 0.012, y, label, va="center", ha="left", fontsize=8, color=INK)
        if is_share:
            ax.axvline(national, color=GRAY, linewidth=1.5, zorder=2)
            ax.text(national, len(data) - 0.35, f" Belgium {national:.1f}%", fontsize=8, color=MUTED, ha="left", va="bottom")
        ax.set_xlim(0, data[column].max() * 1.5)
        ax.xaxis.set_major_formatter(lambda v, _, percent=is_share: f"{v:.0f}%" if percent else f"{v:,.0f}")
        ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(BASELINE)
        ax.tick_params(length=0, labelsize=9, labelcolor=INK_2)
        ax.set_title(title, fontsize=10.5, fontweight="bold", color=INK, loc="left", pad=8)
    fig.text(0.02, 0.975, f"Where do accidents involving {plural} happen? Municipalities, 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.935, "Counts favour big cities; the share shows where the group is an unusually large part of a municipality's accidents. An accident counts once for every road-user group it involves.", fontsize=8, color=INK_2, ha="left", va="top")
    fig.subplots_adjust(left=0.13, right=0.985, top=0.87, bottom=0.05, wspace=0.62)
    fig.savefig(output_dir / f"geo_a_{key}_ranked.png", facecolor=SURFACE)
    plt.close(fig)

    # --- graphs 2 and 3: bubble map and choropleth ---
    map_data = outlines.merge(t.reset_index(), left_on="nis_code", right_on="municipality_nis_code", how="left")
    assert map_data["accidents_total"].notna().all()
    polygon_centres = map_data.geometry.centroid
    bubble = map_data[["nis_code", "municipality", "accidents_group", "group_share_pct", "ranked_by_share"]].copy()
    bubble["x"], bubble["y"] = bubble["nis_code"].map(centre["x_coord"]), bubble["nis_code"].map(centre["y_coord"])
    none_ = bubble["x"].isna()
    bubble.loc[none_, "x"], bubble.loc[none_, "y"] = polygon_centres[none_].x, polygon_centres[none_].y
    edges, classes = quantile_classes(bubble.loc[bubble["ranked_by_share"], "group_share_pct"].values)
    bubble["colour"] = GRAY
    bubble.loc[bubble["ranked_by_share"], "colour"] = [RAMP[c] for c in classes]
    bubble = bubble[bubble["accidents_group"] > 0].sort_values("accidents_group", ascending=False)
    top_n = bubble["accidents_group"].max()
    fig, ax = plt.subplots(figsize=(10.5, 8), dpi=200, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    outlines.plot(ax=ax, color=LAND, edgecolor=BASELINE, linewidth=0.3)
    ax.scatter(bubble["x"], bubble["y"], s=bubble["accidents_group"] / top_n * 900, c=bubble["colour"], alpha=0.85, edgecolors=SURFACE, linewidths=0.6, zorder=3)
    for _, row in bubble.head(8).iterrows():
        ax.annotate(row["municipality"], (row["x"], row["y"]), xytext=(6, 6), textcoords="offset points", fontsize=8, color=INK)
    style_map(ax)
    sizes = [v for v in (50, 250, 1000) if v < top_n] or [int(top_n)]
    size_handles = [Line2D([0], [0], marker="o", color="none", markerfacecolor="none", markeredgecolor=INK_2, markersize=np.sqrt(v / top_n * 900), label=f"{v:,}") for v in sizes]
    colour_handles = [Patch(color=RAMP[i], label=f"{edges[i]:.1f}-{edges[i + 1]:.1f}%") for i in range(len(edges) - 1)] + [Patch(color=GRAY, label=f"fewer than {MIN_ACCIDENTS} accidents (not ranked)")]
    leg1 = ax.legend(handles=size_handles, title=f"Size = accidents with {plural}", loc="lower left", frameon=False, fontsize=8, title_fontsize=8, labelcolor=INK_2, labelspacing=1.6, borderpad=1.2)
    ax.add_artist(leg1)
    ax.legend(handles=colour_handles, title=f"Colour = {key} share of the municipality's accidents", loc="lower right", frameon=False, fontsize=8, title_fontsize=8, labelcolor=INK_2)
    fig.text(0.03, 0.97, f"Accidents involving {plural} per municipality, 2017-2024 (bubble map)", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.03, 0.935, "Each bubble sits at the average position of the municipality's accidents. Municipality outlines: Statbel, CC BY 4.0.", fontsize=8, color=INK_2, ha="left", va="top")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.02)
    fig.savefig(output_dir / f"geo_a_{key}_bubble_map.png", facecolor=SURFACE)
    plt.close(fig)

    count_edges, count_classes = quantile_classes(map_data["accidents_group"].values)
    ranked_mask = map_data["ranked_by_share"].values
    share_edges, share_classes = quantile_classes(map_data.loc[ranked_mask, "group_share_pct"].values)
    colours_share = np.array([GRAY] * len(map_data), dtype=object)
    colours_share[ranked_mask] = [RAMP[c] for c in share_classes]
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.4), dpi=200, facecolor=SURFACE)
    for ax, colours, title, e, fmt in ((axes[0], [RAMP[c] for c in count_classes], f"Accidents involving {plural}", count_edges, lambda a, b: f"{a:,.0f}-{b:,.0f}"),
                                      (axes[1], list(colours_share), f"{group} share of the municipality's accidents", share_edges, lambda a, b: f"{a:.1f}-{b:.1f}%")):
        ax.set_facecolor(SURFACE)
        map_data.plot(ax=ax, color=colours, edgecolor=SURFACE, linewidth=0.25)
        style_map(ax)
        handles = [Patch(color=RAMP[i], label=fmt(e[i], e[i + 1])) for i in range(len(e) - 1)]
        if "share" in title:
            handles.append(Patch(color=GRAY, label=f"fewer than {MIN_ACCIDENTS} accidents (not ranked)"))
        ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=8, labelcolor=INK_2, title="5 quantile classes", title_fontsize=8)
        ax.set_title(title, fontsize=10.5, fontweight="bold", color=INK, loc="left")
    fig.text(0.02, 0.975, f"{group} accidents by municipality, 2017-2024 (choropleth)", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.935, "Five classes with about the same number of municipalities each; the legend gives the exact limits. Municipality outlines: Statbel, CC BY 4.0.", fontsize=8, color=INK_2, ha="left", va="top")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.01, wspace=0.03)
    fig.savefig(output_dir / f"geo_a_{key}_choropleth.png", facecolor=SURFACE)
    plt.close(fig)

# --- the numbers per municipality and period, for the page's buttons (all years, 2022-2024, every single year) ---
periods = {"2017-2024": df["collision_year"] >= 2017, "2022-2024": df["collision_year"] >= 2022}
for y in range(2017, 2025):
    periods[str(y)] = df["collision_year"] == y
rows = []
nis_all = base.index
for period, in_period in periods.items():
    sub = df[in_period]
    for name, m in [("All accidents", pd.Series(True, index=df.index))] + [(g, mask[g]) for g in GROUPS]:
        part = sub[m[in_period]] if name != "All accidents" else sub
        g = part.groupby("municipality_nis_code").agg(accidents=("severe", "size"), severe=("severe", "sum")).reindex(nis_all, fill_value=0).astype(int)
        g.insert(0, "municipality_nis_code", nis_all)
        g.insert(0, "period", period)
        g.insert(0, "group", name)
        rows.append(g)
periods_table = pd.concat(rows, ignore_index=True)
assert int(periods_table[(periods_table["group"] == "All accidents") & (periods_table["period"] == "2017-2024")]["accidents"].sum()) == len(df)
for name in GROUPS:
    assert int(periods_table[(periods_table["group"] == name) & (periods_table["period"] == "2017-2024")]["accidents"].sum()) == int(mask[name].sum())
assert int(periods_table[(periods_table["group"] == "All accidents") & (periods_table["period"] == "2022-2024")]["accidents"].sum()) == int((df["collision_year"] >= 2022).sum())
periods_table.to_csv(output_dir / "geo_municipality_periods.csv", index=False)
print(f"Wrote geo_municipality_periods.csv: {len(periods_table):,} rows (5 groups x {len(periods)} periods x {len(nis_all)} municipalities)")
