"""
Step 20 - Step 5 of the analysis: logistic models of accident severity (Severe = 1) with cluster-robust standard errors.

Models (decisions #115-#131, see beslissingslogboek.md):
  a. baseline: all accidents        b. cyclists       c. pedestrians       d. motorcyclists       e. mopeds
  For each: the specification you asked for ("full": with collision type) and a variant WITHOUT collision type (#119), because collision type
  is almost determined by the road users.

Outcome:       Severe = 1 for accident classes 1, 2 and 3 (fatal, fatally injured, seriously injured); 0 for class 4 (#116).
Explanatory:   road-user group, year, month, region, road type, intersection, lighting, weather, road surface, collision type.
  - Baseline road-user group = one 0/1 variable per group involved (road user 1 OR 2, #33/#117); passenger car is the omitted one.
    "Single road user" is its own 0/1 variable (only in the variant without collision type: with collision type it is perfectly
    collinear with the collision types "against an obstacle" and "single road user, no obstacle", so it is dropped there).
  - In the group models "road-user group" is the COUNTERPART in the accident (#120).
  - Unknown stays a category (#118); year and month are categories (#124); small categories are merged (#125, #129); references as in #128.

Clustering (#121, #122): an accident is the unit, not a participant, and accidents in the same municipality are correlated. The coefficients are the
ordinary logistic ones; standard errors are cluster-robust by municipality (581 clusters). The estimator is written here (numpy) and checked against
scikit-learn and a slow hand-written loop. Intraclass correlations and the growth of the standard errors are reported.

Interactions (#123): pair terms between the two groups involved (pairs with at least 500 accidents; "Unknown" pairs excluded), tested jointly with
a Wald test, and a check whether the ORDER (road user 1 vs 2) matters for the main pairs (at least 2,000 accidents).

Comparison (#126, #130, #131): adjusted odds ratios, average adjusted predicted probabilities (simulation with 1,000 draws), fit quality and four scenarios.

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/20_severity_logit_models.py OPENDATA_MAP_2017-2024_en_flagged.csv.gz reports
"""
import math
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to a file, not to a window
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import chi2, norm, rankdata
from sklearn.linear_model import LogisticRegression

accidents_file = sys.argv[1]  # the flagged English dataset from step 05
output_dir = Path(sys.argv[2])  # the reports/ folder
output_dir.mkdir(exist_ok=True)
rng = np.random.default_rng(2026)
t_start = time.time()

# =====================================================================
# 1. Data
# =====================================================================
header = pd.read_csv(accidents_file, nrows=0).columns
df = pd.read_csv(accidents_file, dtype={c: str for c in header if c.endswith("_code")})
N_ALL = len(df)
y_all = df["accident_class_code"].isin(["1", "2", "3"]).to_numpy().astype(float)  # Severe = 1 (#116)
assert int(y_all.sum()) == 28532, "unexpected number of severe accidents"
cluster_all = pd.factorize(df["municipality_nis_code"])[0]  # municipality number 0..580 (#121)
df["month_label"] = pd.to_datetime(df["collision_month"], format="%m").dt.strftime("%b")
df["year_label"] = df["collision_year"].astype(str)

CODE_NAME = dict(zip(df["road_user_type1_code"], df["road_user_type1"]))  # code -> group name
GROUP_NAMES = {c: n for c, n in CODE_NAME.items()}
SINGLE = df["road_user_type2_code"].isin(["10", "11"]).to_numpy()  # "single road user" in position 2 (not a road user)
t1, t2 = df["road_user_type1_code"].to_numpy(), df["road_user_type2_code"].to_numpy()


def involved(code):
    """True where the group is road user 1 OR road user 2 (once per accident, #33)."""
    return (t1 == code) | (t2 == code)


IND = {name: involved(code) for code, name in GROUP_NAMES.items()}  # 0/1 per group involved
GROUP_ORDER = ["Passenger car", "Van / light truck", "Truck", "Bus", "Motorcycle", "Moped", "Bicycle", "Pedestrian", "Other road user", "Unknown"]
CATEGORICAL = {  # variable -> (column, reference category #128)
    "Region": ("region", "Flemish Region"), "Road type": ("road_type", "Municipal road"), "Intersection": ("crossway", "Not at intersection"),
    "Lighting": ("light_condition", "Daylight"), "Weather": ("weather", "Normal"), "Road surface": ("road_condition", "Dry"),
    "Collision type": ("collision_type", "Between 2 drivers: Rear-end collision"), "Year": ("year_label", "2017"), "Month": ("month_label", "Jan")}
OTHER = "Other / combined"
MERGE_LOG = []  # every merge, for the output (#125, #129)

# Step 1 of the merging rule (#125): weather, road surface and lighting categories with fewer than 100 accidents (on ALL accidents) become "Other / combined".
GLOBAL_MAP = {}
for var in ("Weather", "Road surface", "Lighting"):
    col, ref = CATEGORICAL[var]
    counts = df[col].value_counts()
    small = [c for c, n in counts.items() if n < 100 and not c.startswith("Unknown")]
    GLOBAL_MAP[var] = {c: OTHER for c in small}
    for c in small:
        MERGE_LOG.append(("all accidents", var, c, int(counts[c]), "fewer than 100 accidents on all accidents -> " + OTHER))
