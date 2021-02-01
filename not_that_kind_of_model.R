# gravity model
library(gravity)
library(tidyverse)
library(MASS)

# TO DO
# make it easy to swap between mac/windows
#pc <- path.abspath("N:/johnson/linkedin_recruiter")
#mac <- path.abspath("/Users/scharlottej13/Nextcloud/linkedin_recruiter")
#if (Sys.getenv("HOME") == "/Users/scharlottej13")
#{parent_dir <- "/Users/scharlottej13/Nextcloud/linkedin_recruiter"}

# read in data (thanks Tom!)
df <- read.csv("/Users/scharlottej13/Nextcloud/linkedin_recruiter/outputs/model_input_2021-01-29.csv")
# just pick one date for now
df <- subset(df, query_date == "2020-07-25")

run_cohen_model <- function(df, x_vars, categ_vars = c(), threshold=1) {
  # create indicator variables (matrix of 0s/1s)
  wide_vars <- as.data.frame(model.matrix(~ country_dest + country_orig - 1, data=df))
  df[,c(x_vars, "flow")] <- log10(df[,c(x_vars, "flow")])
  if (length(categ_vars) > 0) {df[,categ_vars] <- factor(df[,categ_vars])}
  df <- cbind(wide_vars, df[,c(x_vars, "flow", categ_vars)])
  fit <- lm(flow ~ ., data = df)
}

df <- fix_data(df)
fit1 <- run_cohen_model(df, c("users_orig", "users_dest", "distance"))
fit2 <- run_cohen_model(df, c("users_orig", "users_dest", "distance", "area_orig", "area_dest"))

plot(log10(df$flow), fit1$fitted.values)
ggplot()
