###############################
# ts-length-model.R
#
# Alewife TS-length model, as the bloaterTS base model (acoustic_target_strength_of_bloater.Rmd, r3): tow mean TS on
# LogL = log10(mean length, cm), lmer fitted by maximum likelihood (REML = FALSE) with a random intercept for the
# calibration unit (vessel-year; one lake, so no lake split). Tows: data/derived/analysis_tows.csv (analysis == TRUE).
# Writes data/derived/ts_length_model.txt and data/derived/ts_length_model.png.
###############################
library(tidyverse)
library(here)
library(lme4)

d <- read_csv(here("data", "derived", "analysis_tows.csv"), show_col_types = FALSE) %>%
  filter(analysis) %>%
  mutate(LogL = log10(Length / 10), CAL_UNIT = factor(paste(vessel, year)))

out <- here("data", "derived", "ts_length_model.txt")
sink(out)
cat("Tows:", nrow(d), " calibration units:", nlevels(d$CAL_UNIT), "\n\n")

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

p <- ggplot(d, aes(LogL, meanTS)) +
  geom_point(aes(colour = acoustic_format), alpha = 0.7) +
  geom_abline(intercept = fixef(r3)[1], slope = fixef(r3)[2]) +
  labs(x = "log10(mean length, cm)", y = "Tow mean TS (dB)", colour = "Data",
       title = sprintf("Alewife: TS = %.1f LogL %+.1f (%d tows)", fixef(r3)[2], fixef(r3)[1], nrow(d))) +
  theme_bw()
ggsave(here("data", "derived", "ts_length_model.png"), p, width = 6, height = 4.5, dpi = 150)
cat(readLines(out), sep = "\n")
