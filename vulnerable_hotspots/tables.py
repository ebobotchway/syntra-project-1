"""
The calculations of step 3b/3c (municipality view) of the focused dashboard, as plain functions on the saved table results/geo_municipality_periods.csv
(accidents and severe accidents per municipality, group and period; written by script 24 of the main project).

The same rules are used by the HTML page (build_html.py / template_extra.html), where they are written in JavaScript:
  #33  an accident counts for a group if the group is road user 1 OR 2
  #88 / #161  a share is only ranked for municipalities with at least 100 accidents of any kind (in the chosen period and region)
  a severe share (% of the group's accidents that are severe) is only shown from 30 accidents of the group
"""
import numpy as np
import pandas as pd

MIN_ALL_FOR_SHARE = 100
MIN_FOR_SEVERE_SHARE = 30
PERIODS = ["2017-2024", "2022-2024"] + [str(y) for y in range(2017, 2025)]
PERIOD_LABELS = {"2017-2024": "All years 2017-2024", "2022-2024": "2022-2024 (most complete coordinates)"} | {str(y): str(y) for y in range(2017, 2025)}


def municipality_table(periods, base, group, period, region=None):
    """One row per municipality: accidents with the group, all accidents, the group's share of them, and the severe accidents of the group.
    periods = the saved period table, base = the municipality names and regions; region = None for all of Belgium."""
    p = periods[(periods["period"] == period)]
    g = p[p["group"] == group].set_index("municipality_nis_code")
    total = p[p["group"] == "All accidents"].set_index("municipality_nis_code")["accidents"]
    out = base[["municipality", "region"]].copy()
    out["accidents"] = g["accidents"]
    out["all accidents"] = total
    out["severe"] = g["severe"]
    if region:
        out = out[out["region"] == region]
    out["share of all accidents %"] = out["accidents"] / out["all accidents"] * 100
    out["severe %"] = np.where(out["accidents"] >= MIN_FOR_SEVERE_SHARE, out["severe"] / out["accidents"].where(out["accidents"] > 0) * 100, np.nan)
    out["note"] = np.where(out["accidents"] == 0, "no accidents with this group", "")
    return out.reset_index()


def top_municipalities(table, by, n=20):
    """The n municipalities with most accidents involving the group (by='accidents') or the highest share of all their accidents (by='share', 100+ accidents)."""
    d = table[table["accidents"] > 0]
    if by == "share":
        d = d[d["all accidents"] >= MIN_ALL_FOR_SHARE].sort_values(["share of all accidents %", "accidents"], ascending=False)
    else:
        d = d.sort_values(["accidents", "share of all accidents %"], ascending=False)
    d = d.head(n).copy()
    d.insert(0, "rank", range(1, len(d) + 1))
    return d


def for_group_charts(table):
    """The same table with the column names the bubble map expects (accidents_group, group_share_pct, accidents_total, ranked_by_share)."""
    return table.rename(columns={"accidents": "accidents_group", "share of all accidents %": "group_share_pct", "all accidents": "accidents_total"}).assign(
        ranked_by_share=lambda d: d["accidents_total"] >= MIN_ALL_FOR_SHARE)
