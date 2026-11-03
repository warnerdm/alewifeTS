###############################
# ts-length-model.R
#
# Alewife TS-length model, as the bloaterTS base model (acoustic_target_strength_of_bloater.Rmd, r3): tow mean TS on
# LogL = log10(mean length, cm), lmer fitted by maximum likelihood (REML = FALSE) with a random intercept for the
# calibration unit (vessel-year; one lake, so no lake split). Tows: data/derived/analysis_tows.csv (analysis == TRUE).
# Outlier rule (user, 2026-11-03): fit on all analysis tows, drop tows whose scaled residual (residual / residual SD) is
# beyond +-2.5, once (no iteration), refit; Cook's distance (4/n) reported as an influence check.
# Writes data/derived/ts_length_model.txt, ts_length_outliers.csv (all analysis tows, residuals, Cook's distance,
# outlier flag) and ts_length_model.png.
###############################
library(tidyverse)
library(here)
library(lme4)

MAX_SCALED_RESID <- 2.5

d_all <- read_csv(here("data", "derived", "analysis_tows.csv"), show_col_types = FALSE) %>%
  filter(analysis) %>%
  mutate(LogL = log10(Length / 10), CAL_UNIT = factor(paste(vessel, year)))

r_all <- lmer(meanTS ~ LogL + (1 | CAL_UNIT), data = d_all, REML = FALSE)
d_all <- d_all %>%
  mutate(fitted = fitted(r_all), scaled_resid = resid(r_all) / sigma(r_all),
         cooks_d = cooks.distance(influence(r_all)),
         outlier = abs(scaled_resid) > MAX_SCALED_RESID)
write_csv(d_all %>% select(OP_ID, year, vessel, Length, n_measured, Ntargs, meanTS, fitted, scaled_resid, cooks_d, outlier),
          here("data", "derived", "ts_length_outliers.csv"))

d <- d_all %>% filter(!outlier) %>% mutate(CAL_UNIT = droplevels(CAL_UNIT))

out <- here("data", "derived", "ts_length_model.txt")
sink(out)
cat("All analysis tows:", nrow(d_all), "; fit on all of them: TS =", round(fixef(r_all)[2], 2), "LogL",
    sprintf("%+.2f", fixef(r_all)[1]), "\n")
cat("Outliers (|scaled residual| >", MAX_SCALED_RESID, "):\n")
print(d_all %>% filter(outlier) %>% select(OP_ID, Length, Ntargs, meanTS, fitted, scaled_resid, cooks_d) %>%
        as.data.frame(), row.names = FALSE, digits = 3)
cat("Cook's distance > 4/n =", round(4 / nrow(d_all), 3), ":", paste(d_all$OP_ID[d_all$cooks_d > 4 / nrow(d_all)], collapse = " "), "\n\n")
cat("Model tows:", nrow(d), " calibration units:", nlevels(d$CAL_UNIT), "\n\n")

r3 <- lmer(meanTS ~ LogL + (1 | CAL_UNIT), data = d, REML = FALSE)
r0 <- lmer(meanTS ~ 1 + (1 | CAL_UNIT), data = d, REML = FALSE)
print(summary(r3))
cat("\nLength term, likelihood-ratio test (r0 vs r3):\n"); print(anova(r0, r3))
cat("\nProfile 95% CI:\n"); print(confint(r3, method = "profile"))
cat("\nR2 (marginal = length alone; conditional = with calibration units):\n"); print(MuMIn::r.squaredGLMM(r3))
vc <- as.data.frame(VarCorr(r3))
cat("\nICC (calibration-unit share of the unexplained variance):", round(vc$vcov[1] / sum(vc$vcov), 3), "\n")
cat("\nCalibration-unit offsets from the line (dB):\n")
print(ranef(r3)$CAL_UNIT %>% rownames_to_column("CAL_UNIT") %>% rename(offset_db = `(Intercept)`) %>%
        left_join(count(d, CAL_UNIT, name = "tows"), by = "CAL_UNIT") %>% arrange(offset_db), row.names = FALSE)

# the same line with the slope fixed at 20 (TS = 20 log10 L + b20), for comparison with published b20 values
b20 <- lmer(meanTS ~ 1 + offset(20 * LogL) + (1 | CAL_UNIT), data = d, REML = FALSE)
cat("\nSlope fixed at 20: b20 =", round(fixef(b20)[1], 2), "dB; vs free slope:\n"); print(anova(b20, r3))
sink()

p <- ggplot(d_all, aes(LogL, meanTS)) +
  geom_point(aes(colour = acoustic_format, shape = outlier), alpha = 0.7) +
  scale_shape_manual(values = c(`FALSE` = 16, `TRUE` = 4)) +
  geom_abline(intercept = fixef(r3)[1], slope = fixef(r3)[2]) +
  labs(x = "log10(mean length, cm)", y = "Tow mean TS (dB)", colour = "Data", shape = "Outlier",
       title = sprintf("Alewife: TS = %.1f LogL %+.1f (%d tows)", fixef(r3)[2], fixef(r3)[1], nrow(d))) +
  theme_bw()
ggsave(here("data", "derived", "ts_length_model.png"), p, width = 6, height = 4.5, dpi = 150)
cat(readLines(out), sep = "\n")
