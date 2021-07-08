library(MASS)
library(tidyverse)

get_parent_dir <- function() {
  os <- Sys.info()[["sysname"]]
  user <- tolower(Sys.info()[["user"]])
  if (os == "Windows") {
    parent_dir <- file.path("N:", user, "linkedin_recruiter")
  } else {
    parent_dir <- file.path("/Users", user, "Nextcloud", "linkedin_recruiter")
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

prep_data <- function(df, keep_vars, min_n, min_dest_prop, location) {
  # TODO! expand to other locations
  # currently only written for global or EU
  if (location != "global") {
    df <- df %>%
      filter(eu_plus == 1)
  } else {
    df <- df %>%
      filter(users_orig_median > min_dest_prop)
  }
  # hacky hack hack
  dep_var <- keep_vars[1]
  df %>%
    filter(dep_var >= min_n) %>%
    dplyr::select(all_of(c(keep_vars, "country_dest", "country_orig"))) %>%
    drop_na()
}

run_model <- function(df, type, formula) {
  # https://www.pnas.org/content/105/40/15269
  if (type == "cohen") {
    fit <- lm(formula, data = df)
  # ! not yet tested
  } else if (type == "nb") {
    fit <- vglm(formula, data = df, family = posnegbinomial())
  # ! not yet tested
  } else if (type == "poisson") {
    # ? no offset b/c one user can want to move to > 1 location
    # fit <- glm(formula, family = poisson(), data = df)
    fit <- vglm(formula, data = df, family = pospoisson())
  # TO DO test/build this part more (if needed)
  # ! not yet tested
  } else if (type == "gravity") {
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
  df, filename, base_dir, formula, location,
  type = "cohen", min_n=1, min_dest_prop=0
) {
    formula <- as.formula(formula)
    keep_vars <- all.vars(formula)
    model_df <- prep_data(df, keep_vars, min_n, min_dest_prop, location)
    fit <- run_model(model_df, type, formula)
    # save model summary output as a text file
    out_dir <- file.path(base_dir, "model-outputs")
    write.csv(
      broom::tidy(fit) %>% add_column(confint(fit), .after = "estimate"),
      file.path(out_dir, paste0(filename, "_betas.csv")), row.names = FALSE
    )
    write.csv(
      broom::glance(fit),
      file.path(out_dir, paste0(filename, "_summary.csv")), row.names = FALSE
    )
    write.csv(broom::augment(fit),
      file.path(out_dir, paste0(filename, ".csv")), row.names = FALSE
    )
    for (file in c(
        paste0(filename, "_betas.csv"),
        paste0(filename, "_summary.csv"),
        paste0(filename, ".csv"))
    ) {
      save_to_archive(file, out_dir)
    }
  }

cl_args <- commandArgs(trailingOnly = T)
mvid <- as.numeric(cl_args[1])
base_dir <- get_parent_dir()
args <- read.csv(
  file.path(base_dir, "model-outputs", "model_versions.csv")
) %>% filter(version_id == mvid)
stopifnot(nrow(args) == 1)

df <- read.csv(file.path(
  base_dir, "processed-data",
  paste0(ifelse(args$recip == 0, "variance", "variance_recip"), ".csv")
))

# I don't know, it breaks otherwise because reasons?
formula <- args$formula
location <- args$location
type <- args$type
min_n <- args$min_n
min_dest_prop <- args$min_dest_prop
output_filename <- paste0(args$description, "-", mvid)

save_model(
  df, output_filename, base_dir, formula, location,
  type, min_n, min_dest_prop
)
