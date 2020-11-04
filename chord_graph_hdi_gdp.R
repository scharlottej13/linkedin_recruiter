# https://gjabel.wordpress.com/2016/05/18/updated-circular-plots-for-directional-bilateral-migration-data/
# https://www.oeaw.ac.at/fileadmin/subsites/Institute/VID/PDF/Publications/Working_Papers/WP2016_02.pdf
# https://github.com/guyabel/migest/blob/master/demo/cfplot_reg2.R
# Gu, Z. (2014) circlize implements and enhances circular visualization in R. Bioinformatics.
library(circlize)
library(dplyr)
library(migest)
library(RColorBrewer)

# actual data
df0 <- read.csv("/Users/scharlottej13/Nextcloud/linkedin_recruiter/outputs/july_hdi_flows_2020-10-21.csv")
df0$flow_per_100000 <- df0$flow / 100000
# plot parameters (e.g. colors, etc.)
color_vector <- setNames(brewer.pal(5, 'RdYlBu'), c("low", "low-middle", "middle", "middle-high", "high"))

#default chord diagram
chord_df <- df0 %>% select(maxhdi_orig_bin, maxhdi_dest_bin, flow_per_100000)
chordDiagram(x = chord_df)
#plot parameters
circos.clear()
circos.par(start.degree = 90, gap.degree = 4, track.margin = c(-0.1, 0.1), points.overflow.warning = FALSE)
par(mar = rep(0, 4))
# real deal
chordDiagram(x = chord_df,
             grid.col = color_vector, transparency = 0.25, directional = 1,
             direction.type = c("arrows", "diffHeight"), diffHeight  = -0.04,
             annotationTrack = "grid", annotationTrackHeight = c(0.05, 0.1),
             link.arr.type = "big.arrow", link.sort = TRUE, link.largest.ontop = TRUE)

circos.trackPlotRegion(
  track.index = 1, 
  bg.border = NA, 
  panel.fun = function(x, y) {
    # function loops through each 'sector.index'
    xlim = get.cell.meta.data("xlim")
    sector.index = get.cell.meta.data("sector.index")
    # add text for reg2
    circos.text(x = mean(xlim), y = 5,  labels = sector.index, facing = "bending", cex = 1.4, niceFacing = FALSE)
    # Add ticks & labels
    circos.axis(
      h = "top", 
      major.at = seq(from = 0, to = xlim[2], by = ifelse(test = xlim[2]>5, yes = 2, no = 1)),
      minor.ticks = 1, 
      major.tick.percentage = 0.5,
      labels.niceFacing = FALSE)
  }
)

dev.copy2pdf(file ="chord_plot_hdi.pdf", height=10, width=10)
file.show("chord_plot_hdi.pdf")

