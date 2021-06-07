library(here)
library(dplyr)
source(here("viz", "chord_helpers.R"))

args <- commandArgs(trailingOnly = T)
level_arg <- as.character(args[1])
group_arg <- as.character(args[2])

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
      # TO DO need to change this to be dynamic column names
      grepl(group_arg, paste0(subregion_dest)),
      grepl(group_arg, paste0(subregion_orig))
    )
  }
}

# for colors & order of the panels
df1 <- read.csv(
    file.path(base_dir, "raw-data", "chord_labels_colors.csv")) %>%
      filter(loc_level == level_arg & loc_group == group_arg) %>%
      arrange(order1)
color_vector <- setNames(df1$col1, df1$loc_name)

# plot 2 chord diagrams, one w/ only reciprocal pairs and another w/ all
for (recip in c(TRUE, FALSE)) {
  df <- get_data(level_arg, group_arg, recip) %>% mutate(flow = flow / 100000)
  plot_n_save_wrapper(
    df, df1, color_vector, base_dir, level_arg, group_arg, recip = recip
  )
}