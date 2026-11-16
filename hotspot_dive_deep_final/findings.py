"""
The fixed 'Key findings' texts of the hotspot deep dive. The numbers come from the saved results (scripts 01 and 02); the build script of the HTML page and app.py use these same texts.
"""
FIXED_NOTE = "Fixed text for all vulnerable groups together, calculated once by the scripts; it does not change with the filters."

STEP_1A = [
    "Passenger cars (70.2% of all accidents) and bicycles (24.8%) are involved most often. Pedestrians follow at 10.3%, vans 8.1%, mopeds 8.0%, motorcycles 6.8%, trucks 4.4%, buses 1.4%.",
    "'Unknown' is 10.7%: for about one accident in ten the road user is not recorded.",
    "Shares add up to more than 100% because one accident can involve two groups (136,144 accidents involve two different groups).",
]
STEP_1B = [
    "Almost every group drops in 2020 (bicycles only -5.5%; buses -37.7% and pedestrians -30.4% most) and rebounds in 2021-2022.",
    "By 2024 (2017 = 100): bicycles 115, mopeds 105, vans and buses 97, pedestrians 86, motorcycles 83, passenger cars 82, trucks 73.",
    "Post vs pre (average per year 2022-2024 against 2017-2019): trucks -17.2%, motorcycles -12.9%, cars -12.2%, pedestrians -10.4%, buses -6.4%, vans +1.5%, mopeds +7.3%, bicycles +14.6%.",
    "'Unknown' more than doubles (+113% from 2017 to 2024). Part of the decline of the named groups may be recording shifting into 'Unknown'; the data cannot show that.",
]
CARE_1 = "Read with care: these are raw counts and 'Covid-19' is my own label for the periods. A group that is common on the road appears often for that reason alone; severity and traffic volume are not part of these graphs."

HEATMAPS = [
    "Hotspots are in the big cities. With 5 km2 cells, the busiest cell for vulnerable road users is in Brussel (264 accidents a year before Covid-19) or Antwerpen (269 a year after Covid-19); Sint-Gillis is third in the pre and post periods.",
    "The hotspots hardly move: 37 of the 40 busiest 5 km2 cells before Covid-19 are still among the 40 busiest after it (34 of 40 for pedestrians, 36 for cyclists, 32 for motorcycles, 33 for mopeds). With 5 x 5 km squares it is 34 of 40 for all four groups together.",
    "During Covid-19 (2020-2021) the located accidents per year fall from 14,705 to 13,006 and rise to 17,083 afterwards. Part of that rise is better coordinates: 15% of the accidents lacked coordinates before Covid-19, 17% during it and only 3.7% after it.",
]
SEVERITY = [
    "Accidents in the 40 hotspot cells are much less often severe than accidents elsewhere: 7.1% against 14.0% (5 km2 cells, 2017-2024); the fatal share is 0.42% against 1.68%.",
    "The same holds in every period: severe share 7.7% (pre), 6.5% (during) and 6.8% (post) in the hotspots against 14.7%, 14.3% and 13.2% in all other cells.",
    "It holds for every group: severe share in the hotspots against other cells is 8.4% against 15.6% for pedestrians, 6.5% against 12.5% for cyclists, 8.5% against 22.3% for motorcycles and 5.6% against 9.5% for mopeds.",
    "5 x 5 km squares give the same picture (8.3% against 15.0%), a bit less strong because a bigger cell contains more of the surroundings.",
]
LOGIT = [
    "Being in a hotspot square lowers the odds of a severe accident: odds ratio 0.59 (95% interval 0.53 to 0.65), with period, group, built-up area and light condition held equal. Raw: 8.5% severe in hotspot squares against 15.3% elsewhere.",
    "As percentage points: if every accident were in a hotspot square the model gives 9.2% severe, if none were 14.6%: 5.4 points lower (95% interval 4.5 to 6.3).",
    "Outside built-up areas the odds of a severe accident are 1.74 times those inside (1.63 to 1.85); at night (public lighting or not) they are 1.40 times those in daylight (1.34 to 1.47); dawn and dusk do not differ from daylight (0.95, 0.87 to 1.03).",
    "Against cyclists, motorcycles have 1.66 times the odds (1.56 to 1.77), pedestrians 1.37 (1.27 to 1.48) and mopeds 0.72 (0.68 to 0.77). After Covid-19 the odds are 0.89 times those before it (0.85 to 0.94); during Covid-19 they do not differ clearly (0.96, 0.91 to 1.01).",
    "The model is simple and only moderately predictive (AUC 0.64, McFadden R2 0.036): it describes differences between groups of accidents and cannot say which single accident will be severe.",
]
LOGIT_CARE = ("Read with care: an odds ratio is not a risk ratio (severe accidents are 12% of the rows, so odds ratios look further from 1 than risk ratios). 'Hotspot' means a top-40 square of the accident's own group and period, so it is a busy place, not a dangerous one. "
              "Speed, traffic volume and road layout are not in the data; the hotspot effect probably carries the lower speeds of city centres. One accident with two vulnerable groups is a row in both groups; standard errors are cluster-robust by municipality. Associations, not causes.")
RATES = [
    "Per resident, the picture changes: for all four groups the highest rates (per 100,000 residents per year, 2017-2024) are Brussel 384, Knokke-Heist 368, Wijnegem 349, Eeklo 321, Wommelgem 306 and Gent 304, against 148 for Belgium; Antwerpen, first by number of accidents (12,043), has 284.",
    "Only 9 of the 20 municipalities with most accidents are also among the 20 with the highest rate (15 for pedestrians, 9 for cyclists, 19 for motorcycles, 12 for mopeds).",
    "Cyclists: Knokke-Heist 233, Eeklo 222, Leuven 217, Sint-Niklaas 212 (Belgium 78). Pedestrians: Brussel 110, Sint-Gillis 88, Koekelberg 84 (Belgium 32). Motorcycles: Brussel 91, far above Elsene 42 (Belgium 22). Mopeds: Knokke-Heist 75, Brugge 64, Sint-Niklaas 61 (Belgium 25).",
    "The rate for all four groups together is 152 per 100,000 residents per year before Covid-19, 137 during it and 152 after it: after the pandemic the rate per resident is back to the level before it, so the 2022-2024 rise in counts is mostly population growth and better coordinates.",
]
CARE = ("Read with care: residents are not traffic. Municipalities that attract many visitors, commuters or tourists (Brussel, Knokke-Heist, Gent) get a high rate because the people involved do not all live there. "
        "Grid cells use only accidents with coordinates (89% of all, 85% before Covid-19, 96% after it, fewer in Wallonia); municipality rates use all accidents. Associations, not causes.")
