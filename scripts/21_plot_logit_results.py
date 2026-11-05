"""
Step 21 - Graphs of the logistic models of step 20 (forest plots of odds ratios, predicted probabilities, scenarios, calibration, interactions).

It reads only the saved tables of step 20 (reports/severity_logit_*.csv); nothing is re-estimated here.
Colours: one colour and marker per model (categorical slots 1-5 of the chart palette, with different marker shapes so they stay apart without colour).

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/21_plot_logit_results.py reports
"""
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to a file, not to a window
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

reports = Path(sys.argv[1])
coef = pd.read_csv(reports / "severity_logit_coefficients.csv")
coef = coef[coef["spec"] == "full"]  # the models as specified (with collision type)
fit = pd.read_csv(reports / "severity_logit_fit.csv")
predicted = pd.read_csv(reports / "severity_logit_predicted_by_category.csv")
scenarios = pd.read_csv(reports / "severity_logit_scenarios.csv")
calibration = pd.read_csv(reports / "severity_logit_calibration.csv")
pairs = pd.read_csv(reports / "severity_logit_interactions_pairs.csv")

MODELS = ["Baseline", "Cyclists", "Pedestrians", "Motorcyclists", "Mopeds"]
STYLE = {"Baseline": ("#2a78d6", "o"), "Cyclists": ("#eb6834", "s"), "Pedestrians": ("#1baf7a", "D"), "Motorcyclists": ("#eda100", "^"), "Mopeds": ("#e87ba4", "v")}
SURFACE, INK, INK_2, MUTED, GRID, BASELINE, GRAY = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#898781"
plt.rcParams["font.family"] = ["Helvetica Neue", "Arial", "DejaVu Sans"]  # a plain system sans
OFFSETS = np.linspace(-0.3, 0.3, 5)


def subtitle(fig, text, y=0.95, width=185):
    """A subtitle wrapped over several lines, so it never runs off the figure."""
    fig.text(0.02, y, textwrap.fill(text, width), fontsize=8, color=INK_2, ha="left", va="top")


def legend_handles(models=MODELS):
    return [Line2D([0], [0], marker=STYLE[m][1], color=STYLE[m][0], markerfacecolor=STYLE[m][0], markersize=7, linewidth=0, label=m) for m in models]


def style_axes(ax, grid_axis):
    ax.set_facecolor(SURFACE)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left" if grid_axis == "x" else "bottom"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom" if grid_axis == "x" else "left"].set_color(BASELINE)
    ax.tick_params(length=0, labelsize=8.5, labelcolor=INK_2)


def terms_for(variables, order_from="Baseline"):
    """The terms (in a sensible order) of the given variables, over all models."""
    t = coef[coef["variable"].isin(variables)]
    first = t.drop_duplicates("term")
    first = first.assign(_o=first["model"].map({m: i for i, m in enumerate(MODELS)}), _v=first["variable"].map({v: i for i, v in enumerate(variables)}))
    return list(first.sort_values(["_v", "_o"], kind="stable")["term"])


def forest(ax, terms, title, models=MODELS):
    """Odds ratios (log scale) with cluster-robust 95% intervals, one row per term, one marker per model."""
    ax.axvline(1, color=GRAY, linewidth=1.4, zorder=1)
    for i, term in enumerate(terms):
        y = len(terms) - 1 - i
        for m, off in zip(MODELS, OFFSETS):
            if m not in models:
                continue
            r = coef[(coef["model"] == m) & (coef["term"] == term)]
            if r.empty:
                continue
            r = r.iloc[0]
            colour, marker = STYLE[m]
            ax.hlines(y + off * 0.6, r["or_ci_low"], r["or_ci_high"], color=colour, linewidth=1.4, zorder=2)
            ax.plot(r["odds_ratio"], y + off * 0.6, marker, color=colour, markersize=4.5, markeredgecolor=SURFACE, markeredgewidth=0.6, zorder=3)
    ax.set_yticks(range(len(terms)), [t.split(": ", 1)[1] if ": " in t else t for t in terms][::-1])
    ax.set_xscale("log")
    ax.set_xlim(0.15, 25)
    ax.set_xticks([0.25, 0.5, 1, 2, 4, 8, 16], ["0.25", "0.5", "1", "2", "4", "8", "16"])
    ax.set_ylim(-0.7, len(terms) - 0.3)
    style_axes(ax, "x")
    ax.set_title(title, fontsize=10.5, fontweight="bold", color=INK, loc="left", pad=8)