df_cat = {}
for var, (col, ref) in CATEGORICAL.items():
    s = df[col].astype(str)
    df_cat[var] = s.replace(GLOBAL_MAP.get(var, {}))


# =====================================================================
# 2. The estimator (written here, #122)
# =====================================================================
def _loglik(X, y, beta):
    eta = X @ beta
    return float(np.sum(y * eta - np.logaddexp(0, eta)))  # a numerically safe form of the logistic log-likelihood


def fit_logit(X, y, max_iter=100, tol=1e-9):
    """Logistic regression by Newton-Raphson (iteratively reweighted least squares) with step-halving: if a step does not raise the log-likelihood it is halved.
    Returns coefficients, the inverse Hessian, probabilities and the log-likelihood."""
    beta = np.zeros(X.shape[1])
    beta[0] = math.log(y.mean() / (1 - y.mean()))  # start at the overall log-odds
    current = _loglik(X, y, beta)
    for it in range(max_iter):
        p = expit(X @ beta)
        w = p * (1 - p)
        gradient = X.T @ (y - p)
        hessian = (X * w[:, None]).T @ X
        step = np.linalg.solve(hessian, gradient)
        size = 1.0
        while size > 1e-6:
            candidate = beta + size * step
            new = _loglik(X, y, candidate)
            if new >= current - 1e-12:
                break
            size /= 2  # halve the step
        beta, current = candidate, new
        if np.max(np.abs(size * step)) < tol:
            break
    else:
        raise RuntimeError("logistic fit did not converge")
    p = expit(X @ beta)
    w = p * (1 - p)
    hessian = (X * w[:, None]).T @ X
    return beta, np.linalg.inv(hessian), p, current


def cluster_robust_cov(X, y, p, bread, clusters):
    """Cluster-robust ("sandwich") covariance: bread x (sum over clusters of score_c score_c') x bread, with the usual small-sample factor
    G/(G-1) * (N-1)/(N-k). The score of an accident is x_i (y_i - p_i); scores are added up within each cluster first."""
    scores = X * (y - p)[:, None]
    n_clusters = clusters.max() + 1
    cluster_scores = np.zeros((n_clusters, X.shape[1]))
    np.add.at(cluster_scores, clusters, scores)
    meat = cluster_scores.T @ cluster_scores
    n, k = X.shape
    factor = n_clusters / (n_clusters - 1) * (n - 1) / (n - k)
    return factor * bread @ meat @ bread


def cluster_robust_cov_slow(X, y, p, bread, clusters):
    """The same thing with plain loops, only used to check the fast version on a small example."""
    n, k = X.shape
    meat = np.zeros((k, k))
    for g in np.unique(clusters):
        total = np.zeros(k)
        for i in np.where(clusters == g)[0]:
            total += X[i] * (y[i] - p[i])
        meat += np.outer(total, total)
    n_clusters = len(np.unique(clusters))
    return n_clusters / (n_clusters - 1) * (n - 1) / (n - k) * bread @ meat @ bread


def auc(y, score):
    """Area under the ROC curve = the chance that a random severe accident gets a higher predicted probability than a random non-severe one (rank formula)."""
    ranks = rankdata(score)
    n1 = y.sum()
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1)))


def icc(values, clusters):
    """Intraclass correlation (one-way ANOVA estimator for unequal cluster sizes): how much of the variation lies between clusters."""
    n = len(values)
    g = clusters.max() + 1
    sizes = np.bincount(clusters, minlength=g).astype(float)
    sums = np.bincount(clusters, weights=values, minlength=g)
    grand = values.mean()
    ss_between = np.sum(sums ** 2 / sizes) - n * grand ** 2
    ss_within = np.sum(values ** 2) - np.sum(sums ** 2 / sizes)
    ms_between, ms_within = ss_between / (g - 1), ss_within / (n - g)
    n0 = (n - np.sum(sizes ** 2) / n) / (g - 1)
    return float((ms_between - ms_within) / (ms_between + (n0 - 1) * ms_within))


# --- checks of the estimator on a small example (before it is used) ---
check_rng = np.random.default_rng(1)
Xs = np.c_[np.ones(300), check_rng.normal(size=(300, 3))]
cs = check_rng.integers(0, 12, 300)
ys = (check_rng.random(300) < expit(Xs @ np.array([-1.0, 0.8, -0.5, 0.3]) + 0.4 * (cs % 3 - 1))).astype(float)
b_s, bread_s, p_s, ll_s = fit_logit(Xs, ys)
assert np.allclose(cluster_robust_cov(Xs, ys, p_s, bread_s, cs), cluster_robust_cov_slow(Xs, ys, p_s, bread_s, cs), rtol=1e-10, atol=1e-12), "robust variance differs from the loop version"
sk = LogisticRegression(C=np.inf, fit_intercept=False, solver="newton-cholesky", tol=1e-12, max_iter=200).fit(Xs, ys)
assert np.allclose(b_s, sk.coef_[0], atol=1e-6), "coefficients differ from scikit-learn"
print("Estimator checks passed: coefficients equal scikit-learn's, and the fast cluster-robust variance equals a slow loop version.")


