# How the five steps were modeled: the technical underpinnings

Plain-language method report for the five steps of the Belgian road-accident analysis 2017-2024 (289,532 accidents). It explains, for each step, **what kind of model or calculation was used, what it assumes, how it works inside, how it was checked, and where it stops being reliable**. It does not repeat the findings (see `findings_summary_steps_1_5.md` and `findings_technical_report_steps_1_5.md`); it explains the machinery behind them, so that every number can be defended without AI. `#n` points to an entry in `beslissingslogboek.md`, where the decision and its reason are written down; `scripts/NN` points to the code.

**What "model" means here.** Steps 1 to 4 are *descriptive models*: carefully defined counts, shares, indexes, groupings and comparisons that turn accident rows into results, with uncertainty added where it matters. Step 5 is a *statistical model*: a logistic regression that estimates how several factors together relate to the chance that an accident is severe.

| Step | Question | Kind of model | Code |
|---|---|---|---|
| 1 | Which road user bears the greatest burden? | Counts, shares, indexes over time and season | `scripts/07-09` |
| 2 | Who experiences the most severe outcomes? | Proportions with Wilson intervals, ratios and gaps | `scripts/12` |
| 3 | Where are vulnerable road users most exposed? | Aggregation by municipality; grid-square hotspot ranking | `scripts/13-14`, `24` |
| 4 | Do regions differ, and does concentration go with severity? | Stratified comparison; density classes and rank correlation; direct standardisation; logistic regression on aggregated cells | `scripts/15-17` |
| 5 | Which factors raise the chance that an accident is severe? | Logistic regression with cluster-robust standard errors, interactions, simulated predictions | `scripts/20-21` |

## 0. The foundations shared by all five steps

### 0.1 The unit of analysis: one row is one accident

