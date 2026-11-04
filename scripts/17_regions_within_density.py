"""
Step 17 - Analysis 4c: is the regional gap in severity still there at the same accident density (and road type)?

Question (#104): Wallonia has a higher fatal share than Flanders (step 15). Does that gap remain when municipalities of the same density
(and the same road type) are compared?  Limit as before: the accident class belongs to the whole accident; density is accidents per km2, not per traffic.

Decisions applied (see beslissingslogboek.md):
  #105 the five density classes of step 16 (quintiles of the 581 municipalities, #101); Brussels is only in the densest class.
  #106 all accidents + cyclists, pedestrians, motorcycles, mopeds, each group with its own density classes (from step 16).
  #107 direct standardisation and a logistic regression (scikit-learn, bootstrap intervals).
  #108 regions compared within density classes AND within density class x road type (motorway, regional, municipal);
       accidents with an unknown road type are left out of the road-type-matched analyses; cells with fewer than 100 accidents are flagged.
  #71 fatal = class 1 + 2; serious = class 3.   #95 shares with 95% Wilson intervals.

How the two adjusted numbers work (plain words):
  Direct standardisation: take Flanders' mix of strata (e.g. what share of its accidents are in density class 1, 2, ...), and calculate what Wallonia's
  fatal share would be if Wallonia had exactly that mix: sum over strata of (Flanders weight x Wallonia's share in that stratum).
  Logistic regression: a model for the chance that an accident is fatal, with region, density class and road type as explanations; the odds ratio of
  Wallonia versus Flanders is the gap that remains after the density class and road type are accounted for.

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/17_regions_within_density.py OPENDATA_MAP_2017-2024_en_flagged.csv.gz reports
"""
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to a file, not to a window
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

accidents_file = sys.argv[1]  # the flagged English dataset from step 05
output_dir = Path(sys.argv[2])  # the reports/ folder (holds the step-16 density classes)
output_dir.mkdir(exist_ok=True)

# --- 1. Read the data and the density classes of step 16 ---
header = pd.read_csv(accidents_file, nrows=0).columns
df = pd.read_csv(accidents_file, dtype={c: str for c in header if c.endswith("_code")})
density = pd.read_csv(output_dir / "severity_municipality_density_table.csv", dtype={"municipality_nis_code": str})  # per group and municipality: density_class
GROUPS = {"All accidents": None, "Bicycle": "03", "Pedestrian": "08", "Motorcycle": "07", "Moped": "06"}
REGIONS = ["Brussels-Capital Region", "Flemish Region", "Walloon Region"]
REGION_SHORT = {"Brussels-Capital Region": "Brussels", "Flemish Region": "Flanders", "Walloon Region": "Wallonia"}
ROAD_TYPES = ["Motorway", "Regional road", "Municipal road"]  # "Unknown" is left out of the road-type-matched analyses (#108)
OUTCOMES = {"fatal": ["1", "2"], "serious": ["3"]}
MIN_N = 100


