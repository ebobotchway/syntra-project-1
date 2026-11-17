"""
Step 4b of the final analysis: a simple binary logistic regression for the severity of accidents with vulnerable road users.

  Dependent variable : severe = 1 when the accident class is 1, 2 or 3 (fatal + serious injury), 0 otherwise                       (#116)
  Explanatory        : hotspot  (1 = the accident is in one of the 40 (or 20) busiest 5 x 5 km squares of ITS OWN group and period)
                       period   (pre 2017-2019 = reference, during 2020-2021, post 2022-2024)
                       group    (bicycle = reference, pedestrian, motorcycle, moped)
                       built-up area (inside = reference, outside)                                                                  extra variable 1
                       light    (daylight = reference, dawn/dusk, night with public lighting lit, night with public lighting present but not lit, night without public lighting)   extra variable 2 (#218)
                       road surface (dry or clean = reference, wet, dirty, ice or snow)                                                   extra variable 3 (#218)

Rows: one row per accident AND group (an accident with a cyclist and a pedestrian is a row in both groups: counting rule #33), only accidents with usable coordinates (#90, needed to know the square),
and only accidents where built-up area, light condition and road surface are known. Because one accident can be two rows, and accidents in the same municipality resemble each other, the standard errors are
cluster-robust by municipality (581 clusters), the same choice as in the main project.

Estimation: Newton-Raphson with step-halving (the same code as in logit_live.py of the main project), sandwich standard errors with the small-sample factor G/(G-1) * (N-1)/(N-k).
The whole model is fitted twice, once with the top 40 and once with the top 20 as the definition of a hotspot (decision #213); every results file has a column top_n.
Besides the odds ratios the script calculates the AVERAGE ADJUSTED PREDICTION of the hotspot effect: the severe share if every accident were in a hotspot against if none were, all other variables as observed.

How to run (from the folder hotspot_dive_deep_osm_4steps, with `conda activate syntra-ds`; the argument is the accident file of the main project):
    python -I scripts/05_logistic_model.py "../OPENDATA_MAP_2017-2024_en_flagged.csv.gz"
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import norm, rankdata

HERE = Path(__file__).resolve().parent.parent
RESULTS = HERE / "results"

SIZE = "5 x 5 km squares"
GROUPS = {"Bicycle": ["03"], "Pedestrian": ["08"], "Motorcycle": ["07"], "Moped": ["06"]}  # the first is the reference group
PERIODS = {"Pre Covid-19 (2017-2019)": range(2017, 2020), "During Covid-19 (2020-2021)": range(2020, 2022), "Post Covid-19 (2022-2024)": range(2022, 2025)}
LIGHT = {"1": "Daylight", "2": "Dawn, dusk", "3": "Night, public lighting lit", "5": "Night, lighting present but not lit", "4": "Night, no public lighting"}  # the three kinds of night are kept apart (#218); code 9 (unknown) is left out
NIGHT = [v for v in LIGHT.values() if v.startswith("Night")]
BUILT_UP = {"1": "Inside built-up area", "2": "Outside built-up area"}  # code 9 (unknown) is left out


def surface(code):
    """Road surface from road_condition_code (1 dry, 2 wet, 3 ice or snow, 4 clean, 5 dirty, 9 unknown; combinations like '2/4' = wet + clean). A combination takes its worst part: ice or snow > wet > dirty > dry or clean (#218)."""
    parts = str(code).split("/")
    if "9" in parts or not set(parts) <= set("12345"):
        return np.nan  # unknown: left out
    for part, name in (("3", "Ice or snow"), ("2", "Wet"), ("5", "Dirty")):
        if part in parts:
            return name
    return "Dry or clean"
SURFACES = ["Wet", "Dirty", "Ice or snow"]  # the reference is "Dry or clean"
N_DRAWS, SEED = 1000, 2026
TOP_NS = (40, 20)  # the hotspot definitions; the model is fitted for each


# ---------------------------------------------------------------------------------------------------------- the estimator
def loglik(X, y, beta):
    eta = X @ beta
    return float(np.sum(y * eta - np.logaddexp(0, eta)))


def fit_logit(X, y, max_iter=100, tol=1e-9):
    """Logistic regression by Newton-Raphson with step-halving. Returns the coefficients, the inverse Hessian, the probabilities and the log-likelihood."""
    beta = np.zeros(X.shape[1])
    beta[0] = math.log(y.mean() / (1 - y.mean()))
    current = loglik(X, y, beta)
    for _ in range(max_iter):
        p = expit(X @ beta)
        w = p * (1 - p)
        step = np.linalg.solve((X * w[:, None]).T @ X, X.T @ (y - p))
        size = 1.0
        while size > 1e-6:
            candidate = beta + size * step
            new = loglik(X, y, candidate)
            if new >= current - 1e-12:
                break
            size /= 2
        beta, current = candidate, new
        if np.max(np.abs(size * step)) < tol:
            break
    else:
        raise RuntimeError("the model did not converge")
    p = expit(X @ beta)
    w = p * (1 - p)
    return beta, np.linalg.inv((X * w[:, None]).T @ X), p, current


def cluster_robust_cov(X, y, p, bread, clusters):
    """Cluster-robust (sandwich) covariance with the small-sample factor G/(G-1) * (N-1)/(N-k)."""
    scores = X * (y - p)[:, None]
    g = clusters.max() + 1
    cluster_scores = np.zeros((g, X.shape[1]))
    np.add.at(cluster_scores, clusters, scores)
    n, k = X.shape
    return g / (g - 1) * (n - 1) / (n - k) * bread @ (cluster_scores.T @ cluster_scores) @ bread


def auc(y, score):
    ranks = rankdata(score)
    n1 = y.sum()
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1)))