# =====================================================================
# 3. Building the design matrix of a model
# =====================================================================
def merge_for_model(series, y, ref, var, model_name):
    """Step 2 of the merging rule (#129): within this model, a category with fewer than 30 accidents, or without severe or without non-severe accidents,
    becomes "Other / combined", or joins the reference if that bucket would still be under 30. The reference falls back to the most common category if it is under 30."""
    s = series.copy()
    stats = pd.DataFrame({"n": s.groupby(s).size(), "events": pd.Series(y, index=s.index).groupby(s).sum()})
    stats["nonevents"] = stats["n"] - stats["events"]
    if ref not in stats.index or stats.loc[ref, "n"] < 30:
        new_ref = stats["n"].idxmax()
        MERGE_LOG.append((model_name, var, ref, int(stats["n"].get(ref, 0)), f"reference has fewer than 30 accidents; the most common category '{new_ref}' is the reference"))
        ref = new_ref
    bad = [c for c in stats.index if c != ref and (stats.loc[c, "n"] < 30 or stats.loc[c, "events"] == 0 or stats.loc[c, "nonevents"] == 0)]
    if bad:
        pool = stats.loc[bad, "n"].sum() + (stats.loc[OTHER, "n"] if (OTHER in stats.index and OTHER not in bad) else 0)
        target = OTHER if pool >= 30 else ref
        for c in bad:
            MERGE_LOG.append((model_name, var, c, int(stats.loc[c, "n"]), f"under 30 accidents or no severe/non-severe accident -> {target}"))
        s = s.replace({c: target for c in bad})
    return s, ref


class Design:
    """The design matrix of one model, with the information needed later (term names, counts, variable blocks for predictions, mappings of merged categories)."""

    def __init__(self, mask, name, spec, extra_cols=None, counterpart=None, drop_single=False, skip_terms=()):
        self.mask, self.name, self.spec = mask, name, spec
        self.skip_terms = set(skip_terms)
        y = y_all[mask]
        index = np.where(mask)[0]
        cols, names, info = [np.ones(mask.sum())], ["Intercept"], []
        self.blocks = {}   # variable -> {"ref": label, "cats": [labels], "cols": {label: column index}, "current": per-accident category label}
        variables = ["Region", "Road type", "Intersection", "Lighting", "Weather", "Road surface", "Year", "Month"] + (["Collision type"] if spec == "full" else [])
        data = {v: pd.Series(df_cat[v].to_numpy()[mask]) for v in variables}
        if counterpart is not None:
            data["Counterpart"] = pd.Series(counterpart[mask])
            variables = ["Counterpart"] + variables
        refs = {v: CATEGORICAL[v][1] for v in CATEGORICAL}
        refs["Counterpart"] = "Passenger car"
        self.maps = {}
        for var in variables:
            s, ref = merge_for_model(data[var], y, refs[var], var, name)
            self.maps[var] = dict(zip(data[var], s))  # original label -> merged label (to place scenarios)
            cats = sorted([c for c in s.unique() if c != ref], key=lambda c: (c == OTHER, c))
            block = {"ref": ref, "cats": cats, "cols": {}, "current": s.to_numpy()}
            for c in cats:
                if var == "Counterpart" and spec == "full" and c == "None (single road user)":
                    # With collision type in the model this 0/1 variable equals the sum of the three single-road-user collision types (perfectly collinear, #119):
                    # it is left out; the collision types carry its effect and the other counterpart odds ratios are unchanged.
                    info.append((f"{var}: {c} (absorbed by collision type)", var, c, int((s == c).sum()), int(y[(s == c).to_numpy()].sum()), True))
                    continue
                if f"{var}: {c}" in self.skip_terms:  # nearly identical to a road-user term (see build_design): left out, its accidents join the reference
                    info.append((f"{var}: {c} (left out: nearly identical to a road-user term)", var, c, int((s == c).sum()), int(y[(s == c).to_numpy()].sum()), True))
                    continue
                block["cols"][c] = len(cols)
                cols.append((s.to_numpy() == c).astype(float))
                names.append(f"{var}: {c}")
                info.append((f"{var}: {c}", var, c, int((s == c).sum()), int(y[(s == c).to_numpy()].sum()), False))
            info.append((f"{var}: {ref} (reference)", var, ref, int((s == ref).sum()), int(y[(s == ref).to_numpy()].sum()), True))
            self.blocks[var] = block
        if counterpart is None:  # baseline: one 0/1 variable per group involved (#117); passenger car omitted
            for g in GROUP_ORDER[1:]:
                cols.append(IND[g][mask].astype(float)); names.append(f"Group involved: {g}")
                info.append((f"Group involved: {g}", "Group involved", g, int(IND[g][mask].sum()), int(y[IND[g][mask]].sum()), False))
            if spec != "full" and not drop_single:  # with collision type this variable is perfectly collinear with three collision types (#119)
                cols.append(SINGLE[mask].astype(float)); names.append("Group involved: Single road user (no second party)")
                info.append((names[-1], "Group involved", "Single road user (no second party)", int(SINGLE[mask].sum()), int(y[SINGLE[mask]].sum()), False))
        for label, column in (extra_cols or {}).items():
            cols.append(column[mask].astype(float)); names.append(label)
            info.append((label, "Interaction", label, int(column[mask].sum()), int(y[column[mask] > 0].sum()), False))
        self.X = np.column_stack(cols)
        self.names, self.y, self.clusters = names, y, cluster_all[mask]
        self.clusters = pd.factorize(self.clusters)[0]
        self.info = pd.DataFrame(info, columns=["term", "variable", "category", "accidents", "events", "is_reference"])
        # a full-rank design is required
        gram = self.X.T @ self.X
        eig = np.linalg.eigvalsh(gram)
        self.min_eig_ratio = eig[0] / eig[-1]
        assert self.min_eig_ratio > 1e-10, f"{name} ({spec}): the design matrix is not full rank (collinear columns)"


