"""
Data layer of the interactive analysis tool (decisions #132-#140): loading the accident-level data, the filters, and the group masks.

Everything the tool shows is calculated from the FILTERED accidents (rows of OPENDATA_MAP_2017-2024_en_flagged.csv.gz), not from saved tables.
Counting rules as in the study: an accident counts for a road-user group if that group is road user 1 OR road user 2 (#33); "Severe" = accident class 1, 2
or 3 (fatal, fatally injured, seriously injured; #116); coordinates outside Belgium's range are treated as missing (#90).
"""
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
ACCIDENTS_FILE = HERE / "OPENDATA_MAP_2017-2024_en_flagged.csv.gz"
AREAS_FILE = HERE / "data" / "municipality_areas.csv"

GROUPS_ALL = ["Passenger car", "Van / light truck", "Truck", "Bus", "Motorcycle", "Moped", "Bicycle", "Pedestrian", "Other road user", "Unknown"]
NAMED_GROUPS = [g for g in GROUPS_ALL if g not in ("Other road user", "Unknown")]
DEFAULT_COMPARE = ["Bicycle", "Pedestrian", "Motorcycle", "Moped"]  # decision #139
YEARS = list(range(2017, 2025))
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SEASONS = {"Winter": [12, 1, 2], "Spring": [3, 4, 5], "Summer": [6, 7, 8], "Autumn": [9, 10, 11]}  # meteorological, whole months (#53)
OUTCOMES = {"fatal": "Fatal (class 1 + 2)", "serious": "Seriously injured (class 3)", "slight": "Slightly injured (class 4)", "severe": "Severe (fatal + serious)"}


def load_accidents():
    """The accident-level data with the analysis columns added: outcome flags, one 0/1 column per road-user group involved, and a few helper columns."""
    header = pd.read_csv(ACCIDENTS_FILE, nrows=0).columns
    df = pd.read_csv(ACCIDENTS_FILE, dtype={c: str for c in header if c.endswith("_code")})
    df["province_label"] = df["province"].fillna("Brussels (no province)")  # Brussels-Capital Region has no province
    classes = df["accident_class_code"]
    df["fatal"] = classes.isin(["1", "2"])
    df["serious"] = classes == "3"
    df["slight"] = classes == "4"
    df["severe"] = classes.isin(["1", "2", "3"])
    t1, t2 = df["road_user_type1_code"], df["road_user_type2_code"]
    names = dict(zip(t1, df["road_user_type1"]))  # code -> group name
    for code, name in names.items():
        df[f"ind_{name}"] = ((t1 == code) | (t2 == code)).to_numpy()
    df["single_road_user"] = t2.isin(["10", "11"]).to_numpy()
    df["usable_xy"] = df["x_coord"].between(20_000, 300_000) & df["y_coord"].between(20_000, 250_000)  # a missing value counts as not usable
    df["month_label"] = df["collision_month"].map(dict(zip(range(1, 13), MONTHS)))
    return df


def load_areas():
    """Area in km2 per municipality (from the Statbel outlines, step 18)."""
    return pd.read_csv(AREAS_FILE, dtype={"municipality_nis_code": str}).set_index("municipality_nis_code")["area_km2"]


@dataclass(frozen=True)
class Filters:
    """The sidebar selection. An empty tuple means 'no restriction' (all categories)."""
    years: tuple = (YEARS[0], YEARS[-1])
    groups: tuple = tuple(DEFAULT_COMPARE)           # the road-user groups to compare
    exclude_overlap: bool = False                     # leave out accidents involving more than one of the compared groups (#135)
    regions: tuple = ()
    provinces: tuple = ()
    municipalities: tuple = ()                        # NIS codes
    road_types: tuple = ()
    intersections: tuple = ()
    lightings: tuple = ()
    weathers: tuple = ()
    surfaces: tuple = ()


def base_mask(df, f):
    """The accidents that pass every filter except the road-user groups (the groups are handled by the analyses: they define who is compared)."""
    mask = df["collision_year"].between(f.years[0], f.years[1]).to_numpy().copy()  # a copy, because the filters below change it in place
    for column, values in (("region", f.regions), ("province_label", f.provinces), ("municipality_nis_code", f.municipalities), ("road_type", f.road_types),
                           ("crossway", f.intersections), ("light_condition", f.lightings), ("weather", f.weathers), ("road_condition", f.surfaces)):
        if values:
            mask &= df[column].isin(values).to_numpy()
    return mask


def selected_group_mask(df, f):
    """True for accidents that involve at least one of the selected groups (used for the data download)."""
    mask = np.zeros(len(df), bool)
    for g in f.groups:
        mask |= df[f"ind_{g}"].to_numpy()
    return mask


def group_masks(sub, groups, exclude_overlap=False):
    """For every group the accidents of `sub` that involve it. With exclude_overlap, accidents that involve more than one of the compared groups are left out of all of them."""
    ind = {g: sub[f"ind_{g}"].to_numpy() for g in groups}
    if exclude_overlap and len(groups) > 1:
        count = sum(v.astype(int) for v in ind.values())
        return {g: ind[g] & (count == 1) for g in groups}
    return ind


def overlap_count(sub, groups):
    """How many accidents involve at least two of the compared groups, and how many for each pair."""
    ind = {g: sub[f"ind_{g}"].to_numpy() for g in groups}
    count = sum(v.astype(int) for v in ind.values()) if ind else np.zeros(len(sub))
    pairs = {}
    names = list(groups)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            n = int((ind[a] & ind[b]).sum())
            if n:
                pairs[f"{a} + {b}"] = n
    return int((count >= 2).sum()), pairs


def describe_filters(f, municipality_names=None):
    """The active filters as short text (used on screen and in the README of an export)."""
    parts = [f"years {f.years[0]}-{f.years[1]}"]
    for label, values in (("regions", f.regions), ("provinces", f.provinces), ("road types", f.road_types), ("intersection", f.intersections),
                          ("lighting", f.lightings), ("weather", f.weathers), ("road surface", f.surfaces)):
        if values:
            parts.append(f"{label}: {', '.join(values)}")
    if f.municipalities:
        shown = [municipality_names.get(n, n) for n in f.municipalities] if municipality_names else list(f.municipalities)
        parts.append("municipalities: " + (", ".join(shown) if len(shown) <= 5 else f"{len(shown)} selected"))
    parts.append("compared groups: " + (", ".join(f.groups) if f.groups else "none"))
    if f.exclude_overlap:
        parts.append("accidents involving more than one compared group excluded")
    return "; ".join(parts)
