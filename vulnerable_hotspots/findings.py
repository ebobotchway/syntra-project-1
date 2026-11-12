"""
The fixed 'Key findings' texts of the vulnerable hotspots analysis. The numbers come from the saved results (scripts 01, 01b and 02 and the results copied from the focused dashboard); app.py and build_html.py use these same texts.
The texts about the grid are given per cell size (the 5 km2 cells and the 5 x 5 km squares).
"""
FIXED_NOTE = "Fixed text for all four vulnerable groups together, calculated once by the scripts; it does not change with the filters."
S5, S25 = "5 km2 cells", "5 x 5 km squares"

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

STEP_2 = [
    "Accidents involving trucks and motorcycles are the most severe: fatal plus serious makes up 17.3% (trucks) and 18.9% (motorcycles) of their accidents, against 9.9% for all accidents.",
    "The fatal share is 5.1% for trucks (3.6 times the 1.4% of all accidents), 2.8% for motorcycles and 2.0% for pedestrians. It is lowest for mopeds (0.6%), bicycles (0.9%) and passenger cars (1.3%).",
    "Bicycle accidents are less often fatal but more often seriously injured (10.0% against 8.4% overall); motorcycles have the highest serious share (16.2%).",
    "The fatal share of all accidents falls from 1.54% (2017-2019) to 1.47% (2020-2021) and 1.29% (2022-2024).",
]
CARE_2 = ("Read with care: these are the severity of the accidents a group is part of, not the harm to that group's own members. A truck accident may be fatal mostly for the other party. "
          "They are shares given that an accident happened, not the risk of having one.")

MUNICIPALITIES = {
    "Pedestrian": ["29,897 accidents involve pedestrians, in 572 of the 581 municipalities.", "By count: Antwerpen 2,687, Brussel 1,637, Gent 1,157, Luik 1,109, Charleroi 809.",
                   "By share (municipalities with 100+ accidents): Koekelberg 31.5%, Sint-Jans-Molenbeek 30.8%, Jette 30.1%, Sint-Agatha-Berchem 29.9%, Sint-Gillis 29.6%; the top of the list is dominated by the Brussels municipalities.",
                   "Pedestrian share by region: Brussels 21.9%, Wallonia 10.8%, Flanders 8.2%."],
    "Motorcycle": ["19,792 accidents involve motorcycles, in 578 of the 581 municipalities.", "By count: Brussel 1,351, Antwerpen 1,029, Gent 427, Luik 416, Anderlecht 352.",
                   "By share (municipalities with 100+ accidents): Stoumont 32.7%, Froidchapelle 32.6%, Cerfontaine 29.4%, La Roche-en-Ardenne 28.0%, Bouillon 24.1%; these are small Walloon municipalities with 113 to 203 accidents, so a few accidents move the share.",
                   "Motorcycle share by region: Brussels 11.2%, Wallonia 8.3%, Flanders 5.4%."],
    "Moped": ["23,258 accidents involve mopeds, in 568 of the 581 municipalities.", "By count: Antwerpen 2,250, Gent 1,215, Brugge 610, Brussel 588, Charleroi 444.",
              "By share (municipalities with 100+ accidents): Hemiksem 20.3%, Lanaken 18.9%, Schilde 18.2%, Schelle 16.9%, Niel 16.6%; all five are in Flanders.",
              "Moped share by region: Flanders 9.5%, Wallonia 5.9%, Brussels 5.3%."],
    "Bicycle": ["71,881 accidents involve cyclists, in 577 of the 581 municipalities.", "By count: Antwerpen 7,405, Gent 4,229, Brussel 2,478, Leuven 1,773, Brugge 1,598.",
                "By share (municipalities with 100+ accidents): Haacht 56.2%, Mortsel 54.4%, Leuven 54.3%, Hove 50.4%, Keerbergen 49.0%.",
                "Cyclist share by region: Flanders 33.5%, Brussels 21.8%, Wallonia 7.0%. Wherever cyclists make up more than a third of the accidents, the municipality is in Flanders."],
}
STEP_4A = [
    "Fatal share: Wallonia 2.26% (1.6 times Belgium), Flanders 1.23%, Brussels 0.42%. Serious-injury share goes the other way: Flanders 9.67%, Wallonia 7.16%, Brussels 4.45%.",
    "By province, the fatal share is highest in Luxembourg (3.37%), Namur (2.95%) and Hainaut (2.17%) and lowest in Antwerp (1.04%) and Brussels (0.42%); the serious share is highest in West Flanders (11.5%).",
]
CARE_4 = "Read with care: Flanders has more serious but fewer fatal accidents than Wallonia. That could be real or come from how the classes are recorded; I have not tested it."


