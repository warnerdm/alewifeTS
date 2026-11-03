###############################
# catch-based-model.R
#
# The TS-length model of ts-length-model.R (lmer, ML, calibration-unit intercept; the 117 model tows) with each tow's
# mean TS from the catch-based correction of Brooking and Rudstam (2009) (python/catch_based.py), beside the -60 dB mean
# TS, for all tows and for tows with >= 90% / >= 75% of their alewife within the curve's 58-159 mm. Exploratory (user,
# 2026-11-03). Writes data/derived/catch_based/catch_based_models.csv and catch_based_models.png.
###############################
library(tidyverse)
library(here)
library(lme4)

d <- read_csv(here("data", "derived", "catch_based", "catch_based.csv"), show_col_types = FALSE) %>%
  inner_join(read_csv(here("data", "derived", "analysis_tows.csv"), show_col_types = FALSE) %>%
               select(OP_ID, vessel, year, Length), by = "OP_ID") %>%
  mutate(LogL = log10(Length / 10), CAL_UNIT = factor(paste(vessel, year)))

fit <- function(x, y, label) {
  x <- x %>% filter(!is.na(.data[[y]])) %>% mutate(TS = .data[[y]])
  m <- lmer(TS ~ LogL + (1 | CAL_UNIT), data = x, REML = FALSE)
  ci <- confint(m, parm = "LogL", method = "profile")
  tibble(tows = label, ts = y, n = nrow(x), slope = fixef(m)[2], slope_lo = ci[1], slope_hi = ci[2],
         intercept = fixef(m)[1], R2m = MuMIn::r.squaredGLMM(m)[1], sd_resid = sigma(m),
         ts_5cm = fixef(m)[1] + fixef(m)[2] * log10(5), ts_13cm = fixef(m)[1] + fixef(m)[2] * log10(13))
}
sets <- list("all 117" = d, ">= 75% in 58-159 mm" = filter(d, share_in_range >= 0.75),
             ">= 90% in 58-159 mm" = filter(d, share_in_range >= 0.90))
res <- imap_dfr(sets, function(x, nm) bind_rows(fit(x, "mean_ts_60", nm), fit(x, "mean_ts_corrected", nm),
                                             fit(x, "mean_ts_corrected_unimodal_small", nm)))
write_csv(res, here("data", "derived", "catch_based", "catch_based_models.csv"))
print(res %>% mutate(across(where(is.double), ~ round(.x, 2))), width = 200)

p <- d %>%
  pivot_longer(c(mean_ts_60, mean_ts_corrected), names_to = "ts", values_to = "TS") %>%
  mutate(ts = recode(ts, mean_ts_60 = "all targets >= -60 dB", mean_ts_corrected = "catch-based correction"),
         in_range = share_in_range >= 0.75) %>%
  ggplot(aes(LogL, TS)) +
  geom_point(aes(colour = in_range), size = 1.5) +
  scale_colour_manual(values = c(`TRUE` = "black", `FALSE` = "grey60"), name = ">= 75% in 58-159 mm") +
  geom_abline(intercept = -64.25, slope = 20.53, colour = "blue") +
  geom_abline(intercept = -58.2, slope = 13.1, colour = "red", linetype = "dashed") +
  facet_wrap(~ ts) +
  labs(x = "log10(mean length, cm)", y = "Tow mean TS (dB)",
       caption = "blue: Warner et al. (2002); red dashed: Brooking and Rudstam (2009) cage mean") +
  theme_bw()
ggsave(here("data", "derived", "catch_based", "catch_based_models.png"), p, width = 9, height = 4.5, dpi = 150)
