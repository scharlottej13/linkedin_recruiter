library(MASS)
library(dplyr)
library(gravity)


file <- "model_input_2021-02-15.csv"
# for swapping between windows & mac
os <- Sys.info()[["sysname"]]
if (os == "Darwin") {
  parent_dir <- "/Users/scharlottej13/Nextcloud/linkedin_recruiter/inputs/"
  filepath <- paste0(parent_dir, file)
} else if (os == "Windows") {
  parent_dir <- "N:\\johnson\\linkedin_recruiter\\inputs\\"
  filepath <- paste0(parent_dir, file)
} else {
  print("not tested for linux yet")
}

# read in data
df <- read.csv(filepath)
keep_isos <- c("usa", "can", "fra", "gbr")
testdf <- df %>% filter(iso3_orig %in% keep_isos & iso3_dest %in% keep_isos)

prep_data <- function(df, factor_vars, log_vars, type) {
  if (type %in% c("cohen", "poisson")) {
    if (type == "cohen") {
      my_func <- "log10"
    } else {
      my_func <- "log"
    }
    df %>%
      # convert to factor variables
      mutate_at(factor_vars, factor) %>%
      # log transform
      mutate_at(log_vars, getFunction(my_func)) %>%
      # only keep columns needed for the model
      select(c(x_vars, "flow", factor_vars))
  } else {
    # TO DO
    # I wonder if in R you can have a function that does nothing?
    df %>%
      # convert to factor variables
      mutate_at(factor_vars, factor) %>%
      # only keep columns needed for the model
      select(c(x_vars, "flow", factor_vars))
  }
}

run_model <- function(df, log_vars = NULL, other_factors = NULL, type = "cohen") {
  # Run a model of flow ~ country_destination + country_origin
  # log_vars: independent variables that will be log transformed
  # other_factors: independent categorical variables
  # in addition to country_dest, country_orig
  # type: type of model to run, one of cohen, poisson, or gravity
  log_vars <- c("flow", log_vars)
  factors <- c(c("country_orig", "country_dest"), other_factors)
  df <- prep_data(df, factors, log_vars, type)
  if (type == "cohen") {
    # https://www.pnas.org/content/105/40/15269
    fit <- lm(flow ~ ., data = df)
  } else if (type == "poisson") {
    fit <- glm(flow ~ ., family = poisson(), data = df)
  } else if (type == "gravity") {
    fit <- ddm(
      dependent_variable = "flow", distance = "distance",
      code_origin = "country_orig", code_destination = "country_dest",
      data = df, additional_regressors = other_factors
    )
  }
  else {
    print("Model type needs to be one of 'cohen', 'poisson', 'gravity'")
 }
}

# first see if number of users, population, or proportion of population is best
fit1 <- run_model(df, c("users_dest", "users_orig"), categ_vars = "query_date")
fit2 <- run_model(df, c("users_dest", "users_orig", "pop_orig", "pop_dest"), categ_vars = "query_date")
# this means don't log any of the independent variables
fit3 <- run_model(df, c("prop_users_dest", "prop_users_orig"), log_vars = NULL, categ_vars = "query_date")

# ok! chose fit3; population drops out of model for fit2
# let's add distance + area in sq km
fit1 <- run_model(df, c("prop_users_dest", "prop_users_orig"), log_vars = "distance", categ_vars = "query_date")
fit2 <- run_model(df, c("prop_users_dest", "prop_users_orig"),
                  log_vars = c("distance", "area_orig", "area_dest"), categ_vars = "query_date")

# model dropped area_orig & area_dest (makes sense, doesn't vary)
fit2 <- run_model(df, c("prop_users_dest", "prop_users_orig", "internet_dest", "internet_orig"),
                  log_vars = "distance", categ_vars = "query_date")
# try gdp
fit2 <- run_model(df, c("prop_users_dest", "prop_users_orig"),
                  log_vars = c("distance", "maxgdp_orig", "maxgdp_dest"), categ_vars = "query_date")
# try hdi
fit2 <- run_model(df, c("prop_users_dest", "prop_users_orig", "maxhdi_dest", "maxhdi_orig"),
                  log_vars = "distance", categ_vars = "query_date")

# and this one?
# pretty much the same as fit1
fit2 <- run_model(df, c("users_dest", "users_orig"), log_vars = "distance", categ_vars = "query_date")

plot(model.frame(fit1)$flow, fit1$fitted.values)
df[["resids"]] <- residuals(fit1)
# https://cran.r-project.org/web/packages/car/car.pdf
df[["sresids"]] <- rstandard(fit1)
df[["preds"]] <- fitted.values(fit1, df)
df[["cooks_dist"]] <- cooks.distance(fit1)
df[["hat_values"]] <- hatvalues(fit1)
write.csv(df, gsub("input", "output", filepath), row.names = FALSE)

# should I use outliers or coefficients to figure out which countries are interesting?
# next steps:
# understand meaning of coefficients
# add "labor market conditions"? see Bijak et al. ref (or other covariates)
# replace w/ population "weighted average" by age?
# [^ maybe useful? perhaps if the linkedin users are younger then they are also more likely to have aspirations?]

