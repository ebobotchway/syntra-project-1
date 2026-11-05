"""
Live logistic severity models for the interactive tool (decisions #137, #143).

Same method as scripts/20_severity_logit_models.py (Severe = 1 for accident classes 1-3; coefficients by Newton-Raphson with step-halving;
standard errors clustered by municipality; references, merging of small categories and the dropping of nearly identical terms as in #119, #125, #128, #129),
but written as functions that take the FILTERED accidents. The code is duplicated on purpose: the script has to keep running on its own,
and a check (test_logit_live in the project's tests) shows that this module reproduces the saved coefficients of script 20 on all accidents.

A model is only estimated when the selection has at least MIN_ACCIDENTS accidents and MIN_EVENTS severe accidents (#137); otherwise ModelNotAvailable explains why.
"""
import math

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import norm, rankdata

MIN_ACCIDENTS = 1000
MIN_EVENTS = 100
OTHER = "Other / combined"
REFERENCES = {"Region": "Flemish Region", "Road type": "Municipal road", "Intersection": "Not at intersection", "Lighting": "Daylight", "Weather": "Normal",
              "Road surface": "Dry", "Collision type": "Between 2 drivers: Rear-end collision", "Year": "2017", "Month": "Jan", "Counterpart": "Passenger car"}
COLUMNS = {"Region": "region", "Road type": "road_type", "Intersection": "crossway", "Lighting": "light_condition", "Weather": "weather", "Road surface": "road_condition",
           "Collision type": "collision_type", "Year": "collision_year", "Month": "month_label"}
GROUP_ORDER = ["Passenger car", "Van / light truck", "Truck", "Bus", "Motorcycle", "Moped", "Bicycle", "Pedestrian", "Other road user", "Unknown"]
FOCAL_MODELS = ["Cyclists", "Pedestrians", "Motorcyclists", "Mopeds"]
FOCAL_GROUP = {"Cyclists": "Bicycle", "Pedestrians": "Pedestrian", "Motorcyclists": "Motorcycle", "Mopeds": "Moped"}
MODEL_CHOICES = ["Baseline (all road users)"] + FOCAL_MODELS


class ModelNotAvailable(Exception):
    """The selection cannot support a model (too few accidents or severe accidents, or a design that cannot be estimated). The message says why."""


# --------------------------------------------------------------------------------------
# The estimator (the same code as in script 20)
# --------------------------------------------------------------------------------------
def _loglik(X, y, beta):
    eta = X @ beta
    return float(np.sum(y * eta - np.logaddexp(0, eta)))


def fit_logit(X, y, max_iter=100, tol=1e-9):
    """Logistic regression by Newton-Raphson with step-halving. Returns coefficients, the inverse Hessian, probabilities and the log-likelihood."""
    beta = np.zeros(X.shape[1])
    beta[0] = math.log(y.mean() / (1 - y.mean()))
    current = _loglik(X, y, beta)
    for _ in range(max_iter):
        p = expit(X @ beta)
        w = p * (1 - p)
        step = np.linalg.solve((X * w[:, None]).T @ X, X.T @ (y - p))
        size = 1.0
        while size > 1e-6:
            candidate = beta + size * step
            new = _loglik(X, y, candidate)
            if new >= current - 1e-12:
                break
            size /= 2
        beta, current = candidate, new
        if np.max(np.abs(size * step)) < tol:
            break
    else:
        raise ModelNotAvailable("the model did not converge for this selection")
    p = expit(X @ beta)
    w = p * (1 - p)
    return beta, np.linalg.inv((X * w[:, None]).T @ X), p, current


def cluster_robust_cov(X, y, p, bread, clusters):
    """Cluster-robust covariance (sandwich) with the small-sample factor G/(G-1) * (N-1)/(N-k)."""
    scores = X * (y - p)[:, None]
    n_clusters = clusters.max() + 1
    cluster_scores = np.zeros((n_clusters, X.shape[1]))
    np.add.at(cluster_scores, clusters, scores)
    n, k = X.shape
    return n_clusters / (n_clusters - 1) * (n - 1) / (n - k) * bread @ (cluster_scores.T @ cluster_scores) @ bread


def auc(y, score):
    ranks = rankdata(score)
    n1 = y.sum()
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1)))


def icc(values, clusters):
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


