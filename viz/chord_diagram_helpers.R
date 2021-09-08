# Set of functions to easily use circilize package
# (heavily influenced by migest package) to create chord diagrams
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
  circos.par(
    start.degree = 90,
    gap.degree = 4, track.margin = c(-0.1, 0.1),
    points.overflow.warning = FALSE)
  chordDiagram(
    x = df, grid.col = color_vector, transparency = 0.25,
    directional = 1, direction.type = c("arrows", "diffHeight"),
    diffHeight = -0.04, annotationTrack = "grid",
    link.arr.type = "big.arrow", link.sort = TRUE, link.largest.ontop = TRUE,
    group = grouper, # still working out the bugs in 'grouper' part
    scale = percent # scales so all sectors are the same size
  )
  circos.track(
    track.index = 1, bg.border = NA, panel.fun = function(x, y) {
      # function loops through each 'sector.index'
      xlim <- get.cell.meta.data("xlim")
      sector_index <- get.cell.meta.data("sector.index")
      ylim <- get.cell.meta.data("ylim")
      # scale up text size a bit
      cex <- 1.6
      style <- "bending"
      num_going <- df %>%
        filter(midregion_orig == sector_index) %>%
        summarise(across(flow_median, sum)) %>%
        pull(flow_median)
      # Add ticks
      if (!percent) {
        # loc1 and loc2 are split to two lines if too long
        loc1 <- df1$loc1[df1$loc_name == sector_index]
        loc2 <- df1$loc2[df1$loc_name == sector_index]
        circos.text(
          x = mean(xlim), y = ifelse(nchar(loc2) == 0, 5.2, 6),
          labels = loc1, facing = style, cex = cex, niceFacing = TRUE
        )
        # and then for loc2
        circos.text(
          x = mean(xlim), y = 4, niceFacing = TRUE,
          labels = loc2, facing = style, cex = cex
        )
        labels <- c(0, num_going, xlim[2])
        circos.axis(labels = FALSE, major.at = labels, minor.ticks = 0)
        for (x in labels) {
          circos.text(
            x, 2, round(x / 100000, ifelse(x / 100000 < 1, 1, 0)),
            cex = 0.8, niceFacing = TRUE,
            adj = ifelse(sector_index == "Oceania", c(0, 0), c(0.5, 0))
          )
        }
      } else {
        # grab values for flow range
        sum1 <- df %>%
          filter(midregion_orig == sector_index |
            midregion_dest == sector_index) %>%
          summarise(across(flow_median, sum)) %>%
          pull(flow_median)
        # add 'double counting' (may revisit this)
        self <- df %>%
          filter(midregion_orig == sector_index &
          midregion_dest == sector_index) %>%
          pull(flow_median)
        total <- sum1 + self
        # set the ticks
        sequence <- seq(0, 1, 0.20)
        circos.axis(
          labels = FALSE, major.at = sequence, minor.ticks = 1,
          labels.niceFacing = FALSE, labels.pos.adjust = FALSE
        )
        # manually add tick labels
        for (p in sequence) {
          circos.text(p, mean(ylim) + 1, p,
          cex = 0.8, adj = c(0.5, 0), niceFacing = FALSE)
        }
        # add text for locations
        circos.text(
          x = mean(xlim), y = 6, labels = sector_index,
          facing = style, cex = cex, niceFacing = TRUE
        )
        # add dotted line
        circos.lines(xlim, c(3, 3), lty = 3)
        circos.text(
          mean(xlim), 3.2,
          paste0("N = ", prettyNum(round(total, -3), big.mark = ",")),
          cex = 0.8, adj = c(0.5, 0), niceFacing = TRUE
        )
      }
    }
  )
  circos.clear()
  dev.off()
  copy2archive(outpath)
}
