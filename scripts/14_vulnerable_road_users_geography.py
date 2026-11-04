"""
Step 14 - Analysis 3: where are vulnerable road users most exposed? (geographical information)

  a. accidents involving cyclists by municipality (counts and cyclist share), ranked chart, bubble map and choropleth
  b. pedestrian accident hotspots (500 m grid squares)
  c. motorcycle and moped accident concentrations (500 m grid squares, two separate groups)

Decisions applied (see beslissingslogboek.md):
  #79 the question.   #80 motorcycles and mopeds are two separate groups.
  #81 3a: counts + cyclist share of the municipality's accidents (no rate per inhabitant: no population data).
  #82 3a: bubble map (bubbles at the average position of the municipality's accidents) AND choropleth.
  #83 hotspots for all years 2017-2024 AND for 2022-2024 only, on accidents that have coordinates; the left-out ones are reported.
  #84 municipality outlines from Statbel (CC BY 4.0), prepared in step 13.
  #85 grid squares.   #86 500 m squares, aligned to multiples of 500 m in Belgian Lambert 1972.
  #87 hotspot = one of the top 20 squares by number of accidents involving the group, with the municipality named.
  #88 the cyclist-share ranking and colours only use municipalities with at least 100 accidents.
  #89 choropleth with 5 quantile classes.
Counting rule as before (#33): an accident counts for a group if that group is road user 1 OR road user 2, once.

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/14_vulnerable_road_users_geography.py OPENDATA_MAP_2017-2024_en_flagged.csv.gz data/municipality_outlines.gpkg reports
"""
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")  # draw to a file, not to a window
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import LogNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage

accidents_file = sys.argv[1]  # the flagged English dataset from step 05
outlines_file = sys.argv[2]   # municipality outlines from step 13
output_dir = Path(sys.argv[3])  # the reports/ folder
output_dir.mkdir(exist_ok=True)

# --- 1. Read the data (code columns as text so "03" keeps its zero) ---
header = pd.read_csv(accidents_file, nrows=0).columns
df = pd.read_csv(accidents_file, dtype={c: str for c in header if c.endswith("_code")})
outlines = gpd.read_file(outlines_file)  # one outline per municipality, EPSG:31370
step7 = pd.read_csv(output_dir / "accidents_per_road_user.csv").set_index("road_user_group")["accidents"]


def involved(code):
    """True for the accidents where the group is road user 1 OR road user 2 (decision #33)."""
    return (df["road_user_type1_code"] == code) | (df["road_user_type2_code"] == code)


GROUPS = {"Bicycle": "03", "Pedestrian": "08", "Motorcycle": "07", "Moped": "06"}
mask = {name: involved(code) for name, code in GROUPS.items()}
for name in GROUPS:
    assert int(mask[name].sum()) == int(step7[name]), f"{name}: count differs from step 07"  # same counting as before
# A usable coordinate lies inside Belgium's range in Belgian Lambert 1972 (metres). Two accidents (Herentals and Knokke-Heist, 2022)
# have impossible values around 10^16; they are treated as having no coordinates (decision #90).
usable = df["x_coord"].between(20_000, 300_000) & df["y_coord"].between(20_000, 250_000)  # a missing value counts as not usable
n_impossible = int((df["x_coord"].notna() & ~usable).sum())
has_coordinates = usable
print(f"Coordinates: {int(df['x_coord'].notna().sum()):,} accidents have a coordinate; {n_impossible} of them are impossible (outside Belgium's range) and are not used.\n")

SURFACE, INK, INK_2, MUTED, GRID, BASELINE, BLUE, GRAY = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#2a78d6", "#898781"
LAND = "#f1f0ec"
RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]  # five blue steps, light to dark (ordinal ramp, no step lighter than 250)
plt.rcParams["font.family"] = ["Helvetica Neue", "Arial", "DejaVu Sans"]  # a plain system sans

# =====================================================================
# 3a. Cyclists by municipality
# =====================================================================
MIN_ACCIDENTS = 100  # decision #88: only municipalities with at least 100 accidents get a share ranking
by_municipality = df.groupby("municipality_nis_code").agg(
    municipality=("municipality", "first"), region=("region", "first"), province=("province", "first"), accidents_total=("collision_year", "size"))
