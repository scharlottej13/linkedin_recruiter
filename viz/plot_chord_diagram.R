library(here)
library(dplyr)
source(here("viz", "chord_helpers.R"))

args <- commandArgs(trailingOnly = T)
level_arg <- as.character(args[1])
group_arg <- as.character(args[2])
orig_col <- paste0(level_arg, "_orig")
dest_col <- paste0(level_arg, "_dest")

# flexible for windows or linux os
base_dir <- get_parent_dir()

# fix this later, shouldn't be redundant w/ get_data
get_grouper <- function(group_arg) {
  data_dir <- file.path(base_dir, "processed-data")
  df <- read.csv(file.path(data_dir, "model_input.csv")) %>%
    filter(
        grepl(group_arg, subregion_dest),
        grepl(group_arg, subregion_orig)
    ) %>%
    select(c(country_dest, subregion_dest)) %>%
    distinct()
  setNames(df$subregion_dest, df$country_dest)
}

get_data <- function(level_arg, group_arg, recip, pct) {
  data_dir <- file.path(base_dir, "processed-data")
  filename <- paste0("chord_diagram_", level_arg)
  if (recip) {
    filename <- paste0(filename, "_recip")
  }
  if (level_arg != "country") {
    df <- read.csv(file.path(data_dir, paste0(filename, ".csv")))
  } else {
    df <- read.csv(file.path(data_dir, "model_input.csv")) %>%
      # for now, only use case is filtering by subregion
      filter(
        grepl(group_arg, subregion_dest),
        grepl(group_arg, subregion_orig)
      ) %>%
      group_by(country_orig, country_dest) %>%
      summarise(flow_median = median(flow))
  }
  if (group_arg != "Global" & level_arg != "country") {
    df <- df %>%
      filter(
        grepl(group_arg, get(dest_col)),
        grepl(group_arg, get(orig_col))
      )
  }
  if (!pct) {
    df <- df %>%
      select(c(orig_col, dest_col, "flow_median")) %>%
      mutate(flow_median = flow_median / 100000)
  } else {
      df <- df %>%
        mutate(total = sum(flow_median), pct = (flow_median / total) * 100) %>%
        select(c(orig_col, dest_col, "pct"))
  }
}

# for colors & order of sections
df1 <- read.csv(
    file.path(base_dir, "raw-data", "chord_labels_colors.csv")) %>%
      filter(loc_level == level_arg & loc_group == group_arg) %>%
      arrange(order1)
color_vector <- setNames(df1$col1, df1$loc_name)

# plot 4 chord diagrams
for (recip in c(FALSE, TRUE)) {
  for (pct in c(FALSE, TRUE)) {
    df <- get_data(level_arg, group_arg, recip, pct)
    if (level_arg == "country") {
      grouper <- get_grouper(group_arg)
      print(head(grouper))
    } else {
      grouper <- NULL
    }
    plot_n_save_wrapper(
      df, df1, color_vector, base_dir, level_arg, group_arg,
      recip = recip, percent = pct, grouper = grouper
    )
  }
}