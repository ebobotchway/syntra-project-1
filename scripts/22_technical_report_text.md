# Road accidents in Belgium 2017-2024: full technical report of steps 1-5

Data: Belgian road accident open data 2017-2024, translated to English (289,532 accidents, 32 columns in the flagged file). This report is the long version of `findings_summary_steps_1_5.md`: the same findings with the tables of the key numbers, the method in detail and the robustness checks. Every table is read from the saved result files in `reports/` by `scripts/22_build_technical_report.py`. `#n` points to an entry in `beslissingslogboek.md`, where the decision and its reason are written down.

## Contents

0. Data and counting rules
1. Step 1: the burden per road-user group
2. Step 2: severity per road-user group
3. Step 3: geography of vulnerable road users
4. Step 4: regional severity, concentration and density
5. Step 5: logistic models of severity
6. The interactive tools and how they were checked
7. Limits, open questions and what was not done

## 0. Data and counting rules

**Data.** One row is one accident (the data has no identifier to prove it). The Dutch and French source was translated to English with an approved list of 120 translations (#1-#10). Possible duplicates were flagged and not removed, and nothing was filled in or removed for empty cells (#20). 12.39% of accidents have no coordinates (35,881) and 10.37% have no province (all Brussels, where "no province" means "not applicable").

**Counting rule (#33).** An accident counts once for every road-user group it involves: road user 1 OR road user 2. One accident can therefore count for two groups, and shares add up to more than 100%: 136,144 accidents involve two different groups. "Single road user" accidents are not a road user. The meaning of "road user 1" and "road user 2" is not documented, so the order is not interpreted except where tested (step 5).

**Severity (#116).** The accident class belongs to the whole accident. Fatal = classes 1 and 2 (fatalities and fatally injured), serious = class 3, slight = class 4. "Severe" = classes 1-3 (28,532 accidents, 9.85%): 3,077 + 1,064 + 24,391.

**Unknown categories (#18, #22).** Unknown stays a category. In the explanatory variables the share unknown or not specified is: weather 9.6%, road surface 8.4%, collision type 8.9%, lighting 3.4%, road type 0.5%. 47,340 accidents (16.4%) have at least one unknown among weather, road surface, lighting, road type and collision type, and about 10% have an unknown road user.

**Intervals.** Shares carry 95% Wilson intervals (#74). A share is not shown for fewer than 30 accidents and flagged as unstable below 100 (#141, in the interactive tool).

**Coordinates.** Belgian Lambert 1972 (EPSG:31370, metres). Two impossible coordinates are treated as missing (#90). Municipality outlines: Statbel statistical sectors 2023 (CC BY 4.0), joined into 581 municipalities and 11 province areas (Brussels included).

## 1. Step 1: the burden per road-user group

**Method.** Accidents per group in total, per year, per month and per season. Three periods that I defined myself: pre (2017-2019), during (2020-2021) and post (2022-2024) "Covid-19". The data states no cause. Seasons are meteorological, in whole months (winter = December to February), because the data has no day (#53). The seasonal index is the share of a group's accidents in a month (or season) divided by the even share (100 = average); it is not corrected for month length, so I also give accidents per day. An urban against rural comparison was dropped because the data has only "built-up area" (#55).

**Accidents per group, 2017-2024.**

{{step1_totals}}

**Accidents per year, the index for 2024 and the change between the pre and post periods.**

{{step1_annual}}

**Findings.**
- Passenger cars and bicycles are involved most often (70.2% and 24.8%). "Unknown" is 10.7%: for about one accident in ten the road user is not recorded, and its share more than doubles from 2017 to 2024 (+113%), so part of the decline of named groups may be recording moving into "Unknown".
- Almost every group drops in 2020 and rebounds in 2021-2022. Bicycles drop only 5.5% in 2020; buses (-37.7%) and pedestrians (-30.4%) drop most. Bicycles (+14.6%) and mopeds (+7.3%) are above their 2017-2019 level in 2022-2024; trucks (-17.2%), motorcycles (-12.9%), cars (-12.2%) and pedestrians (-10.4%) are below it.
- Motorcycles have 13.0% of their accidents in winter and 32.6% in summer; bicycles and mopeds also peak in warm months. Pedestrians are the reverse (28.0% winter, 21.3% summer; December index 123). Per day, January is the quietest month for all accidents (84.8 a day), not February (91.2): February's low index is partly its length. In 2020-2021 the spring share is lower for every group (20.6% against 25.1% before); from 2022 the pattern looks like before.

**Limits.** Counts, not rates: a common road user appears often for that reason alone. The seasonal explanations (riding in good weather, darker months for pedestrians) were not tested.

![Accidents per road-user group](accidents_per_road_user.png)

![Annual change per road-user group](annual_change_per_road_user.png)

![Monthly seasonal index](monthly_seasonal_index_heatmap.png)

## 2. Step 2: severity per road-user group

**Method.** For every group: the shares of its accidents that are fatal, seriously injured and slightly injured, with 95% Wilson intervals, the ratio and the gap in points against all accidents, for all years together and for the three periods. The stacked distribution splits the fatal class into classes 1 and 2.

{{step2}}

**Findings.**
- The fatal share is highest for trucks (5.1%, 3.6 times the 1.4% of all accidents), motorcycles (2.8%) and pedestrians (2.0%) and lowest for mopeds (0.6%), bicycles (0.9%) and passenger cars (1.3%). The intervals of trucks and motorcycles do not overlap that of all accidents.
- Bicycle accidents are less often fatal but more often seriously injured (10.0% against 8.4% overall); motorcycles have the highest serious share (16.2%).
- The fatal share of all accidents falls from 1.54% (2017-2019) to 1.47% (2020-2021) and 1.29% (2022-2024).

**Limits.** These are the severities of the accidents a group is part of, not the harm to that group's own members, and shares given that an accident happened, not risks. Intervals assume independent accidents, which is slightly optimistic because one accident can count for two groups.

![Severity intervals](severity_intervals.png)

![Severity distribution](severity_distribution.png)

## 3. Step 3: geography of vulnerable road users

**Method.** (a) Cyclists by municipality: the number of accidents involving cyclists and their share of all the municipality's accidents (shares for municipalities with 100+ accidents), mapped as a bubble map and a choropleth with five quantile classes. (b, c) Hotspots for pedestrians, motorcycles and mopeds in 500 m squares of the Lambert grid (#86), for all years and for 2022-2024 (when coordinates are most complete); the 20 busiest squares are ranked and named after the municipality where most of their accidents are. Accidents without usable coordinates are left out of the maps and counted separately.

**The ten municipalities with the most accidents involving cyclists** (71,881 accidents in 577 of the 581 municipalities).

{{step3_top}}

**The five highest cyclist shares (municipalities with 100+ accidents).**

{{step3_share}}

**Findings.**
- Cyclists are in 24.8% of all accidents; by region 33.5% in Flanders, 21.8% in Brussels and 7.0% in Wallonia. Wherever cyclists are more than a third of the accidents, the municipality is in Flanders.
- Pedestrians: 17 of the 20 busiest squares are in the Brussels area, 2 in Antwerp and 1 in Liege; the busiest (Antwerp) has 82 accidents, only 0.31% of all located pedestrian accidents. Motorcycles: all 20 are in the Brussels area (busiest 41). Mopeds: 12 in Antwerp, 4 in Gent, 2 in Brussels, 1 in Charleroi, 1 in Knokke-Heist (busiest 45).
- About two thirds of the hotspot squares come back in 2022-2024 (12, 16 and 12 of 20 for pedestrians, motorcycles and mopeds).

**Limits.** Counts favour big cities; there are no population or traffic figures. Hotspots are where accidents are counted, which is mostly where many people and vehicles are. 10-13% of accidents have no coordinates (3-5% in 2022-2024), more in Wallonia, so Walloon hotspots may be understated. A different square size would give different ranks.

![Cyclist accidents per municipality](geo_a_bubble_map.png)

![Pedestrian hotspots](geo_b_pedestrian_hotspots.png)

## 4. Step 4: regional severity, concentration and density

### 4a. Regional severity

**Method.** Fatal and serious shares per region and province, for all accidents and for cyclists, pedestrians, motorcycles and mopeds, and per road type (motorway, regional road, municipal road).

{{step4_regions}}

**Findings.** Wallonia has a fatal share 1.6 times that of Belgium, and Brussels 0.29 times; the serious-injury share goes the other way. The province with the highest fatal share is Luxembourg (3.37%), then Namur (2.95%) and Hainaut (2.17%); the lowest are Antwerp (1.04%) and Brussels (0.42%). The serious share is highest in West Flanders (11.5%). The order Brussels, Flanders, Wallonia in the fatal share holds for all four groups and on every road type: motorways 4.01% in Wallonia against 2.39% in Flanders, regional roads 2.54% against 1.22%, municipal roads 1.52% against 1.02%.

### 4b. Concentration against severity

**Method.** Each accident gets the number of accidents in its 500 m square (accidents with coordinates, two periods; classes 1, 2-4, 5-9, 10-19, 20-49, 50-99, 100+ (#100)); separately, municipalities are put in five equal-sized classes of accidents per km2 per year of the group, using the municipality areas from the Statbel outlines. Spearman's rank correlation links municipality density to severity (municipalities with 100+ accidents; for a group, 30+ of its accidents).

{{step4_squares}}

{{step4_density}}

{{step4_rho}}

**Findings.** The busier the place, the less severe the accidents. For all accidents the fatal share falls from 3.00% in squares with one accident to 0.37% in squares with 100 or more (the serious share from 12.5% to 5.1%), and from 3.66% in the least dense fifth of municipalities to 0.80% in the densest. The same direction holds for cyclists (fatal 1.93% to 0.17%) and pedestrians (4.29% to 0.70%), motorcycles and mopeds, and in 2022-2024. Hotspots are therefore not the deadliest places: an isolated pedestrian accident is fatal in 4.3% of cases, one in a busy square in under 1%. This is an association: dense places differ in speed, road types and the mix of accidents, and density is accidents per km2, not per vehicle.

### 4c. Regions within the same density

**Method.** Is the Wallonia-Flanders gap still there when municipalities of the same accident density (and road type) are compared? Two ways. (1) Direct standardisation: Wallonia's share if it had Flanders' mix of strata (5 density classes, or 15 strata of density class and road type), with the ratio against the crude Wallonia share. (2) A logistic regression of the outcome on region, then adding density class, then adding road type, estimated on aggregated cells (33 cells) with 1,000 multinomial bootstrap repetitions for the intervals; I checked the coefficients against a hand-written iteratively reweighted least squares fit. Brussels is only in the densest class, so the comparison is mostly Wallonia against Flanders.

**Odds ratio Wallonia against Flanders, all accidents.**

{{step4_logit}}

**Findings.** At the same accident density Wallonia's fatal share stays 36-48% higher than Flanders' in every density class (ratios 1.48, 1.36, 1.36, 1.37 and 1.44; overall 1.84). The adjusted fatal odds ratio falls from 1.86 to 1.39 (same density class) and 1.35 (also same road type; 95% interval 1.25-1.44): density and road type explain more than half of the excess and roughly 40% of it remains. The serious-injury gap goes the other way and widens when matched (0.72 crude, 0.60 at the same density and road type). By group (fatal, density plus road type): mopeds 1.70 (the gap remains), pedestrians 1.23 and motorcycles 1.21 (borderline), cyclists 0.69 (no clear gap: the interval of the standardised ratio includes 1).

**Limits.** Only density and road type are matched; speed limits, vehicle mix, enforcement, emergency response and how classes are recorded are not. That Flanders has more serious but fewer fatal accidents than Wallonia could be real or a recording difference; I did not test it.

![Fatal and serious share per region and province](severity_regional_overview.png)

![Severity by square concentration](severity_by_square_concentration.png)

![How much of the Wallonia-Flanders gap remains](severity_regions_gap_adjusted.png)

## 5. Step 5: logistic models of severity

### 5a. Specification

**Outcome and variables.** Severe = 1 for classes 1-3 and 0 for class 4 (#116). Explanatory variables: road-user group, year (categories, reference 2017), month (categories, reference January) (#124), region, road type, intersection, lighting, weather, road surface and collision type. Reference categories (#128): Flanders, municipal road, not at an intersection, daylight, normal weather, dry road, rear-end collision between two drivers; baseline road-user group: passenger car only.

**Road-user group (#117, #120).** Because every accident has two road-user roles and their meaning is undocumented, the baseline uses one yes/no variable per group involved (road user 1 OR 2); passenger car is the omitted group, so every odds ratio compares with a car-only accident. "Single road user" is its own yes/no variable in the models without collision type; with collision type it is perfectly collinear with the single-user collision types and carried by them. In the four group models (cyclists, pedestrians, motorcyclists, mopeds) the variable is the counterpart in the accident (car, van, truck, bus, motorcycle, moped, bicycle, pedestrian, other, unknown, or the same group on both sides).

**Categories (#118, #125, #129).** Unknown stays a category. In weather, road surface and lighting, categories with fewer than 100 accidents on all accidents are merged into "Other / combined" (for example the combinations "Rain + Hail" and "Ice, snow + Clean"), so every model uses the same categories. Within a model, a category with fewer than 30 accidents or with no severe or no non-severe accident is merged into "Other / combined" or into the reference; all merges are saved in `severity_logit_category_merges.csv`.

**Accidents, not participants; clustering (#121).** A row is an accident and carries two roles, and accidents in the same municipality are correlated: across the 504 municipalities with 100+ accidents the severe share runs from 2.5% to 24.8% (standard deviation 4.2 points, against 1.8 expected by chance). The coefficients are the ordinary logistic ones; the standard errors are cluster-robust by municipality (581 clusters, 568-578 in the group models), with the small-sample factor G/(G-1) x (N-1)/(N-k).

**Estimator (#122).** Newton-Raphson (iteratively reweighted least squares) with step-halving and the cluster-robust sandwich, written in the script. Checks: the fast sandwich equals a slow loop version on a test example; the coefficients equal scikit-learn's for the baseline and the moped model; the mean predicted probability equals the observed rate in every model. Nothing was installed in the course environment.

**Collision type (#119).** Collision type is almost determined by the road users. In every model the term "with a pedestrian" is 99.3-99.8% identical to the pedestrian road-user term and the model cannot separate them (coefficients ran off to plus and minus 30 in the first attempt), so the collision-type term is left out and the road-user term stays. Each model was also estimated without collision type.

### 5b. Fit and clustering

{{step5_fit}}

AUC is in-sample (the models were fitted on the same accidents), so it is somewhat optimistic; low McFadden R2 values are normal for accident data. "ICC outcome" is the share of the variation in severe that lies between municipalities; "ICC residual" is what remains after the covariates. The SE ratio is the cluster-robust standard error divided by the ordinary one: on average 1.11 in the baseline, but up to 3.8 for region-level terms, so ignoring the clustering would overstate certainty most for place effects. The highest variance inflation factor is 5.6 (baseline), so no strong overlap remains between the variables.

### 5c. Adjusted odds ratios

Adjusted odds ratios of a severe accident with cluster-robust 95% intervals; * = significant at 5%; models as specified (with collision type).

{{step5_or}}

**Road users in the baseline** (odds ratio against a car-only accident):

{{step5_users}}

**Counterpart in the group models** (odds ratio against a passenger car; * = significant at 5%):

{{step5_counterpart}}

**Findings.**
- Against a car-only accident the odds of a severe accident are 3.44 times higher with a motorcycle and 3.32 times with a pedestrian, 2.94 with a truck, 1.77 with a bicycle and 1.22 with a moped.
- A truck as counterpart is the strongest risk factor in every group model (5.22 for pedestrians, 4.26 for cyclists, 2.63 for mopeds, 2.26 for motorcyclists).
- Night without public lighting raises the odds (1.78 in the baseline, 2.04 for pedestrians, 2.01 for motorcyclists). Brussels has much lower odds than Flanders in every model (0.29 to 0.41), Wallonia somewhat lower (0.74 to 0.81). This differs from the raw fatal shares of step 4 because "severe" is dominated by serious injuries, and Flanders has the higher serious share.
- A motorway raises the odds for pedestrians a lot (6.32) and for cyclists (1.45), but not significantly for motorcyclists and mopeds. 2024 is below 2017 in the baseline (0.85) and for pedestrians and mopeds; the 2020 coefficient is not different from 2017 except for mopeds (0.83).

**Collision type changes the road-user terms** (baseline, odds ratio with and without collision type):

{{step5_withwithout}}

### 5d. Interactions between road users in the same accident (#123)

**Method.** The baseline plus interaction terms for the 22 pairs of groups that occur together in at least 500 accidents (Unknown excluded), tested jointly with a Wald test using the cluster-robust covariance. A second test checks whether the order (road user 1 or 2) matters for the 10 main pairs (at least 2,000 accidents). For each pair the table gives what the baseline predicts by adding the two group effects ("additive"), the odds ratio with the pair's own effect, and the pair term (a ratio of odds ratios).

{{step5_wald}}

{{step5_pairs}}

**Findings.** The road users in one accident do not simply add up (p < 10^-180, and AIC drops from 175,769 to 174,990). Bicycle + pedestrian is far less severe than the two effects added (pair term 0.33), as are moped + bicycle (0.34) and car + bicycle (0.78); car + motorcycle (1.48) and truck + bicycle (1.19) are worse than additive, and truck + bicycle has the highest severe share of any pair (28.3%). The order of road user 1 and 2 also matters jointly (p = 2 x 10^-9): with a car as road user 1 and a pedestrian as road user 2 the odds are 1.51 times those of the reverse order, and for car + bicycle 1.17. Because the meaning of the two roles is undocumented I report this and do not interpret it.

### 5e. Predicted probabilities and typical situations (#126, #130, #131)

**Method.** Average adjusted predicted probability: for each category of a variable everyone in the model's sample is set to that category, all other variables stay as observed, and the predicted probabilities are averaged (average adjusted prediction). Intervals come from 1,000 draws of the coefficients from their cluster-robust sampling distribution. The four situations (all in 2024) are A: daytime urban (municipal road, daylight, normal weather, dry, not at an intersection, June, Flanders); B: night without public lighting (regional road, October, Wallonia); C: wet junction (regional road, daylight, rain, wet road, at an intersection, November, Flanders); D: Brussels junction (municipal road, daylight, normal, dry, at an intersection, June, Brussels). Collision type: the most common one in each model's sample.

{{step5_scen}}

**Findings.** In a daytime urban situation the predicted probability is 5.1% for a car-only accident, 8.6% for a bicycle against a car, 15.0% for a pedestrian and 15.5% for a motorcycle; at night without public lighting on a regional road in Wallonia the pedestrian model gives 22.0% and the motorcyclist model 28.5%. The models cover different accidents, so the levels of the five models differ by design.

![Odds ratios: region, road type, intersection and lighting](logit_forest_1_place_road_light.png)

![Odds ratios: the road users](logit_forest_4_road_users.png)

![Predicted probabilities by category](logit_predicted_by_category.png)

![Predicted probability in four situations](logit_scenarios.png)

![Interactions between road users](logit_interactions_pairs.png)

![Calibration](logit_calibration.png)

**Limits.** Associations, not causes: speed, traffic, vehicle type and helmet use are not in the data. An accident involving a cyclist and a pedestrian is in both group models. Brussels has fewer accidents in the group models, so its intervals are wider. The models were not tested on other data.

## 6. The interactive tools and how they were checked

**Streamlit tool (`app.py`).** One sidebar for all analyses (period, road users with an overlap switch, region, province and municipality, road type, intersection, lighting, weather and road surface), with the analyses overview and severity, compare groups (crude and adjusted), time, geography and hotspots, regions and concentration, statistical models (estimated live on the selection, with safeguards: at least 1,000 accidents and 100 severe ones) and the fixed study results (#132-#144). Every number is calculated from the filtered accidents. Exports: the filtered accident data as CSV, tables as CSV or one Excel workbook, charts as PNG or interactive HTML, and a ZIP package with a README that records the filters.

**Checks.** With no filters the tool reproduces the saved results of steps 1 to 3 exactly (severity counts and intervals for all groups, annual counts, seasonal index, the busiest pedestrian square of 82 accidents in Antwerpen, the municipality table). The live models reproduce the saved coefficients, robust standard errors, AUC and AIC of step 5 up to the rounding of the saved files, and the predicted probabilities to 0.0002. The app ran without errors in all analyses and in 18 filter scenarios including one year, one municipality, no groups chosen and a selection too small for a model. A private claude.ai page shows the saved results of steps 1-5 and was tested in headless Chrome (light and dark mode, phone width, strict security policy).

## 7. Limits, open questions and what was not done

- **No rates.** Without traffic, population or exposure figures nothing here says which road user is riskier per kilometre or per person.
- **Missing and unknown information.** About 10-13% of accidents have no coordinates and about 10% have an unknown road user. Unknown weather and road surface have lower severity, which looks like a recording pattern. Missing coordinates are not random (more in Wallonia and before 2022).
- **Not tested.** Whether the Wallonia-Flanders difference between fatal and serious accidents comes from how classes are recorded; why empty coordinates jump in Brussels in 2024; the difference between the classes "with fatalities" and "fatally injured".
- **Not done.** Urban against rural (#55); a mixed model with a random municipality effect (#121); a model of fatal outcomes only (#116: too few events in the group models, for example 133 for mopeds); an out-of-sample test of the models; a second cluster definition such as 500 m squares.
- **Interpretation.** The pre, during and post "Covid-19" periods are my own definition. All results are associations.

## Where to find things

- Decisions and reasons: `beslissingslogboek.md` (#1-#154).
- Code: `scripts/` (steps 8-23), the dashboard in `dashboard_*.py`, the interactive tool in `app.py`, `tool_*.py` and `logit_live.py`.
- Result tables and charts: `reports/`.
- The short version of this report: `reports/findings_summary_steps_1_5.md`.