def build_design(*args, **kwargs):
    """Build a design; if two terms are nearly identical (correlation above 0.99) the model cannot tell them apart (their coefficients run off in opposite
    directions), so the COLLISION-TYPE term is left out and the road-user term stays; the design is then built again. Every case is reported."""
    design = Design(*args, **kwargs)
    corr = np.corrcoef(design.X[:, 1:], rowvar=False)
    names = design.names[1:]
    skip = set()
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if abs(corr[i, j]) > 0.99:
                pair = [names[i], names[j]]
                drop = [n for n in pair if n.startswith("Collision type:")]
                assert drop and len(drop) == 1, f"{design.name} ({design.spec}): two non-collision terms are nearly identical: {pair}"
                skip.add(drop[0])
                MERGE_LOG.append((design.name, "Collision type", drop[0].split(": ", 1)[1], int(design.X[:, 1:][:, names.index(drop[0])].sum()),
                                  f"correlation {abs(corr[i, j]):.3f} with '{[n for n in pair if n != drop[0]][0]}': left out, the road-user term stays"))
    if skip:
        kwargs = dict(kwargs)
        kwargs["skip_terms"] = set(kwargs.get("skip_terms", ())) | skip
        design = Design(*args, **kwargs)
    return design


def estimate(design):
    """Fit a design and attach ordinary and cluster-robust standard errors, fit statistics and residual clustering."""
    X, y = design.X, design.y
    try:
        beta, bread, p, loglik = fit_logit(X, y)
    except np.linalg.LinAlgError:
        constant = [n for n, c in zip(design.names, X.T) if c.std() == 0 and n != "Intercept"]
        raise RuntimeError(f"{design.name} ({design.spec}): singular matrix; constant columns: {constant}; smallest eigenvalue ratio {design.min_eig_ratio:.2e}")
    cov_robust = cluster_robust_cov(X, y, p, bread, design.clusters)
    se_ordinary, se_robust = np.sqrt(np.diag(bread)), np.sqrt(np.diag(cov_robust))
    ll0 = float(len(y) * (y.mean() * math.log(y.mean()) + (1 - y.mean()) * math.log(1 - y.mean())))
    design.beta, design.cov, design.p, design.loglik = beta, cov_robust, p, loglik
    design.se_robust, design.se_ordinary = se_robust, se_ordinary
    assert abs(p.mean() - y.mean()) < 1e-8, "mean predicted probability differs from the observed rate"  # holds for a logistic model with an intercept
    design.fit = {"model": design.name, "spec": design.spec, "accidents": len(y), "events": int(y.sum()), "event_rate_pct": y.mean() * 100, "parameters": X.shape[1], "clusters": int(design.clusters.max() + 1),
                  "log_likelihood": loglik, "mcfadden_r2": 1 - loglik / ll0, "aic": 2 * X.shape[1] - 2 * loglik, "auc": auc(y, p),
                  "icc_outcome": icc(y, design.clusters), "icc_residual": icc(y - p, design.clusters),
                  "median_se_ratio_robust_to_ordinary": float(np.median(se_robust[1:] / se_ordinary[1:])), "max_se_ratio": float(np.max(se_robust[1:] / se_ordinary[1:]))}
    return design


def coefficient_table(design):
    z = design.beta / design.se_robust
    out = pd.DataFrame({"model": design.name, "spec": design.spec, "term": design.names, "coefficient": design.beta, "se_robust": design.se_robust, "se_ordinary": design.se_ordinary,
                        "odds_ratio": np.exp(design.beta), "or_ci_low": np.exp(design.beta - 1.96 * design.se_robust), "or_ci_high": np.exp(design.beta + 1.96 * design.se_robust),
                        "z": z, "p_value": 2 * norm.sf(np.abs(z))})
    out = out.merge(design.info[["term", "variable", "category", "accidents", "events"]], on="term", how="left")
    return out[out["term"] != "Intercept"]


def vif_table(design):
    """Variance inflation factor per term: how much the variance of a coefficient grows because the term overlaps with the others (above 10 = strong overlap)."""
    corr = np.corrcoef(design.X[:, 1:], rowvar=False)
    vif = np.diag(np.linalg.inv(corr))
    return pd.DataFrame({"model": design.name, "spec": design.spec, "term": design.names[1:], "vif": vif})


# =====================================================================
# 4. The five models, each with and without collision type
# =====================================================================
FOCAL = {"Cyclists": "Bicycle", "Pedestrians": "Pedestrian", "Motorcyclists": "Motorcycle", "Mopeds": "Moped"}
MODEL_LABELS = ["Baseline", "Cyclists", "Pedestrians", "Motorcyclists", "Mopeds"]


