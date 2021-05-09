library(MASS)
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
gravityModelData <- read.csv(
    file.path(get_parent_dir(), "raw-data", "VagrantsExampleData.csv")
)
gravityModel <- glm.nb(
    vagrants ~ log(population) + log(distance) + wheat + wages + wageTrajectory,
    data = gravityModelData
)
summary(gravityModel)

gravityModelData <- gravityModelData %>%
    mutate(pred1 = exp(-3.848
        + (1.235 * log(population))
            + (-0.542 * log(distance))
            + (-0.024 * wheat)
            + (-0.025 * wages)
            + (-0.014 * wageTrajectory)),
            pred2 = gravityModel$fitted.value
    )
# ^ they are the same