# ---------------------------------------------------------------------------------------------------------- the data: one row per accident and group
header = pd.read_csv(sys.argv[1], nrows=0).columns
df = pd.read_csv(sys.argv[1], dtype={c: str for c in header if c.endswith("_code")})
assert len(df) == 289532
df["row"] = np.arange(len(df))
usable = df["x_coord"].between(20_000, 300_000) & df["y_coord"].between(20_000, 250_000)  # decision #90
df["severe"] = df["accident_class_code"].isin(["1", "2", "3"]).astype(int)
assert int(df["severe"].sum()) == 28532
side = 5000.0
df["cx"], df["cy"] = np.floor(df["x_coord"] / side).fillna(-1).astype(int), np.floor(df["y_coord"] / side).fillna(-1).astype(int)

top = pd.read_csv(RESULTS / "hotspots_top40.csv")
top = top[top["size"] == SIZE]
hot_cells = {n: {(g, p): set(zip(t["cx"], t["cy"])) for (g, p), t in top[top["rank"] <= n].groupby(["group", "period"])} for n in TOP_NS}
assert all(len(v) == n for n in TOP_NS for v in hot_cells[n].values())

pieces, flow = [], []
for group, codes in GROUPS.items():
    in_group = df["road_user_type1_code"].isin(codes) | df["road_user_type2_code"].isin(codes)  # road user 1 OR 2
    for period, years in PERIODS.items():
        sub = df[in_group & df["collision_year"].isin(years)].copy()
        n_all = len(sub)
        sub = sub[usable[sub.index]]
        n_located = len(sub)
        for n in TOP_NS:
            sub[f"hotspot{n}"] = [int((cx, cy) in hot_cells[n][(group, period)]) for cx, cy in zip(sub["cx"], sub["cy"])]
        sub["group"], sub["period"] = group, period
        sub["built_up"], sub["light"] = sub["built_up_area_code"].map(BUILT_UP), sub["light_condition_code"].map(LIGHT)
        sub["surface"] = sub["road_condition_code"].map(surface)
        sub = sub.dropna(subset=["built_up", "light", "surface"])
        flow.append({"group": group, "period": period, "accidents": n_all, "with coordinates": n_located, "with built-up area, light and road surface known (used)": len(sub)})
        pieces.append(sub)
data = pd.concat(pieces, ignore_index=True)
flow = pd.DataFrame(flow)
flow.to_csv(RESULTS / "logit_selection.csv", index=False)
print(f"Rows in the model: {len(data):,} (from {flow['accidents'].sum():,} accident-group rows; {data['row'].nunique():,} different accidents), severe {data['severe'].mean() * 100:.2f}%")