def counterpart_of(focal):
    """The other party in the accident, for each accident (#120): another group, 'none' for a single-road-user accident, or 'same group' if both sides are the focal group."""
    code = [c for c, n in GROUP_NAMES.items() if n == focal][0]
    other = np.where(t1 == code, t2, t1)  # the code of the other side (if road user 1 is the focal group, then road user 2, otherwise road user 1)
    label = np.array([GROUP_NAMES.get(c, "None (single road user)") if c not in ("10", "11") else "None (single road user)" for c in other], dtype=object)
    label[(t1 == code) & (t2 == code)] = f"Same group ({focal})"
    return label


models = {}  # (label, spec) -> Design
all_mask = np.ones(N_ALL, bool)
for spec in ("full", "no_collision"):
    models[("Baseline", spec)] = estimate(build_design(all_mask, "Baseline", spec))
    for label, focal in FOCAL.items():
        cp = counterpart_of(focal)
        models[(label, spec)] = estimate(build_design(IND[focal], label, spec, counterpart=cp))
        if spec == "full":  # with collision type the counterpart 'None (single road user)' is collinear with the single-user collision types: handled by the rank check below
            pass
print(f"Estimated {len(models)} models in {time.time() - t_start:.0f} s.\n")

# =====================================================================
# 5. Checks of the fitted models and the result tables
# =====================================================================
for key in (("Baseline", "full"), ("Mopeds", "full")):  # an independent fit with scikit-learn must give the same coefficients
    d = models[key]
    sk = LogisticRegression(C=np.inf, fit_intercept=False, solver="newton-cholesky", tol=1e-12, max_iter=300).fit(d.X, d.y)
    assert np.allclose(d.beta, sk.coef_[0], atol=1e-4), f"{key}: coefficients differ from scikit-learn (largest difference {np.abs(d.beta - sk.coef_[0]).max():.2e})"
print("Model check passed: the baseline and the moped model give the same coefficients as scikit-learn.")
assert models[("Baseline", "full")].fit["events"] == 28532 and models[("Cyclists", "full")].fit["events"] == 7852, "event counts differ from the earlier look"

coefficients = pd.concat([coefficient_table(d) for d in models.values()], ignore_index=True)
fit_table = pd.DataFrame([d.fit for d in models.values()])
vifs = pd.concat([vif_table(d) for d in models.values()], ignore_index=True)
merge_log = pd.DataFrame(MERGE_LOG, columns=["model", "variable", "category", "accidents", "what_happened"]).drop_duplicates()
coefficients.to_csv(output_dir / "severity_logit_coefficients.csv", index=False, float_format="%.5f")
fit_table.to_csv(output_dir / "severity_logit_fit.csv", index=False, float_format="%.5f")
fit_table[["model", "spec", "accidents", "clusters", "icc_outcome", "icc_residual", "median_se_ratio_robust_to_ordinary", "max_se_ratio"]].to_csv(output_dir / "severity_logit_clustering.csv", index=False, float_format="%.5f")
vifs.to_csv(output_dir / "severity_logit_vif.csv", index=False, float_format="%.3f")
merge_log.to_csv(output_dir / "severity_logit_category_merges.csv", index=False)

main = {label: models[(label, "full")] for label in MODEL_LABELS}  # the models as specified (with collision type)

print("\n=== FIT AND CLUSTERING (models as specified, with collision type) ===")
show = fit_table[fit_table["spec"] == "full"].set_index("model")[["accidents", "events", "event_rate_pct", "parameters", "mcfadden_r2", "aic", "auc", "icc_outcome", "icc_residual", "median_se_ratio_robust_to_ordinary"]]
print(show.to_string(formatters={"accidents": "{:,.0f}".format, "events": "{:,.0f}".format, "event_rate_pct": "{:.1f}%".format, "mcfadden_r2": "{:.3f}".format, "aic": "{:,.0f}".format, "auc": "{:.3f}".format,
                                 "icc_outcome": "{:.3f}".format, "icc_residual": "{:.3f}".format, "median_se_ratio_robust_to_ordinary": "{:.2f}".format}))
print("(icc_outcome = share of the variation in 'severe' that lies between municipalities; icc_residual = what remains after the covariates; "
      "ratio = cluster-robust standard error / ordinary standard error)")
print("\nFit of the variant WITHOUT collision type:")
print(fit_table[fit_table["spec"] == "no_collision"].set_index("model")[["mcfadden_r2", "aic", "auc"]].to_string(formatters={"mcfadden_r2": "{:.3f}".format, "aic": "{:,.0f}".format, "auc": "{:.3f}".format}))

# --- collinearity ---
print("\n=== OVERLAP BETWEEN VARIABLES (variance inflation factors above 10) ===")
for (label, spec), d in models.items():
    v = vifs[(vifs["model"] == label) & (vifs["spec"] == spec)].sort_values("vif", ascending=False)
    high = v[v["vif"] > 10]
    print(f"{label:14s} {spec:13s} highest VIF {v['vif'].max():6.1f}  terms above 10: {len(high)}" + ("  -> " + "; ".join(f"{t} ({x:.0f})" for t, x in zip(high['term'].head(3), high['vif'].head(3))) if len(high) else ""))
print("\nMerges and left-out terms in the models (first 25 lines; all in severity_logit_category_merges.csv):")
print(merge_log.head(25).to_string(index=False, max_colwidth=90))