def wilson(k, n, z=1.96):
    """95% Wilson interval for a share, in percent."""
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z ** 2 / n
    c = (p + z ** 2 / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / d
    return (c - h) * 100, (c + h) * 100


# --- 2. One table of cells: group x region x density class x road type, with counts ---
frames = []
for group, code in GROUPS.items():
    mask = pd.Series(True, index=df.index) if code is None else (df["road_user_type1_code"] == code) | (df["road_user_type2_code"] == code)  # road user 1 OR 2
    classes = density[density["group"] == group].set_index("municipality_nis_code")["density_class"]
    sub = df[mask].copy()
    sub["density_class"] = sub["municipality_nis_code"].map(classes)
    assert sub["density_class"].notna().all(), f"{group}: a municipality has no density class"
    sub["fatal"] = sub["accident_class_code"].isin(OUTCOMES["fatal"])
    sub["serious"] = sub["accident_class_code"].isin(OUTCOMES["serious"])
    cells = sub.groupby(["region", "density_class", "road_type"]).agg(accidents=("fatal", "size"), fatal=("fatal", "sum"), serious=("serious", "sum")).reset_index()
    cells.insert(0, "group", group)
    frames.append(cells)
cells = pd.concat(frames, ignore_index=True)
totals = {g: int(((df["road_user_type1_code"] == c) | (df["road_user_type2_code"] == c)).sum()) if c else len(df) for g, c in GROUPS.items()}
for g in GROUPS:
    assert cells[cells["group"] == g]["accidents"].sum() == totals[g], f"{g}: cells do not add up"
matched = cells[cells["road_type"].isin(ROAD_TYPES)]  # without "Unknown" road type
left_out = {g: int(cells[(cells["group"] == g) & (cells["road_type"] == "Unknown")]["accidents"].sum()) for g in GROUPS}
print("Checks passed: the region x density x road type cells add up to the accidents of every group.")
print("Accidents with an unknown road type, left out of the road-type-matched analyses:", {g: n for g, n in left_out.items()}, "\n")


def with_shares(table, keys):
    """Sum cells to the given keys and add shares, 95% intervals and the 'few accidents' flag."""
    out = table.groupby(keys, as_index=False)[["accidents", "fatal", "serious"]].sum()
    for label in OUTCOMES:
        out[f"{label}_share_pct"] = out[label] / out["accidents"] * 100
        ci = [wilson(k, n) for k, n in zip(out[label], out["accidents"])]
        out[f"{label}_ci_low"], out[f"{label}_ci_high"] = [c[0] for c in ci], [c[1] for c in ci]
    out["few_accidents"] = out["accidents"] < MIN_N
    return out


# --- 3. Class-by-class tables ---
by_density = with_shares(cells, ["group", "density_class", "region"])  # all accidents of the group (incl. unknown road type)
by_density_road = with_shares(matched, ["group", "density_class", "road_type", "region"])
by_density.to_csv(output_dir / "severity_regions_within_density.csv", index=False, float_format="%.3f")
by_density_road.to_csv(output_dir / "severity_regions_within_density_roadtype.csv", index=False, float_format="%.3f")

print("FATAL share (%) by density class and region, ALL accidents ('*' = fewer than 100 accidents; Wallonia / Flanders = ratio)")
part = by_density[by_density["group"] == "All accidents"]
rows = []
for k in range(1, 6):
    row = {"density class": k}
    for r in REGIONS:
        c = part[(part["density_class"] == k) & (part["region"] == r)]
        row[REGION_SHORT[r]] = f"{c['fatal_share_pct'].iat[0]:.2f}%{'*' if c['few_accidents'].iat[0] else ''} ({c['accidents'].iat[0]:,})" if len(c) else "-"
    w = part[(part["density_class"] == k) & (part["region"] == "Walloon Region")]["fatal_share_pct"].iat[0]
    f = part[(part["density_class"] == k) & (part["region"] == "Flemish Region")]["fatal_share_pct"].iat[0]
    row["Wallonia / Flanders"] = f"{w / f:.2f}"
    rows.append(row)
print(pd.DataFrame(rows).set_index("density class").to_string(), "\n")

# --- 4. Direct standardisation: Wallonia with Flanders' mix of strata ---
def standardise(group, outcome, strata_keys):
    """Wallonia's share if it had Flanders' mix of strata; returns crude and adjusted numbers with 95% intervals (normal approximation)."""
    table = matched if "road_type" in strata_keys else cells
    sub = table[table["group"] == group]
    f = sub[sub["region"] == "Flemish Region"].groupby(strata_keys)[["accidents", outcome]].sum()
    w = sub[sub["region"] == "Walloon Region"].groupby(strata_keys)[["accidents", outcome]].sum()
    common = f.index.intersection(w.index)
    f, w = f.loc[common], w.loc[common]
    weights = f["accidents"] / f["accidents"].sum()  # Flanders' mix
    covered = f["accidents"].sum() / table[(table["group"] == group) & (table["region"] == "Flemish Region")]["accidents"].sum()  # share of Flanders' accidents in the used strata
    p_f, p_w = f[outcome] / f["accidents"], w[outcome] / w["accidents"]
    # variance of a standardised share: sum of weight^2 x p(1-p)/n, with p nudged away from 0 and 1 so a stratum with 0 fatal accidents is not treated as certain
    adj = lambda k, n: (k + 1) / (n + 2)
    var_f = (weights ** 2 * adj(f[outcome], f["accidents"]) * (1 - adj(f[outcome], f["accidents"])) / f["accidents"]).sum()
    var_w = (weights ** 2 * adj(w[outcome], w["accidents"]) * (1 - adj(w[outcome], w["accidents"])) / w["accidents"]).sum()
    flanders = (weights * p_f).sum() * 100            # Flanders in its own mix = its crude share in the used strata
    wallonia_adj = (weights * p_w).sum() * 100         # Wallonia in Flanders' mix
    wallonia_crude = w[outcome].sum() / w["accidents"].sum() * 100  # Wallonia in its own mix (same strata)
    se_gap = math.sqrt(var_f + var_w) * 100
    se_log_ratio = math.sqrt(var_w * 1e4 / wallonia_adj ** 2 + var_f * 1e4 / flanders ** 2) if wallonia_adj > 0 and flanders > 0 else float("nan")
    ratio = wallonia_adj / flanders
    return {"group": group, "outcome": outcome, "strata": "+".join(strata_keys), "strata_used": len(common), "flanders_accidents_covered_pct": covered * 100,
            "flanders_share_pct": flanders, "wallonia_crude_share_pct": wallonia_crude, "wallonia_standardised_share_pct": wallonia_adj,
            "gap_crude_points": wallonia_crude - flanders, "gap_standardised_points": wallonia_adj - flanders,
            "gap_standardised_ci_low": wallonia_adj - flanders - 1.96 * se_gap, "gap_standardised_ci_high": wallonia_adj - flanders + 1.96 * se_gap,
            "ratio_crude": wallonia_crude / flanders, "ratio_standardised": ratio,
            "ratio_standardised_ci_low": ratio * math.exp(-1.96 * se_log_ratio), "ratio_standardised_ci_high": ratio * math.exp(1.96 * se_log_ratio)}


standardised = pd.DataFrame([standardise(g, o, keys) for g in GROUPS for o in OUTCOMES for keys in (["density_class"], ["density_class", "road_type"])])
standardised.to_csv(output_dir / "severity_regions_standardised.csv", index=False, float_format="%.3f")
# check: standardising Flanders to its own mix must give its crude share (weights add up to 1)
check = matched[(matched["group"] == "All accidents") & (matched["region"] == "Flemish Region")]
assert abs(standardised[(standardised["group"] == "All accidents") & (standardised["outcome"] == "fatal") & (standardised["strata"] == "density_class+road_type")]["flanders_share_pct"].iat[0]
           - check["fatal"].sum() / check["accidents"].sum() * 100) < 1e-9, "standardisation check failed"
print("DIRECT STANDARDISATION: Wallonia's share if it had Flanders' mix (fatal share, %)")
show = standardised[standardised["outcome"] == "fatal"].copy()
show["strata"] = show["strata"].map({"density_class": "density", "density_class+road_type": "density + road type"})
print(show[["group", "strata", "flanders_share_pct", "wallonia_crude_share_pct", "wallonia_standardised_share_pct", "ratio_crude", "ratio_standardised", "ratio_standardised_ci_low", "ratio_standardised_ci_high", "flanders_accidents_covered_pct"]].to_string(
    index=False, formatters={c: "{:.2f}".format for c in ["flanders_share_pct", "wallonia_crude_share_pct", "wallonia_standardised_share_pct", "ratio_crude", "ratio_standardised", "ratio_standardised_ci_low", "ratio_standardised_ci_high"]} | {"flanders_accidents_covered_pct": "{:.1f}%".format}), "\n")

# --- 5. Logistic regression on the cells (equivalent to fitting every accident), with bootstrap intervals ---
def design(table, model):
    """Design matrix for a model: 0 = region only, 1 = + density class, 2 = + density class + road type. Reference: Flanders, class 1, municipal road."""
    X = pd.DataFrame({"Wallonia vs Flanders": (table["region"] == "Walloon Region").astype(float), "Brussels vs Flanders": (table["region"] == "Brussels-Capital Region").astype(float)})
    if model >= 1:
        for k in range(2, 6):
            X[f"density class {k}"] = (table["density_class"] == k).astype(float)
    if model >= 2:
        X["motorway"] = (table["road_type"] == "Motorway").astype(float)
        X["regional road"] = (table["road_type"] == "Regional road").astype(float)
    return X


def fit(X, n, k):
    """Weighted logistic regression: each cell counts k times as 'yes' and n-k times as 'no'. No penalty (C = infinity), so it is the ordinary maximum-likelihood fit."""
    stacked = pd.concat([X, X], ignore_index=True)
    y = np.r_[np.ones(len(X)), np.zeros(len(X))]
    weights = np.r_[k, n - k]
    keep = weights > 0
    model = LogisticRegression(C=np.inf, max_iter=2000, tol=1e-10)  # C=infinity = no penalty (the new scikit-learn spelling of penalty=None)
    model.fit(stacked[keep], y[keep], sample_weight=weights[keep])
    return model.coef_[0]


def irls(X, n, k, steps=50):
    """The same fit written out by hand (Newton-Raphson), used only to check the scikit-learn result."""
    A = np.c_[np.ones(len(X)), X.values]
    beta = np.zeros(A.shape[1])
    for _ in range(steps):
        p = 1 / (1 + np.exp(-A @ beta))
        gradient = A.T @ (k - n * p)
        hessian = (A * (n * p * (1 - p))[:, None]).T @ A
        beta = beta + np.linalg.solve(hessian, gradient)
    return beta[1:]


rng = np.random.default_rng(2026)
BOOTSTRAPS = 1000
logistic_rows = []
for group in GROUPS:
    sub = matched[matched["group"] == group].groupby(["region", "density_class", "road_type"], as_index=False)[["accidents", "fatal", "serious"]].sum()
    sub = sub[sub["accidents"] > 0].reset_index(drop=True)
    for outcome in OUTCOMES:
        n, k = sub["accidents"].values.astype(float), sub[outcome].values.astype(float)
        probs = np.r_[k, n - k] / n.sum()  # a bootstrap draws N accidents again from the observed (cell, outcome) mix
        for model in (0, 1, 2):
            X = design(sub, model)
            coefficients = fit(X, n, k)
            if group == "All accidents" and outcome == "fatal":  # verify the fit with a hand-written version
                assert np.allclose(coefficients, irls(X, n, k), atol=1e-4), "logistic fit differs from the hand-written check"
            draws = rng.multinomial(int(n.sum()), probs, size=BOOTSTRAPS)
            boot = np.array([fit(X, draws[b][: len(X)] + draws[b][len(X):], draws[b][: len(X)].astype(float)) for b in range(BOOTSTRAPS)])
            for j, term in enumerate(X.columns[:2]):
                low, high = np.percentile(boot[:, j], [2.5, 97.5])
                logistic_rows.append({"group": group, "outcome": outcome, "model": ["region only", "+ density class", "+ density class + road type"][model], "term": term,
                                      "odds_ratio": math.exp(coefficients[j]), "ci_low": math.exp(low), "ci_high": math.exp(high), "cells_used": len(sub), "accidents": int(n.sum())})
logistic = pd.DataFrame(logistic_rows)
logistic.to_csv(output_dir / "severity_regions_logistic.csv", index=False, float_format="%.4f")
print("Check passed: the scikit-learn logistic fit equals a hand-written Newton-Raphson fit.\n")
print("LOGISTIC REGRESSION: odds ratio Wallonia vs Flanders (1 = no difference; 95% bootstrap interval)")
for outcome in OUTCOMES:
    show = logistic[(logistic["outcome"] == outcome) & (logistic["term"] == "Wallonia vs Flanders")].copy()
    show["odds ratio (95% interval)"] = [f"{o:.2f} ({lo:.2f}-{hi:.2f})" for o, lo, hi in zip(show["odds_ratio"], show["ci_low"], show["ci_high"])]
    print(f"{outcome} accidents:")
    print(show.pivot(index="group", columns="model", values="odds ratio (95% interval)").loc[list(GROUPS)][["region only", "+ density class", "+ density class + road type"]].to_string(), "\n")

# --- 6. Graphs ---
SURFACE, INK, INK_2, MUTED, GRID, BASELINE, BLUE, GRAY = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#2a78d6", "#898781"
COLOUR = {"Brussels-Capital Region": "#2a78d6", "Flemish Region": "#eb6834", "Walloon Region": "#1baf7a"}  # categorical slots 1-3
SHIFT = {"Brussels-Capital Region": -0.22, "Flemish Region": 0.0, "Walloon Region": 0.22}
plt.rcParams["font.family"] = ["Helvetica Neue", "Arial", "DejaVu Sans"]  # a plain system sans


def style(ax):
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}%")
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(length=0, labelsize=8.5, labelcolor=INK_2)