# --------------------------------------------------------------------------------------
# Categories and the design matrix
# --------------------------------------------------------------------------------------
def global_merge_maps(full):
    """Step 1 of the merging rule (#125): in weather, road surface and lighting, categories with fewer than 100 accidents on ALL accidents become 'Other / combined'."""
    maps = {}
    for var in ("Weather", "Road surface", "Lighting"):
        counts = full[COLUMNS[var]].value_counts()
        maps[var] = {c: OTHER for c, n in counts.items() if n < 100 and not str(c).startswith("Unknown")}
    return maps


def _labels(sub, var, gmaps):
    s = sub[COLUMNS[var]].astype(str)
    return s.replace(gmaps.get(var, {}))


def _merge_in_model(s, y, ref, var, notes):
    """Step 2 (#129): a category with fewer than 30 accidents, or with no severe or no non-severe accident, is merged into 'Other / combined' or into the reference."""
    stats = pd.DataFrame({"n": s.groupby(s).size(), "events": pd.Series(y, index=s.index).groupby(s).sum()})
    stats["non"] = stats["n"] - stats["events"]
    if ref not in stats.index or stats.loc[ref, "n"] < 30:
        new_ref = stats["n"].idxmax()
        notes.append(f"{var}: the reference '{ref}' has fewer than 30 accidents here; '{new_ref}' is the reference")
        ref = new_ref
    bad = [c for c in stats.index if c != ref and (stats.loc[c, "n"] < 30 or stats.loc[c, "events"] == 0 or stats.loc[c, "non"] == 0)]
    if bad:
        pool = stats.loc[bad, "n"].sum() + (stats.loc[OTHER, "n"] if (OTHER in stats.index and OTHER not in bad) else 0)
        target = OTHER if pool >= 30 else ref
        notes.append(f"{var}: {', '.join(bad)} merged into '{target}' (fewer than 30 accidents, or no severe or no non-severe accident)")
        s = s.replace({c: target for c in bad})
    return s, ref


def counterpart_labels(sub, focal, group_names, group_codes):
    """The other party in each accident (#120): a group, 'None (single road user)' or 'Same group (...)'."""
    code = group_codes[focal]
    t1, t2 = sub["road_user_type1_code"].to_numpy(), sub["road_user_type2_code"].to_numpy()
    other = np.where(t1 == code, t2, t1)
    label = np.array(["None (single road user)" if c in ("10", "11") else group_names.get(c, "Unknown") for c in other], dtype=object)
    label[(t1 == code) & (t2 == code)] = f"Same group ({focal})"
    return pd.Series(label, index=sub.index)


class Design:
    """The design matrix of one model with the information needed for tables and predictions."""

    def __init__(self, sub, spec, gmaps, counterpart=None, group_term=None, extra_notes=None):
        y = sub["severe"].to_numpy().astype(float)
        self.y, self.notes = y, list(extra_notes or [])
        self.clusters = pd.factorize(sub["municipality_nis_code"])[0]
        cols, names, info = [np.ones(len(sub))], ["Intercept"], []
        self.blocks = {}
        variables = ["Region", "Road type", "Intersection", "Lighting", "Weather", "Road surface", "Year", "Month"] + (["Collision type"] if spec == "full" else [])
        data = {v: _labels(sub, v, gmaps).reset_index(drop=True) for v in variables}
        data["Year"] = data["Year"].astype(str)
        if counterpart is not None:
            data["Counterpart"] = counterpart.reset_index(drop=True)
            variables = ["Counterpart"] + variables
        for var in variables:
            s, ref = _merge_in_model(data[var], y, REFERENCES[var], var, self.notes)
            cats = sorted([c for c in s.unique() if c != ref], key=lambda c: (c == OTHER, c))
            block = {"ref": ref, "cats": cats, "cols": {}, "current": s.to_numpy()}
            for c in cats:
                if var == "Counterpart" and spec == "full" and c == "None (single road user)":
                    self.notes.append("Counterpart 'None (single road user)' is carried by the collision types (they overlap completely)")
                    continue
                block["cols"][c] = len(cols)
                cols.append((s.to_numpy() == c).astype(float)); names.append(f"{var}: {c}")
                info.append((names[-1], var, c, int((s == c).sum()), int(y[(s == c).to_numpy()].sum())))
            info.append((f"{var}: {ref} (reference)", var, ref, int((s == ref).sum()), int(y[(s == ref).to_numpy()].sum())))
            self.blocks[var] = block
        if group_term is not None:  # the pairwise comparison: 1 = group B, 0 = group A
            cols.append(group_term.astype(float)); names.append("Group B (versus group A)")
            info.append((names[-1], "Group", "Group B", int(group_term.sum()), int(y[group_term > 0].sum())))
        elif counterpart is None:  # baseline (#117)
            for g in GROUP_ORDER[1:]:
                col = sub[f"ind_{g}"].to_numpy().astype(float)
                if col.sum() >= 30:
                    cols.append(col); names.append(f"Group involved: {g}")
                    info.append((names[-1], "Group involved", g, int(col.sum()), int(y[col > 0].sum())))
            if spec != "full":
                col = sub["single_road_user"].to_numpy().astype(float)
                if col.sum() >= 30:
                    cols.append(col); names.append("Group involved: Single road user (no second party)")
                    info.append((names[-1], "Group involved", "Single road user (no second party)", int(col.sum()), int(y[col > 0].sum())))
        self.X = np.column_stack(cols)
        self.names = names
        self.info = pd.DataFrame(info, columns=["term", "variable", "category", "accidents", "events"])


