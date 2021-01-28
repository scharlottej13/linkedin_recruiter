# gravity model
library(gravity)
library(tidyverse)
library(MASS)

# read in data from Tom (thanks Tom!)
df <- read.csv("/Users/scharlottej13/Nextcloud/linkedin_recruiter/outputs/model_input_2021-01-28.csv")
# drop some rows
df <- df %>% dplyr::filter(query_date == "2020-07-25" & distance > 0)
# already has no zeros
# turn this into a check god knows how to do that in R
zeros <- row_number(df %>% filter(flow == 0))

run_cohen_model <- function(df, x_vars, y_var=c("flow")) {
  wide_vars <- as.data.frame(model.matrix(~ country_dest + country_orig - 1, data=df))
  df[x_vars + y_var] <- log10(df[x_vars + y_var])
  fit <- lm(y_var ~ x_vars + ., data=bind_cols(wide_vars, df[x_vars + y_var]))
}

fit1 <- run_cohen_model(df, c("users_orig", "users_dest", "distance"))
df %>% dplyr::filter(area_org > 0)
fit2 <- run_cohen_model(df, c("users_orig", "users_dest", "distance", "area_orig", "area_dest"))

plot(fit$y, fit$fitted.values)
ggplot()