by_municipality["accidents_cyclists"] = df[mask["Bicycle"]].groupby("municipality_nis_code").size().reindex(by_municipality.index, fill_value=0)
by_municipality["cyclist_share_pct"] = by_municipality["accidents_cyclists"] / by_municipality["accidents_total"] * 100
by_municipality["ranked_by_share"] = by_municipality["accidents_total"] >= MIN_ACCIDENTS
by_municipality["rank_count"] = by_municipality["accidents_cyclists"].rank(ascending=False, method="min").astype(int)
by_municipality["rank_share"] = by_municipality.loc[by_municipality["ranked_by_share"], "cyclist_share_pct"].rank(ascending=False, method="min")
by_municipality = by_municipality.sort_values("rank_count")
assert by_municipality["accidents_total"].sum() == len(df), "municipality totals do not add up to the number of accidents"
assert by_municipality["accidents_cyclists"].sum() == mask["Bicycle"].sum() == 71881, "cyclist accidents do not add up"
by_municipality.to_csv(output_dir / "geo_a_cyclists_by_municipality.csv", float_format="%.2f")
national_share = by_municipality["accidents_cyclists"].sum() / len(df) * 100
n_ranked = int(by_municipality["ranked_by_share"].sum())

print(f"3a. Cyclists by municipality: {by_municipality['accidents_cyclists'].sum():,} accidents involving cyclists in {len(by_municipality)} municipalities "
      f"({(by_municipality['accidents_cyclists'] > 0).sum()} have at least one); national cyclist share {national_share:.1f}%")
print(f"    {n_ranked} municipalities have at least {MIN_ACCIDENTS} accidents and are ranked by share; {len(by_municipality) - n_ranked} are marked 'too few to rank'\n")
print("Top 15 by number of accidents involving cyclists:")
print(by_municipality.head(15)[["municipality", "region", "accidents_cyclists", "accidents_total", "cyclist_share_pct"]].to_string(
    formatters={"accidents_cyclists": "{:,.0f}".format, "accidents_total": "{:,.0f}".format, "cyclist_share_pct": "{:.1f}%".format}), "\n")
top_share = by_municipality[by_municipality["ranked_by_share"]].sort_values("cyclist_share_pct", ascending=False)
print(f"Top 15 by cyclist share (municipalities with at least {MIN_ACCIDENTS} accidents):")
print(top_share.head(15)[["municipality", "region", "cyclist_share_pct", "accidents_cyclists", "accidents_total"]].to_string(
    formatters={"accidents_cyclists": "{:,.0f}".format, "accidents_total": "{:,.0f}".format, "cyclist_share_pct": "{:.1f}%".format}), "\n")
by_region = df.assign(cyc=mask["Bicycle"]).groupby("region").agg(accidents=("cyc", "size"), cyclists=("cyc", "sum"))
by_region["cyclist_share_pct"] = by_region["cyclists"] / by_region["accidents"] * 100
print("Cyclist share by region:"); print(by_region.to_string(formatters={"accidents": "{:,.0f}".format, "cyclists": "{:,.0f}".format, "cyclist_share_pct": "{:.1f}%".format}), "\n")

# --- 3a graph 1: ranked charts ---
fig, axes = plt.subplots(1, 2, figsize=(13, 6.6), dpi=200, facecolor=SURFACE)
panels = [(by_municipality.head(20), "accidents_cyclists", "Top 20 by number of accidents involving cyclists", False),
          (top_share.head(20), "cyclist_share_pct", f"Top 20 by cyclist share (municipalities with at least {MIN_ACCIDENTS} accidents)", True)]
for ax, (data, column, title, is_share) in zip(axes, panels):
    ax.set_facecolor(SURFACE)
    data = data.iloc[::-1]  # biggest at the top
    ax.barh(data["municipality"], data[column], height=0.6, color=BLUE, zorder=3)
    for y, (_, row) in enumerate(data.iterrows()):
        label = f"{row[column]:.1f}%  ({row['accidents_cyclists']:,.0f} of {row['accidents_total']:,.0f})" if is_share else f"{row[column]:,.0f}  ({row['cyclist_share_pct']:.0f}% of {row['accidents_total']:,.0f})"
        ax.text(row[column] + data[column].max() * 0.012, y, label, va="center", ha="left", fontsize=8, color=INK)
    if is_share:
        ax.axvline(national_share, color=GRAY, linewidth=1.5, zorder=2)
        ax.text(national_share, len(data) - 0.35, f" Belgium {national_share:.1f}%", fontsize=8, color=MUTED, ha="left", va="bottom")
    ax.set_xlim(0, data[column].max() * 1.5)
    ax.xaxis.set_major_formatter(lambda v, _, percent=is_share: f"{v:.0f}%" if percent else f"{v:,.0f}")  # 'percent=' fixes the value per panel
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(length=0, labelsize=9, labelcolor=INK_2)
    ax.set_title(title, fontsize=10.5, fontweight="bold", color=INK, loc="left", pad=8)
