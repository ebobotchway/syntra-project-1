# Talking notes: Road accidents in Belgium 2017-2024 (steps 1-5)

Notes for presenting the analysis in class. Everything is in plain words, so you can say it aloud. All numbers come from `reports/findings_summary_steps_1_5.md` and the saved tables in `reports/`; `#n` points to an entry in `beslissingslogboek.md`, where the decision and the reason are written down. Read the lines after **Say:** nearly as they are; the lines after **If they push:** are for follow-up questions.

## How to use these notes

Plan for about 25 minutes of talking and 10 minutes of questions. If the slot is shorter, cut the parts marked *(cut first)*.

| Part | What you show | Minutes |
|---|---|---|
| Opening | The question and the counting rule | 2 |
| Step 1 | Burden per road-user group | 4 |
| Step 2 | Severity | 3 |
| Step 3 | Geography (maps) | 4 *(cut first)* |
| Step 4 | Regions and concentration | 5 |
| Step 5 | The models, "One model at a time" | 6 |
| Live demo | Streamlit tool: Compare groups | 4 |
| Limits and close | What the data cannot say | 2 |
| Questions | The question bank below | 10 |

**Before class (10 minutes).**
- Log in to claude.ai in the browser you will present from, open the private page and click through all five steps once. The page needs internet.
- Start the tool: `conda activate syntra-ds`, then in the project folder `streamlit run app.py`. Wait for the first page to load, then run your demo scenario once.
- Open the Word summary (`findings_summary_steps_1_5.docx`) in another window as a backup, and keep these notes open on a second screen or on paper.
- If the internet fails: show the charts from the `reports/` folder (the PNG files) and talk from these notes.

## Opening (2 minutes)

**Show:** the title of the page.

**Say:** "I analysed all 289,532 road accidents in Belgium with injuries between 2017 and 2024. I wanted to know four things: which road user is involved most often, who suffers the most severe outcomes, where vulnerable road users are most exposed, and which conditions raise the chance that an accident is severe."

**Say:** "One rule you need for every number: each row is one accident, not one person. An accident counts once for every road-user group it involves. So an accident between a car and a bicycle counts for cars and for bicycles. That is why the shares add up to more than 100%."

**Say:** "All numbers are counts and shares of accidents. The data has no traffic or population figures, so I can say what happens in accidents, but not which road user is riskier per kilometre."

## Step 1. Which road user bears the greatest burden? (4 minutes)

**Show:** accidents per road-user group, then the annual change chart.

**Say:**
- "Passenger cars are in 70.2% of the accidents, bicycles in 24.8% and pedestrians in 10.3%. Vans 8.1%, mopeds 8.0%, motorcycles 6.8%, trucks 4.4%, buses 1.4%."
- "Nearly every group drops in 2020, the Covid year, and rebounds in 2021-2022."
- "Compare the average of 2022-2024 with 2017-2019: bicycles are up 14.6% and mopeds up 7.3%. Cars (-12.2%), motorcycles (-12.9%), trucks (-17.2%) and pedestrians (-10.4%) are down."
- "Seasons differ: motorcycles have 32.6% of their accidents in summer and 13.0% in winter. Pedestrians are the reverse, with a peak in December."

**If they push:** "The Covid periods (before 2017-2019, during 2020-2021, after 2022-2024) are my own definition; the data does not say anything about a cause." "The category 'Unknown' road user more than doubled from 2017 to 2024, so part of the decline of other groups may be a change in recording. The data cannot show that."

## Step 2. Who experiences the most severe outcomes? (3 minutes)

**Show:** the severity intervals chart.

**Say:**
- "For each group I looked at the share of its accidents that are fatal, seriously injured or slightly injured."
- "1.4% of all accidents are fatal. For trucks it is 5.1%, which is 3.6 times as much. Motorcycles 2.8%, pedestrians 2.0%."
- "Mopeds (0.6%), bicycles (0.9%) and cars (1.3%) are the least often fatal."
- "If I add fatal and serious, motorcycles are at 18.9% and trucks at 17.3%, against 9.9% for all accidents."
- "Bicycle accidents are less often fatal but more often serious: 10.0% against 8.4%."

