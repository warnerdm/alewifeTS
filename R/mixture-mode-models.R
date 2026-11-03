###############################
# mixture-mode-models.R
#
# The alewife TS mode of each tow from the mixture fit (python/mixture_fit.py all) against length, with the tow's mean
# length (as Brooking and Rudstam 2009, whose cage groups were near-uniform in size) and with its modal length (the most
# common 5-mm bin of the catch; create-tow-sizes.R), as a sensitivity check (user, 2026-11-03). lmer, ML,
# calibration-unit intercept, as ts-length-model.R. Subsets: all 117 tows; mode > -55 dB; and >= 20 alewife targets with a
# sound weak-group fit (indicative only: the first two cuts use the fitted mode).
# Writes data/derived/mixture_fit/mode_models.csv and mode_models.png.
###############################
library(tidyverse)
library(here)
library(lme4)

d <- read_csv(here("data", "derived", "mixture_fit", "mixture_fit_all.csv"), show_col_types = FALSE) %>%
  inner_join(read_csv(here("data", "derived", "analysis_tows.csv"), show_col_types = FALSE) %>%
               select(OP_ID, vessel, year, modal_length), by = "OP_ID") %>%
  mutate(CAL_UNIT = factor(paste(vessel, year)), LogL_mean = log10(length_mm / 10), LogL_modal = log10(modal_length / 10))
stopifnot(!any(is.na(d$modal_length)))

subsets <- list("all" = d,
                "mode > -55 dB" = filter(d, alewife_mode > -55),
                ">= 20 alewife targets, weak fit ok" = filter(d, alewife_mode > -55, n_alewife >= 20, weak_scale <= 50))
res <- imap_dfr(subsets, function(x, nm) {
  map_dfr(c("LogL_mean", "LogL_modal"), function(v) {
    x$LogL <- x[[v]]
    m <- lmer(alewife_mode ~ LogL + (1 | CAL_UNIT), data = x, REML = FALSE)
    ci <- confint(m, parm = "LogL", method = "profile")
    tibble(subset = nm, length = sub("LogL_", "", v), tows = nrow(x), slope = fixef(m)[2], slope_lo = ci[1],
           slope_hi = ci[2], intercept = fixef(m)[1], R2m = MuMIn::r.squaredGLMM(m)[1], sd_resid = sigma(m),
           mode_10cm = fixef(m)[1] + fixef(m)[2])
  })
})
write_csv(res, here("data", "derived", "mixture_fit", "mode_models.csv"))
print(res %>% mutate(across(where(is.double), ~ round(.x, 2))), width = 200)

p <- d %>%
  pivot_longer(c(LogL_mean, LogL_modal), names_to = "length", values_to = "LogL") %>%
  mutate(length = recode(length, LogL_mean = "mean length", LogL_modal = "modal length"),
         fit = if_else(alewife_mode > -55 & n_alewife >= 20 & weak_scale <= 50, "well determined", "other")) %>%
  ggplot(aes(LogL, alewife_mode)) +
  geom_point(aes(colour = fit), size = 1.5) +
  scale_colour_manual(values = c("well determined" = "black", other = "grey60")) +
  geom_abline(intercept = -62.2, slope = 19.1, colour = "red") +
  facet_wrap(~ length) +
  labs(x = "log10(length, cm)", y = "Fitted alewife TS mode (dB)", colour = NULL,
       caption = "red: Brooking and Rudstam (2009) cage mode, 19.1 log10 L - 62.2") +
  theme_bw()
ggsave(here("data", "derived", "mixture_fit", "mode_models.png"), p, width = 9, height = 4.5, dpi = 150)
