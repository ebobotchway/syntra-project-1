"""
The fixed 'Key findings' texts of the focused dashboard (the numbers come from the saved results and were checked against them in the main project).
They are shared by app.py; the HTML page has the same texts in template_page.html and template_extra.html.
"""
FIXED_NOTE = "Fixed text for all years 2017-2024; it does not change with the filters."

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
STEP_2 = [
    "Accidents involving trucks and motorcycles are the most severe: fatal plus serious makes up 17.3% (trucks) and 18.9% (motorcycles) of their accidents, against 9.9% for all accidents.",
    "The fatal share is 5.1% for trucks (3.6 times the 1.4% of all accidents), 2.8% for motorcycles and 2.0% for pedestrians. It is lowest for mopeds (0.6%), bicycles (0.9%) and passenger cars (1.3%).",
    "Bicycle accidents are less often fatal but more often seriously injured (10.0% against 8.4% overall); motorcycles have the highest serious share (16.2%).",
    "The fatal share of all accidents falls from 1.54% (2017-2019) to 1.47% (2020-2021) and 1.29% (2022-2024).",
]
HOTSPOTS = {
    "Pedestrian": ["17 of the top 20 squares are in the Brussels area, 2 in Antwerp and 1 in Liège; the busiest square (Antwerp) has 82 accidents, only 0.31% of all located pedestrian accidents.",
                   "About two thirds of the hotspot squares come back in 2022-2024 (12 of 20)."],
    "Motorcycle": ["All 20 busiest squares are in the Brussels area (busiest: 41 accidents).", "About two thirds of the hotspot squares come back in 2022-2024 (16 of 20)."],
    "Moped": ["12 of the top 20 squares are in Antwerp, 4 in Gent, 2 in Brussels, 1 in Charleroi and 1 in Knokke-Heist (busiest: 45 accidents).", "About two thirds of the hotspot squares come back in 2022-2024 (12 of 20)."],
    "Bicycle": ["9 of the top 20 squares are in Antwerpen, 4 in Brussel, 3 in Gent, 2 in Elsene and 1 each in Leuven and Sint-Niklaas; the busiest square (Antwerpen) has 113 accidents, 0.18% of all located cyclist accidents.",
                "13 of the 20 hotspot squares come back in 2022-2024."],
}
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
CARE_1 = "Read with care: these are raw counts and 'Covid-19' is my own label for the periods. A group that is common on the road appears often for that reason alone; severity and traffic volume are not part of these graphs."
CARE_2 = ("Read with care: these are the severity of the accidents a group is part of, not the harm to that group's own members. A truck accident may be fatal mostly for the other party. "
          "They are shares given that an accident happened, not the risk of having one.")
CARE_3 = ("Read with care: counts favour big cities and the data has no population or traffic figures, so these are not rates. Hotspots are where accidents are COUNTED, which is mostly where many people and vehicles are. "
          "10-13% of accidents have no coordinates (3-5% in 2022-2024), more in Wallonia, so Walloon hotspots may be understated.")
CARE_4 = "Read with care: Flanders has more serious but fewer fatal accidents than Wallonia. That could be real or come from how the classes are recorded; I have not tested it."
