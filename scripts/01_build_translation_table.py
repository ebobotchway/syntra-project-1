"""
Step 01 - Build the translation table (for review, nothing is applied yet).

What this script does
---------------------
The dataset has every text field twice: once in French (_FR) and once in Dutch (_NL).
Each text also has a numeric code (CD_...). There are only a few distinct texts per field
(3 to 25), so instead of translating 289,532 rows we translate each distinct text ONCE.

This script:
  1. reads the original data,
  2. lists every distinct (code, French text, Dutch text) per field,
  3. checks that each code belongs to exactly ONE French and ONE Dutch text,
  4. adds the English text from the TRANSLATIONS dictionary below,
  5. writes two small CSV files that you can read and correct:
       translation/translation_table.csv   (field, code, french, dutch, english)
       translation/column_names.csv        (new English column name <- source column)

Step 02 will read these two files, so if you change a translation in the CSV,
the change is used automatically. The original data is NOT modified here.

How to run (from the project folder, with `conda activate syntra-ds`):
    python -I scripts/01_build_translation_table.py OPENDATA_MAP_2017-2024.csv.gz translation
"""
import sys
from pathlib import Path

import pandas as pd

input_file = sys.argv[1]  # the original gzipped CSV
output_dir = Path(sys.argv[2])  # folder where the two review files are written
output_dir.mkdir(exist_ok=True)

# --- 1. Read everything as text (dtype=str) so codes like "01" keep their leading zero ---
df = pd.read_csv(input_file, dtype=str)

# --- 2. The fields to translate ---
# Each entry: (new English field name, code column, French text column, Dutch text column)
# Note: CD_ROAD_TYPE_FR / CD_ROAD_TYPE_NL are named like codes in the source file,
# but they contain the text.
FIELDS = [
    ("crossway",        "CD_CROSSWAY",        "TX_CROSSWAY_FR",        "TX_CROSSWAY_NL"),
    ("weather",         "CD_WEATHER",         "TX_WEATHER_FR",         "TX_WEATHER_NL"),
    ("road_condition",  "CD_ROAD_CONDITION",  "TX_ROAD_CONDITION_FR",  "TX_ROAD_CONDITION_NL"),
    ("built_up_area",   "CD_BUILD_UP_AREA",   "TX_BUILD_UP_AREA_FR",   "TX_BUILD_UP_AREA_NL"),
    ("light_condition", "CD_LIGHT_CONDITION", "TX_LIGHT_CONDITION_FR", "TX_LIGHT_CONDITION_NL"),
    ("road_type",       "CD_ROAD_TYPE",       "CD_ROAD_TYPE_FR",       "CD_ROAD_TYPE_NL"),
    ("accident_class",  "CD_CLASS_ACCIDENTS", "TX_CLASS_ACCIDENTS_FR", "TX_CLASS_ACCIDENTS_NL"),
    ("road_user_type1", "CD_ROAD_USR_TYPE1",  "TX_ROAD_USR_TYPE1_FR",  "TX_ROAD_USR_TYPE1_NL"),
    ("road_user_type2", "CD_ROAD_USR_TYPE2",  "TX_ROAD_USR_TYPE2_FR",  "TX_ROAD_USR_TYPE2_NL"),
    ("collision_type",  "CD_COLLISION_TYPE",  "TX_COLLISON_TYPE_FR",   "TX_COLLISION_TYPE_NL"),  # sic: COLLISON in source
    ("obstacle",        "CD_OBSTACLES",       "TX_OBSTACLES_FR",       "TX_OBSTACLES_NL"),
]

# Region and province have NO code column, so they are identified by their French text.
PLACE_FIELDS = [
    ("region",   "TX_RGN_COLLISION_FR",  "TX_RGN_COLLISION_NL"),
    ("province", "TX_PROV_COLLISION_FR", "TX_PROV_COLLISION_NL"),
]

