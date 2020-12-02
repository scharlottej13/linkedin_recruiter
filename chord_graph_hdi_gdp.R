# https://gjabel.wordpress.com/2016/05/18/updated-circular-plots-for-directional-bilateral-migration-data/
# https://www.oeaw.ac.at/fileadmin/subsites/Institute/VID/PDF/Publications/Working_Papers/WP2016_02.pdf
# https://github.com/guyabel/migest/blob/master/demo/cfplot_reg2.R
# Gu, Z. (2014) circlize implements and enhances circular visualization in R. Bioinformatics.
library(circlize)
library(dplyr)
library(migest)
library(RColorBrewer)

# the files are *IN* the computer!
BASE_DIR <- "/Users/scharlottej13/Nextcloud/linkedin_recruiter/outputs/"
# set this manually
DATE <- "2020-12-02"

create_chord_diagram <- function(chord_df, color_vector, meta_col, val_col) {
  chordDiagram(x = chord_df)
  circos.clear()
  circos.par(start.degree = 90, gap.degree = 4, track.margin = c(-0.1, 0.1), points.overflow.warning = FALSE)
  par(mar = rep(0, 4))
  # use this later for tick marks
  max <- max(chord_df[,val_col])
  # real deal
  chordDiagram(x = chord_df,
               grid.col = color_vector, transparency = 0.25, directional = 1,
               direction.type = c("arrows", "diffHeight"), diffHeight  = -0.04,
               annotationTrack = "grid", annotationTrackHeight = c(0.05, 0.1),
               link.arr.type = "big.arrow", link.sort = TRUE, link.largest.ontop = TRUE)
  circos.trackPlotRegion(
    track.index = 1, 
    bg.border = NA,
    # loops through each 'sector.index' (values of the "meta_col")
    panel.fun = function(x, y) {
      xlim = get.cell.meta.data("xlim")
      # print, then set the major ticks manually (for now)
      print(xlim)
      sector.index = get.cell.meta.data("sector.index")
      circos.text(x = mean(xlim), y = 4,  labels = sector.index, facing = "bending",
                  cex = 1.4, niceFacing = FALSE)
      # Add ticks & labels
      circos.axis(
        h = "top", 
        major.at = seq(from = 0, to = xlim[2], by = ifelse(xlim[2]>180, yes = 50, no = 20)),
        minor.ticks = 5,
        labels.niceFacing = FALSE)
    }
  )
  text(x = -.6, y = 1.2, cex = 1.8, labels = paste0("Migration flows by ", toupper(meta_col),  " quintile"))
  if (grepl("norm", val_col)) {
    text(x = -.6, y = 1.12, cex = 1.5, labels = "per 100,000 LinkedIn users in origin") 
  }
  filename = paste0(BASE_DIR, "chord_plot_", meta_col, "_", DATE, ".pdf")
  dev.copy2pdf(file = filename, height=12, width=10)
  file.show(filename)
}

color_vector <- setNames(brewer.pal(5, "RdYlBu"), c("Low", "Low-middle", "Middle", "Middle-high", "High"))
for (measure in c("gdp", "hdi")) {
  df <- read.csv(paste0(BASE_DIR, measure, "_flows_", DATE, ".csv"))
  chord_df <- df %>% filter(query_date == "2020-07-25") %>% select(c(contains(measure), flow_norm))
  create_chord_diagram(chord_df, color_vector, measure, "flow_norm")
}

