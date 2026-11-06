"""
Statistics of the interactive tool (decisions #132-#140). Every function takes the FILTERED accidents (a DataFrame from tool_data) and returns tables;
no graphs here and nothing is read from saved results. Shares come with 95% Wilson intervals (#74).
Rule for small numbers (#141): a share rests on at least 30 accidents; under 100 accidents it is flagged as unstable.
"""
import calendar
import math

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, spearmanr

import tool_data as td

MIN_SHOWN = 30     # fewer accidents: the share is not shown
MIN_STABLE = 100   # fewer accidents: the share is flagged as unstable
Z = 1.959964


def wilson(k, n):
    """95% Wilson confidence interval for a share k/n, as percentages (arrays allowed)."""
    k, n = np.asarray(k, float), np.asarray(n, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = k / n
        d = 1 + Z ** 2 / n
        c = (p + Z ** 2 / (2 * n)) / d
        h = Z * np.sqrt(p * (1 - p) / n + Z ** 2 / (4 * n ** 2)) / d
    return (c - h) * 100, (c + h) * 100


def share_columns(table, count_cols, total_col="accidents"):
    """Add share, interval and a note for every outcome count column ('fatal' -> 'fatal %', 'fatal low', 'fatal high')."""
    for c in count_cols:
        table[f"{c} %"] = table[c] / table[total_col] * 100
        table[f"{c} low"], table[f"{c} high"] = wilson(table[c], table[total_col])
    table["note"] = np.where(table[total_col] < MIN_SHOWN, "too few accidents (under 30): shares not shown",
                             np.where(table[total_col] < MIN_STABLE, "fewer than 100 accidents: unstable", ""))
    small = table[total_col] < MIN_SHOWN
    for c in count_cols:
        table.loc[small, [f"{c} %", f"{c} low", f"{c} high"]] = np.nan
    return table


def counts_of(sub, mask):
    part = sub[mask]
    return {"accidents": len(part), "fatal": int(part["fatal"].sum()), "serious": int(part["serious"].sum()), "slight": int(part["slight"].sum()), "severe": int(part["severe"].sum())}


# --------------------------------------------------------------------------------------
# Group overview and severity comparison
# --------------------------------------------------------------------------------------
def severity_by_group(sub, masks):
    """One row per compared group (and one for all accidents in the selection): accidents, outcome counts, shares and intervals."""
    rows = [{"group": g, **counts_of(sub, m)} for g, m in masks.items()]
    rows.append({"group": "All accidents in the selection", **counts_of(sub, np.ones(len(sub), bool))})
    table = pd.DataFrame(rows)
    return share_columns(table, ["fatal", "serious", "slight", "severe"])


def compare_two(sub, masks, a, b):
    """Is the severe share of group B different from that of group A? Difference in points (Newcombe-Wilson interval), ratio and crude odds ratio with intervals,
    and a chi-square test. Where the groups overlap (accidents counted for both), the two samples are not independent: the test is then only indicative."""
    ca, cb = counts_of(sub, masks[a]), counts_of(sub, masks[b])
    na, ka, nb, kb = ca["accidents"], ca["severe"], cb["accidents"], cb["severe"]
    if min(na, nb) < MIN_SHOWN or ka + kb == 0:
        return None
    pa, pb = ka / na, kb / nb
    la, ua = (x / 100 for x in wilson(ka, na))
    lb, ub = (x / 100 for x in wilson(kb, nb))
    diff = pb - pa
    low = diff - math.sqrt((pb - lb) ** 2 + (ua - pa) ** 2)   # Newcombe's hybrid score interval for a difference of proportions
    high = diff + math.sqrt((ub - pb) ** 2 + (pa - la) ** 2)
    out = {"group A": a, "group B": b, "accidents A": na, "severe A": ka, "severe share A %": pa * 100, "accidents B": nb, "severe B": kb, "severe share B %": pb * 100,
           "difference B - A (points)": diff * 100, "difference low": low * 100, "difference high": high * 100}
    if pa > 0 and pb > 0:
        se_log_rr = math.sqrt(1 / ka - 1 / na + 1 / kb - 1 / nb)
        out.update({"risk ratio B / A": pb / pa, "risk ratio low": math.exp(math.log(pb / pa) - Z * se_log_rr), "risk ratio high": math.exp(math.log(pb / pa) + Z * se_log_rr)})
    if 0 < ka < na and 0 < kb < nb:
        odds = (kb / (nb - kb)) / (ka / (na - ka))
        se_log_or = math.sqrt(1 / ka + 1 / (na - ka) + 1 / kb + 1 / (nb - kb))
        out.update({"odds ratio B / A": odds, "odds ratio low": math.exp(math.log(odds) - Z * se_log_or), "odds ratio high": math.exp(math.log(odds) + Z * se_log_or)})
        out["chi-square p-value"] = float(chi2_contingency([[ka, na - ka], [kb, nb - kb]], correction=False)[1])
    shared = int((masks[a] & masks[b]).sum())
    out["accidents in both groups"] = shared
    return out


def severity_distribution_long(table):
    """The severity table in long form (group, outcome, share) for charts."""
    t = table[table["note"] != "too few accidents (under 30): shares not shown"]
    rows = []
    for _, r in t.iterrows():
        for key in ("fatal", "serious", "slight"):
            rows.append({"group": r["group"], "outcome": td.OUTCOMES[key], "share %": r[f"{key} %"], "accidents": r["accidents"]})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Time
# --------------------------------------------------------------------------------------
def annual_table(sub, masks):
    """Per group and year: accidents, severe accidents, severe share with interval, and the index (first selected year = 100)."""
    rows = []
    for g, m in masks.items():
        part = sub[m]
        by_year = part.groupby("collision_year").agg(accidents=("severe", "size"), severe=("severe", "sum"))
        for year in sorted(sub["collision_year"].unique()):
            n = int(by_year["accidents"].get(year, 0))
            rows.append({"group": g, "year": int(year), "accidents": n, "severe": int(by_year["severe"].get(year, 0))})
    table = pd.DataFrame(rows)
    if table.empty:
        return table
    table = share_columns(table, ["severe"])
    first = table.groupby("group")["accidents"].transform("first")
    table["index (first year = 100)"] = np.where(first > 0, table["accidents"] / first * 100, np.nan)
    return table


def monthly_table(sub, masks, years):
    """Per group and month: accidents, share of the group's accidents, accidents per day, and the seasonal index (100 = an average month)."""
    days = {m: sum(calendar.monthrange(y, m)[1] for y in range(years[0], years[1] + 1)) for m in range(1, 13)}
    rows = []
    for g, m in masks.items():
        part = sub[m]
        counts = part.groupby("collision_month").size().reindex(range(1, 13), fill_value=0)
        total = counts.sum()
        for month in range(1, 13):
            share = counts[month] / total * 100 if total else np.nan
            rows.append({"group": g, "month": month, "month name": td.MONTHS[month - 1], "accidents": int(counts[month]), "share of group's accidents %": share,
                         "accidents per day": counts[month] / days[month], "seasonal index": share / (100 / 12) * 100 if total else np.nan})
    return pd.DataFrame(rows)


def seasonal_table(monthly):
    """Seasons from the monthly table (meteorological seasons; per-day uses the days of the selected years)."""
    rows = []
    for g, part in monthly.groupby("group", sort=False):
        total = part["accidents"].sum()
        for season, months in td.SEASONS.items():
            sel = part[part["month"].isin(months)]
            share = sel["accidents"].sum() / total * 100 if total else np.nan
            rows.append({"group": g, "season": season, "accidents": int(sel["accidents"].sum()), "share of group's accidents %": share, "seasonal index": share / 25 * 100 if total else np.nan})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Place
# --------------------------------------------------------------------------------------
def by_area(sub, masks, level):
    """Per area (region, province or municipality) and group: accidents involving the group and their severe share. level: 'region', 'province_label' or 'municipality'."""
    rows = []
    for g, m in masks.items():
        part = sub[m]
        grouped = part.groupby(level).agg(accidents=("severe", "size"), fatal=("fatal", "sum"), serious=("serious", "sum"), slight=("slight", "sum"), severe=("severe", "sum"))
        total = sub.groupby(level).size()
        for area, r in grouped.iterrows():
            rows.append({"group": g, "area": area, **{k: int(r[k]) for k in ("accidents", "fatal", "serious", "slight", "severe")}, "all accidents in the area": int(total[area]),
                         "share of the area's accidents %": r["accidents"] / total[area] * 100})
    table = pd.DataFrame(rows)
    return share_columns(table, ["fatal", "serious", "severe"]) if not table.empty else table


def municipality_table(sub, group_mask):
    """Per municipality: accidents involving the group, all accidents, the group's share of them, and its severe share."""
    names = sub.groupby("municipality_nis_code")["municipality"].first()
    out = pd.DataFrame({"municipality": names,
                        "region": sub.groupby("municipality_nis_code")["region"].first(),
                        "all accidents": sub.groupby("municipality_nis_code").size()})
    part = sub[group_mask]
    g = part.groupby("municipality_nis_code").agg(accidents=("severe", "size"), severe=("severe", "sum"), fatal=("fatal", "sum"))
    out = out.join(g).fillna({"accidents": 0, "severe": 0, "fatal": 0})
    out[["accidents", "severe", "fatal"]] = out[["accidents", "severe", "fatal"]].astype(int)
    out["share of all accidents %"] = out["accidents"] / out["all accidents"] * 100
    out = share_columns(out, ["severe"])
    out.loc[out["accidents"] == 0, "note"] = "no accidents with this group"
    return out.reset_index()


MIN_ALL_FOR_SHARE = 100  # a municipality is ranked by share only with at least 100 accidents of any kind in the selection (#88, #161)


def top_municipalities(table, by, n=20):
    """The n municipalities with most accidents involving the group (by='accidents') or the highest share of all their accidents (by='share', 100+ accidents in the selection)."""
    d = table[table["accidents"] > 0]
    if by == "share":
        d = d[d["all accidents"] >= MIN_ALL_FOR_SHARE].sort_values(["share of all accidents %", "accidents"], ascending=False)
    else:
        d = d.sort_values(["accidents", "share of all accidents %"], ascending=False)
    d = d.head(n).copy()
    d.insert(0, "rank", range(1, len(d) + 1))
    return d


CELL = 500  # metres: the squares of the hotspot analysis (#86)


def hotspot_cells(sub, group_mask):
    """Accidents involving the group per 500 m square (accidents with usable coordinates), and the 20 busiest squares with their municipality."""
    part = sub[group_mask]
    located = part[part["usable_xy"]].copy()
    located["cx"], located["cy"] = (located["x_coord"] // CELL).astype(int), (located["y_coord"] // CELL).astype(int)
    cells = located.groupby(["cx", "cy"]).agg(accidents=("severe", "size"), severe=("severe", "sum")).reset_index()
    cells = cells.sort_values(["accidents", "cx", "cy"], ascending=[False, True, True]).reset_index(drop=True)
    top = cells.head(20).copy()
    top.insert(0, "rank", range(1, len(top) + 1))
    key = located.set_index(["cx", "cy"])["municipality"]
    top["municipality"] = [key.loc[(r.cx, r.cy)].mode().iat[0] if len(top) else "" for r in top.itertuples()]
    top["centre x (m)"], top["centre y (m)"] = top["cx"] * CELL + CELL / 2, top["cy"] * CELL + CELL / 2
    top["severe share %"] = top["severe"] / top["accidents"] * 100
    return cells, top, int(len(part)), int(len(located))


# --------------------------------------------------------------------------------------
# Regions and concentration
# --------------------------------------------------------------------------------------
SQUARE_BINS = [1, 2, 5, 10, 20, 50, 100, np.inf]
SQUARE_LABELS = ["1", "2-4", "5-9", "10-19", "20-49", "50-99", "100+"]


def concentration_squares(sub, masks):
    """Severity by the number of the group's accidents in the accident's 500 m square (same classes as step 4b, #100)."""
    rows = []
    for g, m in masks.items():
        part = sub[m & sub["usable_xy"].to_numpy()].copy()
        if part.empty:
            continue
        part["cx"], part["cy"] = (part["x_coord"] // CELL).astype(int), (part["y_coord"] // CELL).astype(int)
        part["in_square"] = part.groupby(["cx", "cy"])["severe"].transform("size")
        part["class"] = pd.cut(part["in_square"], bins=SQUARE_BINS, right=False, labels=SQUARE_LABELS)
        for label in SQUARE_LABELS:
            sel = part[part["class"] == label]
            rows.append({"group": g, "accidents in the square": label, "accidents": len(sel), "fatal": int(sel["fatal"].sum()), "serious": int(sel["serious"].sum()),
                         "slight": int(sel["slight"].sum()), "severe": int(sel["severe"].sum())})
    table = pd.DataFrame(rows)
    return share_columns(table, ["fatal", "severe"]) if not table.empty else table


def concentration_density(sub, masks, areas, years):
    """Municipalities of the selection in five equal-sized classes of accidents per km2 per year (of the group); severity of the accidents in each class, and Spearman's correlation."""
    n_years = years[1] - years[0] + 1
    rows, corr_rows, per_municipality = [], [], []
    for g, m in masks.items():
        part = sub[m]
        per = part.groupby("municipality_nis_code").agg(accidents=("severe", "size"), severe=("severe", "sum"), fatal=("fatal", "sum"))
        per = per.join(areas.rename("area_km2"), how="left")
        per["density"] = per["accidents"] / per["area_km2"] / n_years
        if len(per) < 10:
            continue
        per["class"] = pd.qcut(per["density"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
        for k, grp in per.groupby("class"):
            rows.append({"group": g, "density class (1 = least dense)": int(k), "municipalities": len(grp), "density from": grp["density"].min(), "density to": grp["density"].max(),
                         "accidents": int(grp["accidents"].sum()), "fatal": int(grp["fatal"].sum()), "severe": int(grp["severe"].sum())})
        eligible = per[per["accidents"] >= MIN_STABLE]
        if len(eligible) >= 10:
            rho, p = spearmanr(eligible["density"], eligible["severe"] / eligible["accidents"])
            corr_rows.append({"group": g, "municipalities used": len(eligible), "minimum accidents": MIN_STABLE, "Spearman rho (density vs severe share)": rho, "p-value": p})
        per = per.assign(group=g, municipality_nis_code=per.index)
        per_municipality.append(per.reset_index(drop=True))
    table = pd.DataFrame(rows)
    table = share_columns(table, ["fatal", "severe"]) if not table.empty else table
    return table, pd.DataFrame(corr_rows), (pd.concat(per_municipality) if per_municipality else pd.DataFrame())
