###############################
# ts-floor-models.R
#
# TS floor sensitivity of the TS-length model. Targets detected down to -77 dB (scripts/10_ts_floor_run.py) are
# subset at each floor (TS_comp >= floor, <= -30 dB); each analysis tow's mean TS (mean sigma_bs, in dB) is recomputed
# and the model of ts-length-model.R refitted (lmer, ML, calibration-unit intercept). Check: at -60 dB the subset
# should give step 05's tow means (data/derived/tow_ts.csv).
# Writes data/derived/ts_floor/tow_ts_by_floor.csv, ts_floor_models.csv and ts_floor_models.png.
###############################
library(tidyverse)
library(here)
library(lme4)

FLOORS <- c(-60, -63, -66, -70, -77)
dir <- here("data", "derived", "ts_floor")

d <- read_csv(here("data", "derived", "analysis_tows.csv"), show_col_types = FALSE) %>%
  filter(analysis) %>%
  mutate(LogL = log10(Length / 10), CAL_UNIT = factor(paste(vessel, year)))

files <- file.path(dir, "single_targets_st77", paste0(d$OP_ID, "_single_targets.csv"))
stopifnot(all(file.exists(files)))
targets <- map_dfr(files, ~ read_csv(.x, show_col_types = FALSE, col_select = c(OP_ID, TS_comp)))

by_floor <- map_dfr(FLOORS, function(fl) {
  targets %>%
    filter(TS_comp >= fl) %>%
    summarise(.by = OP_ID, n = n(), meanTS = 10 * log10(mean(10^(TS_comp / 10)))) %>%
    mutate(floor = fl)
})
write_csv(by_floor, file.path(dir, "tow_ts_by_floor.csv"))

# check against step 05 at -60 dB
chk <- by_floor %>% filter(floor == -60) %>%
  inner_join(read_csv(here("data", "derived", "tow_ts.csv"), show_col_types = FALSE), by = "OP_ID")
cat("check at -60 dB:", nrow(chk), "tows; targets equal in", sum(chk$n == chk$Ntargs),
    "; max |mean TS difference|", signif(max(abs(chk$meanTS.x - chk$meanTS.y)), 3), "dB\n")

fits <- map_dfr(FLOORS, function(fl) {
  x <- d %>% select(-meanTS, -Ntargs) %>% inner_join(filter(by_floor, floor == fl), by = "OP_ID")
  m <- lmer(meanTS ~ LogL + (1 | CAL_UNIT), data = x, REML = FALSE)
  ci <- confint(m, parm = "LogL", method = "profile")
  tibble(floor = fl, tows = nrow(x), targets = sum(x$n), slope = fixef(m)[2], slope_lo = ci[1], slope_hi = ci[2],
         intercept = fixef(m)[1], R2m = MuMIn::r.squaredGLMM(m)[1], sd_unit = attr(VarCorr(m)$CAL_UNIT, "stddev"),
         sd_resid = sigma(m),
         ts_5cm = fixef(m)[1] + fixef(m)[2] * log10(5), ts_13cm = fixef(m)[1] + fixef(m)[2] * log10(13))
})
write_csv(fits, file.path(dir, "ts_floor_models.csv"))
print(fits %>% mutate(across(where(is.double), ~ round(.x, 2))), width = 200)

p <- d %>% select(OP_ID, LogL) %>% inner_join(by_floor, by = "OP_ID") %>%
  ggplot(aes(LogL, meanTS)) +
  geom_point(alpha = 0.5, size = 1) +
  geom_abline(data = fits, aes(intercept = intercept, slope = slope)) +
  facet_wrap(~ floor, labeller = label_both) +
  labs(x = "log10(mean length, cm)", y = "Tow mean TS (dB)") +
  theme_bw()
ggsave(file.path(dir, "ts_floor_models.png"), p, width = 9, height = 6, dpi = 150)