def forest_figure(variables_by_panel, filename, title, sub, width=13.5):
    subtitle_fn = subtitle
    sizes = [len(terms_for(v)) for v in variables_by_panel.values()]
    fig, axes = plt.subplots(1, len(sizes), figsize=(width, max(4.5, 0.27 * max(sizes) + 2.4)), dpi=200, facecolor=SURFACE, gridspec_kw={"width_ratios": [max(s, 6) for s in sizes]})
    axes = np.atleast_1d(axes)
    for ax, (panel_title, variables) in zip(axes, variables_by_panel.items()):
        forest(ax, terms_for(variables), panel_title)
    fig.legend(handles=legend_handles(), loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=5, frameon=False, fontsize=9, labelcolor=INK_2)
    fig.text(0.02, 0.985, title, fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
    subtitle_fn(fig, sub, y=0.925)
    longest = max(len(t.split(": ", 1)[1]) for v in variables_by_panel.values() for t in terms_for(v))
    left = min(0.5, 0.0085 * longest * (13.5 / width) + 0.03) if len(sizes) == 1 else 0.1
    fig.subplots_adjust(left=left, right=0.99, top=0.82, bottom=0.14, wspace=0.75)
    fig.savefig(reports / filename, facecolor=SURFACE)
    plt.close(fig)


SUB = "Adjusted odds ratio of a severe accident (fatal or seriously injured); dot = estimate, line = 95% interval with standard errors clustered by municipality; the baseline category of each variable is the reference (odds ratio 1)."
forest_figure({"Place, road and light": ["Region", "Road type", "Intersection", "Lighting"]}, "logit_forest_1_place_road_light.png", "Adjusted odds ratios: region, road type, intersection and lighting", SUB, width=9)
forest_figure({"Weather and road surface": ["Weather", "Road surface"]}, "logit_forest_2_weather_surface.png", "Adjusted odds ratios: weather and road surface", SUB, width=10)
forest_figure({"Year (reference 2017)": ["Year"], "Month (reference January)": ["Month"]}, "logit_forest_3_year_month.png", "Adjusted odds ratios: year and month", SUB, width=12)
forest_figure({"Collision type (reference: rear-end, or the most common)": ["Collision type"]}, "logit_forest_5_collision_type.png", "Adjusted odds ratios: collision type", SUB, width=10)

# the road-user terms: the baseline 'group involved' and the 'counterpart' of the group models
fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.6), dpi=200, facecolor=SURFACE, gridspec_kw={"width_ratios": [1, 1.25]})
forest(axes[0], terms_for(["Group involved"]), "Baseline: group involved (versus a car-only accident)", models=["Baseline"])
forest(axes[1], terms_for(["Counterpart"]), "Group models: the counterpart (versus a passenger car)", models=MODELS[1:])
fig.legend(handles=legend_handles(), loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=5, frameon=False, fontsize=9, labelcolor=INK_2)
fig.text(0.02, 0.985, "Adjusted odds ratios: the road users in the accident", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
subtitle(fig, SUB + " 'Single road user' is not shown for the models with collision type: it is carried by the collision types.")
fig.subplots_adjust(left=0.1, right=0.99, top=0.84, bottom=0.14, wspace=0.55)
fig.savefig(reports / "logit_forest_4_road_users.png", facecolor=SURFACE)
plt.close(fig)

# --- predicted probabilities by category ---
fig, axes = plt.subplots(2, 3, figsize=(14, 8), dpi=200, facecolor=SURFACE)
for ax, var in zip(axes.ravel(), ["Region", "Road type", "Intersection", "Lighting", "Year", "Month"]):
    p = predicted[predicted["variable"] == var]
    cats = list(dict.fromkeys(p[p["model"] == "Baseline"]["category"]))
    if var == "Month":
        cats = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    if var == "Road type":
        cats = [c for c in cats if c != "Unknown"]
    if var == "Lighting":
        cats = [c for c in cats if not c.startswith("Unknown")]
    for m, off in zip(MODELS, OFFSETS):
        d = p[p["model"] == m].set_index("category")
        colour, marker = STYLE[m]
        xs = np.array([cats.index(c) for c in cats if c in d.index]) + off * (0.7 if var in ("Year", "Month") else 1)
        sel = [c for c in cats if c in d.index]
        ax.vlines(xs, d.loc[sel, "ci_low_pct"], d.loc[sel, "ci_high_pct"], color=colour, linewidth=1.3, zorder=2)
        ax.plot(xs, d.loc[sel, "predicted_pct"], marker, color=colour, markersize=4.5, markeredgecolor=SURFACE, markeredgewidth=0.5, linestyle="none", zorder=3)
    labels = [c.replace("Night, public lighting present and lit", "Night, lit").replace("Night, public lighting present but not lit", "Night, not lit").replace("Night, no public lighting", "Night, no light").replace("-Capital Region", "").replace(" Region", "") for c in cats]
    ax.set_xticks(range(len(cats)), labels, rotation=30 if var in ("Lighting", "Road type", "Region") else 0, ha="right" if var in ("Lighting", "Road type", "Region") else "center", fontsize=8)
    ax.set_xlim(-0.6, len(cats) - 0.4)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}%")
    style_axes(ax, "y")
    ax.set_title(var, fontsize=10.5, fontweight="bold", color=INK, loc="left", pad=6)
