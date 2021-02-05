library(MASS)
library(dplyr)
# install.packages("~/Users/scharlottej13/repos/gravity")

file <- "model_input_2021-02-05.csv"
# for swapping between windows & mac
os <- Sys.info()[["sysname"]]
if (os == "Darwin") {
  filepath <- paste0("/Users/scharlottej13/Nextcloud/linkedin_recruiter/outputs/", file)
} else if (os == "Windows") {
  filepath <- paste0("N:\\johnson\\linkedin_recruiter\\outputs\\", file)
} else {print("not tested for linux yet")}

# read in data
df <- read.csv(filepath)
# quick test to see if this helps other important variables not drop out
# tl;dr did not help
keep_isos <- c("usa", "can", "fra", "gbr", "uae")
testdf <- df %>% filter(iso3_orig %in% keep_isos & iso3_dest %in% keep_isos)

prep_data <- function(df, x_vars, categ_vars = c(), threshold = 0) {
  # drop small flow values, default will not drop anything
  df <- df[df$flow > threshold, ]
  # drop rows with null values if column is a covariate
  df <- df[complete.cases(df[,c(x_vars, categ_vars)]),]
  # create indicator variables (matrix of 0s/1s); -1 drops intercept column
  # this is how it was done in cohen paper; in a test dataset I compared
  # this to factor(country_dest) + factor(country_orig) and though fitted values
  # were identical, the beta coefficients were different
  wide_vars <- as.data.frame(model.matrix(~ country_dest + country_orig - 1, data=df))
  if (length(categ_vars) > 0) {df[,categ_vars] <- factor(df[,categ_vars])}
  df <- cbind(wide_vars, df[,c(x_vars, "flow", categ_vars)])
}

run_model <- function(df, x_vars, type = "cohen", log_vars = x_vars,
                      categ_vars = c(), threshold = 1) {
  x_vars <- union(x_vars, log_vars)
  df <- prep_data(df, x_vars, categ_vars, threshold)
  if (type == "cohen") {
    # https://www.pnas.org/content/105/40/15269
    df[,c(log_vars, "flow")] <- log10(df[,c(log_vars, "flow")])
    fit <- lm(flow ~ ., data = df)
  } else if(type == "poisson") {
    df[,c(log_vars)] <- log(df[,c(log_vars)])
    fit <- glm(flow ~ ., family = poisson(), data = df)
  } else { print("Model type needs to be one of 'cohen' or 'poisson''") }
}

fit <- run_model(df, c("users_dest"))
fit <- run_model(df, c("users_orig", "users_dest"))
testfit <- run_model(testdf, c("users_orig", "users_dest"))

fit1 <- run_model(df, c("users_orig", "users_dest", "distance"))
fit2 <- run_model(df, c("users_orig", "users_dest", "distance", "area_orig", "area_dest"))
fit3 <- run_model(df, c("users_orig", "users_dest", "distance", "area_orig"))
fit4 <- run_model(df, c("users_orig", "users_dest", "distance", "area_dest"))
fit5 <- run_model(df, c("internet_orig", "internet_dest"), log_vars = c("users_orig", "users_dest", "distance"))
fit6 <- run_model(df, c("users_orig", "users_dest", "distance", "maxgdp_dest", "maxgdp_orig"))

plot(model.frame(fit1)$flow, fit1$fitted.values)

# some countries do seem to have much larger coefficients than others
# should I use outliers or coefficients to figure out which countries are interesting?
# also, other variables don't seem to be important at all
# next steps:
# 1) how to incorporate repeated measures?
# 2) find outliers
# 3) understand meaning of coefficients
# 4) how does using one-hot encoding differ from a categorical variable?
# 5) add "labor market conditions"? see Bijak et al. ref
# 6) replace w/ population "weighted average" by age?
# [^ maybe useful? perhaps if the linkedin users are younger then they are also more likely to have aspirations?]