fig.text(0.02, 0.975, "Where do accidents involving cyclists happen? Municipalities, 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.935, "Counts favour big cities; the share shows where cyclists are an unusually large part of a municipality's accidents. An accident counts once for every road-user group it involves.",
         fontsize=8, color=INK_2, ha="left", va="top")
fig.subplots_adjust(left=0.085, right=0.985, top=0.87, bottom=0.05, wspace=0.55)
fig.savefig(output_dir / "geo_a_ranked.png", facecolor=SURFACE)
plt.close(fig)

# --- 3a graph 2 and 3: bubble map and choropleth ---
located = df[has_coordinates]
centre = located.groupby("municipality_nis_code")[["x_coord", "y_coord"]].mean()  # average position of the municipality's accidents (decision #82)
map_data = outlines.merge(by_municipality.reset_index(), left_on="nis_code", right_on="municipality_nis_code", how="left")
assert map_data["accidents_total"].notna().all(), "a municipality outline has no accident data"
polygon_centres = map_data.geometry.centroid
bubble = map_data[["nis_code", "municipality", "accidents_cyclists", "cyclist_share_pct", "ranked_by_share"]].copy()
bubble["x"] = bubble["nis_code"].map(centre["x_coord"]); bubble["y"] = bubble["nis_code"].map(centre["y_coord"])
no_position = bubble["x"].isna()
bubble.loc[no_position, "x"], bubble.loc[no_position, "y"] = polygon_centres[no_position].x, polygon_centres[no_position].y  # fallback: middle of the outline
print(f"Bubble map: {int(no_position.sum())} municipalities have no accident coordinates; their bubble is placed in the middle of the outline\n")


def quantile_classes(values, n=5):
    """Class limits with about the same number of municipalities per class (decision #89)."""
    edges = np.unique(np.quantile(values, np.linspace(0, 1, n + 1)))
    classes = np.clip(np.digitize(values, edges[1:-1], right=True), 0, len(edges) - 2)
    return edges, classes


def style_map(ax):
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for side in ax.spines.values():
        side.set_visible(False)


# Bubble map
share_edges, share_classes = quantile_classes(bubble.loc[bubble["ranked_by_share"], "cyclist_share_pct"].values)
bubble["colour"] = GRAY
bubble.loc[bubble["ranked_by_share"], "colour"] = [RAMP[c] for c in share_classes]
bubble = bubble[bubble["accidents_cyclists"] > 0].sort_values("accidents_cyclists", ascending=False)  # big bubbles first, small ones on top
fig, ax = plt.subplots(figsize=(10.5, 8), dpi=200, facecolor=SURFACE)
ax.set_facecolor(SURFACE)
outlines.plot(ax=ax, color=LAND, edgecolor=BASELINE, linewidth=0.3)
ax.scatter(bubble["x"], bubble["y"], s=bubble["accidents_cyclists"] / bubble["accidents_cyclists"].max() * 900, c=bubble["colour"], alpha=0.85, edgecolors=SURFACE, linewidths=0.6, zorder=3)
for _, row in bubble.head(8).iterrows():  # name only the biggest
    ax.annotate(row["municipality"], (row["x"], row["y"]), xytext=(6, 6), textcoords="offset points", fontsize=8, color=INK)
