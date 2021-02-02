library(MASS)

# TO DO
# make it easy to swap between mac/windows
#pc <- path.abspath("N:/johnson/linkedin_recruiter")
#mac <- path.abspath("/Users/scharlottej13/Nextcloud/linkedin_recruiter")
#if (Sys.getenv("HOME") == "/Users/scharlottej13")
#{parent_dir <- "/Users/scharlottej13/Nextcloud/linkedin_recruiter"}

# read in data (thanks Tom!)
df <- read.csv("/Users/scharlottej13/Nextcloud/linkedin_recruiter/outputs/model_input_2021-02-01.csv")
# just pick one date for now
df <- subset(df, query_date == "2020-07-25")

run_cohen_model <- function(df, x_vars, categ_vars = c(), threshold=1) {
  # drop small flow values, arbitrary threshold
  df <- df[df$flow > threshold, ]
  # drop rows with null values if column is a covariate
  df <- df[complete.cases(df[,x_vars]),]
  # create indicator variables (matrix of 0s/1s)
  wide_vars <- as.data.frame(model.matrix(~ country_dest + country_orig - 1, data=df))
  # log10 transform
  # nice post on when to log t'form:
  # https://stats.stackexchange.com/questions/298/in-linear-regression-when-is-it-appropriate-to-use-the-log-of-an-independent-va
  df[,c(x_vars, "flow")] <- log10(df[,c(x_vars, "flow")])
  if (length(categ_vars) > 0) {df[,categ_vars] <- factor(df[,categ_vars])}
  df <- cbind(wide_vars, df[,c(x_vars, "flow", categ_vars)])
  fit <- lm(flow ~ ., data = df)
}

fit1 <- run_cohen_model(df, c("users_orig", "users_dest", "distance"))
fit2 <- run_cohen_model(df, c("users_orig", "users_dest", "distance", "area_orig", "area_dest"))
fit3 <- run_cohen_model(df, c("users_orig", "users_dest", "distance", "area_orig"))
fit4 <- run_cohen_model(df, c("users_orig", "users_dest", "distance", "area_dest"))
fit5 <- run_cohen_model(df, c("users_orig", "users_dest", "distance", "population_dest", "population_orig"))
fit6 <- run_cohen_model(df, c("distance", "population_dest", "population_orig"))

# see if indicator variables way is same as factor variables-- not quite, but similar
lm(log10(flow) ~ factor(country_dest) + factor(country_orig) + log10(distance) + log10(users_orig) + log10(users_dest), data = df)

plot(model.frame(fit1)$flow, fit1$fitted.values)

# progress today
# some countries do seem to have much larger coefficients than others
# should I use outliers or coefficients to figure out which countries are interesting?
# also, other variables don't seem to be important at all
# next steps:
# 1) how to incorporate repeated measures?
# 2) find outliers
# 3) understand meaning of coefficients
# 4) how does using one-hot encoding differ from a categorical variable?
# 5) add "labor market conditions" see Bijak et al. ref
# 6) replace w/ population "weighted average" by age?
# [^ maybe useful? perhaps if the linkedin users are younger then they are also more likely to have aspirations?]