# --- 3. The English translations, written by hand ---
# Key = the code in the data, value = English text.
# Where the French and Dutch texts disagree, the French/Dutch columns in the output show both.
TRANSLATIONS = {
    "crossway": {
        "1": "At intersection", "2": "Not at intersection", "9": "Unknown",
    },
    "weather": {
        "1": "Normal",
        "2": "Rain",
        "2/3": "Rain + Fog (visibility under 100 m)",
        "2/4": "Rain + Strong wind, gusts",
        "2/5": "Rain + Snowfall",
        "2/6": "Rain + Hail",
        "2/7": "Rain + Other (thick smoke, ...)",
        "3": "Fog (visibility under 100 m)",
        "4": "Strong wind, gusts",
        "4/5": "Strong wind, gusts + Snowfall",
        "4/6": "Strong wind, gusts + Hail",
        "5": "Snowfall",
        "5/6": "Snowfall + Hail",
        "6": "Hail",
        "7": "Other (thick smoke, ...)",
        "9": "Unknown, undetermined",
    },
    "road_condition": {
        "1": "Dry",
        "1/4": "Dry + Clean",
        "1/5": "Dry + Dirty (sand, gravel, leaves, ...)",
        "2": "Wet, puddles",
        "2/3": "Wet, puddles + Ice or snow",
        "2/4": "Wet, puddles + Clean",
        "2/5": "Wet, puddles + Dirty (sand, gravel, leaves, ...)",
        "3": "Ice, snow",
        "3/4": "Ice, snow + Clean",
        "3/5": "Ice, snow + Dirty (sand, gravel, leaves, ...)",
        "4": "Clean",
        "5": "Dirty (sand, gravel, leaves, ...)",
        "9": "Unknown, undetermined",
    },
    "built_up_area": {
        "1": "Inside built-up area", "2": "Outside built-up area", "9": "Unknown",
    },
    "light_condition": {
        "1": "Daylight",
        "2": "Dawn, dusk",
        "3": "Night, public lighting present and lit",
        "4": "Night, no public lighting",
        "5": "Night, public lighting present but not lit",
        "9": "Unknown, undetermined",
    },
    "road_type": {
        "1": "Motorway", "2": "Municipal road", "3": "Regional road", "9": "Unknown",
    },
    "accident_class": {
        "1": "With fatalities",
        "2": "Fatally injured",
        "3": "With seriously injured",
        "4": "With slightly injured",
    },
    # Road user type 1 and 2 share the codes 01-09 and 99; type 2 adds 10 and 11.
    "road_user_type1": {
        "01": "Bus", "02": "Other road user", "03": "Bicycle", "04": "Truck",
        "05": "Van / light truck", "06": "Moped", "07": "Motorcycle",
        "08": "Pedestrian", "09": "Passenger car", "99": "Unknown",
    },
    "road_user_type2": {
        "01": "Bus", "02": "Other road user", "03": "Bicycle", "04": "Truck",
        "05": "Van / light truck", "06": "Moped", "07": "Motorcycle",
        "08": "Pedestrian", "09": "Passenger car",
        "10": "Single road user, no obstacle",
        "11": "Single road user against an obstacle",
        "99": "Unknown",
    },
    "collision_type": {
        "0": "Collision type not specified",
        "1": "Chain collision (3 or more drivers)",
        "2": "Between 2 drivers: Head-on collision",
        "3": "Between 2 drivers: Rear-end collision",
        "4": "Between 2 drivers: Side collision (front/rear against flank)",
        "5": "With a pedestrian",
        "6": "Road user against obstacle on the roadway",
        "7": "Road user against obstacle outside the roadway",
        "8": "Single road user, no obstacle (incl. fall)",
        "9": "Other or unknown",
        "A": "Between 2 drivers: Flank against flank",
    },
    "obstacle": {
        "-1": "Collision type not specified",  # sic: the source text says this for obstacle code -1
        "-3": "Presence of obstacle not specified",
        "0": "No obstacle",
        "50": "On the roadway: Animal (pet)",
        "51": "Train",
        "53": "On the roadway: Load",
        "54": "On the roadway: Container",
        "55": "On the roadway: Roadworks (signs, soil, equipment, ...)",
        "56": "Off the roadway: Traffic island, central reservation",
        "57": "Speed bump, hump, hole, gutter, ...",
        "58": "Tram rail",
        "59": "Off the roadway: Tree",
        "60": "Off the roadway: Lighting pole",
        "61": "Off the roadway: Other pole",
        "62": "Off the roadway: Crash barrier breached",
        "63": "Off the roadway: Crash barrier not breached",
        "64": "Off the roadway: Wall, building",
        "65": "Off the roadway: Fence",
        "66": "Off the roadway: Ditch",
        "67": "Other obstacle",
        "68": "On the roadway: Animal (wild animal)",
        "69": "Off the roadway: Animal",
        "70": "On the roadway: Speed bump, hump",
        "71": "On the roadway: Hole, gutter, tram rail",
        "99": "Unknown",
    },
}

