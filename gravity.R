log_distance <- function(data, distance) {
  data %>%
    mutate(
      dist_log = log(!!sym(distance))
    )
}
d <- log_distance(df, "distance")
d <- mutate(d, y_log = log(!!sym("flow")))
code_origin <- "iso3_orig"
code_destination <- "iso3_dest"
d <- d %>%
  mutate(
    y_log_ddm = !!sym("y_log"),
    dist_log_ddm = !!sym("dist_log")
  ) %>%
  group_by(!!sym(code_origin), .add = FALSE) %>%
  mutate(
    ym1 = mean(!!sym("y_log_ddm"), na.rm = TRUE),
    dm1 = mean(!!sym("dist_log_ddm"), na.rm = TRUE)
  ) %>%
  group_by(!!sym(code_destination), .add = FALSE) %>%
  mutate(
    ym2 = mean(!!sym("y_log_ddm"), na.rm = TRUE),
    dm2 = mean(!!sym("dist_log_ddm"), na.rm = TRUE)
  ) %>%
  group_by(!!sym(code_origin), .add = FALSE) %>%
  mutate(
    y_log_ddm = !!sym("y_log_ddm") - !!sym("ym1"),
    dist_log_ddm = !!sym("dist_log_ddm") - !!sym("dm1")
  ) %>%
  group_by(!!sym(code_destination), .add = FALSE) %>%
  mutate(
    y_log_ddm = !!sym("y_log_ddm") - !!sym("ym2"),
    dist_log_ddm = !!sym("dist_log_ddm") - !!sym("dm2")
  ) %>%
  ungroup() %>%
  mutate(
    y_log_ddm = !!sym("y_log_ddm") + mean(!!sym("y_log"), na.rm = TRUE),
    dist_log_ddm = !!sym("dist_log_ddm") + mean(!!sym("dist_log"), na.rm = TRUE)
  )



fit <- ddm(
    dependent_variable = "flow", distance = "distance",
    code_origin = "iso3_orig", code_destination = "iso3_dest", data = select(df, flow, distance, iso3_orig, iso3_dest)
    )