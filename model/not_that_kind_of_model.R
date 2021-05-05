library(MASS)
library(dplyr)
library(gravity)

get_parent_dir <- function() {
  os <- Sys.info()[["sysname"]]
  if (os == "Windows") {
    parent_dir <- "N:\\johnson\\linkedin_recruiter"
  } else {
    parent_dir <- "/Users/scharlottej13/Nextcloud/linkedin_recruiter"
  }
  normalizePath(parent_dir, mustWork = TRUE)
}

return_df <- function(df) {
  # TODO does R have a builtin f'n for this?
  df
}

prep_data <- function(
  df, dep_var, factor_vars, log_vars, keep_vars, type, min_n) {
  if (type == "cohen") {
    log_vars <- c(dep_var, log_vars)
    my_func <- "log10"
  } else if (type == "poisson") {
    # glm has log-link
    my_func <- "log"
  } else {
    # gravity model already log transforms
    my_func <- "return_df"
  }
  df %>%
    filter(dep_var >= min_n) %>%
    mutate_at(factor_vars, factor) %>%
    mutate_at(log_vars, getFunction(my_func)) %>%
    dplyr::select(all_of(keep_vars))
}

run_model <- function(
  df, dep_var = "flow", log_vars = NULL, factors = NULL,
  other_numeric = NULL, type = "cohen", min_n=25) {
  # Run a model of flow ~ country_destination + country_origin
  # log_vars: independent variables that will be log transformed
  # other_factors: independent categorical variables in addition to
  # country_dest, country_orig)
  # other_numeric: independent numeric variables that are not log transformed
  # type: type of model to run, one of cohen, poisson, or gravity
  # min_n: minimum value for the count of the dependent variable
  keep_vars <- unique(c(dep_var, log_vars, factors, other_numeric))
  df <- prep_data(df, dep_var, factors, log_vars, keep_vars, type, min_n)
  formula <- as.formula(paste(
    dep_var, paste(keep_vars[keep_vars != dep_var],
    collapse = " + "), sep = " ~ "))
  if (type == "cohen") {
    # https://www.pnas.org/content/105/40/15269
    fit <- lm(formula, data = df)
  } else if (type == "poisson") {
    # ? decided no offset b/c one user can want to move to > 1 location
    fit <- glm(formula, family = poisson(), data = df)
  } else if (type == "gravity") {
    # TO DO test/build this part more (as needed)
    fit <- ddm(
      dependent_variable = dep_var, distance = "distance",
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
  keep_vars <- unique(
    c("country_dest", "country_orig"), attr(fit$terms, "term.labels")
  )
  df %>%
    select(keep_vars) %>%
    mutate(
      r2 = fit$r.squared,
      adj_r2 = fit$adj.r.squared,
      resids = residuals(fit),
      sresids = rstandard(fit),
      preds = fit$fitted.values,
      cooks_dist = cooks.distance(fit),
      hat_values = hatvalues(fit)
    )
}

base_dir <- get_parent_dir()
out_dir <- file.path(base_dir, "model-outputs")
arch_dir <- file.path(base_dir, "model-outputs", "_archive")
date <- Sys.Date()
# read in data
df <- read.csv(
  file.path(base_dir, "processed-data", "variance.csv")
) %>% filter(prop_dest_median > 0.05)
# linear model
fit <- run_model(
  df,
  dep_var = "flow_median",
  log_vars = c("dist_biggest_cities", "users_orig_median", "users_dest_median"),
  other_numeric = c("contig", "csl"),
  factors = c("country_dest", "country_orig")
)
sink(file.path(out_dir, "cohen_5.txt"))
print(summary(fit))
sink()
write.csv(fit$model, file.path(out_dir, "cohen_modelframe_5.csv"),
  row.names = FALSE
)
write.csv(
  add_fit_quality(fit, df),
  file.path(out_dir, "cohen_5.csv"), row.names = FALSE
)
# # poisson
# fit2 <- run_model(df,
#   log_vars = c("distance"), other_factors = c("query_date"),
#   other_numeric = c("prop_users_orig", "prop_users_dest"), type = "poisson"
# )
# write.csv(add_fit_quality(fit2, df),
#           gsub("model", "poisson_model", outpath), row.names = FALSE)

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