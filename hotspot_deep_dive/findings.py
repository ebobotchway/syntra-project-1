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
    "Hotspots are in the big cities. With 5 x 5 km squares, the busiest square for vulnerable road users is in Brussel before Covid-19 (634 accidents a year), during it (604) and after it (656); the second is in Antwerpen (562, 459 and 620 a year) and the third in Anderlecht before and after it (455 and 499).",
    "The hotspots hardly move: 18 of the 20 busiest squares before Covid-19 are still among the 20 busiest after it for all four groups together (17 for pedestrians, 19 for cyclists, 16 for motorcycles, 19 for mopeds).",
    "During Covid-19 (2020-2021) the located accidents per year fall from 14,705 to 13,006 and rise to 17,083 afterwards. Part of that rise is better coordinates: 15% of the accidents lacked coordinates before Covid-19, 17% during it and only 3.7% after it.",
]
SEVERITY = [
    "Accidents in the 20 hotspot squares are much less often severe than accidents elsewhere: 7.6% against 14.3% (2017-2024); the fatal share is 0.47% against 1.76%.",
    "The same holds in every period: severe share 8.2% (pre), 7.2% (during) and 7.2% (post) in the hotspots against 15.1%, 14.7% and 13.6% in all other squares.",
    "It holds for every group: severe share in the hotspots against other squares is 8.9% against 16.0% for pedestrians, 6.9% against 12.9% for cyclists, 10.0% against 22.9% for motorcycles and 6.0% against 9.7% for mopeds.",
]
SQUARE_RATES = [
    "Per resident of the square the busiest squares are not the highest: the busiest square (Brussel, 635 accidents a year, 2017-2024) has 333,000 residents and 190 accidents per 100,000 residents per year; the second busiest (Antwerpen) has 180,000 residents and 310.",
    "The highest rates are in squares with a few thousand residents on a through road or in a tourist town: Stabroek 537 (92 accidents, 2,100 residents), Brugge 459 (89 accidents, 2,400 residents), Knokke-Heist 362; and in the larger Gent (341, 74,000 residents).",
    "Only 7 of the 20 busiest squares are also among the 20 squares with the highest rate. 594 of the 1,274 squares with accidents have the 1,000 residents and 30 accidents needed for a rate; the typical (median) rate is 116 per 100,000 residents per year.",
    "Squares count only accidents with coordinates (89% of all), so their rates are lower than the municipality rates of section 5, which use all accidents.",
]
RATES = [
    "Per resident, the picture changes: for all four groups the highest rates (per 100,000 residents per year, 2017-2024) are Brussel 384, Knokke-Heist 368, Wijnegem 349, Eeklo 321, Wommelgem 306 and Gent 304, against 148 for Belgium; Antwerpen, first by number of accidents (12,043), has 284.",
    "Only 9 of the 20 municipalities with most accidents are also among the 20 with the highest rate (15 for pedestrians, 9 for cyclists, 19 for motorcycles, 12 for mopeds).",
    "Cyclists: Knokke-Heist 233, Eeklo 222, Leuven 217, Sint-Niklaas 212 (Belgium 78). Pedestrians: Brussel 110, Sint-Gillis 88, Koekelberg 84 (Belgium 32). Motorcycles: Brussel 91, far above Elsene 42 (Belgium 22). Mopeds: Knokke-Heist 75, Brugge 64, Sint-Niklaas 61 (Belgium 25).",
    "The rate for all four groups together is 152 per 100,000 residents per year before Covid-19, 137 during it and 152 after it: after the pandemic the rate per resident is back to the level before it, so the 2022-2024 rise in counts is mostly population growth and better coordinates.",
]
CARE = ("Read with care: residents are not traffic. Municipalities that attract many visitors, commuters or tourists (Brussel, Knokke-Heist, Gent) get a high rate because the people involved do not all live there. "
        "Grid cells use only accidents with coordinates (89% of all, 85% before Covid-19, 96% after it, fewer in Wallonia); municipality rates use all accidents. Associations, not causes.")