# --- the road-user odds ratios with and without collision type ---
ru = coefficients[coefficients["variable"].isin(["Group involved", "Counterpart"])]
ru_wide = ru.pivot_table(index=["model", "term"], columns="spec", values="odds_ratio")
ru_wide["change_pct"] = (ru_wide["full"] / ru_wide["no_collision"] - 1) * 100
ru_wide = ru_wide.reset_index()
ru_wide.to_csv(output_dir / "severity_logit_roaduser_with_without_collision.csv", index=False, float_format="%.4f")
print("\n=== ROAD-USER ODDS RATIOS WITH vs WITHOUT COLLISION TYPE (baseline) ===")
print(ru_wide[ru_wide["model"] == "Baseline"].to_string(index=False, formatters={"full": "{:.2f}".format, "no_collision": "{:.2f}".format, "change_pct": "{:+.0f}%".format}))

# =====================================================================
# 6. Interactions between the road users in the same accident (#123)
# =====================================================================
REAL = [g for g in GROUP_ORDER if g != "Unknown"]
pairs = []
for i, g1 in enumerate(REAL):
    for g2 in REAL[i + 1:]:
        both = IND[g1] & IND[g2]
        if both.sum() >= 500:
            pairs.append((g1, g2, int(both.sum())))
MAIN_PAIRS = [p for p in pairs if p[2] >= 2000]
pair_cols = {f"Pair: {g1} + {g2}": (IND[g1] & IND[g2]) for g1, g2, _ in pairs}
CODE_OF = {n: c for c, n in GROUP_NAMES.items()}
order_cols = {f"Order: {g1} is road user 1 ({g1} + {g2})": (IND[g1] & IND[g2] & (t1 == CODE_OF[g1])) for g1, g2, _ in MAIN_PAIRS}
print(f"\n=== INTERACTIONS: {len(pairs)} pairs of groups with at least 500 accidents; {len(MAIN_PAIRS)} main pairs (2,000+) for the order check ===")

inter_models, wald_rows, pair_rows = {}, [], []
for spec in ("full", "no_collision"):
    base = models[("Baseline", spec)]
    m_pairs = estimate(build_design(all_mask, "Baseline + pairs", spec, extra_cols=pair_cols))
    m_order = estimate(build_design(all_mask, "Baseline + pairs + order", spec, extra_cols={**pair_cols, **order_cols}))
    inter_models[spec] = (m_pairs, m_order)
    for label, model, terms in (("pair interactions (joint)", m_pairs, list(pair_cols)), ("order of road user 1 / 2 (joint)", m_order, list(order_cols))):
        idx = [model.names.index(t) for t in terms if t in model.names]
        b, V = model.beta[idx], model.cov[np.ix_(idx, idx)]
        w = float(b @ np.linalg.solve(V, b))
        wald_rows.append({"spec": spec, "test": label, "terms": len(idx), "wald_chi2": w, "p_value": float(chi2.sf(w, len(idx))), "aic_baseline": base.fit["aic"], "aic_with_terms": model.fit["aic"]})
    # Pair-specific odds ratios (versus a car-only accident, using the cluster-robust variance):
    #   "additive" = what the BASELINE model predicts for the pair: the effects of the two groups just added up (passenger car has effect 0);
    #   "with the pair's own effect" = the two group effects plus the pair term of the model with pair interactions;
    #   "interaction term" = the pair term itself, i.e. how much the pair differs from the additive pattern (a ratio of odds ratios).
    for g1, g2, n in pairs:
        d = m_pairs
        term = f"Pair: {g1} + {g2}"
        c_add = np.zeros(len(base.names)); c_full = np.zeros(len(d.names))
        for g in (g1, g2):
            name = f"Group involved: {g}"
            if name in base.names:
                c_add[base.names.index(name)] = 1
            if name in d.names:
                c_full[d.names.index(name)] = 1
        c_full[d.names.index(term)] = 1
        sub = IND[g1] & IND[g2]
        for label, c, model in (("additive (baseline model)", c_add, base), ("with the pair's own effect", c_full, d)):
            est, se = float(c @ model.beta), float(math.sqrt(c @ model.cov @ c))
            pair_rows.append({"spec": spec, "pair": f"{g1} + {g2}", "accidents": n, "severe_pct": y_all[sub].mean() * 100, "version": label, "odds_ratio_vs_car_only": math.exp(est),
                              "ci_low": math.exp(est - 1.96 * se), "ci_high": math.exp(est + 1.96 * se)})
        j = d.names.index(term)
        pair_rows.append({"spec": spec, "pair": f"{g1} + {g2}", "accidents": n, "severe_pct": y_all[sub].mean() * 100, "version": "interaction term (ratio of odds ratios)", "odds_ratio_vs_car_only": math.exp(d.beta[j]),
                          "ci_low": math.exp(d.beta[j] - 1.96 * d.se_robust[j]), "ci_high": math.exp(d.beta[j] + 1.96 * d.se_robust[j])})