HEATMAPS = {
    S5: [
        "Hotspots are in the big cities. With 5 km2 cells, the busiest cell for vulnerable road users is in Brussel before Covid-19 (264 accidents a year) and during it (252) and in Antwerpen after it (269, against 268 in Brussel); Sint-Gillis is third before and after Covid-19 (210 and 219).",
        "The hotspots hardly move: 17 of the 20 busiest 5 km2 cells before Covid-19 are still among the 20 busiest after it for all four groups together (18 for pedestrians, 19 for cyclists, 15 for motorcycles, 12 for mopeds).",
        "During Covid-19 (2020-2021) the located accidents per year fall from 14,705 to 13,006 and rise to 17,083 afterwards. Part of that rise is better coordinates: 15% of the accidents lacked coordinates before Covid-19, 17% during it and only 3.7% after it.",
    ],
    S25: [
        "Hotspots are in the big cities. With 5 x 5 km squares, the busiest square for vulnerable road users is in Brussel before Covid-19 (634 accidents a year), during it (604) and after it (656); the second is in Antwerpen (562, 459 and 620 a year) and the third in Anderlecht before and after it (455 and 499).",
        "The hotspots hardly move: 18 of the 20 busiest squares before Covid-19 are still among the 20 busiest after it for all four groups together (17 for pedestrians, 19 for cyclists, 16 for motorcycles, 19 for mopeds).",
        "During Covid-19 (2020-2021) the located accidents per year fall from 14,705 to 13,006 and rise to 17,083 afterwards. Part of that rise is better coordinates: 15% of the accidents lacked coordinates before Covid-19, 17% during it and only 3.7% after it.",
    ],
}
SEVERITY = {
    S5: [
        "Accidents in the 20 hotspot cells are much less often severe than accidents elsewhere: 6.4% against 13.4% (5 km2 cells, 2017-2024); the fatal share is 0.40% against 1.56%.",
        "The same holds in every period: severe share 7.3% (pre), 5.7% (during) and 6.1% (post) in the hotspots against 14.1%, 13.7% and 12.7% in all other cells.",
        "It holds for every group: severe share in the hotspots against other cells is 7.6% against 14.9% for pedestrians, 6.1% against 12.0% for cyclists, 7.0% against 21.7% for motorcycles and 5.5% against 9.2% for mopeds.",
    ],
    S25: [
        "Accidents in the 20 hotspot squares are much less often severe than accidents elsewhere: 7.6% against 14.3% (5 x 5 km squares, 2017-2024); the fatal share is 0.47% against 1.76%.",
        "The same holds in every period: severe share 8.2% (pre), 7.2% (during) and 7.2% (post) in the hotspots against 15.1%, 14.7% and 13.6% in all other squares.",
        "It holds for every group: severe share in the hotspots against other squares is 8.9% against 16.0% for pedestrians, 6.9% against 12.9% for cyclists, 10.0% against 22.9% for motorcycles and 6.0% against 9.7% for mopeds.",
    ],
}
SQUARE_RATES = {
    S5: [
        "Per resident of the cell the busiest cells are not the highest: the busiest cell (Brussel, 262 accidents a year, 2017-2024) has 68,000 residents and 386 accidents per 100,000 residents per year; the second (Antwerpen) has 68,000 residents and 354; the third (Sint-Gillis) has 86,000 and 241.",
        "The highest rates are in cells with 2,000 to 7,000 residents on a through road: Schoten 819 (128 accidents, 1,954 residents), Antwerpen 665 (223 accidents, 4,191 residents), Wetteren 563 and Lier 516.",
        "Only 2 of the 20 busiest cells are also among the 20 cells with the highest rate. 769 of the 5,013 cells with accidents have the 1,000 residents and 30 accidents needed for a rate; the typical (median) rate is 153 per 100,000 residents per year.",
        "Cells count only accidents with coordinates (89% of all), so their rates are lower than the municipality rates, which use all accidents.",
    ],
    S25: [
        "Per resident of the square the busiest squares are not the highest: the busiest square (Brussel, 635 accidents a year, 2017-2024) has 333,000 residents and 190 accidents per 100,000 residents per year; the second busiest (Antwerpen) has 180,000 residents and 310.",
        "The highest rates are in squares with a few thousand residents on a through road or in a tourist town: Stabroek 537 (92 accidents, 2,100 residents), Brugge 459 (89 accidents, 2,400 residents), Knokke-Heist 362; and in the larger Gent (341, 74,000 residents).",
        "Only 7 of the 20 busiest squares are also among the 20 squares with the highest rate. 594 of the 1,274 squares with accidents have the 1,000 residents and 30 accidents needed for a rate; the typical (median) rate is 116 per 100,000 residents per year.",
        "Squares count only accidents with coordinates (89% of all), so their rates are lower than the municipality rates, which use all accidents.",
    ],
}
RATES = [
    "Per resident of the square the busiest squares are not the highest: the busiest square (Brussel, 635 accidents a year, 2017-2024) has 333,000 residents and 190 accidents per 100,000 residents per year; the second busiest (Antwerpen) has 180,000 residents and 310.",
    "The highest rates are in squares with a few thousand residents on a through road or in a tourist town: Stabroek 537 (92 accidents, 2,100 residents), Brugge 459 (89 accidents, 2,400 residents), Knokke-Heist 362; and in the larger Gent (341, 74,000 residents).",
    "Only 7 of the 20 busiest squares are also among the 20 squares with the highest rate. 594 of the 1,274 squares with accidents have the 1,000 residents and 30 accidents needed for a rate; the typical (median) rate is 116 per 100,000 residents per year.",
    "Squares count only accidents with coordinates (89% of all), so their rates are lower than the municipality rates of section 5, which use all accidents.",
]
CARE = ("Read with care: residents are not traffic. Municipalities that attract many visitors, commuters or tourists (Brussel, Knokke-Heist, Gent) get a high rate because the people involved do not all live there. "
        "Grid cells use only accidents with coordinates (89% of all, 85% before Covid-19, 96% after it, fewer in Wallonia); municipality rates use all accidents. Associations, not causes.")
