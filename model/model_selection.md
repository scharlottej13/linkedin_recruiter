# model selection
started w/ a "base" gravity model (all log-transformed):
- distance (expect negative beta)
- area origin (expect negative or near 0)
- area destination (expect negative or near 0)
- users origin (expect positive)
- users destination (expect positive)
*area and number of users are supposed to represent "population density". In our
use case, this number is more like, "user density" (population/area). If area is not important, beta should be close to 0. If it is important, should be the negative of the beta of number of users.

I used 3 different measures of distance (unweighted, population weighted, and biggest cities). All three models had simliar r2. Of these, the population weighted metric had the most negative beta coefficient with CIs, so I chose this metric of distance. Betas on area and users are as expected, w/ area close to 0 and users positive.

Next, I tried out different covariates for language. so the covariates are:
- population weighted distance
- area origin
- area destination
- users origin
- users destination
- one of: col, cnl, csl, prox2 (expect positive)
results of betas: cnl > csl > col > prox2 (prox2 close to 0)
Either cnl or csl would be a good choice. Both increase r2, csl increases it *slightly* more. This combined with the fact that I think common spoken language is a priori better led me to choose csl.

Ok, time for the colonizer covariates:
- population weighted distance
- area origin
- area destination
- users origin
- users destination
- csl
- one of: col45, colony, comcol (expect positive)
(same country and current colony are also there, but doesn't make sense just for europe)

col45 (shared common colonizer pre 1945) wins the betas! and increased r2 juuuuust a bit. Could probably choose to exclude this one (either way).

GDP is highly collinear w/ number of linkedin users, so don't want to add that.

proportion of population using linkedin & internet are kind of the same, add one or the other (but not both)

I think using whether two countries share a border *and* distance is redundant. Model verion 39 has this, and when added it drops the coefficient for distance.

comparing model versions 26 vs. 38 (prop internet vs. prop linkedin users)-- 26 is a little better, slightly higher adj. r2 and betas for internet are a bit stronger. Try this one again w/o area (b/c those betas are close to 0)
- w/o area at all is slightly worse than w/ only area in the destination
- just area in destination seems enough? basically, versions 26 and 40 are good.
(re run 26 since I added rmse as a calculation, so now it's 42)
