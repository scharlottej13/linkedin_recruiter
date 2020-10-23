# https://gjabel.wordpress.com/2016/05/18/updated-circular-plots-for-directional-bilateral-migration-data/
# https://www.oeaw.ac.at/fileadmin/subsites/Institute/VID/PDF/Publications/Working_Papers/WP2016_02.pdf
# https://github.com/guyabel/migest/blob/master/demo/cfplot_reg2.R
# Gu, Z. (2014) circlize implements and enhances circular visualization in R. Bioinformatics.
library(circlize)
library(dplyr)
library(migest)

# actual data
# df0 <- read.csv("N:/johnson/linkedin_recruiter/outputs/july_midregion_flows_2020-10-16.csv")
df0 <- read.csv("/Users/scharlottej13/Downloads/july_midregion_flows_2020-10-16.csv")
df0$flow_per_100000 <- df0$flow / 100000
# plot parameters (e.g. colors, etc.)
# df1 <- read.csv(system.file("vidwp", "reg_plot.csv", package = "migest"), stringsAsFactors=FALSE)
df1 <- read.csv("/Users/scharlottej13/Desktop/chord_labels_colors.csv")
df1 %>% arrange(order1)
# set colors for regions
color_vector <- setNames(df1$col1, df1$region)

#default chord diagram
chordDiagram(x = df0 %>% select(orig_midreg, dest_midreg, flow_per_100000))
#plot parameters
circos.clear()
circos.par(start.degree = 90, gap.degree = 4, track.margin = c(-0.1, 0.1), points.overflow.warning = FALSE)
par(mar = rep(0, 4))
# real deal
chordDiagram(x = df0 %>% select(orig_midreg, dest_midreg, flow_per_100000),
             grid.col = color_vector, transparency = 0.25,
             order = df1$region, directional = 1,
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
    # only need reg1, reg2 bits if labels differ from sector.index values
    reg1 = df1$reg1[df1$region == sector.index]
    reg2 = df1$reg2[df1$region == sector.index]
    # add text for reg1
    circos.text(x = mean(xlim), y = ifelse(test = nchar(reg2) == 0, yes = 3, no = 4), 
                labels = reg1, facing = "bending", cex = 1.4)
    # add text for reg2
    circos.text(x = mean(xlim), y = 3, 
                labels = reg2, facing = "bending", cex = 1.4)
    # Add ticks & labels
    circos.axis(
      h = "top", 
      major.at = seq(from = 0, to = xlim[2], by = ifelse(test = xlim[2]>5, yes = 2, no = 1)), 
      minor.ticks = 1, 
      major.tick.percentage = 0.5,
      labels.niceFacing = FALSE)
  }
)

dev.copy2pdf(file ="chord_plot_region.pdf", height=10, width=10)
file.show("chord_plot_region.pdf")

