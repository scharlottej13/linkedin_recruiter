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

run_cohen_model <- function(df, x_vars, categ_vars = c()) {
  # drop any rows witih null values
  # TO DO this could be handled more carefully/intentionally
  # YES DEF NEED TO FIX THIS
  #keep_cols <- c(x_vars, categ_vars, "flow", "country_dest", "country_orig")
  #df <- df[complete.cases(df[keep_cols]), ]
  # create indicator variables (matrix of 0s/1s)
  wide_vars <- as.data.frame(model.matrix(~ country_dest + country_orig - 1, data=df))
  # log10 (still don't know why base 10) numeric variables
  df[x_vars] <- sapply(df[x_vars], as.numeric)
  df[c(x_vars, "flow")] <- sapply(df[c(x_vars, "flow")], log10)
  if (length(categ_vars) > 0) {df[categ_vars] <- factor(df[categ_vars])}
  df <- bind_cols(wide_vars, df[c(x_vars, "flow", categ_vars)])
  formula <- reformulate(c(x_vars, categ_vars, "."), "flow")
  fit <- lm(formula = formula, data = df)
}

fit1 <- run_cohen_model(df, c("users_orig", "users_dest", "distance"))
fit2 <- run_cohen_model(df, c("users_orig", "users_dest", "distance", "area_orig", "area_dest"))

plot(fit$y, fit$fitted.values)
ggplot()
