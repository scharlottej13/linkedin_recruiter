library(MASS)
library(tidyverse)

get_parent_dir <- function() {
  os <- Sys.info()[["sysname"]]
  user <- tolower(Sys.info()[["user"]])
  if (os == "Windows") {
    parent_dir <- file.path("N:", user, "linkedin_recruiter")
  } else {
    parent_dir <- file.path("Users", user, "Nextcloud", "linkedin_recruiter")
  }
  parent_dir
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
  # log_vars: independent variables that will be log transformed
  # other_factors: independent categorical variables
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
    # TO DO test/build this part more (if needed)
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

save_model <- function(
  df, filename, base_dir, dep_var = "flow_median",
  log_vars = NULL, factors = NULL,
  other_numeric = NULL, type = "cohen", min_n=0,
  min_dest_prop = 0.05, global = FALSE
) {
    keep_vars <- unique(c(dep_var, log_vars, factors, other_numeric))
    model_df <- prep_data(df, dep_var, factors, log_vars, keep_vars,
      type, min_n, min_dest_prop, global)
    fit <- run_model(model_df, dep_var, type, keep_vars)
    # save model summary output as a text file
    out_dir <- file.path(base_dir, "model-outputs")
    write.csv(
      broom::tidy(fit) %>% add_column(confint(fit), .after = "estimate"),
      file.path(out_dir, paste0(filename, "_betas.csv"))
    )
    write.csv(broom::glance(fit), file.path(out_dir, paste0(filename, "_summary.csv")))
    write.csv(broom::augment(fit),
      file.path(out_dir, paste0(filename, ".csv"))
    )
    for (file in c(
        paste0(filename, "_betas.csv"),
        paste0(filename, "_summary.csv"),
        paste0(filename, ".csv"))
    ) {save_to_archive(file, out_dir)}
  }

main <- function(filename, dep_var, log_vars, factors, other_numeric,
                 type, min_n, min_dest_prop, global)


args <- commandArgs(trailingOnly = T)
filename <- as.character(args[1])
dep_var <- as.character(args[2])



base_dir <- get_parent_dir()
df <- read.csv(file.path(base_dir, "processed-data", "variance.csv"))
save_model(
  df, filename, base_dir, dep_var, log_vars, factors,
  other_numeric, type, min_n, min_dest_prop, global
)