**If they push:** "These shares describe the accident, not the harm to that group's own members. In a truck accident the dead person is often not in the truck. And they are shares given that an accident happened, not the chance of having one." "The bars have 95% intervals (Wilson); with small groups the interval is wide, which is why I hide numbers below 30 accidents in the tool."

## Step 3. Where are vulnerable road users exposed? (4 minutes, cut first)

**Show:** the cyclist map by municipality, then the "Municipalities: top 20 per road-user group" part of the page (buttons for group, rank by, period and region).

**Say:**
- "71,881 accidents involve cyclists, in 577 of the 581 municipalities."
- "By count: Antwerpen 7,405, Gent 4,229, Brussel 2,478. By share, Haacht, Mortsel and Leuven are above 54%."
- "Every municipality where cyclists are more than a third of the accidents is in Flanders. By region: Flanders 33.5%, Brussels 21.8%, Wallonia 7.0%."
- "For pedestrians, motorcycles and mopeds I used 500-metre squares. Pedestrian and motorcycle hotspots are mostly in the Brussels area; moped hotspots are in Antwerp and Gent."
- "I repeated the municipality view for the other groups. By number the big cities lead: pedestrians Antwerpen 2,687, Brussel 1,637; motorcycles Brussel 1,351, Antwerpen 1,029; mopeds Antwerpen 2,250, Gent 1,215."
- "By share, other places lead. Pedestrians: the Brussels municipalities (Koekelberg 31.5%). Motorcycles: small Walloon municipalities (Stoumont 32.7%, but that is 37 of 113 accidents). Mopeds: Flemish municipalities (Hemiksem 20.3%)."
- "A share needs at least 100 accidents in the municipality; below that a few accidents would decide the ranking."

**If they push:** "Cities have more accidents because they have more people and vehicles; without population or cycling counts these are not rates." "Why are small Ardennes municipalities at the top for motorcycles? I do not know. The data has no speed, road or traffic information, and the shares come from a few dozen accidents." "Between 10% and 13% of accidents have no coordinates, more in Wallonia, so Walloon hotspots may be understated."

## Step 4. Regions and concentration (5 minutes)

**Show:** the regional overview chart, then "How much of the gap remains".

**Say:**
- "Wallonia has a fatal share of 2.26%, Flanders 1.23% and Brussels 0.42%. But Flanders has more serious injuries (9.67% against 7.16% in Wallonia). The order holds for cyclists, pedestrians, motorcycles and mopeds."
- "Busy places are less severe. In squares with one accident, 3.00% are fatal; in squares with 100 or more, 0.37%. An isolated pedestrian accident is fatal in 4.3% of cases."
- "So hotspots are where most accidents happen, not where the deadliest ones happen."
- "Is Wallonia worse only because it is less dense? I compared at the same density and road type. The odds of a fatal accident stay 35% higher in Wallonia than in Flanders (odds ratio 1.35, interval 1.25 to 1.44). Density and road type explain more than half of the gap; about 40% remains."

**If they push:** "This is an association. Dense places differ in speed limits, road type and the mix of accidents; I only matched density and road type." "I did not test whether the Flanders-Wallonia difference comes from how fatal and serious classes are recorded."

## Step 5. The models (6 minutes)

**Show:** the odds ratios forest plot, the four situations chart, then "One model at a time" for a group model.

**Say:**
- "Steps 1-4 compare groups one by one. A logistic model compares them while keeping everything else equal: year, month, region, road type, intersection, lighting, weather, road surface and collision type."
- "The outcome is 1 for a severe accident (fatal, fatally injured or serious injury; 28,532 of 289,532, which is 9.85%) and 0 otherwise."
- "Compared with an accident with only cars, the odds of a severe accident are 3.44 times higher with a motorcycle, 3.32 with a pedestrian, 2.94 with a truck, 1.77 with a bicycle and 1.22 with a moped."
- "Night without public lighting raises the odds by 1.78 times. Brussels has much lower odds than Flanders (0.39)."
- "A truck as counterpart is the strongest factor in the group models: 5.22 for a pedestrian, 4.26 for a cyclist, 2.63 for a moped and 2.26 for a motorcycle."
- "In everyday numbers: on a normal daytime urban situation in 2024, a car-only accident has a predicted 5.1% chance of being severe, a bicycle against a car 8.6%, a pedestrian 15.0% and a motorcycle 15.5%."