fig.legend(handles=legend_handles(), loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=5, frameon=False, fontsize=9, labelcolor=INK_2)
fig.text(0.02, 0.985, "Average adjusted predicted probability of a severe accident", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
subtitle(fig, "Each model is evaluated on its own accidents: everyone is set to the category, all other variables stay as observed (average adjusted prediction). Line = 95% interval (1,000 draws, clustered by municipality). Models cover different accidents, so levels differ by design.", y=0.955)
fig.subplots_adjust(left=0.06, right=0.99, top=0.88, bottom=0.14, wspace=0.18, hspace=0.38)
fig.savefig(reports / "logit_predicted_by_category.png", facecolor=SURFACE)
plt.close(fig)

# --- scenarios ---
rows = list(dict.fromkeys(scenarios["model"] + " | " + scenarios["evaluated_as"]))
sc_names = list(dict.fromkeys(scenarios["scenario"]))
fig, axes = plt.subplots(1, 4, figsize=(14.5, 5.4), dpi=200, facecolor=SURFACE, sharex=True)
for ax, sname in zip(axes, sc_names):
    part = scenarios[scenarios["scenario"] == sname]
    for i, row in enumerate(rows):
        r = part[(part["model"] + " | " + part["evaluated_as"]) == row].iloc[0]
        if np.isnan(r["predicted_pct"]):
            continue
        model = r["model"]
        colour, marker = STYLE[model]
        y = len(rows) - 1 - i
        hollow = model == "Baseline" and r["evaluated_as"] != "car-only accident"
        ax.hlines(y, r["ci_low_pct"], r["ci_high_pct"], color=colour, linewidth=1.6, zorder=2)
        ax.plot(r["predicted_pct"], y, marker, color=colour, markersize=6, markerfacecolor=SURFACE if hollow else colour, markeredgecolor=colour, zorder=3)
        ax.text(r["ci_high_pct"] + 0.6, y, f"{r['predicted_pct']:.1f}%", va="center", fontsize=7.5, color=INK)
    ax.set_yticks(range(len(rows)), [r.replace("(counterpart: passenger car)", "vs car").replace(" | ", ": ") for r in rows][::-1] if ax is axes[0] else [])
    ax.set_xlim(0, 52)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:g}%")
    style_axes(ax, "x")
    ax.set_title(sname, fontsize=10, fontweight="bold", color=INK, loc="left", pad=6)
