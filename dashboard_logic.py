"""
The calculations behind the dashboard (app.py). Pure functions on the summary table
data/dashboard_data.csv (columns: road_user_group, year, month, accidents), so they can be tested
without Streamlit. They follow steps 07-09 of the analysis and the decision log (beslissingslogboek.md).
"""
import calendar

import pandas as pd

REFERENCE = "All accidents"  # every accident once; used as a reference line
GROUPS = ["Passenger car", "Bicycle", "Unknown", "Pedestrian", "Van / light truck", "Moped",
          "Motorcycle", "Truck", "Other road user", "Bus"]  # ranked by total accidents, as in step 07
NOT_A_GROUP = ["Unknown", "Other road user"]  # shown gray, hidden by default (decisions #34, #41, #58)
NAMED_GROUPS = [g for g in GROUPS if g not in NOT_A_GROUP]
YEARS = list(range(2017, 2025))
MONTH_NAMES = [calendar.month_abbr[m] for m in range(1, 13)]
SEASON_MONTHS = {"Winter": [12, 1, 2], "Spring": [3, 4, 5], "Summer": [6, 7, 8], "Autumn": [9, 10, 11]}  # decision #53
PERIODS = {  # my own names (decision #38); the data does not state a cause
    "Pre Covid-19 (2017-2019)": (2017, 2019),
    "During Covid-19 (2020-2021)": (2020, 2021),
    "Post Covid-19 (2022-2024)": (2022, 2024),
}
MEASURES = ["Accidents", "% share", "Per day", "Seasonal index"]  # decision #52


def load_data(path):
    return pd.read_csv(path)


def _select(df, groups, first_year, last_year):
    """The rows for the reference line and the chosen groups in the chosen years."""
    return df[df["road_user_group"].isin([REFERENCE] + list(groups)) & df["year"].between(first_year, last_year)]


def totals(df, groups, first_year, last_year):
    """Accidents involving each group in the chosen years, ranked, with % of all accidents (step 07)."""
    sel = _select(df, groups, first_year, last_year)
    per_group = sel.groupby("road_user_group")["accidents"].sum()
    all_accidents = per_group[REFERENCE]
    result = per_group.drop(REFERENCE).reindex(list(groups)).rename("accidents").reset_index()
    result["percent_of_all_accidents"] = result["accidents"] / all_accidents * 100
    return result.sort_values("accidents", ascending=False).reset_index(drop=True), int(all_accidents)


def yearly(df, groups, first_year, last_year):
    """Accidents per group per year: rows = groups, columns = years (step 08)."""
    sel = _select(df, groups, first_year, last_year)
    table = sel.pivot_table(index="road_user_group", columns="year", values="accidents", aggfunc="sum")
    return table.loc[[REFERENCE] + list(groups)]


def yearly_index(df, groups, first_year, last_year):
    """Index where the FIRST selected year = 100 (decision #66)."""
    table = yearly(df, groups, first_year, last_year)
    return table.div(table[first_year], axis=0) * 100


def period_summary(df, groups, first_year, last_year):
    """Average accidents per year in the pre and post period, and the % difference (decisions #46, #47).
    A period is only used when the selected years cover it completely. Returns None if both are not covered."""
    table = yearly(df, groups, first_year, last_year)
    averages = {}
    for name, (start, end) in PERIODS.items():
        if first_year <= start and end <= last_year:
            averages[name] = table[list(range(start, end + 1))].mean(axis=1)
    pre, post = "Pre Covid-19 (2017-2019)", "Post Covid-19 (2022-2024)"
    if pre not in averages or post not in averages:
        return None
    result = pd.DataFrame({"average per year pre": averages[pre], "average per year post": averages[post]})
    result["post vs pre %"] = (result["average per year post"] / result["average per year pre"] - 1) * 100
    return result


def distributions(df, groups, first_year, last_year):
    """Monthly and seasonal tables for the four measures (step 09, decision #52).
    Returns {"monthly": {measure: table}, "seasonal": {measure: table}}; rows = reference + groups."""
    sel = _select(df, groups, first_year, last_year)
    monthly = sel.pivot_table(index="road_user_group", columns="month", values="accidents", aggfunc="sum").loc[[REFERENCE] + list(groups)]
    years = range(first_year, last_year + 1)
    days = pd.Series({m: sum(calendar.monthrange(y, m)[1] for y in years) for m in range(1, 13)})  # days per month in the range
    seasonal = pd.DataFrame({s: monthly[ms].sum(axis=1) for s, ms in SEASON_MONTHS.items()})
    season_days = pd.Series({s: days[ms].sum() for s, ms in SEASON_MONTHS.items()})
    result = {}
    for kind, table, day_counts, even_share in (("monthly", monthly, days, 100 / 12), ("seasonal", seasonal, season_days, 25.0)):
        share = table.div(table.sum(axis=1), axis=0) * 100  # % of the group's accidents in this month/season
        result[kind] = {
            "Accidents": table,
            "% share": share,
            "Per day": table.div(day_counts, axis=1),
            "Seasonal index": share / even_share * 100,  # 100 = even share (8.33% per month, 25% per season)
        }
    result["monthly"] = {m: t.rename(columns=dict(zip(range(1, 13), MONTH_NAMES))) for m, t in result["monthly"].items()}
    return result
