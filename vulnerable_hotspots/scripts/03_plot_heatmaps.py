"""
Step 3 of the vulnerable hotspots analysis: the heat maps as pictures (PNG) for the report.

For each group (5) it draws, from the saved results of script 02 (no recalculation):
  heat_<group>_<size>_accidents.png   accidents per year per grid cell (size = 5km2 or 5x5km), the three periods side by side (same grid, same colour scale, log scale), the 20 busiest cells ringed
  heat_<group>_<size>_rate.png        accidents per 100,000 residents of the cell per year (cells with 1,000+ residents and 30+ accidents), the 20 highest rates ringed
  heat_<group>_<size>_severe.png      the severe share per cell (cells with 30+ accidents)
  rates_<group>.png                   accidents per 100,000 residents per year per municipality, the three periods side by side (100+ accidents full colour, 30-99 faded)
Municipality outlines: Statbel, CC BY 4.0 (data/municipality_outlines.json).

How to run (from the folder hotspot_deep_dive, with `conda activate syntra-ds`):
    python -I scripts/03_plot_heatmaps.py
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap, LogNorm, Normalize, to_rgba

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import charts  # noqa: E402  (the loaders and the constants: group names, periods, cell sizes)

OUT = HERE / "images"
cells, top, mun, coverage = charts.load_cells(), charts.load_top(), charts.load_municipalities(), charts.load_coverage()
outlines = json.loads((HERE / "data" / "municipality_outlines.json").read_text(encoding="utf-8"))
SURFACE, INK, INK_2, MUTED, BASELINE, LAND = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#c3c2b7", "#f1f0ec"
plt.rcParams["font.family"] = ["Helvetica Neue", "Arial", "DejaVu Sans"]
COUNT_CMAP = LinearSegmentedColormap.from_list("counts", ["#cde2fb", "#86b6ef", "#2a78d6", "#104281", "#0d366b"])
WARM_CMAP = LinearSegmentedColormap.from_list("warm", ["#fdeadf", "#f8c3a2", "#eb6834", "#b8431a", "#6e260c"])
FILE = {g: g.split(" ")[0].lower() for g in charts.GROUPS}
FILE_SIZE = {"5 km2 cells": "5km2", "5 x 5 km squares": "5x5km"}


def draw_outline(ax):
    polys = [np.array(ring).reshape(-1, 2) for f in outlines["features"] for polygon in f["polys"] for ring in polygon]
    ax.add_collection(PolyCollection(polys, facecolors=LAND, edgecolors=BASELINE, linewidths=0.2))
    ax.set_aspect("equal"); ax.set_xlim(20_000, 300_000); ax.set_ylim(20_000, 250_000)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


def squares(c, side):
    return [[(x * side, y * side), ((x + 1) * side, y * side), ((x + 1) * side, (y + 1) * side), (x * side, (y + 1) * side)] for x, y in zip(c["cx"], c["cy"])]


def grid_figure(group, size, measure):
    side = charts.CELL_SIZES[size]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.6), dpi=170, facecolor=SURFACE)
    c_all = cells[(cells["size"] == size) & (cells["group"] == group) & cells["period"].isin(charts.THREE)]
    zmax = c_all[c_all["rate_ok"]]["rate"].max() if measure == "rate" else c_all["per_year"].max()
    for ax, period in zip(axes, charts.THREE):
        ax.set_facecolor(SURFACE); draw_outline(ax)
        c = c_all[c_all["period"] == period]
        if measure == "severe":
            c = c[c["accidents"] >= charts.MIN_SHARE]
            values, norm, cmap = c["severe"] / c["accidents"] * 100, Normalize(0, 40), WARM_CMAP
        elif measure == "rate":
            c = c[c["rate_ok"]]
            values, norm, cmap = c["rate"], LogNorm(10, zmax), COUNT_CMAP
        else:
            values, norm, cmap = c["per_year"], LogNorm(0.1, zmax), COUNT_CMAP
        pc = PolyCollection(squares(c, side), array=np.clip(values.to_numpy(), norm.vmin if measure != "severe" else 0, None), cmap=cmap, norm=norm, edgecolors="none", zorder=3)
        ax.add_collection(pc)
        t = top[(top["size"] == size) & (top["group"] == group) & (top["period"] == period) & (top["ranking"] == ("rate" if measure == "rate" else "accidents"))]
        ax.add_collection(PolyCollection(squares(t, side), facecolors="none", edgecolors=INK, linewidths=1.0, zorder=4))
        cov = coverage[(coverage["group"] == group) & (coverage["period"] == period)].iloc[0]
        ax.set_title(f"{period}\n{int(cov['with coordinates']):,} accidents with coordinates ({100 - cov['left out %']:.0f}%)", fontsize=9.5, fontweight="bold", color=INK, loc="left")
    cbar = fig.colorbar(pc, ax=axes, orientation="horizontal", fraction=0.04, pad=0.03, aspect=45)
    cbar.outline.set_visible(False); cbar.ax.tick_params(length=0, labelsize=8, labelcolor=MUTED)
    if measure == "severe":
        cbar.set_label("severe share of the accidents in the cell (%), cells with 30+ accidents", fontsize=8.5, color=MUTED)
        title = f"How severe are the accidents with {charts.GROUP_WORDS[group]}? {size}, three periods"
    elif measure == "rate":
        cbar.set_label("accidents per 100,000 residents of the cell per year (log scale), cells with 1,000+ residents and 30+ accidents", fontsize=8.5, color=MUTED)
        ticks = [t_ for t_ in (10, 30, 100, 300, 1000) if t_ <= zmax * 1.05]
        cbar.set_ticks(ticks); cbar.set_ticklabels([f"{t_:g}" for t_ in ticks])
        title = f"Accidents with {charts.GROUP_WORDS[group]} per 100,000 residents of the cell per year, {size}"
    else:
        cbar.set_label("accidents per year per cell (log scale)", fontsize=8.5, color=MUTED)
        ticks = [t_ for t_ in (0.1, 0.3, 1, 3, 10, 30, 100, 300) if t_ <= zmax * 1.05]
        cbar.set_ticks(ticks); cbar.set_ticklabels([f"{t_:g}" for t_ in ticks])
        title = f"Where do accidents with {charts.GROUP_WORDS[group]} concentrate? {size}, accidents per year"
    fig.text(0.02, 0.975, title, fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.93, "Black squares = the " + ("20 highest rates" if measure == "rate" else "20 busiest cells") + " of the period. Only accidents with coordinates. Same grid and colour scale in the three maps. Outlines: Statbel, CC BY 4.0.", fontsize=8, color=INK_2, ha="left", va="top")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.86, bottom=0.12, wspace=0.03)
    fig.savefig(OUT / f"heat_{FILE[group]}_{FILE_SIZE[size]}_{ {'severe': 'severe', 'rate': 'rate'}.get(measure, 'accidents') }.png", facecolor=SURFACE)
    plt.close(fig)


def rate_figure(group):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.8), dpi=170, facecolor=SURFACE)
    ramp = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]
    from matplotlib.patches import Patch
    legend_period = None
    for ax, period in zip(axes, charts.THREE):
        ax.set_facecolor(SURFACE); draw_outline(ax)
        t = charts.municipality_table(mun, group, period).set_index("municipality_nis_code")
        rel = t[t["reliable"]]
        info = ""
        if len(rel):
            edges, _ = charts.quantile_classes(rel[charts.RATE].to_numpy())
            cls = lambda v: int(np.clip(np.digitize(v, edges[1:-1], right=True), 0, len(edges) - 2))
            polys, colours = [], []
            for f in outlines["features"]:
                r = t.loc[f["nis"]]
                if not (r["reliable"] or r["flagged"]):
                    continue
                for polygon in f["polys"]:
                    for ring in polygon:
                        polys.append(np.array(ring).reshape(-1, 2)); colours.append(to_rgba(ramp[cls(r[charts.RATE])], 1.0 if r["reliable"] else 0.4))
            ax.add_collection(PolyCollection(polys, facecolors=colours, edgecolors="white", linewidths=0.15, zorder=3))
            handles = [Patch(color=ramp[k], label=f"{edges[k]:.0f}-{edges[k + 1]:.0f}" if edges[1] > 10 else f"{edges[k]:.1f}-{edges[k + 1]:.1f}") for k in range(len(edges) - 1)]
            handles.append(Patch(facecolor=to_rgba(ramp[2], 0.4), label="faded: 30-99 accidents"))
            ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=7.5, labelcolor=INK_2, title="per 100,000 residents per year", title_fontsize=7.5)
            info = f"{int(t['reliable'].sum())} municipalities with 100+ accidents"
        else:
            info = "no municipality has 100+ accidents"
        belgium = t["accidents"].sum() / t["resident_years"].sum() * 1e5
        ax.set_title(f"{period}\nBelgium {belgium:.0f} per 100,000; {info}", fontsize=9.5, fontweight="bold", color=INK, loc="left")
    fig.text(0.02, 0.975, f"Accidents with {charts.GROUP_WORDS[group]} per 100,000 residents per year, by municipality", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.93, "Accidents divided by the residents of each year (Statbel, 1 January). Five quantile classes of the municipalities with 100+ accidents; 30-99 accidents faded; fewer: no colour. Outlines: Statbel, CC BY 4.0.", fontsize=8, color=INK_2, ha="left", va="top")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.86, bottom=0.02, wspace=0.03)
    fig.savefig(OUT / f"rates_{FILE[group]}.png", facecolor=SURFACE)
    plt.close(fig)


for group in charts.GROUPS:
    for size in charts.CELL_SIZES:
        grid_figure(group, size, "per_year")
        grid_figure(group, size, "rate")
        grid_figure(group, size, "severe")
    rate_figure(group)
    print(f"{group}: 4 pictures")
print(f"Wrote {len(list(OUT.glob('*.png')))} pictures to images/")
