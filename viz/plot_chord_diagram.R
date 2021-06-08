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

get_data <- function(level_arg, group_arg, recip) {
  data_dir <- file.path(base_dir, "processed-data")
  filename <- paste0("chord_diagram_", level_arg)
  if (recip) {
    filename <- paste0(filename, "_recip")
  }
  df <- read.csv(file.path(data_dir, paste0(filename, ".csv")))
  if (group_arg != "Global") {
    df <- df %>%
      filter(
        grepl(group_arg, get(dest_col)),
        grepl(group_arg, get(orig_col))
      )
  }
  df <- df %>%
    select(c(orig_col, dest_col, "flow_median"))
  # df <- df %>%
  #   select(c(orig_col, dest_col, "pct_orig", "pct_dest"))
}

# for colors & order of sections
df1 <- read.csv(
    file.path(base_dir, "raw-data", "chord_labels_colors.csv")) %>%
      filter(loc_level == level_arg & loc_group == group_arg) %>%
      arrange(order1)
color_vector <- setNames(df1$col1, df1$loc_name)

# plot 2 chord diagrams, one w/ only reciprocal pairs and another w/ all
for (recip in c(FALSE, TRUE)) {
  df <- get_data(level_arg, group_arg, recip) %>%
    mutate(flow_median = flow_median / 100000)
  plot_n_save_wrapper(
    df, df1, color_vector, base_dir, level_arg, group_arg, recip = recip
  )
}