# https://gjabel.wordpress.com/2016/05/18/updated-circular-plots-for-directional-bilateral-migration-data/
# https://www.oeaw.ac.at/fileadmin/subsites/Institute/VID/PDF/Publications/Working_Papers/WP2016_02.pdf
# https://github.com/guyabel/migest/blob/master/demo/cfplot_reg2.R
# Gu, Z. (2014) circlize implements and enhances circular visualization in R. Bioinformatics.
library(circlize)
library(dplyr)
library(migest)

BASE_DIR <- "/Users/scharlottej13/Nextcloud/linkedin_recruiter/"
# set this manually
DATE <- "2020-12-02"

df1 <- read.csv(paste0(BASE_DIR, "inputs/chord_labels_colors.csv")) %>% arrange(order1)
color_vector <- setNames(df1$col1, df1$region)

df <- read.csv(paste0(BASE_DIR, "outputs/midreg_flows_", DATE, ".csv"))
df$flow_norm <- df$flow_norm / 100
chord_df <- df %>% select(orig_midreg, dest_midreg, flow_norm)
  
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
    # add text for reg1
    circos.text(x = mean(xlim), y = ifelse(test = nchar(reg2) == 0, yes = 4, no = 5), 
                labels = reg1, facing = "bending", cex = 1.4)
    # add text for reg2
    circos.text(x = mean(xlim), y = 4, 
                labels = reg2, facing = "bending", cex = 1.4)
    # Add ticks & labels
    circos.axis(
      h = "top", 
      major.at = seq(from = 0, to = xlim[2], by = ifelse(xlim[2]>100, yes = 20, no = 10)), 
      minor.ticks = 5, 
      labels.niceFacing = FALSE)
  }
)
text(x = -.6, y = 1.2, cex = 1.8, labels = "Migration flows by region")
if (grepl("norm", val_col)) {
  text(x = -.6, y = 1.12, cex = 1.5, labels = "per 1,000 LinkedIn users in origin")
}
filename = paste0(BASE_DIR, "/outputs/chord_plot_region", "_", DATE, ".pdf")
dev.copy2pdf(file = filename, height=10, width=10)

