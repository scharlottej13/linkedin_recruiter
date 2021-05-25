library(MASS)
library(dplyr)
library(tidyr)
library(gravity)
library(VGAM)


get_parent_dir <- function() {
  os <- Sys.info()[["sysname"]]
  if (os == "Windows") {
    parent_dir <- "N:\\johnson\\linkedin_recruiter"
  } else {
    parent_dir <- "/Users/scharlottej13/Nextcloud/linkedin_recruiter"
  }
  normalizePath(parent_dir, mustWork = TRUE)
}

save_to_archive <- function(name, active_dir) {
  archive_dir <- file.path(active_dir, "_archive")
  split_name <- unlist(strsplit(name, ".", fixed = T))
  # append timestamp
  newname <- paste0(split_name[1], "_", Sys.Date(), ".", split_name[2])
  file.copy(file.path(active_dir, name), archive_dir)
  file.rename(
    from = file.path(archive_dir, name),
    to = file.path(archive_dir, newname)
  )
}

return_df <- function(df) {
  df
}

prep_data <- function(
  df, dep_var, factor_vars, log_vars, keep_vars, type, min_n,
  min_dest_prop, global
  ) {
  if (!global) {
    df <- df %>%
      filter(eu_plus == 1)
  } else {
    df <- df %>%
      filter(users_orig_median > min_dest_prop)
  }
  if (type == "cohen") {
    log_vars <- c(dep_var, log_vars)
    my_func <- "log10"
  } else if ((type == "poisson") | (type == "nb")) {
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
    dplyr::select(all_of(c(keep_vars, "country_dest", "country_orig"))) %>%
    drop_na()
}

run_model <- function(df, dep_var, type, keep_vars) {
  # Run a model of flow ~ country_destination + country_origin
  # log_vars: independent variables that will be log transformed
  # other_factors: independent categorical variables in addition to
  # country_dest, country_orig)
  # other_numeric: independent numeric variables that are not log transformed
  # type: type of model to run, one of cohen, poisson, or gravity
  # min_n: minimum value for the count of the dependent variable
  formula <- as.formula(paste(
    dep_var, paste(keep_vars[keep_vars != dep_var],
    collapse = " + "), sep = " ~ "))
  if (type == "cohen") {
    # https://www.pnas.org/content/105/40/15269
    fit <- lm(formula, data = df)
  } else if (type == "nb") {
    fit <- vglm(formula, data = df, family = posnegbinomial())
  } else if (type == "poisson") {
    # ? decided no offset b/c one user can want to move to > 1 location
    # fit <- glm(formula, family = poisson(), data = df)
    fit <- vglm(formula, data = df, family = pospoisson())
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
  df %>%
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

save_model <- function(
  df, suffix, base_dir, dep_var = "flow_median",
  log_vars = NULL, factors = NULL,
  other_numeric = NULL, type = "cohen", min_n=0,
  min_dest_prop = 0.05, global = FALSE
) {
    keep_vars <- unique(c(dep_var, log_vars, factors, other_numeric))
    model_df <- prep_data(df, dep_var, factors, log_vars, keep_vars,
      type, min_n, min_dest_prop, global)
    fit <- run_model(model_df, dep_var, type, keep_vars)
    if (global) {
      filename <- paste0(type, "_global_", suffix)
    } else {
      filename <- paste0(type, "_eu_", suffix)
    }
    # save model summary output as a text file
    out_dir <- file.path(base_dir, "model-outputs")
    sink(file.path(out_dir, paste0(filename, ".txt")))
    print(summary(fit))
    sink()
    write.csv(add_fit_quality(fit, model_df),
      file.path(out_dir, paste0(filename, ".csv")),
      row.names = FALSE
    )
    for (file in c(paste0(filename, ".txt"), paste0(filename, ".csv"))) {
      save_to_archive(file, out_dir)
    }
  }

# get working directories
data_dir <- get_parent_dir()
# read in data
df <- read.csv(
  file.path(data_dir, "processed-data", "variance.csv")
)

save_model(
  df, "dist_biggest_cities_plus_gdp", data_dir,
  global = FALSE,
  log_vars = c(
    "dist_biggest_cities", "users_orig_median",
    "users_dest_median", "area_dest", "area_orig", "gdp_dest", "gdp_orig"
  ), other_numeric = c("csl", "contig")
)

# save_model(df, "base_dist_pop_weighted_plus_colony",
#   global = TRUE,
#   log_vars = c(
#     "dist_pop_weighted", "users_orig_median",
#     "users_dest_median", "area_dest", "area_orig"
#   ), other_numeric = c("csl", "contig", "colony")
# )
# save_model(df, "base_dist_pop_weighted_plus_col45",
#   global = TRUE,
#   log_vars = c(
#     "dist_pop_weighted", "users_orig_median",
#     "users_dest_median", "area_dest", "area_orig"
#   ), other_numeric = c("csl", "contig", "col45")
# )

# # poisson
# fit2 <- run_model(df,
#   log_vars = c("distance"), other_factors = c("query_date"),
#   other_numeric = c("prop_users_orig", "prop_users_dest"), type = "poisson"
# )
# should I use outliers or coefficients to figure out which countries are interesting?
# next steps:
# understand meaning of coefficients
# add "labor market conditions"? see Bijak et al. ref (or other covariates)
# replace w/ population "weighted average" by age?
# [^ maybe useful? perhaps if the linkedin users are younger then they are also more likely to have aspirations?]