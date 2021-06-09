# Set of functions to easily use circilize package
# (heavily influenced by migest package)
# to create chord diagrams
# other resources:
# https://github.com/guyabel/migest/blob/master/demo/cfplot_reg2.R
# https://www.streetlightdata.com/chord-diagrams-visualizing-data/?type=blog/
# https://jokergoo.github.io/circlize_book/book/advanced-usage-of-chorddiagram.html

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

get_outpath <- function(base_dir, loc_level, loc_group, recip, percent) {
  out_dir <- file.path(base_dir, "plots")
  filename <- paste0("chord_diagram_", loc_level, "_", loc_group, ".pdf")
  if (percent) {
    filename <- paste0(
      "chord_diagram_", loc_level, "_", loc_group, "_pct", ".pdf")
  }
  path <- file.path(out_dir, filename)
  if (recip) {
    path <- file.path(out_dir, "recip", filename)
  }
  path
}

copy2archive <- function(active_path) {
  archive_dir <- file.path(dirname(active_path), "_archive")
  split_name <- unlist(strsplit(basename(active_path), ".", fixed = T))
  # append timestamp
  newname <- paste0(split_name[1], "_", Sys.Date(), ".", split_name[2])
  file.copy(active_path, archive_dir)
  file.rename(
    from = file.path(archive_dir, basename(active_path)),
    to = file.path(archive_dir, newname)
  )
}

plot_n_save_wrapper <- function(
  df, df1, color_vector, base_dir, loc_level, loc_group,
  recip = FALSE, percent = FALSE, grouper = NULL
) {
  outpath <- get_outpath(base_dir, loc_level, loc_group, recip, percent)
  pdf(outpath, width = 10, height = 12)
  circos.par(start.degree = 90, gap.degree = 4, track.margin = c(-0.1, 0.1),
             points.overflow.warning = FALSE)
  if (!is.null(grouper)) {
    chordDiagram(
      x = df, grid.col = color_vector, transparency = 0.25,
      big.gap = 4, group = grouper,
      directional = 1, direction.type = c("arrows", "diffHeight"),
      diffHeight = -0.04, annotationTrack = "grid",
      link.arr.type = "big.arrow", link.sort = TRUE, link.largest.ontop = TRUE
    )
  } else {
    chordDiagram(
      x = df, grid.col = color_vector, transparency = 0.25,
      # order = df1$loc_name,
      directional = 1, direction.type = c("arrows", "diffHeight"),
      diffHeight = -0.04, annotationTrack = "grid",
      link.arr.type = "big.arrow", link.sort = TRUE, link.largest.ontop = TRUE
    )
  }
  chordDiagram(
    x = df, grid.col = color_vector, transparency = 0.25,
    # order = df1$loc_name,
    directional = 1, direction.type = c("arrows", "diffHeight"),
    diffHeight  = -0.04, annotationTrack = "grid",
    link.arr.type = "big.arrow", link.sort = TRUE, link.largest.ontop = TRUE
  )
  circos.trackPlotRegion(
    track.index = 1, bg.border = NA, panel.fun = function(x, y) {
      # function loops through each 'sector.index'
      xlim <- get.cell.meta.data("xlim")
      sector_index <- get.cell.meta.data("sector.index")
      # need this since labels differ from sector.index values
      # loc1 and loc2 are split to two lines if too long
      # add text for loc1
      loc1 <- df1$loc1[df1$loc_name == sector_index]
      loc2 <- df1$loc2[df1$loc_name == sector_index]
      # scales text size, 1 is default
      cex <- 1.6
      circos.text(
        x = mean(xlim), y = ifelse(test = nchar(loc2) == 0, yes = 5.2, no = 6),
        labels = loc1, facing = "bending", cex = cex, niceFacing = TRUE
      )
      # and then for loc2
      circos.text(x = mean(xlim), y = 4, niceFacing = TRUE,
                  labels = loc2, facing = "bending", cex = cex)
      # Add ticks
      if (percent) {
        circos.axis(
        h = "top",
        major.at = seq(from = 0, to = xlim[2], by = 5),
        minor.ticks = 1,
        labels.niceFacing = TRUE
      )
      } else {
        circos.axis(
          h = "top",
          major.at = seq(from = 0, to = xlim[2],
            by = ifelse(test = xlim[2] > 10, yes = 2, no = 1)
          ),
          minor.ticks = 1,
          labels.niceFacing = TRUE
        )
      }
    }
  )
  circos.clear()
  dev.off()
  copy2archive(outpath)
}
