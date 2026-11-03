###############################
# tracked-ts-model.R
#
# The TS-length model of ts-length-model.R (lmer, ML, calibration-unit intercept; the same 117 tows, outliers out)
# with each tow's mean TS from tracked targets only (python/tracked_ts.py): per detection and per fish (track), beside
# all targets. Exploratory (user, 2026-11-03). Writes data/derived/tracked_ts/tracked_ts_models.csv.
###############################
library(tidyverse)
library(here)
library(lme4)

o <- read_csv(here("data", "derived", "ts_length_outliers.csv"), show_col_types = FALSE) %>% filter(!outlier)
d <- read_csv(here("data", "derived", "analysis_tows.csv"), show_col_types = FALSE) %>%
  filter(OP_ID %in% o$OP_ID) %>%
  inner_join(read_csv(here("data", "derived", "tracked_ts", "tow_tracked_ts.csv"), show_col_types = FALSE), by = "OP_ID") %>%
  mutate(LogL = log10(Length / 10), CAL_UNIT = factor(paste(vessel, year)))

fit <- function(y, label) {
  x <- d %>% filter(!is.na(.data[[y]])) %>% mutate(TS = .data[[y]])
  m <- lmer(TS ~ LogL + (1 | CAL_UNIT), data = x, REML = FALSE)
  ci <- confint(m, parm = "LogL", method = "profile")
  tibble(ts = label, tows = nrow(x), slope = fixef(m)[2], slope_lo = ci[1], slope_hi = ci[2], intercept = fixef(m)[1],
         R2m = MuMIn::r.squaredGLMM(m)[1], ts_5cm = fixef(m)[1] + fixef(m)[2] * log10(5),
         ts_13cm = fixef(m)[1] + fixef(m)[2] * log10(13))
}
res <- bind_rows(fit("mean_ts_all", "all targets"), fit("mean_ts_tracked", "tracked targets"),
                 fit("mean_ts_fish", "per fish (track)"))
write_csv(res, here("data", "derived", "tracked_ts", "tracked_ts_models.csv"))
print(res %>% mutate(across(where(is.double), ~ round(.x, 2))), width = 200)