style_map(ax)
size_handles = [Line2D([0], [0], marker="o", color="none", markerfacecolor="none", markeredgecolor=INK_2, markersize=np.sqrt(v / bubble["accidents_cyclists"].max() * 900), label=f"{v:,}") for v in (100, 1000, 5000)]
colour_handles = [Patch(color=RAMP[i], label=f"{share_edges[i]:.0f}-{share_edges[i + 1]:.0f}%") for i in range(len(share_edges) - 1)] + [Patch(color=GRAY, label=f"fewer than {MIN_ACCIDENTS} accidents (not ranked)")]
leg1 = ax.legend(handles=size_handles, title="Size = accidents with cyclists", loc="lower left", frameon=False, fontsize=8, title_fontsize=8, labelcolor=INK_2, labelspacing=1.6, borderpad=1.2)
ax.add_artist(leg1)
ax.legend(handles=colour_handles, title="Colour = cyclist share of the municipality's accidents", loc="lower right", frameon=False, fontsize=8, title_fontsize=8, labelcolor=INK_2)
fig.text(0.03, 0.97, "Accidents involving cyclists per municipality, 2017-2024 (bubble map)", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.03, 0.935, "Each bubble sits at the average position of the municipality's accidents. Municipality outlines: Statbel, CC BY 4.0.", fontsize=8, color=INK_2, ha="left", va="top")
fig.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.02)
fig.savefig(output_dir / "geo_a_bubble_map.png", facecolor=SURFACE)
plt.close(fig)

# Choropleth: counts (all municipalities) and share (only ranked municipalities)
count_edges, count_classes = quantile_classes(map_data["accidents_cyclists"].values)
ranked_mask = map_data["ranked_by_share"].values
share_edges2, share_classes2 = quantile_classes(map_data.loc[ranked_mask, "cyclist_share_pct"].values)
fig, axes = plt.subplots(1, 2, figsize=(13, 6.4), dpi=200, facecolor=SURFACE)
colours_count = [RAMP[c] for c in count_classes]
colours_share = np.array([GRAY] * len(map_data), dtype=object)
colours_share[ranked_mask] = [RAMP[c] for c in share_classes2]
for ax, colours, title, edges, formatter in (
        (axes[0], colours_count, "Accidents involving cyclists", count_edges, lambda a, b: f"{a:,.0f}-{b:,.0f}"),
        (axes[1], list(colours_share), "Cyclist share of the municipality's accidents", share_edges2, lambda a, b: f"{a:.0f}-{b:.0f}%")):
    ax.set_facecolor(SURFACE)
    map_data.plot(ax=ax, color=colours, edgecolor=SURFACE, linewidth=0.25)
    style_map(ax)
    handles = [Patch(color=RAMP[i], label=formatter(edges[i], edges[i + 1])) for i in range(len(edges) - 1)]
    if title.startswith("Cyclist share"):
        handles.append(Patch(color=GRAY, label=f"fewer than {MIN_ACCIDENTS} accidents (not ranked)"))
    ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=8, labelcolor=INK_2, title="5 quantile classes", title_fontsize=8)
    ax.set_title(title, fontsize=10.5, fontweight="bold", color=INK, loc="left")
fig.text(0.02, 0.975, "Cyclist accidents by municipality, 2017-2024 (choropleth)", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.935, "Five classes with about the same number of municipalities each; the legend gives the exact limits. Municipality outlines: Statbel, CC BY 4.0.", fontsize=8, color=INK_2, ha="left", va="top")
fig.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.01, wspace=0.03)
fig.savefig(output_dir / "geo_a_choropleth.png", facecolor=SURFACE)
plt.close(fig)
print(f"Choropleth class limits (accidents): {[round(float(e)) for e in count_edges]}; (cyclist share %): {[round(float(e), 1) for e in share_edges2]}\n")

# =====================================================================
# 3b, 3c. Hotspots: 500 m grid squares
# =====================================================================
CELL = 500  # metres (decision #86); the squares are aligned to multiples of 500 m in Belgian Lambert 1972
SCOPES = {"2017-2024": range(2017, 2025), "2022-2024": range(2022, 2025)}  # decision #83
HOTSPOTS = [("Pedestrian", "b_pedestrian", "geo_b_pedestrian_hotspots.png"), ("Motorcycle", "c_motorcycle", "geo_c_motorcycle_hotspots.png"), ("Moped", "c_moped", "geo_c_moped_hotspots.png")]

# Check: do the coordinates fit the municipality they belong to? (a point should lie inside its own municipality)
points = gpd.GeoDataFrame(located[["municipality_nis_code"]], geometry=gpd.points_from_xy(located["x_coord"], located["y_coord"]), crs=outlines.crs)
joined = gpd.sjoin(points, outlines[["nis_code", "geometry"]], how="left", predicate="within")
joined = joined[~joined.index.duplicated(keep="first")]
inside_own = (joined["nis_code"] == joined["municipality_nis_code"]).mean() * 100
inside_any = joined["nis_code"].notna().mean() * 100
print(f"Coordinate check: {inside_any:.1f}% of the {len(located):,} located accidents lie inside Belgium's outline, {inside_own:.1f}% inside their own municipality "
      "(the rest are close to a boundary or have a coordinate that does not fit).\n")