# Region and province: key = the French text in the data (decision #8: English names).
PLACE_TRANSLATIONS = {
    "region": {
        "Région de Bruxelles-Capitale": "Brussels-Capital Region",
        "Région flamande": "Flemish Region",
        "Région wallonne": "Walloon Region",
    },
    "province": {
        "Province d’Anvers": "Antwerp",
        "Province de Limbourg": "Limburg",
        "Province de Flandre orientale": "East Flanders",
        "Province de Flandre occidentale": "West Flanders",
        "Province du Brabant flamand": "Flemish Brabant",
        "Province du Brabant wallon": "Walloon Brabant",
        "Province de Hainaut": "Hainaut",
        "Province de Namur": "Namur",
        "Province de Luxembourg": "Luxembourg",
        "Province de Liège": "Liège",
    },
}

# --- 4. Build the translation table ---
rows = []  # each row = one distinct phrase with its English translation

for field, code_col, fr_col, nl_col in FIELDS:
    distinct = df[[code_col, fr_col, nl_col]].drop_duplicates()

    # Safety check: one code must not belong to two different French/Dutch texts.
    # If this fails, the data is inconsistent and we must stop and look at it.
    assert distinct[code_col].is_unique, f"{field}: a code has more than one text"

    for code, fr, nl in distinct.sort_values(code_col).itertuples(index=False):
        # A KeyError here means a code in the data has no translation yet.
        rows.append((field, code, fr, nl, TRANSLATIONS[field][code]))

for field, fr_col, nl_col in PLACE_FIELDS:
    distinct = df[[fr_col, nl_col]].dropna().drop_duplicates()  # empty provinces are NOT translated
    assert distinct[fr_col].is_unique, f"{field}: a French name has two Dutch names"
    for fr, nl in distinct.itertuples(index=False):
        rows.append((field, "", fr, nl, PLACE_TRANSLATIONS[field][fr]))

translation_table = pd.DataFrame(rows, columns=["field", "code", "french", "dutch", "english"])
translation_table.to_csv(output_dir / "translation_table.csv", index=False, encoding="utf-8")

# --- 5. Build the column-name table (decisions #5 and #10) ---
# One English column replaces each French/Dutch pair; the CD_ code columns are kept.
column_rows = [
    # when
    ("collision_year",  "DT_YEAR_COLLISION",  "renamed"),
    ("collision_month", "DT_MONTH_COLLISION", "renamed"),
    ("collision_hour",  "DT_TIME",            "renamed; value 99 becomes empty (decision #11)"),
    # where
    ("municipality_nis_code", "CD_NIS",                "renamed"),
    ("region",                "TX_RGN_COLLISION_FR/NL",  "FR+NL pair -> English name"),
    ("province",              "TX_PROV_COLLISION_FR/NL", "FR+NL pair -> English name; stays empty where missing"),
    ("municipality",          "TX_MUNTY_COLLISION_NL",   "Dutch name kept (decision #8); French column dropped"),
    ("x_coord",               "MS_X_COORD",              "renamed; stays empty where missing"),
    ("y_coord",               "MS_Y_COORD",              "renamed; stays empty where missing"),
]
for field, code_col, fr_col, nl_col in FIELDS:
    column_rows.append((f"{field}_code", code_col, "renamed code column"))
    column_rows.append((field, f"{fr_col}/{nl_col.split('_')[-1]}", "FR+NL pair -> English text"))

pd.DataFrame(column_rows, columns=["new_column", "source_column", "how"]).to_csv(
    output_dir / "column_names.csv", index=False, encoding="utf-8"
)

print(f"Distinct phrases translated: {len(translation_table)}")
print(f"New columns: {len(column_rows)} (from {df.shape[1]} source columns)")