# ---------------------------------------------------------------------------------------------------------- the model, for one definition of a hotspot
def run(top_n):
    data["hotspot"] = data[f"hotspot{top_n}"]
    TERMS = [("Intercept", None, None)]
    columns = {"Intercept": np.ones(len(data))}


    def add(name, label, mask, block):
        columns[name] = mask.astype(float).to_numpy() if hasattr(mask, "astype") else mask
        TERMS.append((name, label, block))


    add("hotspot", f"In a hotspot square (top {top_n} of own group and period)", data["hotspot"] == 1, "Hotspot")
    for p in list(PERIODS)[1:]:
        add(f"period={p}", f"{p} (against Pre Covid-19)", data["period"] == p, "Period")
    for g in list(GROUPS)[1:]:
        add(f"group={g}", f"{g} (against Bicycle)", data["group"] == g, "Group")
    add("built_up=outside", "Outside built-up area (against inside)", data["built_up"] == "Outside built-up area", "Built-up area")
    for light in ["Dawn, dusk"] + NIGHT:
        add(f"light={light}", f"{light} (against daylight)", data["light"] == light, "Light condition")
    for surf in SURFACES:
        add(f"surface={surf}", f"{surf} road surface (against dry or clean)", data["surface"] == surf, "Road surface")

    X = np.column_stack([columns[name] for name, _, _ in TERMS])
    y = data["severe"].to_numpy(float)
    clusters = pd.factorize(data["municipality_nis_code"])[0]
    beta, bread, p, ll = fit_logit(X, y)
    cov = cluster_robust_cov(X, y, p, bread, clusters)
    se = np.sqrt(np.diag(cov))
    z = beta / se
    low, high = beta - 1.96 * se, beta + 1.96 * se
    table = pd.DataFrame({"term": [t[0] for t in TERMS], "variable": [t[2] or "" for t in TERMS], "label": [t[1] or "Intercept (baseline log-odds)" for t in TERMS],
                          "coefficient": beta, "std error": se, "odds ratio": np.exp(beta), "OR low": np.exp(low), "OR high": np.exp(high), "p value": 2 * norm.sf(np.abs(z))})
    table.loc[0, ["odds ratio", "OR low", "OR high"]] = np.nan  # the intercept has no odds ratio worth reading

    # ---------------------------------------------------------------------------------------------------------- fit measures and the hotspot effect as percentage points
    null_ll = len(y) * (y.mean() * math.log(y.mean()) + (1 - y.mean()) * math.log(1 - y.mean()))
    vif = []
    for j, (name, _, _) in enumerate(TERMS[1:], start=1):  # variance inflation factors: how much of a column the other columns explain
        others = np.delete(X, j, axis=1)
        coef = np.linalg.lstsq(others, X[:, j], rcond=None)[0]
        resid = X[:, j] - others @ coef
        vif.append(1 / (resid @ resid / np.sum((X[:, j] - X[:, j].mean()) ** 2)))
    rng = np.random.default_rng(SEED)
    draws = rng.multivariate_normal(beta, cov, size=N_DRAWS)
    j_hot = 1
    X1, X0 = X.copy(), X.copy()
    X1[:, j_hot], X0[:, j_hot] = 1, 0
    share1, share0 = expit(X1 @ draws.T).mean(axis=0) * 100, expit(X0 @ draws.T).mean(axis=0) * 100  # one average per simulated coefficient set
    point1, point0 = expit(X1 @ beta).mean() * 100, expit(X0 @ beta).mean() * 100
    diff = share1 - share0
    adjusted = pd.DataFrame([{"severe % if all in a hotspot": point1, "severe % if none in a hotspot": point0, "difference (percentage points)": point1 - point0,
                              "difference low": np.percentile(diff, 2.5), "difference high": np.percentile(diff, 97.5)}])
    fit = pd.DataFrame([{"rows": len(y), "different accidents": data["row"].nunique(), "severe accidents": int(y.sum()), "severe %": y.mean() * 100, "clusters (municipalities)": int(clusters.max() + 1),
                         "log-likelihood": ll, "McFadden R2": 1 - ll / null_ll, "AUC": auc(y, p), "AIC": -2 * ll + 2 * X.shape[1], "highest VIF": max(vif)}])

    # plain descriptive shares behind the model: severe % per category of every variable
    desc = []
    for variable, col in (("Hotspot", "hotspot"), ("Period", "period"), ("Group", "group"), ("Built-up area", "built_up"), ("Light condition", "light"), ("Road surface", "surface")):
        for value, part in data.groupby(col):
            desc.append({"variable": variable, "category": ("Hotspot square" if value == 1 else "Not a hotspot square") if col == "hotspot" else value, "rows": len(part), "severe": int(part["severe"].sum()), "severe %": part["severe"].mean() * 100})
    return table, fit, adjusted, pd.DataFrame(desc)


results = {n: run(n) for n in TOP_NS}
for name, number, fmt in (("severity_model", 0, "%.5f"), ("severity_fit", 1, "%.5f"), ("hotspot_adjusted", 2, "%.3f"), ("severity_descriptives", 3, "%.3f")):
    out = pd.concat([r[number].assign(top_n=n) for n, r in sorted(results.items())], ignore_index=True)  # top 20 first, then top 40
    out.to_csv(RESULTS / f"logit_{name}.csv", index=False, float_format=fmt)


for n, (table, fit, adjusted, _) in sorted(results.items()):
    print(f"\n=== Hotspot = top {n} ===\nOdds ratios (95% CI, cluster-robust by municipality):")
    print(table[["label", "odds ratio", "OR low", "OR high", "p value"]].round(3).to_string(index=False))
    print("\nFit:", fit.round(4).to_dict("records")[0])
    print("Hotspot adjusted prediction:", adjusted.round(2).to_dict("records")[0])
print("\nSelection:\n" + flow.to_string(index=False))