def _drop_columns(design, drop, note):
    """Remove columns from a design (and keep the blocks consistent)."""
    keep = [i for i in range(len(design.names)) if design.names[i] not in drop]
    remap = {old: new for new, old in enumerate(keep)}
    design.X = design.X[:, keep]
    design.names = [design.names[i] for i in keep]
    for block in design.blocks.values():
        block["cols"] = {c: remap[i] for c, i in block["cols"].items() if i in remap}
    design.info = design.info[~design.info["term"].isin(drop)].reset_index(drop=True)
    design.notes.append(note)


def prepare(sub, spec, gmaps, counterpart=None, group_term=None):
    """Build a design; leave out a collision-type term that is nearly identical (correlation above 0.99) to a road-user term (#119); check the rank."""
    design = Design(sub, spec, gmaps, counterpart=counterpart, group_term=group_term)
    corr = np.corrcoef(design.X[:, 1:], rowvar=False) if design.X.shape[1] > 2 else np.array([[1.0]])
    names = design.names[1:]
    drop = set()
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if abs(corr[i, j]) > 0.99:
                collision = [n for n in (names[i], names[j]) if n.startswith("Collision type:")]
                if collision:
                    drop.add(collision[0])
                else:
                    raise ModelNotAvailable(f"two terms are nearly identical in this selection ({names[i]} and {names[j]}); widen the selection")
    if drop:
        _drop_columns(design, drop, "Left out (nearly identical to a road-user term): " + ", ".join(sorted(drop)))
    eig = np.linalg.eigvalsh(design.X.T @ design.X)
    if eig[0] / eig[-1] < 1e-10:
        raise ModelNotAvailable("the explanatory variables cannot be separated in this selection (too narrow); widen the filters")
    return design


def estimate(design):
    """Fit the design and add robust and ordinary standard errors and fit statistics."""
    X, y = design.X, design.y
    beta, bread, p, loglik = fit_logit(X, y)
    cov = cluster_robust_cov(X, y, p, bread, design.clusters)
    ll0 = float(len(y) * (y.mean() * math.log(y.mean()) + (1 - y.mean()) * math.log(1 - y.mean())))
    design.beta, design.cov, design.p, design.loglik = beta, cov, p, loglik
    design.se_robust, design.se_ordinary = np.sqrt(np.diag(cov)), np.sqrt(np.diag(bread))
    design.fit = {"accidents": len(y), "severe accidents": int(y.sum()), "severe share %": y.mean() * 100, "parameters": X.shape[1], "municipalities (clusters)": int(design.clusters.max() + 1),
                  "log-likelihood": loglik, "McFadden R2": 1 - loglik / ll0, "AIC": 2 * X.shape[1] - 2 * loglik, "AUC (in-sample)": auc(y, p),
                  "ICC of the outcome": icc(y, design.clusters), "ICC of the residuals": icc(y - p, design.clusters),
                  "median robust / ordinary SE": float(np.median(design.se_robust[1:] / design.se_ordinary[1:]))}
    return design


