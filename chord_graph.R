# https://gjabel.wordpress.com/2016/05/18/updated-circular-plots-for-directional-bilateral-migration-data/
# https://www.oeaw.ac.at/fileadmin/subsites/Institute/VID/PDF/Publications/Working_Papers/WP2016_02.pdf
# https://github.com/guyabel/migest/blob/master/demo/cfplot_reg2.R
# Gu, Z. (2014) circlize implements and enhances circular visualization in R. Bioinformatics.
library(circlize)
library(dplyr)
library(migest)

BASE_DIR <- normalizePath("/Users/scharlottej13/Nextcloud/linkedin_recruiter/")
# BASE_DIR <- normalizePath("N:/johnson/linkedin_recruiter/")
# set this manually
DATE <- "2020-12-07"

df1 <- read.csv(normalizePath(paste0(BASE_DIR, "/inputs/chord_labels_colors.csv"))) %>% arrange(order1)
color_vector <- setNames(df1$col1, df1$region)

df <- read.csv(normalizePath(paste0(BASE_DIR, "/outputs/midreg_flows_", DATE, ".csv")))
df$flow <- df$flow / 10000
chord_df <- df %>% filter(query_date == "2020-07-25") %>% select(orig_midreg, dest_midreg, flow)

chordDiagram(x = chord_df)
circos.clear()
circos.par(start.degree = 90, gap.degree = 4, track.margin = c(-0.1, 0.1), points.overflow.warning = FALSE)
par(mar = rep(0, 4))
chordDiagram(x = chord_df, grid.col = color_vector, transparency = 0.25,
             order = df1$region, directional = 1, direction.type = c("arrows", "diffHeight"),
             diffHeight  = -0.04, annotationTrack = "grid", annotationTrackHeight = c(0.05, 0.1),
             link.arr.type = "big.arrow", link.sort = TRUE, link.largest.ontop = TRUE)

circos.trackPlotRegion(
  track.index = 1, 
  bg.border = NA, 
  panel.fun = function(x, y) {
    # function loops through each 'sector.index'
    xlim = get.cell.meta.data("xlim")
    print(xlim)
    sector.index = get.cell.meta.data("sector.index")
    # need this since labels differ from sector.index values
    reg1 = df1$reg1[df1$region == sector.index]
    reg2 = df1$reg2[df1$region == sector.index]
    sector_limit = df$total_orig[df$orig_midreg == sector.index][[1]] / 10000
    print(sector_limit)
    # add text for reg1
    circos.text(x = mean(xlim), y = ifelse(test = nchar(reg2) == 0, yes = 4, no = 5), 
                labels = reg1, facing = "bending", cex = 1.4)
    # add text for reg2
    circos.text(x = mean(xlim), y = 4, 
                labels = reg2, facing = "bending", cex = 1.4)
    # Add ticks & labels
    circos.axis(
      h = "top", 
      major.at = seq(from = 0, to = sector_limit, by = 10),
      minor.ticks = 1, 
      labels.niceFacing = FALSE)
  }
)
text(x = 0, y = 1.2, cex = 1.8, labels = "International migration flows as percent of origin")

filename = normalizePath(paste0(BASE_DIR, "/outputs/chord_plot_region_percent", "_", DATE, ".pdf"))
dev.copy2pdf(file = filename, height=12, width=15)

