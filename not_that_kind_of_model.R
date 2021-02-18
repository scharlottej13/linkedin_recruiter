library(MASS)
library(dplyr)
library(gravity)

get_filepath <- function() {
  # this is changed manually
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
}

return_df <- function(df) {
  # does R have a builtin f'n for this?
  df
}

prep_data <- function(df, factor_vars, log_vars, keep_vars, type) {
  if (type == "cohen") {
    my_func <- "log10"
  } else if (type == "poisson") {
    # drop 'flow' b/c in glm R handles this
    log_vars <- log_vars[!log_vars == "flow"]
    my_func <- "log"
  } else {
    # gravity model already log transforms
    my_func <- "return_df"
  }
  df %>%
    mutate_at(factor_vars, factor) %>%
    mutate_at(log_vars, getFunction(my_func)) %>%
    dplyr::select(all_of(keep_vars))
}

run_model <- function(df, log_vars = NULL, other_factors = NULL,
                      other_numeric = NULL, type = "cohen") {
  # Run a model of flow ~ country_destination + country_origin
  # log_vars: independent variables that will be log transformed
  # other_factors: independent categorical variables
  # other_numeric: independent numeric variables that are not log transformed
  # in addition to country_dest, country_orig
  # type: type of model to run, one of cohen, poisson, or gravity
  log_vars <- c("flow", log_vars)
  factors <- c(c("country_orig", "country_dest"), other_factors)
  keep_vars <- unique(c(log_vars, factors, other_numeric))
  df <- prep_data(df, factors, log_vars, keep_vars, type)
  if (type == "cohen") {
    # https://www.pnas.org/content/105/40/15269
    fit <- lm(flow ~ ., data = df)
  } else if (type == "poisson") {
    # no offset b/c one user can want to move to > 1 location
    fit <- glm(flow ~ ., family = poisson(), data = df)
  } else if (type == "gravity") {
    # TO DO test/build this part more
    # need to see how to add other categorical covariates
    fit <- ddm(
      dependent_variable = "flow", distance = "distance",
      code_origin = "country_orig", code_destination = "country_dest",
      data = df
    )
  }
  else {
    print("Model type needs to be one of 'cohen', 'poisson', 'gravity'")
 }
 return(fit)
}

add_fit_quality <- function(fit, df) {
  df[["resids"]] <- residuals(fit)
  df[["sresids"]] <- rstandard(fit)
  df[["preds"]] <- fitted.values(fit, df)
  df[["cooks_dist"]] <- cooks.distance(fit)
  df[["hat_values"]] <- hatvalues(fit)
}

# read in data
df <- read.csv(get_filepath())
# create test df for fun
keep_isos <- c("usa", "can", "fra", "gbr")
testdf <- df %>% filter(iso3_orig %in% keep_isos & iso3_dest %in% keep_isos)

## tried a bunch, see git diff

fit <- run_model(df, log_vars = c("distance"), other_factors = c("query_date"),
                 other_numeric = c("prop_users_orig", "prop_users_dest"))
df <- add_fit_quality(fit, df)
write.csv(df, paste0('cohen_', gsub("input", "output", filepath)), row.names = FALSE)
fit <- run_model(df,
  log_vars = c("distance"), other_factors = c("query_date"),
  other_numeric = c("prop_users_orig", "prop_users_dest"), type = "poisson"
)
df <- add_fit_quality(fit, df)
write.csv(df, paste0('poisson_', gsub("input", "output", filepath)), row.names = FALSE)
# fit <- run_model(df,
#   log_vars = c("distance"), type = "gravity"
# )

# df <- add_fit_quality(fit, df)
# write.csv(df, gsub("input", "output", filepath), row.names = FALSE)

# should I use outliers or coefficients to figure out which countries are interesting?
# next steps:
# understand meaning of coefficients
# add "labor market conditions"? see Bijak et al. ref (or other covariates)
# replace w/ population "weighted average" by age?
# [^ maybe useful? perhaps if the linkedin users are younger then they are also more likely to have aspirations?]