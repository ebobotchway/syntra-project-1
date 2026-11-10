"""
The fixed 'Key findings' texts of the hotspot deep dive. The numbers come from the saved results (scripts 01 and 02); the build script of the HTML page and app.py use these same texts.
"""
FIXED_NOTE = "Fixed text for all vulnerable groups together, calculated once by the scripts; it does not change with the filters."

HEATMAPS = [
    "Hotspots are in the big cities. With 5 km2 cells, the busiest cell for vulnerable road users is in Brussel (264 accidents a year before Covid-19) or Antwerpen (269 a year after Covid-19); Sint-Gillis is third in the pre and post periods.",
    "The hotspots hardly move: 17 of the 20 busiest 5 km2 cells before Covid-19 are still among the 20 busiest after it (18 of 20 for pedestrians, 19 for cyclists, 15 for motorcycles, 12 for mopeds). With 5 x 5 km squares it is 18 of 20 for all four groups together.",
    "During Covid-19 (2020-2021) the located accidents per year fall from 14,705 to 13,006 and rise to 17,083 afterwards. Part of that rise is better coordinates: 15% of the accidents lacked coordinates before Covid-19, 17% during it and only 3.7% after it.",
]
SEVERITY = [
    "Accidents in the 20 hotspot cells are much less often severe than accidents elsewhere: 6.4% against 13.4% (5 km2 cells, 2017-2024); the fatal share is 0.40% against 1.56%.",
    "The same holds in every period: severe share 7.3% (pre), 5.7% (during) and 6.1% (post) in the hotspots against 14.1%, 13.7% and 12.7% in all other cells.",
    "It holds for every group: severe share in the hotspots against other cells is 7.6% against 14.9% for pedestrians, 6.1% against 12.0% for cyclists, 7.0% against 21.7% for motorcycles and 5.5% against 9.2% for mopeds.",
    "5 x 5 km squares give the same picture (7.6% against 14.3%), a bit less strong because a bigger cell contains more of the surroundings.",
]
RATES = [
    "Per resident, the picture changes: for all four groups the highest rates (per 100,000 residents per year, 2017-2024) are Brussel 384, Knokke-Heist 368, Wijnegem 349, Eeklo 321, Wommelgem 306 and Gent 304, against 148 for Belgium; Antwerpen, first by number of accidents (12,043), has 284.",
    "Only 9 of the 20 municipalities with most accidents are also among the 20 with the highest rate (15 for pedestrians, 9 for cyclists, 19 for motorcycles, 12 for mopeds).",
    "Cyclists: Knokke-Heist 233, Eeklo 222, Leuven 217, Sint-Niklaas 212 (Belgium 78). Pedestrians: Brussel 110, Sint-Gillis 88, Koekelberg 84 (Belgium 32). Motorcycles: Brussel 91, far above Elsene 42 (Belgium 22). Mopeds: Knokke-Heist 75, Brugge 64, Sint-Niklaas 61 (Belgium 25).",
    "The rate for all four groups together is 152 per 100,000 residents per year before Covid-19, 137 during it and 152 after it: after the pandemic the rate per resident is back to the level before it, so the 2022-2024 rise in counts is mostly population growth and better coordinates.",
]
CARE = ("Read with care: residents are not traffic. Municipalities that attract many visitors, commuters or tourists (Brussel, Knokke-Heist, Gent) get a high rate because the people involved do not all live there. "
        "Grid cells use only accidents with coordinates (89% of all, 85% before Covid-19, 96% after it, fewer in Wallonia); municipality rates use all accidents. Associations, not causes.")