def clusters_of(top, distance=8000):
    """Give the top squares a group number: squares within 8 km of each other (single linkage) belong to one city area."""
    if len(top) < 2:
        return np.ones(len(top), dtype=int)
    return fcluster(linkage(top[["centre_x_m", "centre_y_m"]].values, "single"), t=distance, criterion="distance")


def square(cx, cy):
    """The four corners of the 500 m grid square with index (cx, cy)."""
    return [(cx * CELL, cy * CELL), ((cx + 1) * CELL, cy * CELL), ((cx + 1) * CELL, (cy + 1) * CELL), (cx * CELL, (cy + 1) * CELL)]


def area_name(part):
    """Name of a city area: the municipality that holds most of its hotspot squares (ties: the one with the best-ranked square)."""
    counts = part.groupby("municipality")["rank"].agg(["size", "min"]).sort_values(["size", "min"], ascending=[False, True])
    return counts.index[0]


CMAP = matplotlib.colors.ListedColormap(["#cde2fb"] + RAMP + ["#0d366b"])  # light to dark blue for few to many accidents per square
HALO = [pe.withStroke(linewidth=2.5, foreground=SURFACE)]  # a light halo so text stays readable on any colour
LABEL_OFFSETS = [(22, 18), (-78, 20), (26, -30), (-70, -32)]  # where the city-area labels go, to keep them apart