def coefficient_table(design):
    z = design.beta / design.se_robust
    out = pd.DataFrame({"term": design.names, "odds ratio": np.exp(design.beta), "OR low": np.exp(design.beta - 1.96 * design.se_robust), "OR high": np.exp(design.beta + 1.96 * design.se_robust),
                        "coefficient": design.beta, "robust SE": design.se_robust, "ordinary SE": design.se_ordinary, "z": z, "p-value": 2 * norm.sf(np.abs(z))})
    out = out.merge(design.info, on="term", how="left")
    return out[out["term"] != "Intercept"].reset_index(drop=True)


def check_selection(sub):
    n, e = len(sub), int(sub["severe"].sum())
    if n < MIN_ACCIDENTS or e < MIN_EVENTS:
        raise ModelNotAvailable(f"this selection has {n:,} accidents and {e:,} severe accidents; a model needs at least {MIN_ACCIDENTS:,} accidents and {MIN_EVENTS} severe ones. Widen the filters.")


# --------------------------------------------------------------------------------------
# The models of the tool
# --------------------------------------------------------------------------------------
def fit_study_model(sub, model, spec, gmaps, group_names, group_codes):
    """One of the five models of the study (baseline or a group model) on the filtered accidents. sub = all accidents of the selection; for a group model it is
    narrowed to the accidents involving the group."""
    if model == MODEL_CHOICES[0]:
        sample, counterpart = sub, None
    else:
        focal = FOCAL_GROUP[model]
        sample = sub[sub[f"ind_{focal}"].to_numpy()]
        counterpart = counterpart_labels(sample, focal, group_names, group_codes)
    check_selection(sample)
    return estimate(prepare(sample, spec, gmaps, counterpart=counterpart))


def fit_pair(sub, mask_a, mask_b, gmaps):
    """The adjusted comparison of two groups (#143): odds of a severe accident for group B against group A at the same conditions. Accidents involving both are left out."""
    both = mask_a & mask_b
    sample_mask = (mask_a | mask_b) & ~both
    sample = sub[sample_mask]
    check_selection(sample)
    group_b = mask_b[sample_mask].astype(float)
    if group_b.sum() < 30 or (1 - group_b).sum() < 30:
        raise ModelNotAvailable("one of the two groups has fewer than 30 accidents once accidents involving both are left out")
    design = prepare(sample, "no_collision", gmaps, group_term=group_b)
    design.notes.append(f"{int(both.sum()):,} accidents involving both groups are left out of the adjusted comparison")
    return estimate(design)


def predicted_by_category(design, variables, n_draws=300, seed=2026):
    """Average adjusted predicted probability (%) of a severe accident for each category of the variables, with 95% intervals from draws of the cluster-robust distribution (#130)."""
    rng = np.random.default_rng(seed)
    w, U = np.linalg.eigh(design.cov)
    B = np.vstack([design.beta, design.beta + rng.standard_normal((n_draws, len(design.beta))) @ (U * np.sqrt(np.clip(w, 0, None))).T])
    plan = []
    for var in variables:
        if var not in design.blocks:
            continue
        block = design.blocks[var]
        cats = [block["ref"]] + block["cats"]
        if len(cats) < 2:
            continue
        current = np.array([cats.index(c) for c in block["current"]])
        plan.append((var, cats, current, [None] + [block["cols"].get(c) for c in block["cats"]]))
    results = {(var, c): np.empty(len(B)) for var, cats, _, _ in plan for c in cats}
    for r in range(len(B)):
        eta = design.X @ B[r]
        for var, cats, current, columns in plan:
            coef = np.array([0.0 if col is None else B[r][col] for col in columns])
            base = eta - coef[current]
            for k, c in enumerate(cats):
                results[(var, c)][r] = expit(base + coef[k]).mean()
    rows = [{"variable": var, "category": c, "predicted %": v[0] * 100, "low %": np.percentile(v[1:], 2.5) * 100, "high %": np.percentile(v[1:], 97.5) * 100} for (var, c), v in results.items()]
    return pd.DataFrame(rows)


def calibration_table(design):
    order = np.argsort(design.p)
    return pd.DataFrame([{"decile": k, "accidents": len(part), "mean predicted %": design.p[part].mean() * 100, "observed %": design.y[part].mean() * 100}
                         for k, part in enumerate(np.array_split(order, 10), start=1)])