**Say (the three technical points):**
- "Each row is an accident, and accidents in the same municipality are alike. So I used standard errors clustered by municipality (581 clusters). They are on average 11% larger than the plain ones, so the plain ones would have been too optimistic."
- "I tested whether road users add up. They do not: a bicycle and a pedestrian together are less severe than the two effects added (0.33), a car and a motorcycle more (1.48)."
- "The models explain a little, not everything: AUC 0.65 to 0.68. Speed, helmet use and traffic are not in the data."

**If they push:** see "Questions about the models" below.

## Live demo of the Streamlit tool (4 minutes)

**Do:** open the tool, choose *Compare groups* in the sidebar.
1. Set the period to 2022-2024 and the region to Wallonia.
2. Compare cyclists against pedestrians.
3. Point at the crude result (fatal share, risk ratio) and then at the adjusted result.
4. Click one export, for example the Excel workbook.

**Second demo option (1 minute):** open *Geography and hotspots*, choose Motorcycle, view Municipalities, and switch "Top 20 by" from number of accidents to share. Say: "Same table, different question: by number the cities win, by share small municipalities win."

**Say:** "Everything on this page is recalculated from the accidents that match the filters in the sidebar: year, region, province, municipality, road and light conditions. If a group has fewer than 30 accidents the number is hidden; below 100 it is flagged as unreliable. The adjusted result is a model estimated live on your selection, and it needs at least 1,000 accidents and 100 severe ones."

**If the demo fails:** say what it does and show the *Study results* page or the PNG charts instead. Do not debug in front of the class.

## Limits and close (2 minutes)

**Say:**
- "No traffic or population figures, so no rates and no statement about who is riskier per kilometre."
- "Associations, not causes. Speed, vehicle type and helmet use are not in the data."
- "About 10-13% of accidents have no coordinates and about 10% have an unknown road user, and that is not random."
- "Not done: urban against rural (the data has no official classification, #55), a mixed model with a random municipality effect (#121), and an out-of-sample test."
- "Every decision and the reason is in my decision log, 157 entries, on GitHub."

## Question bank

### General questions

**Why did you count an accident for every group involved?**
Because the question is how big the burden is for each group. An accident between a car and a bicycle is a bicycle accident and a car accident. The cost is that shares add up to more than 100% (136,144 accidents involve two different groups). The decision is #33.

