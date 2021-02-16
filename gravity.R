library(gravity)

fit <- ddm(
    dependent_variable = "flow", distance = "distance",
    code_origin = "iso3_orig", code_destination = "iso3_dest",
    data = select(df, flow, distance, iso3_orig, iso3_dest)
)