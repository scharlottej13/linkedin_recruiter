# gravity model
library(gravity)
library(tidyverse)

# read in data from Tom (thanks Tom!)
df <- read.csv("/Users/scharlottej13/Nextcloud/linkedin_recruiter/inputs/LinkedInRecruiter_dffromtobase_merged_gdp.csv")
# only keep july, october has an issue with CAR
df <- df %>% filter(query_time_round == "2020-07-25 02:00:00")
# already has no zeros
zeros <- row_number(df %>% filter(number_people_who_indicated == 0))

# for later:
# http://www.cepii.fr/PDF_PUB/wp/2011/wp2011-25.pdf
# http://www.cepii.fr/CEPII/en/publications/wp/abstract.asp?NoDoc=3877
# https://cran.r-project.org/web/packages/gravity/vignettes/crash-course-on-gravity-models.html
fit <- glm(
  number_people_who_indicated ~ log(linkedinusers_from) + log(linkedinusers_to),
  family="poisson",
  data=df
)
require(MASS)
fit2 <- glm.nb(
  number_people_who_indicated ~ log(linkedinusers_from) + log(linkedinusers_to),
  data=df
)
# closer to Cohen paper w/ indicator variables
# they did log10 (why?!?) t'form (no poisson/nb) which is weird yeah?
wide_vars <- as.data.frame(model.matrix(~ country_from + country_to - 1, data=df))
model_df <- bind_cols(wide_vars, df %>% select(number_people_who_indicated, linkedinusers_from, linkedinusers_to))
# this will surely fail
fit <- glm(
  number_people_who_indicated ~ log(linkedinusers_from) + log(linkedinusers_to) + .,
  family="poisson",
  data=model_df
)
plot(fit$y, fit$fitted.values)
# WOW it works and is *way* better, only a couple outliers
#    country_from   country_to     number_people_who_indicated
       # India        United States  84545
       # India United Arab Emirates  114654
       # India               Canada  89995
## TO DO!!
# the log area (square kilometers) of the origin
# the log area (square kilometers) of the destination
# the log great circle distance (kilometers) from the capital
# of the origin to the capital of the destination
# the source of the migration data, and “neighbor”
