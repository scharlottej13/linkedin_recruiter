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