The data are *accident-level*, not person-level: one row per accident, with the road-user type of up to two parties (road user 1 and road user 2), the conditions (weather, light, road type, road surface, junction, collision type), the place, and one **accident class** for the whole accident. There is no identifier to prove that a row is a unique accident (#20), so possible duplicates were flagged and kept. Nothing was filled in or removed for empty cells; "Unknown" stays a category (#18, #22).

**Consequence for every model:** the severity belongs to the accident, not to a person. In a car-pedestrian accident the same class is attached to the pedestrian group and to the car group. All results therefore describe *the accidents a group is part of*, not the harm to that group's own members.

### 0.2 The counting rule (#33)

An accident counts for a road-user group if that group is road user 1 **or** road user 2, once per accident. So a car-bicycle accident counts for cars *and* for bicycles. This has three technical consequences:

- Group counts add up to more than the number of accidents (136,144 accidents involve two different groups), and shares of groups add up to more than 100%.
- The groups overlap, so they cannot be treated as independent samples in any test (this is why step 2's intervals are slightly optimistic, and why step 5 uses yes/no variables per group involved rather than one category).
- The meaning of "road user 1" versus "road user 2" is not documented, so the *order* is not interpreted, except where it is explicitly tested (step 5).

### 0.3 The severity coding (#71, #116)

| Name | Accident classes | Share of all accidents |
|---|---|---|
| Fatal | class 1 (with fatalities) + class 2 (fatally injured) | 1.43% |
| Serious | class 3 (with seriously injured) | 8.42% |
| Slight | class 4 (with slightly injured) | 90.15% |
| Severe (step 5) | classes 1 + 2 + 3 | 9.85% (28,532 accidents) |

"Severe" is used in the regression because fatal accidents alone are too few in the smaller groups (133 for mopeds) to estimate a model with many variables.

### 0.4 Uncertainty: the 95% Wilson interval (#74)

Every share (for example "5.1% of truck accidents are fatal") is a *sample proportion*, so it carries uncertainty. The interval used is the **Wilson score interval**. In words: it asks "which true shares are still plausible given k events out of n accidents?" and returns the range of those shares at the 95% level. Compared with the simple textbook interval (share ± 1.96 standard errors) it behaves well when the share is close to 0 or 100% or the count is small, and it never leaves the 0-100% range. That matters here because many fatal shares are around 1%.

*Assumption:* accidents are independent draws. This is slightly optimistic, because one accident can count for two groups and accidents in one municipality resemble each other (step 5 deals with the second point explicitly).

### 0.5 The small-number rule (#141 and others)

Shares and rates based on very few accidents jump around. Rule used throughout: **no share under 30 accidents; flagged as unstable between 30 and 99; municipality shares are only ranked from 100 accidents of any kind** (#88). In the interactive tool a live model needs at least 1,000 accidents and 100 severe ones.

### 0.5b Geography basics

Coordinates are Belgian Lambert 1972 (EPSG:31370, metres), so distances and square sizes are real metres. Two impossible coordinates (values around 10^16) are treated as missing (#90). About 12% of accidents have no coordinates (more in Wallonia and before 2022), so everything map-based uses a subset of accidents; the share left out is always reported. Municipality outlines come from the Statbel statistical sectors of 2023 (CC BY 4.0), joined into 581 municipalities.

### 0.6 How correctness was protected

- Every analysis is a script with the decision numbers in its header, runnable from the command line.
- Scripts contain checks that stop the run if a total is wrong (for example the 28,532 severe accidents, the 71,881 cyclist accidents).
- Each later tool (Streamlit app, claude.ai page, reports) is checked against the saved results of the scripts: with no filters it must reproduce them.
- A mistake that was caught this way: the number of severe accidents was first written as 28,517 in a check; the data say 28,532, and the script and log were corrected (#116).

## 1. Step 1: the burden per road-user group

**Question.** How many accidents involve each road-user group, how did that change over the years, and in which months?

**The model.** Pure counting, followed by three transformations that make groups and periods comparable.

1. **Count and share.** For each group, the number of accidents it is involved in, and that number divided by all 289,532 accidents.
2. **Index over time (step 1b).** Accidents per year for each group, divided by the group's accidents in the first year and multiplied by 100 (2017 = 100). The index removes the different sizes of the groups, so a small group (buses) and a large one (cars) can be compared by *change*. The effect of the pandemic is read from three periods that I defined myself: pre 2017-2019, during 2020-2021, post 2022-2024; the average per year in post is compared with pre. The data state no cause for any change.
3. **Seasonal index (step 1c).** For each group, the share of its accidents that falls in a month (or in a season), divided by the share that an even spread would give (8.33% per month, 25% per season) and multiplied by 100. 100 means an average month; 123 means 23% more accidents than an even spread. Seasons are *meteorological* (winter = December to February), in whole months, because the data have no day (#53).
4. **Per day.** Because the seasonal index does not correct for the length of a month (February has 28 or 29 days), accidents per day is also given (January is the quietest month per day, not February).

**Assumptions and choices.** Counting rule of section 0.2. Shares of groups can overlap. "Unknown" and "Other road user" are separate lines and are hidden by default in the graphs. An urban-against-rural comparison was dropped because the data have only "built-up area" and no official urban/rural classification (#55).

**Checked.** The group totals equal those of the first count (the script stops if they differ); the interactive page's browser calculations equal the Python tables to 10^-6 (the page recalculates 1a to 1c in JavaScript from a summary table).

**Limits.** These are counts, not rates: a road user that is common on the road appears often for that reason alone. "Unknown" more than doubles from 2017 to 2024, so part of the decline of named groups may be recording that moves into "Unknown". Explanations such as riding in good weather were not tested.

## 2. Step 2: severity per road-user group

**Question.** Of the accidents a group is involved in, how many are fatal, seriously injured or slight?

**The model.** For each group *g* and each severity class: the proportion *p = k / n* (k accidents of that class among the n accidents of the group), with a 95% Wilson interval, plus two comparisons with all accidents: the **ratio** (p of the group divided by p of all accidents) and the **gap in percentage points**. This is done for all years together and for the three periods. The stacked distribution splits the fatal class into classes 1 and 2.

**Why proportions and not counts.** A group with many accidents (cars) has many fatal accidents in absolute terms even if the fatal *share* is low. Proportions answer "how severe are the accidents of this group", counts answer "how many".

**Assumptions.** Independence of accidents for the intervals (slightly optimistic, section 0.4); the counting rule (a truck-pedestrian accident counts for both groups).

**Checked.** With no filters the interactive tool reproduces the saved severity tables and intervals for all groups.

**How to read it.** A group's fatal share of 5.1% (trucks) against 1.4% for all accidents means: *accidents that involve a truck are fatal 3.6 times as often as accidents in general*. It does not mean that truck drivers die more often (the dead are often in the other vehicle), and it is not the risk of having an accident.

## 3. Step 3: where are vulnerable road users most exposed?

Two different models, both aggregation-based.

### 3a. Cyclists by municipality

**The model.** For each of the 581 municipalities: the number of accidents involving cyclists, and the cyclist share of *all* accidents in the municipality. Results are shown as ranked bars, a bubble map (a bubble at the average position of the municipality's accidents, sized by count, coloured by share) and a choropleth (municipalities coloured by value in **five quantile classes**: the class limits are chosen so that each class holds about the same number of municipalities, which keeps a skewed distribution readable).

**Choices and assumptions.** No rate per inhabitant: the data have no population or traffic figures (#81). The share is only ranked for municipalities with at least 100 accidents of any kind (#88), because a share of 3 accidents out of 5 would otherwise top the list. A municipality outline is needed for the choropleth: the 19,795 Statbel statistical sectors were joined into 581 municipality shapes and simplified by 50 m (#84).

### 3b/3c. Hotspots on a grid

**The model.** A **grid-square count**. The map is divided into squares of 500 m by 500 m aligned to multiples of 500 m in Belgian Lambert 1972 (#86): the square of an accident is `(floor(x / 500), floor(y / 500))`. For each group (pedestrians, motorcycles and mopeds are analysed separately, #80) the accidents in each square are counted, the squares are ranked, and the **20 busiest squares** are called hotspots (#87); each hotspot is named after the municipality that holds most of its accidents. The analysis is done for all years and for 2022-2024 only (the years with the fewest missing coordinates, #83).

**Why grid squares.** The alternatives I considered were a smoothed density surface (kernel density) and clustering (DBSCAN) (#85). A grid count has no tuning parameters beyond the square size, is easy to reproduce and to explain, and gives exact counts per square. Its drawback: the result depends on the square size and on where the grid starts (a hotspot split across two squares looks weaker).

**Assumptions and checks.** Only accidents with usable coordinates are placed on the map (the left-out share is reported per group and period). A check confirms that coordinates fit their municipality (a point should lie inside its own municipality). The cell counts add up to the located accidents of the group.

**Limits.** Hotspots are where accidents are *counted*, which is mostly where many people and vehicles are; they are not a risk measure. Walloon hotspots may be understated because more Walloon accidents lack coordinates.

## 4. Step 4: regions, concentration and density

### 4a. Regional severity

**The model.** The step-2 proportions, computed per region (3) and province (10; Brussels is its own line), for all accidents and for the four vulnerable groups, with Wilson intervals, the ratio to Belgium and the gap to Belgium. The same is repeated **within each road type** (motorway, regional road, municipal road) to see whether a regional difference is only a difference in road types. This is a *stratified comparison*: it controls for road type and for nothing else (#94).

### 4b. Concentration against severity

**The model.** Two ways to measure "how concentrated are the accidents here" and then look at severity:

1. **Squares.** Each accident gets the number of accidents in its 500 m square (all of the group's accidents in that square; classes 1, 2-4, 5-9, 10-19, 20-49, 50-99, 100+, #100); the severity of the accidents in each class is compared.
2. **Municipalities.** The 581 municipalities are put into five equal-sized classes of **accidents per km2 per year** (quintiles, using the municipality areas from the outlines), and severity is compared across classes. The strength of the relation is summarized by **Spearman's rank correlation** between density and the severe share, over the municipalities with enough accidents (100+; for a group 30+ of its accidents, #102). Spearman works on ranks, so it is not distorted by a few extreme cities and does not assume a straight-line relation.

**What it showed and how to read it.** The busier the place, the less severe the accidents (fatal share 3.00% in squares with one accident, 0.37% in squares with 100 or more; Spearman rho -0.66 across municipalities). It is an *association*: dense places differ in speed, road type and the mix of accidents; density here is accidents per km2, not traffic.

### 4c. Is the Wallonia-Flanders gap still there at the same density?

Wallonia has a higher fatal share than Flanders. Is this just because Walloon municipalities are less dense? Two adjusted comparisons answer it.

**Direct standardisation.** Take Flanders' mix of strata (for example what share of its accidents lie in density class 1, 2, ... or in each density class by road type), and calculate what Wallonia's fatal share *would be* if Wallonia had exactly that mix: the sum over strata of (Flanders' weight x Wallonia's share in that stratum). The ratio of Wallonia's crude share to this standardised share shows how much of the gap is due to a different mix. Strata with fewer than 100 accidents are flagged.

**Logistic regression on aggregated cells.** A model for the chance that an accident is fatal, with region, then region plus density class, then region plus density class plus road type. The **odds ratio** for Wallonia against Flanders is the gap that remains after those factors are accounted for: it fell from 1.86 (region only) to 1.39 (same density) and 1.35 (also same road type; 95% interval 1.25-1.44), so density and road type explain more than half of the excess and about 40% remains. The model is fitted on *aggregated* counts (33 cells of region x density x road type, with the number of fatal and non-fatal accidents in each), and the intervals come from **1,000 bootstrap repetitions** (resampling the cell counts from a multinomial distribution). The coefficients were checked against a hand-written iteratively reweighted least-squares fit.

**Assumptions and limits.** Only density class and road type are controlled for; speed limits, vehicle mix, enforcement, emergency response and how classes are recorded are not. Brussels lies only in the densest class, so the adjusted comparison is mostly Wallonia against Flanders. That Flanders has more *serious* but fewer *fatal* accidents than Wallonia could be real or come from how the classes are recorded; I did not test it.

## 5. Step 5: logistic models of accident severity

This is the only step that uses a *statistical model* in the usual sense. It asks: when many factors are considered at the same time, which of them go with a higher chance that an accident is severe?

### 5.1 Why a logistic regression

The outcome is yes/no (**Severe = 1** for classes 1-3, 0 for class 4). An ordinary straight-line (linear) regression can predict values below 0 or above 1; a **logistic** regression keeps every prediction between 0 and 1 by modeling the *log-odds* of the outcome. **Odds** are "severe compared with not severe": if 1 accident in 10 is severe, the odds are 1 to 9 (0.11). The model says

`log-odds of severe = b0 + b1 x (factor 1) + b2 x (factor 2) + ...`

Each coefficient b is the change in the log-odds when its factor changes by one step, with all other factors kept the same. The **odds ratio** is `exp(b)`: how many times higher the odds are. An odds ratio of 3.44 for a motorcycle means that, other things equal, the odds of a severe accident are 3.44 times those of the reference accident. Odds ratios are not the same as ratios of probabilities (which is why predicted probabilities are also given, section 5.7).

### 5.2 The variables and how they are coded

Explanatory variables (as requested): road-user group, year, month, region, road type, intersection, lighting, weather, road surface and collision type. Every category variable becomes a set of 0/1 columns ("dummy variables"), one per category, **except a reference category** that everything is compared against (#128): Flanders, municipal road, not at an intersection, daylight, normal weather, dry road, rear-end collision between two drivers, year 2017, month January (year and month are categories, not straight lines, #124). **Unknown** is its own category (#118).

**Road users (#117, #120).** Because every accident has two road-user roles whose meaning is not documented, the baseline model uses *one yes/no variable per group involved* (road user 1 or 2), with "passenger car" as the omitted group: every road-user odds ratio compares with an accident with cars only. In the four group models (cyclists, pedestrians, motorcyclists, mopeds) the road-user variable is the **counterpart**: who the focal group collided with (car, van, truck, bus, ..., the same group on both sides).

**Small categories (#125, #129).** A category with fewer than 100 accidents on all accidents is merged into "Other / combined" for weather, road surface and lighting, so every model uses the same categories; inside a model, a category with fewer than 30 accidents, or with no severe or no non-severe accident, is merged too (it would give an unstable or infinite estimate). All merges are saved in `severity_logit_category_merges.csv`.

**Collision type (#119).** Collision type is nearly determined by the road users: the term "with a pedestrian" is 99.3-99.8% identical to the pedestrian road-user term, so the model cannot tell them apart (in the first attempt the coefficients ran off to plus and minus 30, a classic sign of collinearity). The collision-type term is left out where this happens, and every model is also estimated **without collision type**, so the effect of that choice is visible (the pedestrian odds ratio is 3.32 with collision type and 2.54 without).

### 5.3 How the model is estimated (the estimator, #122)

The coefficients are found by **maximum likelihood**: choose the b's that make the observed pattern of severe and non-severe accidents most probable. There is no formula for this, so it is done by an iterative method:

1. Start with all coefficients at zero except the intercept (the overall log-odds).
2. From the current coefficients, calculate each accident's predicted probability and how much weight it should get (accidents with probabilities near 0.5 carry more information than those near 0 or 1).
3. Take one **Newton-Raphson** step: solve a weighted least-squares problem that points toward better coefficients. (This is the same as *iteratively reweighted least squares*.)
4. **Step-halving:** if the step does not increase the likelihood, halve it until it does. This prevents the method from jumping past the answer when the problem is hard (it was needed for the motorcyclist model).
5. Stop when the largest change is below 10^-9.

The estimator is written in `scripts/20` with numpy, not taken from a package, so that every step could be inspected. It was **checked** before use: on a test example the coefficients equal scikit-learn's to 10^-6, and in every model the mean predicted probability equals the observed severe rate (a property that a correctly fitted logistic model must have).

### 5.4 Accidents are not independent: clustered standard errors (#121)

The ordinary standard errors assume that every accident is an independent observation. Here they are not: accidents in the same municipality share roads, recording habits and traffic. Across the 504 municipalities with 100+ accidents the severe share runs from 2.5% to 24.8% (standard deviation 4.2 percentage points, against 1.8 expected by chance alone).

The coefficients stay the ordinary logistic ones, but their uncertainty is recalculated with a **cluster-robust ("sandwich") variance**: scores (each accident's "push" on the coefficients) are added up within each municipality first, and the uncertainty is measured from how much those cluster totals vary; a small-sample correction factor G/(G-1) x (N-1)/(N-k) is applied (G = 581 municipalities). Two summary numbers describe how much clustering matters:

- **Intraclass correlation (ICC):** the share of the variation in "severe" that lies *between* municipalities (0.016 in the baseline; what remains after adding the factors is smaller still). It is estimated with a one-way analysis-of-variance formula that allows clusters of unequal size.
- **Standard-error ratio:** cluster-robust standard error divided by the ordinary one: on average 1.11 in the baseline but up to 3.8 for region terms. Ignoring the clustering would overstate certainty most for place effects.

*Checked:* the fast vectorised sandwich equals a slow loop version on a test example to 10^-10.

**What was not done:** a mixed model with a random effect per municipality (it would also give a municipality-level variance, but is heavier and was left out, #121); a second cluster definition such as 500 m squares.

### 5.5 Five models (#115)

| Model | Accidents | Severe | Road-user variable |
|---|---|---|---|
| Baseline (all accidents) | 289,532 | 28,532 | one yes/no per group involved |
| Cyclists | 71,881 | 7,852 | counterpart |
| Pedestrians | 29,897 | 3,820 | counterpart |
| Motorcyclists | 19,792 | 3,749 | counterpart |
| Mopeds | 23,258 | 1,985 | counterpart |

An accident with a cyclist and a pedestrian is in both group models. The five models cover different accidents, so their *levels* (intercepts, predicted probabilities) differ by design; what is compared is the pattern of odds ratios.

### 5.6 Do road users in the same accident simply add up? Interactions (#123)

**The model.** The baseline plus **pair terms** for the 22 pairs of groups that occur together in at least 500 accidents ("Unknown" pairs excluded). A pair term lets the effect of, say, bicycle + pedestrian differ from what the two separate effects add up to. It is reported as a ratio of odds ratios (1 = the effects simply multiply; below 1 = less severe than expected, above 1 = more severe).

**The test.** The 22 pair terms are tested **jointly with a Wald test** using the cluster-robust covariance (do all of them together improve on the baseline?). A second Wald test checks whether the **order** (road user 1 or 2) matters for the 10 main pairs (at least 2,000 accidents). The AIC (a fit-with-penalty measure) also falls from 175,769 to 174,990 when the terms are added.

**Result and caution.** The road users do not simply add up (p < 10^-180), and the order matters jointly too (p = 2 x 10^-9). Because the meaning of the two roles is undocumented, the order effect is reported but **not interpreted**.

### 5.7 Predicted probabilities (#126, #130, #131)

Odds ratios are relative; people also want absolute chances. Two tools are used:

- **Average adjusted prediction.** For each category of a variable, *everyone* in the model's sample is set to that category, all other variables stay as observed, the predicted probabilities are calculated and averaged. This answers "what would the average severe probability be if everyone had this category?".
- **Intervals by simulation.** 1,000 sets of coefficients are drawn from a normal distribution with the estimated coefficients as mean and the cluster-robust covariance as spread; the prediction is recalculated for each draw; the 2.5th and 97.5th percentiles are the 95% interval.
- **Four typical situations** (all in 2024): A daytime urban (municipal road, daylight, normal weather, dry, not at a junction, June, Flanders); B night without public lighting (regional road, October, Wallonia); C wet junction (regional road, daylight, rain, wet road, at a junction, November, Flanders); D Brussels junction. For example in situation A the predicted severe probability is 5.1% for a car-only accident, 8.6% for a bicycle against a car, 15.0% for a pedestrian and 15.5% for a motorcycle.

### 5.8 How well does the model fit? (and what that does not mean)

| Measure | What it is | Result |
|---|---|---|
| McFadden R2 | 1 minus (log-likelihood of the model / log-likelihood of a model with only the intercept) | 0.041-0.069: low, which is normal for accident data (most of what decides severity, such as speed and vehicle, is not in the data) |
| AUC | The chance that a random severe accident gets a higher predicted probability than a random non-severe one (0.5 = coin flip, 1 = perfect) | 0.65-0.68; **in-sample** (measured on the data the model was fitted on), so somewhat optimistic |
| Calibration | Accidents sorted into ten groups by predicted probability; mean predicted against observed severe share | shown per model in the chart `logit_calibration.png`; overall the mean predicted probability equals the observed rate in every model |
| VIF | How much a variable's variance is inflated by overlap with the others | highest 5.6 (baseline): no strong overlap left after the collision-type decision |
| AIC | Fit with a penalty for the number of parameters; lower is better | used to compare a model with and without interaction terms |

**Limits of the models.** All results are associations, not causes: speed, traffic volume, vehicle type and helmet use are not in the data. The models were not tested on other data (no out-of-sample test). A model of *fatal* outcomes only was not made (too few events in the group models). The Covid-19 periods are my own definition.

## 6. How each model was verified

| Step | Check | Result |
|---|---|---|
| All | Script totals stop the run if wrong (289,532 accidents; 28,532 severe; group totals) | passed; one error of my own (28,517 instead of 28,532) was caught and corrected |
| 1 | Browser calculation on the claude.ai page against Python tables | equal to 10^-6 in several scenarios |
| 2 | Interactive tool against the saved severity tables and intervals | equal |
| 3 | Grid-square counts add up to the located accidents (checked in the script); the share of coordinates that lie inside their own municipality is reported | passed / reported |
| 4 | Logistic coefficients against a hand-written IRLS fit; 1,000 bootstrap repetitions for intervals | passed |
| 5 | Coefficients against scikit-learn; fast sandwich against a slow loop; mean prediction equals observed rate; live tool against saved coefficients, standard errors, AUC, AIC | passed (live tool to the rounding of the saved files; predictions to 0.0002) |

## 7. What was deliberately not modeled

- **Rates per exposure.** There are no traffic, population or distance-travelled figures in the accident data, so nothing says which road user is riskier per kilometre or per person (a later extension used Statbel residents; see `hotspot_deep_dive/`).
- **Causes.** Every result is an association.
- **A random-effects (mixed) model** for municipalities, a **fatal-only model**, an **urban/rural split**, and an **out-of-sample test** of the logistic models.
- **Time-series modeling** of the Covid-19 effect: the pre/during/post comparison is descriptive.

## 8. Glossary

- **Odds / odds ratio:** odds are severe compared with not severe; an odds ratio is how many times higher (or lower) the odds are than in the reference situation.
- **Log-odds:** the logarithm of the odds; the scale on which the logistic model is a straight line.
- **Reference category:** the category all others of a variable are compared with.
- **Dummy variable:** a 0/1 column that says whether an accident belongs to a category.
- **Maximum likelihood:** choosing the coefficients that make the observed data most probable.
- **Newton-Raphson / IRLS:** the iterative method used to find them; step-halving prevents overshooting.
- **Cluster-robust standard error:** an uncertainty estimate that allows accidents in the same municipality to resemble each other.
- **ICC:** the share of variation that lies between clusters.
- **Wald test:** a test of whether a set of coefficients is jointly zero.
- **AIC:** a fit measure with a penalty for complexity.
- **AUC:** how well the model ranks severe above non-severe accidents.
- **Wilson interval:** a 95% interval for a share that stays valid for small counts and shares near 0 or 100%.
- **Quantile classes:** map classes chosen so that each holds about the same number of areas.
- **Spearman correlation:** a correlation of ranks that does not assume a straight-line relation.
- **Direct standardisation:** recalculating one group's share as if it had another group's mix of strata.
- **Bootstrap:** repeating a calculation on resampled data (here 1,000 times) to see how much it varies.

## Where to find things

- Decisions and reasons: `beslissingslogboek.md`.
- Code: `scripts/07-09` (step 1), `12` (step 2), `13-14` and `24` (step 3), `15-17` (step 4), `20-21` (step 5); interactive tools `app.py`, `tool_*.py`, `logit_live.py`.
- Results and charts: `reports/`. Findings: `reports/findings_summary_steps_1_5.md` and `reports/findings_technical_report_steps_1_5.md`.