def draw_cells(ax, table, label, x_of, shift_scale=1.0, ymax_from_reliable=True):
    tops = []
    for region in REGIONS:
        for _, r in table[table["region"] == region].iterrows():
            x = x_of(r) + SHIFT[region] * shift_scale
            ax.vlines(x, r[f"{label}_ci_low"], r[f"{label}_ci_high"], color=COLOUR[region], linewidth=1.8, zorder=2)
            ax.plot(x, r[f"{label}_share_pct"], "o", markersize=6.5, markeredgecolor=COLOUR[region], markeredgewidth=1.5, markerfacecolor=SURFACE if r["few_accidents"] else COLOUR[region], zorder=3)
            if not r["few_accidents"]:
                tops.append(r[f"{label}_ci_high"])
    return max(tops) if tops else 1


legend = [Line2D([0], [0], marker="o", color=COLOUR[r], markerfacecolor=COLOUR[r], markersize=7, linewidth=0, label=REGION_SHORT[r]) for r in REGIONS] + \
         [Line2D([0], [0], marker="o", color=INK_2, markerfacecolor=SURFACE, markersize=7, linewidth=0, label="hollow = fewer than 100 accidents (may run off the panel)")]

# 6a. All accidents: regions within density classes (fatal | serious)
fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.0), dpi=200, facecolor=SURFACE)
for ax, label, title in zip(axes, ("fatal", "serious"), ("Fatal share", "Serious-injury share")):
    ax.set_facecolor(SURFACE)
    part = by_density[by_density["group"] == "All accidents"]
    top = draw_cells(ax, part, label, lambda r: r["density_class"])
    ax.set_ylim(0, top * 1.12)
    ax.set_xlim(0.4, 5.6)
    ax.set_xticks(range(1, 6), ["1\nleast dense", "2", "3", "4", "5\ndensest"])
    style(ax)
    ax.set_title(title, fontsize=10.5, fontweight="bold", color=INK, loc="left", pad=8)
    ax.set_xlabel("accident density class of the municipality (same classes as step 16)", fontsize=8.5, color=MUTED)
fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=4, frameon=False, fontsize=8.5, labelcolor=INK_2)
fig.text(0.02, 0.975, "Is the regional gap still there at the same accident density? All accidents, 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.925, "Dot = share of the accidents in that region and density class; line = 95% interval. Brussels is only in the densest class.", fontsize=8, color=INK_2, ha="left", va="top")
fig.subplots_adjust(left=0.07, right=0.985, top=0.80, bottom=0.2, wspace=0.18)
fig.savefig(output_dir / "severity_regions_within_density.png", facecolor=SURFACE)
plt.close(fig)

# 6b. The four vulnerable groups (and all accidents again): 2 rows x 5 columns
fig, axes = plt.subplots(2, 5, figsize=(15, 6.6), dpi=200, facecolor=SURFACE)
for col, group in enumerate(GROUPS):
    part = by_density[by_density["group"] == group]
    for row, label in enumerate(("fatal", "serious")):
        ax = axes[row, col]
        ax.set_facecolor(SURFACE)
        top = draw_cells(ax, part, label, lambda r: r["density_class"])
        ax.set_ylim(0, top * 1.12)
        ax.set_xlim(0.4, 5.6)
        ax.set_xticks(range(1, 6), ["1\nleast", "2", "3", "4", "5\ndensest"], fontsize=8)
        style(ax)
        if row == 0:
            ax.set_title(group, fontsize=10, fontweight="bold", color=INK, loc="left", pad=6)
        if row == 1:
            ax.set_xlabel("density class", fontsize=8.5, color=MUTED)
        if col == 0:
            ax.set_ylabel("fatal share" if label == "fatal" else "serious share", fontsize=9, color=INK_2)
fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=4, frameon=False, fontsize=8.5, labelcolor=INK_2)
fig.text(0.02, 0.975, "Regions within density classes, per road-user group, 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.935, "Each group has its own density classes (step 16). Dot = share; line = 95% interval. Each panel has its own scale.", fontsize=8, color=INK_2, ha="left", va="top")
fig.subplots_adjust(left=0.05, right=0.99, top=0.82, bottom=0.13, wspace=0.35, hspace=0.38)
fig.savefig(output_dir / "severity_regions_within_density_groups.png", facecolor=SURFACE)
plt.close(fig)

# 6c. All accidents: density class x road type
fig, axes = plt.subplots(2, 3, figsize=(13, 6.8), dpi=200, facecolor=SURFACE)
for col, road_type in enumerate(ROAD_TYPES):
    part = by_density_road[(by_density_road["group"] == "All accidents") & (by_density_road["road_type"] == road_type)]
    for row, label in enumerate(("fatal", "serious")):
        ax = axes[row, col]
        ax.set_facecolor(SURFACE)
        top = draw_cells(ax, part, label, lambda r: r["density_class"])
        ax.set_ylim(0, top * 1.12)
        ax.set_xlim(0.4, 5.6)
        ax.set_xticks(range(1, 6), ["1\nleast", "2", "3", "4", "5\ndensest"], fontsize=8)
        style(ax)
        if row == 0:
            ax.set_title(road_type, fontsize=10.5, fontweight="bold", color=INK, loc="left", pad=6)
        if row == 1:
            ax.set_xlabel("density class", fontsize=8.5, color=MUTED)
        if col == 0:
            ax.set_ylabel("fatal share" if label == "fatal" else "serious share", fontsize=9, color=INK_2)
fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=4, frameon=False, fontsize=8.5, labelcolor=INK_2)
fig.text(0.02, 0.975, "Regions within the same density class AND road type, all accidents, 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.935, "The strictest like-with-like comparison. Dot = share; line = 95% interval; accidents with an unknown road type are left out.", fontsize=8, color=INK_2, ha="left", va="top")
fig.subplots_adjust(left=0.06, right=0.99, top=0.82, bottom=0.13, wspace=0.22, hspace=0.38)
fig.savefig(output_dir / "severity_regions_within_density_roadtype.png", facecolor=SURFACE)
plt.close(fig)

# 6d. How much of the gap remains: Wallonia vs Flanders, ratio crude -> adjusted (standardisation and logistic regression)
fig, axes = plt.subplots(2, 2, figsize=(12.5, 7.4), dpi=200, facecolor=SURFACE)
groups = list(GROUPS)
for col, outcome in enumerate(OUTCOMES):
    # top row: direct standardisation
    ax = axes[0, col]
    ax.set_facecolor(SURFACE)
    for i, group in enumerate(groups):
        y = len(groups) - 1 - i
        crude = standardised[(standardised["group"] == group) & (standardised["outcome"] == outcome) & (standardised["strata"] == "density_class")].iloc[0]
        ax.plot(crude["ratio_crude"], y + 0.2, "o", markersize=7, markeredgecolor=INK_2, markerfacecolor=SURFACE, markeredgewidth=1.5, zorder=3)
        for strata, marker, dy in (("density_class", "D", 0.0), ("density_class+road_type", "s", -0.2)):
            r = standardised[(standardised["group"] == group) & (standardised["outcome"] == outcome) & (standardised["strata"] == strata)].iloc[0]
            ax.hlines(y + dy, r["ratio_standardised_ci_low"], r["ratio_standardised_ci_high"], color=BLUE, linewidth=2, zorder=2)
            ax.plot(r["ratio_standardised"], y + dy, marker, markersize=6.5, color=BLUE, markeredgecolor=SURFACE, zorder=3)
    ax.axvline(1, color=GRAY, linewidth=1.3, zorder=1)
    ax.set_yticks(range(len(groups)), groups[::-1])
    ax.set_title(f"{outcome.capitalize()} accidents: standardised ratio (Wallonia / Flanders)", fontsize=10, fontweight="bold", color=INK, loc="left", pad=8)
    # bottom row: logistic regression odds ratios
    ax = axes[1, col]
    ax.set_facecolor(SURFACE)
    for i, group in enumerate(groups):
        y = len(groups) - 1 - i
        for model, marker, dy, filled in (("region only", "o", 0.2, False), ("+ density class", "D", 0.0, True), ("+ density class + road type", "s", -0.2, True)):
            r = logistic[(logistic["group"] == group) & (logistic["outcome"] == outcome) & (logistic["model"] == model) & (logistic["term"] == "Wallonia vs Flanders")].iloc[0]
            colour = INK_2 if model == "region only" else BLUE
            ax.hlines(y + dy, r["ci_low"], r["ci_high"], color=colour, linewidth=2 if filled else 1.6, zorder=2)
            ax.plot(r["odds_ratio"], y + dy, marker, markersize=7 if not filled else 6.5, markeredgecolor=colour, markerfacecolor=colour if filled else SURFACE, markeredgewidth=1.5, zorder=3)
    ax.axvline(1, color=GRAY, linewidth=1.3, zorder=1)
    ax.set_yticks(range(len(groups)), groups[::-1])
    ax.set_title(f"{outcome.capitalize()} accidents: odds ratio, Wallonia vs Flanders (logistic regression)", fontsize=10, fontweight="bold", color=INK, loc="left", pad=8)
    ax.set_xlabel("1 = no difference between the regions", fontsize=8.5, color=MUTED)
for ax in axes.ravel():
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(length=0, labelsize=9, labelcolor=INK_2)
fig.legend(handles=[Line2D([0], [0], marker="o", color=INK_2, markerfacecolor=SURFACE, markersize=7, linewidth=0, label="crude / region only"),
                    Line2D([0], [0], marker="D", color=BLUE, markersize=6.5, linewidth=0, label="same density class"),
                    Line2D([0], [0], marker="s", color=BLUE, markersize=6.5, linewidth=0, label="same density class and road type")],
           loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=3, frameon=False, fontsize=9, labelcolor=INK_2)
fig.text(0.02, 0.975, "How much of the Wallonia-Flanders gap remains at the same density and road type? 2017-2024", fontsize=13, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.935, "Above 1 = Wallonia higher. Lines = 95% intervals (standardisation: normal approximation; regression: bootstrap, 1,000 repetitions). Each accident counts once for every road-user group it involves.",
         fontsize=8, color=INK_2, ha="left", va="top")
fig.subplots_adjust(left=0.1, right=0.985, top=0.86, bottom=0.12, wspace=0.28, hspace=0.38)
fig.savefig(output_dir / "severity_regions_gap_adjusted.png", facecolor=SURFACE)
plt.close(fig)
print(f"Saved 4 CSV files and 4 graphs (severity_regions_within_density*.png, severity_regions_gap_adjusted.png) in {output_dir}/")