fig.text(0.02, 0.985, "Predicted probability of a severe accident in four typical situations (2024)", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
subtitle(fig, "Dot = estimate, line = 95% interval. Group models: the group against a passenger car. Baseline (blue): a car-only accident (filled) and, hollow, the baseline model evaluated for each group against a car. Collision type: the most common one of each model's sample.")
fig.subplots_adjust(left=0.2, right=0.99, top=0.85, bottom=0.08, wspace=0.08)
fig.savefig(reports / "logit_scenarios.png", facecolor=SURFACE)
plt.close(fig)

# --- calibration ---
fig, axes = plt.subplots(1, 5, figsize=(15, 3.9), dpi=200, facecolor=SURFACE)
for ax, m in zip(axes, MODELS):
    c = calibration[calibration["model"] == m]
    colour, marker = STYLE[m]
    top = max(c["mean_predicted_pct"].max(), c["observed_pct"].max()) * 1.08
    ax.plot([0, top], [0, top], color=GRAY, linewidth=1.3, zorder=1)
    ax.plot(c["mean_predicted_pct"], c["observed_pct"], marker, color=colour, markersize=6, markeredgecolor=SURFACE, zorder=3)
    f = fit[(fit["model"] == m) & (fit["spec"] == "full")].iloc[0]
    ax.text(0.04, 0.96, f"AUC {f['auc']:.2f}\nMcFadden R2 {f['mcfadden_r2']:.3f}", transform=ax.transAxes, va="top", fontsize=8.5, color=INK)
    ax.set_xlim(0, top); ax.set_ylim(0, top)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:g}%"); ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}%")
    style_axes(ax, "y")
    ax.set_xlabel("mean predicted (decile)", fontsize=8.5, color=MUTED)
    if ax is axes[0]:
        ax.set_ylabel("observed share severe", fontsize=8.5, color=MUTED)
    ax.set_title(m, fontsize=10, fontweight="bold", color=INK, loc="left", pad=6)
fig.text(0.02, 0.985, "Calibration: do the predicted probabilities match what happened? (10 groups of accidents by predicted probability)", fontsize=12, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.925, "On the gray line, prediction = observation. In-sample: the models were fitted on these same accidents, so AUC is somewhat optimistic.", fontsize=8, color=INK_2, ha="left", va="top")
fig.subplots_adjust(left=0.045, right=0.995, top=0.8, bottom=0.17, wspace=0.28)
fig.savefig(reports / "logit_calibration.png", facecolor=SURFACE)
plt.close(fig)

# --- interactions: pair-specific odds ratios, additive against with the pair's own effect ---
pf = pairs[pairs["spec"] == "full"]
order = list(pf[pf["version"] == "with the pair's own effect"].sort_values("accidents", ascending=False)["pair"])
fig, ax = plt.subplots(figsize=(11, 0.34 * len(order) + 2.2), dpi=200, facecolor=SURFACE)
ax.axvline(1, color=GRAY, linewidth=1.4, zorder=1)
for i, pair in enumerate(order):
    y = len(order) - 1 - i
    for version, colour, marker, dy, hollow in (("additive (baseline model)", MUTED, "o", 0.15, True), ("with the pair's own effect", "#2a78d6", "s", -0.15, False)):
        r = pf[(pf["pair"] == pair) & (pf["version"] == version)].iloc[0]
        ax.hlines(y + dy, r["ci_low"], r["ci_high"], color=colour, linewidth=1.5, zorder=2)
        ax.plot(r["odds_ratio_vs_car_only"], y + dy, marker, color=colour, markersize=6, markerfacecolor=SURFACE if hollow else colour, markeredgecolor=colour, zorder=3)
ax.set_yticks(range(len(order)), [f"{p}  ({int(pf[(pf['pair'] == p)]['accidents'].iloc[0]):,})" for p in order][::-1])
ax.set_xscale("log"); ax.set_xlim(0.5, 20)
ax.set_xticks([0.5, 1, 2, 4, 8, 16], ["0.5", "1", "2", "4", "8", "16"])
style_axes(ax, "x")
fig.legend(handles=[Line2D([0], [0], marker="o", color=MUTED, markerfacecolor=SURFACE, markersize=7, linewidth=0, label="what the baseline predicts by adding the two group effects"),
                    Line2D([0], [0], marker="s", color="#2a78d6", markersize=7, linewidth=0, label="with the pair's own effect (model with pair interactions)")],
           loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False, fontsize=8.5, labelcolor=INK_2)
fig.text(0.02, 0.985, "Do the road users in one accident interact? Odds of a severe accident for each pair, versus a car-only accident", fontsize=12.5, fontweight="bold", color=INK, ha="left", va="top")
subtitle(fig, "Pairs of groups with at least 500 accidents (number of accidents in brackets). Where the two markers differ, the pair is not just the sum of its parts. Adjusted for all other variables; 95% intervals clustered by municipality.", y=0.955)
fig.subplots_adjust(left=0.3, right=0.98, top=0.9, bottom=0.07)
fig.savefig(reports / "logit_interactions_pairs.png", facecolor=SURFACE)
plt.close(fig)
print("Saved 9 graphs (logit_*.png) in", reports)
