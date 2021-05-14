# https://gjabel.wordpress.com/2016/05/18/updated-circular-plots-for-directional-bilateral-migration-data/
# https://www.oeaw.ac.at/fileadmin/subsites/Institute/VID/PDF/Publications/Working_Papers/WP2016_02.pdf
# https://github.com/guyabel/migest/blob/master/demo/cfplot_reg2.R
# Gu, Z. (2014) circlize implements and enhances circular visualization in R. Bioinformatics.
library(circlize)
library(dplyr)

get_parent_dir <- function() {
  os <- Sys.info()[["sysname"]]
  if (os == "Windows") {
    parent_dir <- "N:\\johnson\\linkedin_recruiter"
  } else {
    parent_dir <- "/Users/scharlottej13/Nextcloud/linkedin_recruiter"
  }
  normalizePath(parent_dir, mustWork = TRUE)
}

plot_n_save_wrapper <- function(df, df1, color_vector,
 base_dir, recip = FALSE) {
  circos.clear()
  circos.par(start.degree = 90, gap.degree = 4, track.margin = c(-0.1, 0.1),
            points.overflow.warning = FALSE)
  chordDiagram(
    x = df, grid.col = color_vector, transparency = 0.25, order = df1$region,
    directional = 1, direction.type = c("arrows", "diffHeight"),
    diffHeight  = -0.04, annotationTrack = "grid",
    link.arr.type = "big.arrow", link.sort = TRUE, link.largest.ontop = TRUE)
  circos.trackPlotRegion(
    track.index = 1,
    bg.border = NA,
    panel.fun = function(x, y) {
      # function loops through each 'sector.index'
      xlim <- get.cell.meta.data("xlim")
      print(xlim)
      sector_index <- get.cell.meta.data("sector.index")
      # need this since labels differ from sector.index values
      reg1 <- df1$reg1[df1$region == sector_index]
      reg2 <- df1$reg2[df1$region == sector_index]
      # add text for reg1
      circos.text(
        x = mean(xlim), y = ifelse(test = nchar(reg2) == 0, yes = 5.2, no = 6),
        labels = reg1, facing = "bending", cex = 1.6
      )
      # add text for reg2
      circos.text(x = mean(xlim), y = 4.4,
                  labels = reg2, facing = "bending", cex = 1.6)
      # Add ticks & labels
      circos.axis(
        h = "top",
        major.at = seq(from = 0, to = xlim[2],
                      by = ifelse(test = xlim[2] > 10, yes = 2, no = 1)),
        minor.ticks = 1, labels.niceFacing = FALSE)
    }
  )
  # TODO clean up this if block
  if (recip) {
    filepaths <- c(
      normalizePath(
        file.path(
          base_dir, "plots", "recip", "_archive",
          paste0("chord_diagram_region", "_", Sys.Date(), ".pdf")
        ),
        normalizePath(file.path(
          base_dir, "plots", "recip", "chord_diagram_region.pdf"))
      )
    )
  } else {
    filepaths <- c(
      normalizePath(
        file.path(
          base_dir, "plots", "_archive",
          paste0("chord_diagram_region", "_", Sys.Date(), ".pdf")
        ),
        normalizePath(file.path(base_dir, "plots", "chord_diagram_region.pdf"))
      )
    )
  }
  for (filename in filepaths) {
    dev.copy2pdf(file = filename, height = 12, width = 15)
  }
}

# flexible for windows or linux os
base_dir <- get_parent_dir()
# for colors & order of the panels
df1 <- read.csv(file.path(base_dir, "raw-data", "chord_labels_colors.csv")
  ) %>% arrange(order1)
color_vector <- setNames(df1$col1, df1$region)
# read in bilateral flows of 'prospective relocators' data
df <- read.csv(file.path(
  base_dir, "processed-data", "chord_diagram_midreg.csv"))
df$flow <- df$flow / 100000
# save circle sankey
plot_n_save_wrapper(df, df1, color_vector, base_dir)
# read in bilateral flows of 'prospective relocators' data
df <- read.csv(file.path(
  base_dir, "processed-data", "chord_diagram_midreg_recip.csv"
))
df$flow <- df$flow / 100000
# save circle sankey
plot_n_save_wrapper(df, df1, color_vector, base_dir, recip = TRUE)