coverage = []
for group, key, picture in HOTSPOTS:
    plural = {"Pedestrian": "pedestrians", "Motorcycle": "motorcycles", "Moped": "mopeds"}[group]
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.6), dpi=200, facecolor=SURFACE)
    tables, top_by, cells_by = [], {}, {}
    for ax, (scope, years) in zip(axes, SCOPES.items()):
        in_scope = mask[group] & df["collision_year"].isin(years)
        used = in_scope & has_coordinates
        coverage.append((group, scope, int(in_scope.sum()), int(used.sum()), int(in_scope.sum() - used.sum()), (in_scope.sum() - used.sum()) / in_scope.sum() * 100))
        sub = df[used].copy()
        sub["cx"], sub["cy"] = (sub["x_coord"] // CELL).astype(int), (sub["y_coord"] // CELL).astype(int)  # which square the accident is in
        cells = sub.groupby(["cx", "cy"]).size().rename("accidents").reset_index().sort_values(["accidents", "cx", "cy"], ascending=[False, True, True]).reset_index(drop=True)
        assert cells["accidents"].sum() == len(sub), "cell counts do not add up to the located accidents"
        top = cells.head(20).copy()
        top.insert(0, "rank", range(1, len(top) + 1))
        # municipality of each top square: the most common municipality among its accidents
        top["municipality"] = [sub[(sub["cx"] == r.cx) & (sub["cy"] == r.cy)]["municipality"].mode().iat[0] for r in top.itertuples()]
        top["centre_x_m"], top["centre_y_m"] = top["cx"] * CELL + CELL / 2, top["cy"] * CELL + CELL / 2
        top["share_of_located_pct"] = top["accidents"] / len(sub) * 100
        all_in_cell = df[has_coordinates & df["collision_year"].isin(years)].assign(cx=lambda d: (d["x_coord"] // CELL).astype(int), cy=lambda d: (d["y_coord"] // CELL).astype(int)).groupby(["cx", "cy"]).size()
        top["all_accidents_in_square"] = [int(all_in_cell.get((r.cx, r.cy), 0)) for r in top.itertuples()]
        top["group_share_of_square_pct"] = top["accidents"] / top["all_accidents_in_square"] * 100
        ties = int((cells["accidents"] == top["accidents"].iloc[-1]).sum() - (top["accidents"] == top["accidents"].iloc[-1]).sum())
        top.insert(0, "scope", scope)
        tables.append(top.drop(columns=["cx", "cy"]))
        top["area"] = clusters_of(top)  # group number of the city area (only used for the maps, not saved)
        top_by[scope], cells_by[scope] = top, cells
        print(f"{group}, {scope}: {int(in_scope.sum()):,} accidents, {int(used.sum()):,} with coordinates ({int(used.sum()) / int(in_scope.sum()) * 100:.1f}%) in {len(cells):,} squares of 500 m"
              f"{'; ' + str(ties) + ' more square(s) tie with the 20th' if ties else ''}")
        # --- the national map for this scope ---
        ax.set_facecolor(SURFACE)
        outlines.plot(ax=ax, color=LAND, edgecolor=BASELINE, linewidth=0.25)
        collection = PolyCollection([square(cx, cy) for cx, cy in zip(cells["cx"], cells["cy"])], array=cells["accidents"].values, cmap=CMAP,
                                    norm=LogNorm(vmin=1, vmax=cells["accidents"].max()), edgecolors="none", zorder=3)
        ax.add_collection(collection)
        ax.add_collection(PolyCollection([square(r.cx, r.cy) for r in top.itertuples()], facecolors="none", edgecolors=INK, linewidths=1.0, zorder=4))  # ring around the 20 hotspots
        for n, (_, part) in enumerate(sorted(top.groupby("area"), key=lambda kv: kv[1]["rank"].min())):  # one label per city area
            ranks = ", ".join(str(r) for r in sorted(part["rank"])) if len(part) <= 5 else f"{len(part)} squares, best rank {part['rank'].min()}"
            ax.annotate(f"{area_name(part)} area\n{ranks}", (part["centre_x_m"].mean(), part["centre_y_m"].mean()), xytext=LABEL_OFFSETS[n % 4], textcoords="offset points",
                        fontsize=7.5, color=INK, path_effects=HALO, zorder=6, arrowprops=dict(arrowstyle="-", color=INK, lw=0.6))
        style_map(ax)
        ax.set_title(f"{scope}: {int(used.sum()):,} accidents with coordinates", fontsize=10.5, fontweight="bold", color=INK, loc="left", pad=8)
        cbar = fig.colorbar(collection, ax=ax, orientation="horizontal", fraction=0.035, pad=0.02, aspect=40)
        cbar.outline.set_visible(False)
        cbar.ax.tick_params(length=0, labelsize=8, labelcolor=MUTED)
        cbar.set_label("accidents per 500 m square (log scale)", fontsize=8, color=MUTED)
    fig.text(0.02, 0.975, f"Where do accidents involving {plural} concentrate? 500 m grid squares", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.935, "Black rings = the 20 squares with the most accidents (the zoom maps show them one by one). Only accidents with coordinates; Wallonia and 2017-2021 have more gaps. Outlines: Statbel, CC BY 4.0.",
             fontsize=8, color=INK_2, ha="left", va="top")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.87, bottom=0.05, wspace=0.04)
    fig.savefig(output_dir / picture, facecolor=SURFACE)
    plt.close(fig)
    pd.concat(tables).to_csv(output_dir / f"geo_hotspots_{key.split('_')[1]}.csv", index=False, float_format="%.2f")

    # --- the zoom map: every hotspot square of 2017-2024, numbered, per city area (the 4 areas with the best-ranked squares) ---
    top, cells = top_by["2017-2024"], cells_by["2017-2024"]
    areas = sorted(top.groupby("area"), key=lambda kv: kv[1]["rank"].min())[:4]
    n_panels = len(areas)
    rows_n, cols_n = (1, n_panels) if n_panels <= 2 else (2, 2)
    fig, axs = plt.subplots(rows_n, cols_n, figsize=(max(9.5, 5.4 * cols_n), 5.6 * rows_n + 1.0), dpi=200, facecolor=SURFACE)  # at least 9.5 inches wide, so the title fits
    axs = np.atleast_1d(axs).ravel()
    norm = LogNorm(vmin=1, vmax=cells["accidents"].max())
    for ax, (_, part) in zip(axs, areas):
        x_low, x_high = part["cx"].min() * CELL - 1500, (part["cx"].max() + 1) * CELL + 1500  # a window with 1.5 km around the hotspot squares
        y_low, y_high = part["cy"].min() * CELL - 1500, (part["cy"].max() + 1) * CELL + 1500
        side = max(x_high - x_low, y_high - y_low, 4000)  # the window is square and at least 4 km wide
        x_mid, y_mid = (x_low + x_high) / 2, (y_low + y_high) / 2
        xmin, xmax, ymin, ymax = x_mid - side / 2, x_mid + side / 2, y_mid - side / 2, y_mid + side / 2
        window = cells[(cells["cx"] * CELL + CELL > xmin) & (cells["cx"] * CELL < xmax) & (cells["cy"] * CELL + CELL > ymin) & (cells["cy"] * CELL < ymax)]
        ax.set_facecolor(SURFACE)
        outlines.plot(ax=ax, color=LAND, edgecolor=BASELINE, linewidth=0.6)
        shown = PolyCollection([square(cx, cy) for cx, cy in zip(window["cx"], window["cy"])], array=window["accidents"].values, cmap=CMAP, norm=norm, edgecolors=SURFACE, linewidths=0.4, zorder=3)
        ax.add_collection(shown)
        ax.add_collection(PolyCollection([square(r.cx, r.cy) for r in part.itertuples()], facecolors="none", edgecolors=INK, linewidths=1.2, zorder=4))
        for r in part.itertuples():
            ax.text(r.centre_x_m, r.centre_y_m, str(r.rank), ha="center", va="center", fontsize=8.5, fontweight="bold", color=INK, path_effects=HALO, zorder=6)
        ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)
        style_map(ax)
        ax.plot([xmin + 300, xmin + 1300], [ymin + 300, ymin + 300], color=INK, linewidth=2.5, zorder=7)  # scale bar: 1 km
        ax.text(xmin + 800, ymin + 420, "1 km", ha="center", va="bottom", fontsize=8, color=INK, path_effects=HALO, zorder=7)
        listed = ", ".join(str(r) for r in sorted(part["rank"])) if len(part) <= 6 else f"ranks {part['rank'].min()} to {part['rank'].max()}, {len(part)} squares"
        ax.set_title(f"{area_name(part)} area: {listed}", fontsize=9.5, fontweight="bold", color=INK, loc="left", pad=6)
    for ax in axs[n_panels:]:
        ax.axis("off")
    fig.text(0.02, 0.985, f"Hotspots of accidents involving {plural}, 2017-2024: the 20 busiest 500 m squares", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.953, "Numbers = rank by number of accidents. Colour = accidents per square, same scale as the national map (log). Municipality borders: Statbel, CC BY 4.0.", fontsize=8, color=INK_2, ha="left", va="top")
    colour_axis = fig.add_axes([0.3, 0.075, 0.4, 0.012])  # a colour scale in its own strip below the maps, so it never covers a map
    cbar = fig.colorbar(shown, cax=colour_axis, orientation="horizontal")
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(length=0, labelsize=8, labelcolor=MUTED)
    cbar.set_label("accidents per 500 m square (log scale)", fontsize=8, color=MUTED)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.90, bottom=0.16, wspace=0.06, hspace=0.14)
    fig.savefig(output_dir / picture.replace("_hotspots", "_zoom"), facecolor=SURFACE)
    plt.close(fig)

    # print the all-years top 20 and how stable the hotspots are between the two scopes
    show = tables[0].drop(columns=["scope", "centre_x_m", "centre_y_m"]).rename(columns={"share_of_located_pct": "% of located", "all_accidents_in_square": "all accidents there", "group_share_of_square_pct": f"% {group.lower()}"})
    print(f"\n{group}: top 20 squares, 2017-2024")
    print(show.to_string(index=False, formatters={"accidents": "{:,.0f}".format, "% of located": "{:.2f}".format, "all accidents there": "{:,.0f}".format, f"% {group.lower()}": "{:.0f}".format}))
    same = len(set(zip(top_by["2017-2024"]["cx"], top_by["2017-2024"]["cy"])) & set(zip(top_by["2022-2024"]["cx"], top_by["2022-2024"]["cy"])))
    print(f"-> {same} of the 20 squares are in the top 20 of both 2017-2024 and 2022-2024\n")

coverage = pd.DataFrame(coverage, columns=["group", "scope", "accidents", "with_coordinates", "left_out", "left_out_pct"])
coverage.to_csv(output_dir / "geo_coverage.csv", index=False, float_format="%.2f")
print("Coverage (accidents with coordinates):"); print(coverage.to_string(index=False, formatters={"accidents": "{:,.0f}".format, "with_coordinates": "{:,.0f}".format, "left_out": "{:,.0f}".format, "left_out_pct": "{:.1f}%".format}))
print(f"\nSaved the CSV files, geo_coverage.csv and 9 graphs (6 maps and 3 zoom maps) in {output_dir}/")