wald = pd.DataFrame(wald_rows)
pair_table = pd.DataFrame(pair_rows)
wald.to_csv(output_dir / "severity_logit_interactions_tests.csv", index=False, float_format="%.5g")
pair_table.to_csv(output_dir / "severity_logit_interactions_pairs.csv", index=False, float_format="%.4f")
pd.concat([coefficient_table(m) for spec_models in inter_models.values() for m in spec_models], ignore_index=True).to_csv(output_dir / "severity_logit_interactions_coefficients.csv", index=False, float_format="%.5f")
print("\nJoint tests (Wald chi-square with cluster-robust variance):")
print(wald.to_string(index=False, formatters={"wald_chi2": "{:.1f}".format, "p_value": "{:.2g}".format, "aic_baseline": "{:,.0f}".format, "aic_with_terms": "{:,.0f}".format}))
print("\nPair-specific odds ratios vs a car-only accident, baseline WITH collision type:")
pt = pair_table[(pair_table["spec"] == "full")].pivot_table(index=["pair", "accidents", "severe_pct"], columns="version", values="odds_ratio_vs_car_only").reset_index()
print(pt.sort_values("accidents", ascending=False).to_string(index=False, formatters={"severe_pct": "{:.1f}%".format, "accidents": "{:,.0f}".format, **{c: "{:.2f}".format for c in pt.columns[3:]}}))
print("\nOrder terms (is the pair different when road user 1 is the first group of the pair?), baseline with collision type:")
o = coefficient_table(inter_models["full"][1]); o = o[o["term"].str.startswith("Order:")]
print(o[["term", "accidents", "odds_ratio", "or_ci_low", "or_ci_high", "p_value"]].to_string(index=False, formatters={"accidents": "{:,.0f}".format, "odds_ratio": "{:.2f}".format, "or_ci_low": "{:.2f}".format, "or_ci_high": "{:.2f}".format, "p_value": "{:.2g}".format}))

# =====================================================================
# 7. Predicted probabilities (average adjusted) and scenarios (#126, #130, #131)
# =====================================================================
N_DRAWS = 1000


def draws_of(design):
    """1,000 coefficient vectors drawn from the cluster-robust sampling distribution (row 0 is the estimate itself)."""
    w, U = np.linalg.eigh(design.cov)
    root = U * np.sqrt(np.clip(w, 0, None))
    draws = design.beta + rng.standard_normal((N_DRAWS, len(design.beta))) @ root.T
    return np.vstack([design.beta, draws])


KEY_VARIABLES = ["Region", "Road type", "Intersection", "Lighting", "Year", "Month"]
t_pred = time.time()
pred_rows, draws_store = [], {}
for label, d in main.items():
    B = draws_of(d)
    draws_store[label] = B
    plan = []
    for var in KEY_VARIABLES:
        block = d.blocks[var]
        cats = [block["ref"]] + block["cats"]
        current = np.array([cats.index(c) for c in block["current"]])
        columns = [None] + [block["cols"].get(c) for c in block["cats"]]  # None = the reference (coefficient 0)
        plan.append((var, cats, current, columns))
    results = {(var, c): np.empty(len(B)) for var, cats, _, _ in plan for c in cats}
    for r in range(len(B)):
        eta = d.X @ B[r]
        for var, cats, current, columns in plan:
            coef = np.array([0.0 if col is None else B[r][col] for col in columns])
            eta_without = eta - coef[current]
            for k, c in enumerate(cats):
                results[(var, c)][r] = expit(eta_without + coef[k]).mean()
    for (var, c), vals in results.items():
        pred_rows.append({"model": label, "variable": var, "category": c, "accidents_in_category": int((np.array(plan[KEY_VARIABLES.index(var)][1])[plan[KEY_VARIABLES.index(var)][2]] == c).sum()),
                          "predicted_pct": vals[0] * 100, "ci_low_pct": np.percentile(vals[1:], 2.5) * 100, "ci_high_pct": np.percentile(vals[1:], 97.5) * 100,
                          "observed_pct": d.y[np.array(plan[KEY_VARIABLES.index(var)][1])[plan[KEY_VARIABLES.index(var)][2]] == c].mean() * 100 if (np.array(plan[KEY_VARIABLES.index(var)][1])[plan[KEY_VARIABLES.index(var)][2]] == c).any() else np.nan})
    print(f"  predicted probabilities for {label}: {time.time() - t_pred:.0f} s")
predicted = pd.DataFrame(pred_rows)
predicted.to_csv(output_dir / "severity_logit_predicted_by_category.csv", index=False, float_format="%.4f")

SCENARIOS = {  # decision #131; all in 2024
    "A: daytime urban": {"Region": "Flemish Region", "Road type": "Municipal road", "Intersection": "Not at intersection", "Lighting": "Daylight", "Weather": "Normal", "Road surface": "Dry", "Month": "Jun"},
    "B: night, no public lighting": {"Region": "Walloon Region", "Road type": "Regional road", "Intersection": "Not at intersection", "Lighting": "Night, no public lighting", "Weather": "Normal", "Road surface": "Dry", "Month": "Oct"},
    "C: wet junction": {"Region": "Flemish Region", "Road type": "Regional road", "Intersection": "At intersection", "Lighting": "Daylight", "Weather": "Rain", "Road surface": "Wet, puddles", "Month": "Nov"},
    "D: Brussels junction": {"Region": "Brussels-Capital Region", "Road type": "Municipal road", "Intersection": "At intersection", "Lighting": "Daylight", "Weather": "Normal", "Road surface": "Dry", "Month": "Jun"},
}