**What does "severe" mean?**
Fatal, fatally injured, or seriously injured: classes 1 to 3 in the data. That is 28,532 accidents (9.85%). Slight injuries are the rest. The class belongs to the whole accident, not to one person (#116).

**Why not rates per kilometre or per inhabitant?**
The data has no traffic or population figures. I could add Statbel population, but cycling and driving distances are not available. So I use counts and shares and say so.

**Does this prove that motorcycles are dangerous?**
No. It shows that accidents with a motorcycle are much more often severe than accidents with only cars. A motorcyclist has no protection, so that fits, but the data has no speed or helmet information.

**Why did the accidents fall in 2020?**
Covid lockdowns reduced traffic. The data does not state a cause, so I say "during 2020-2021" and not "because of Covid".

**Why is "Unknown" a problem?**
About 10.7% of accidents have an unknown road user, and it more than doubled from 2017 to 2024. I kept it as its own category instead of deleting it. Part of the decline of other groups could be recording shifting into Unknown.

**What would you do with more time?**
Add traffic and population data to calculate rates, test the models on data they were not estimated on, and try a model with a random effect per municipality.

### Questions about steps 2-4

**Trucks have the highest fatal share. Are trucks the most dangerous road user?**
They are in the most severe accidents, mostly because the other party is often a pedestrian, cyclist or motorcycle. The share describes the accident, not the truck driver.

**Wallonia has more fatal accidents but Flanders has more serious injuries. Why?**
I do not know. It could be real (speeds on Walloon roads) or come from how the classes are recorded. I did not test it. In step 5, where fatal and serious are combined, Wallonia is slightly lower than Flanders (odds ratio 0.74 to 0.81).

**Why does the fatal share fall in busy squares?**
One possible reason is that busy places have lower speeds and an isolated accident more often happens on a faster road. That is a guess: speed is not in the data, so I only report the association.

**What does "35% higher odds" mean?**
Odds are fatal accidents compared with non-fatal accidents. If in Flanders the odds were 1 to 80, in Wallonia they would be about 1.35 to 80. It is not the same as 35% more accidents.

**Why a minimum of 100 accidents for the share ranking?** With only a handful of accidents a share jumps around: 3 of 5 is 60%. A minimum of 100 accidents in the municipality keeps the ranking stable. It is the same rule for every group (#88, #161).

**Why 500 metre squares?**
It is small enough to find a street or crossroads and big enough to have a few accidents per square. The choice is #86.

### Questions about the models

**What is an odds ratio, in one sentence?**
How many times higher the odds of "severe" are, compared with the reference situation, with the other variables kept equal. Odds are severe compared with not severe: if 1 in 10 is severe, the odds are 1 to 9.

**Is an odds ratio of 3.44 the same as 3.44 times the probability?**
No. When the probability is small the two are close, but not equal. That is why I also show predicted probabilities: 5.1% for a car-only accident against 15.5% for a motorcycle.

**What is the reference, the thing everything is compared with?**
A car-only accident (the passenger car is left out of the road-user variables), in Flanders, on a municipal road, not at an intersection, in daylight, with normal weather, a dry road, in 2017 and January, and with a rear-end collision.

**Why logistic regression and not linear regression?**
The outcome is yes or no. A linear model can predict values below 0 or above 1. A logistic model keeps predictions between 0 and 1.

**What does "clustered standard errors" mean and why did you do it?**
Accidents in one municipality share things I do not measure (roads, police recording, culture). They are not fully independent, so the plain standard errors are too small. Clustering by municipality (581 groups) corrects that: they come out on average 11% larger, and up to 3.8 times larger for the region variables. The similarity inside a municipality is small but real (intraclass correlation 0.016).

**Why did you write the estimator yourself?**
I chose to, so I understand every step (Newton-Raphson with step-halving and the sandwich formula for the clustered errors). I checked the live version against the saved results. The decision is in the log.

**What does an AUC of 0.68 mean?**
If you take one severe and one non-severe accident at random, the model gives the severe one the higher score 68% of the time. 0.5 is a coin flip, 1.0 is perfect. So the model helps, but a lot is not in the data. It is measured on the same data used to estimate the model (in-sample), so out-of-sample it would probably be a little lower.

**Why are there separate models for cyclists, pedestrians, motorcyclists and mopeds?**
The factors can work differently for each group, for example a truck as counterpart. In these models the road-user variable is the counterpart (who they collided with).

**What does the interaction test say?**
That road users in the same accident do not simply add up: 22 pairs together are significant (p < 10^-180, so the test is practically certain). Bicycle + pedestrian is far less severe than the sum of the two effects (0.33), car + motorcycle more (1.48).

**Why did you leave out "With a pedestrian" in the pedestrian model?**
It is 99% the same as the pedestrian road-user variable, so the model cannot tell them apart. Without the collision type the pedestrian odds ratio is 2.54 instead of 3.32. I show both versions (#119).

**Why did you merge small categories into "Other / combined"?**
Categories with fewer than 100 accidents give unstable estimates. I merged them for weather, surface and lighting; in single models also categories with fewer than 30 accidents, or with perfect separation.

**Where do the 95% intervals on predicted probabilities come from?**
Simulation: I draw 1,000 sets of coefficients from the estimated uncertainty and calculate the probability each time. The 2.5th and 97.5th percentiles are the interval.

**Can I trust the Wallonia result in step 4 and step 5 at the same time?**
Yes, they answer different questions. Step 4 is about fatal accidents (1.35 times higher in Wallonia at the same density). Step 5 is about fatal plus serious, and Wallonia has fewer serious injuries than Flanders, so the combined odds are lower.

**How do you know the numbers in the report are right?**
Every table is generated by a script from the saved results, with checks (asserts) on key totals. The live tool was tested against the saved results for the same filters. I corrected one mistake of my own: the severe count is 28,532, not 28,517 (#116).

### Questions about the tool and the work

**What can the Streamlit tool do that the page cannot?**
Filter on your own selection, compare two groups with crude and adjusted results, estimate the models live, and export data, tables, charts and a ZIP with a README.

**Why a page and a tool?**
The page shows the saved results for everybody without installing anything. The tool lets you explore your own question.

**What did the AI do and what did you do?**
Say it openly: the AI wrote the code and proposed choices; I decided every choice and wrote the reasons in the log (157 entries). For each result I can explain how the number is calculated.

**Which of its proposals did you reject or change?**
Pick two or three from the log before class that you can explain. For example the choice to count both groups in an accident (#33), the severe definition (#116), and keeping both the five-model view and the single-model view (#151).

## Cheat sheet of numbers

| Topic | Number |
|---|---|
| Accidents in the data | 289,532 (2017-2024) |
| Severe (classes 1-3) | 28,532 (9.85%) |
| Accidents involving two groups | 136,144 |
| Share per group | cars 70.2%, bicycles 24.8%, pedestrians 10.3%, vans 8.1%, mopeds 8.0%, motorcycles 6.8%, trucks 4.4%, buses 1.4% |
| Change 2022-2024 against 2017-2019 | bicycles +14.6%, mopeds +7.3%, cars -12.2%, motorcycles -12.9%, trucks -17.2%, pedestrians -10.4% |
| Fatal share | trucks 5.1%, motorcycles 2.8%, pedestrians 2.0%, buses 1.6%, vans 1.5%, cars 1.3%, bicycles 0.9%, mopeds 0.6%, all 1.4% |
| Fatal + serious | motorcycles 18.9%, trucks 17.3%, all 9.9% |
| Cyclist accidents | 71,881; Flanders 33.5%, Brussels 21.8%, Wallonia 7.0% |
| Fatal share by region | Wallonia 2.26%, Flanders 1.23%, Brussels 0.42% |
| Fatal share by square | 3.00% (one accident) to 0.37% (100 or more) |
| Wallonia against Flanders, fatal, adjusted | odds ratio 1.35 (1.25-1.44) |
| Odds ratios against car-only | motorcycle 3.44, pedestrian 3.32, truck 2.94, bicycle 1.77, moped 1.22 |
| Night without lighting | 1.78 |
| Region against Flanders (severe) | Brussels 0.39, Wallonia 0.81 |
| Truck as counterpart | pedestrians 5.22, cyclists 4.26, mopeds 2.63, motorcyclists 2.26 |
| Predicted severe, daytime urban 2024 | car-only 5.1%, bicycle against car 8.6%, pedestrian 15.0%, motorcycle 15.5% |
| Municipality top by number | pedestrians Antwerpen 2,687; motorcycles Brussel 1,351; mopeds Antwerpen 2,250 |
| Municipality top by share (100+ accidents) | pedestrians Koekelberg 31.5%; motorcycles Stoumont 32.7%; mopeds Hemiksem 20.3% |
| Clusters and fit | 581 municipalities; ICC 0.016; AUC 0.65-0.68 |

## Words in plain language

- **Odds:** severe compared with not severe. 1 in 10 severe means odds of 1 to 9.
- **Odds ratio:** how many times the odds are higher or lower than in the reference situation.
- **Adjusted:** the other variables are kept equal.
- **Cluster-robust standard errors:** error margins that take into account that accidents in one municipality resemble each other.
- **Confidence interval (95%):** the range in which the true value probably lies.
- **Interaction:** the effect of two things together is not the sum of the effects.
- **AUC:** how well the model separates severe from non-severe accidents (0.5 is a coin flip, 1 is perfect).
- **Wilson interval:** a 95% interval for a share that also works for small counts.
- **In-sample:** tested on the same data the model was built on.