def scenario_vector(d, spec, group_term=None):
    """The design-matrix row of a scenario in model d (None if a category of the scenario does not exist in that model's sample)."""
    x = np.zeros(len(d.names)); x[0] = 1
    for var, cat in {**spec, "Year": "2024"}.items():
        block = d.blocks[var]
        merged = d.maps[var].get(cat)
        if merged is None:
            return None
        if merged != block["ref"]:
            if merged not in block["cols"]:
                return None
            x[block["cols"][merged]] = 1
    if "Collision type" in d.blocks:  # the most common collision type of the model's sample
        block = d.blocks["Collision type"]
        common = pd.Series(block["current"]).value_counts().idxmax()
        if common != block["ref"] and common in block["cols"]:
            x[block["cols"][common]] = 1
    if group_term is not None:
        if group_term not in d.names:
            return None
        x[d.names.index(group_term)] = 1
    return x


scenario_rows = []
for label, d in main.items():
    B = draws_store[label]
    variants = [("(counterpart: passenger car)", None)] if label != "Baseline" else [("car-only accident", None)] + [(f"{g} against a car", f"Group involved: {g}") for g in ("Bicycle", "Pedestrian", "Motorcycle", "Moped")]
    for variant, term in variants:
        for sname, spec in SCENARIOS.items():
            x = scenario_vector(d, spec, term)
            if x is None:
                scenario_rows.append({"model": label, "evaluated_as": variant, "scenario": sname, "predicted_pct": np.nan, "ci_low_pct": np.nan, "ci_high_pct": np.nan})
                continue
            p = expit(B @ x)
            scenario_rows.append({"model": label, "evaluated_as": variant, "scenario": sname, "predicted_pct": p[0] * 100, "ci_low_pct": np.percentile(p[1:], 2.5) * 100, "ci_high_pct": np.percentile(p[1:], 97.5) * 100})
scenarios = pd.DataFrame(scenario_rows)
scenarios.to_csv(output_dir / "severity_logit_scenarios.csv", index=False, float_format="%.4f")

# calibration: predicted against observed by decile of the predicted probability
cal_rows = []
for label, d in main.items():
    order = np.argsort(d.p)
    for k, part in enumerate(np.array_split(order, 10), start=1):
        cal_rows.append({"model": label, "decile": k, "accidents": len(part), "mean_predicted_pct": d.p[part].mean() * 100, "observed_pct": d.y[part].mean() * 100})
calibration = pd.DataFrame(cal_rows)
calibration.to_csv(output_dir / "severity_logit_calibration.csv", index=False, float_format="%.4f")
print(f"Predicted probabilities and scenarios done in {time.time() - t_pred:.0f} s.\n")

# =====================================================================
# 8. Printing the comparison
# =====================================================================
def or_text(label, term, spec="full"):
    r = coefficients[(coefficients["model"] == label) & (coefficients["spec"] == spec) & (coefficients["term"] == term)]
    if r.empty:
        return "-"
    r = r.iloc[0]
    star = "*" if r["p_value"] < 0.05 else " "
    return f"{r['odds_ratio']:.2f}{star} ({r['or_ci_low']:.2f}-{r['or_ci_high']:.2f})"


SELECTED = ["Region: Brussels-Capital Region", "Region: Walloon Region", "Road type: Motorway", "Road type: Regional road", "Intersection: At intersection", "Lighting: Night, no public lighting",
            "Lighting: Night, public lighting present and lit", "Weather: Rain", "Road surface: Wet, puddles", "Year: 2020", "Year: 2024", "Month: Dec", "Month: Jun"]
print("=== ADJUSTED ODDS RATIOS (Severe = 1) with cluster-robust 95% intervals; * = significant at 5%; models as specified ===")
table = pd.DataFrame({label: [or_text(label, t) for t in SELECTED] for label in MODEL_LABELS}, index=SELECTED)
print(table.to_string())
print("\nRoad-user terms: baseline 'group involved' (versus a car-only accident):")
print(pd.DataFrame({"Baseline": [or_text("Baseline", f"Group involved: {g}") for g in GROUP_ORDER[1:]]}, index=GROUP_ORDER[1:]).to_string())
print("\nRoad-user terms: counterpart in the group models (versus a passenger car):")
cps = sorted({t for t in coefficients[coefficients["variable"] == "Counterpart"]["term"]})
print(pd.DataFrame({label: [or_text(label, t) for t in cps] for label in MODEL_LABELS[1:]}, index=[t.replace("Counterpart: ", "") for t in cps]).to_string())

print("\n=== AVERAGE ADJUSTED PREDICTED PROBABILITY OF A SEVERE ACCIDENT (%) ===")
for var in ("Region", "Road type", "Lighting"):
    piv = predicted[predicted["variable"] == var].assign(text=lambda t: [f"{a:.1f} ({b:.1f}-{c:.1f})" for a, b, c in zip(t["predicted_pct"], t["ci_low_pct"], t["ci_high_pct"])]).pivot(index="category", columns="model", values="text")[MODEL_LABELS]
    print(var); print(piv.to_string(), "\n")
print("=== SCENARIOS: predicted probability of a severe accident (%), 2024 ===")
sc = scenarios.assign(text=lambda t: [("n/a" if np.isnan(a) else f"{a:.1f} ({b:.1f}-{c:.1f})") for a, b, c in zip(t["predicted_pct"], t["ci_low_pct"], t["ci_high_pct"])])
sc["row"] = sc["model"] + " - " + sc["evaluated_as"]
print(sc.pivot(index="row", columns="scenario", values="text").loc[list(dict.fromkeys(sc["row"]))].to_string())
