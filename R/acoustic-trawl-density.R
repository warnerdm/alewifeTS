###############################
# acoustic-trawl-density.R
#
# Acoustic fish density in each tow region against alewife caught per minute (user, 2026-11-24), as the bloaterTS
# manuscript chunk acoustic-trawl-density (2026-11-09):
#   density = region mean sv / mean sigma_bs of the tow's single targets (fish per m3)
#   lm(log10 density ~ log10 catch per minute) for each choice of mean sigma_bs; slope (profile 95% CI), R2, Pearson r.
# Mean sigma_bs choices:
#   lower TS limits -60 / -63 / -66 / -70 / -77 dB: tow mean TS at each limit (data/derived/ts_floor/tow_ts_by_floor.csv;
#     -60 = the analysis tow mean TS). A lower limit gives a smaller sigma_bs, so a higher density.
#   (The Brooking and Rudstam catch-based mean TS was a sixth choice on 2026-11-24 and was then dropped, user.)
# Region Sv: pydt4 (data/derived/tow_results.csv mean_sv_db), as R/acoustic-trawl-screen.R. Tows: the 121 analysis tows.
# Descriptive only; nothing dropped.
# Outputs: data/derived/acoustic_trawl_density.csv (fits), acoustic_trawl_density_tows.csv (per tow),
#   review/acoustic_vs_trawl_density.png.
###############################
library(tidyverse)
library(here)

tows <- read_csv(here("data", "derived", "analysis_tows.csv"), show_col_types = FALSE) %>%
  filter(analysis) %>%
  select(OP_ID, year, vessel, Length, N_catch)
region_sv <- read_csv(here("data", "derived", "tow_results.csv"), show_col_types = FALSE) %>%
  select(OP_ID, sv_mean_db = mean_sv_db)
tow_minutes <- read_csv(here("data", "derived", "LM_tow_list_alewife_run.csv"), show_col_types = FALSE) %>%
  select(OP_ID, TOW_TIME)
ts_floor <- read_csv(here("data", "derived", "ts_floor", "tow_ts_by_floor.csv"), show_col_types = FALSE) %>%
  transmute(OP_ID, ts_choice = paste(floor, "dB"), meanTS)
choices <- paste(c(-60, -63, -66, -70, -77), "dB")

density_data <- tows %>%
  left_join(region_sv, by = "OP_ID") %>%
  left_join(tow_minutes, by = "OP_ID") %>%
  inner_join(ts_floor, by = "OP_ID", relationship = "one-to-many") %>%
  mutate(ts_choice = factor(ts_choice, levels = choices),
         cpue      = N_catch / TOW_TIME,
         density   = 10^(sv_mean_db / 10) / 10^(meanTS / 10))      # fish per m3
stopifnot(!anyNA(density_data$density), !anyNA(density_data$cpue),
          all(count(density_data, ts_choice)$n == nrow(tows)))

density_fit <- function(d) {
  m  <- lm(log10(density) ~ log10(cpue), data = d)
  ci <- confint(m, parm = "log10(cpue)")
  tibble(tows = nrow(d), slope = coef(m)[2], slope_lo = ci[1], slope_hi = ci[2],
         r2 = summary(m)$r.squared, r_pearson = cor(log10(d$density), log10(d$cpue)),
         resid_sd_log10 = sigma(m))
}
density_check <- density_data %>%
  group_by(ts_choice) %>%
  group_modify(~ density_fit(.x)) %>%
  ungroup()
print(density_check %>% mutate(across(where(is.double), ~ round(.x, 3))), width = 200)
write_csv(density_check, here("data", "derived", "acoustic_trawl_density.csv"))
write_csv(density_data %>% select(OP_ID, year, vessel, Length, N_catch, TOW_TIME, cpue, sv_mean_db, ts_choice, meanTS,
                                  density),
          here("data", "derived", "acoustic_trawl_density_tows.csv"))

# the same with the region Sv alone (no TS), for comparison: R/acoustic-trawl-screen.R without the length term
m_sv <- lm(sv_mean_db / 10 ~ log10(N_catch / TOW_TIME), data = distinct(density_data, OP_ID, .keep_all = TRUE))
cat(sprintf("\nRegion sv alone (no TS): slope %.3f, R2 %.3f\n", coef(m_sv)[2], summary(m_sv)$r.squared))

p <- density_data %>%
  ggplot(aes(cpue, density)) +
  geom_point(aes(colour = Length), size = 1.4) +
  geom_smooth(method = "lm", formula = y ~ x, se = FALSE, colour = "black", linewidth = 0.5) +
  scale_x_log10() + scale_y_log10() +
  scale_colour_viridis_c(name = "Mean length (mm)") +
  facet_wrap(~ts_choice, nrow = 2) +
  labs(x = "Alewife caught per minute", y = expression("Acoustic density (fish m"^-3*")"),
       caption = "Line: lm(log10 density ~ log10 catch per minute).") +
  theme_bw() + theme(panel.grid = element_blank(), legend.position = "top")
ggsave(here("review", "acoustic_vs_trawl_density.png"), p, width = 9, height = 6.8, dpi = 150)

# Age groups at -60 dB (user, 2026-11-24): tow mean length < 100 mm ~ age-0, >= 100 mm ~ age-1 and older.
#   m_age:  log10 density ~ log10 cpue + age group (parallel lines; the group offset is the density ratio at equal catch)
#   m_int:  with a slope per group, to check the lines are parallel
AGE_SPLIT_MM <- 100
d60 <- density_data %>%
  filter(ts_choice == "-60 dB") %>%
  mutate(age = factor(if_else(Length < AGE_SPLIT_MM, "age-0 (< 100 mm)", "age-1+ (>= 100 mm)")))
m_age <- lm(log10(density) ~ log10(cpue) + age, data = d60)
m_int <- lm(log10(density) ~ log10(cpue) * age, data = d60)
ci_age <- confint(m_age)
age_fit <- tibble(term = names(coef(m_age)), estimate = coef(m_age), se = summary(m_age)$coefficients[, 2],
                  lo = ci_age[, 1], hi = ci_age[, 2]) %>%
  mutate(n = nobs(m_age), r2 = summary(m_age)$r.squared, resid_sd_log10 = sigma(m_age),
         slope_difference_p = anova(m_age, m_int)$`Pr(>F)`[2])
print(age_fit %>% mutate(across(where(is.double), ~ signif(.x, 4))), width = 200)
off <- age_fit %>% filter(str_detect(term, "age"))
cat(sprintf("age-1+ density / age-0 density at equal catch: %.2f (95%% CI %.2f-%.2f)\n",
            10^off$estimate, 10^off$lo, 10^off$hi))
write_csv(age_fit, here("data", "derived", "acoustic_trawl_density_age.csv"))

lines_age <- d60 %>%
  reframe(cpue = 10^seq(log10(min(cpue)), log10(max(cpue)), length.out = 50), .by = age)
lines_age$density <- 10^predict(m_age, newdata = lines_age)
p_age <- ggplot(d60, aes(cpue, density, colour = age)) +
  geom_point(size = 1.8) +
  geom_line(data = lines_age, linewidth = 0.8) +
  scale_x_log10() + scale_y_log10() +
  scale_colour_manual(values = c("#1b9e77", "#7570b3"), name = NULL) +
  labs(x = "Alewife caught per minute", y = expression("Acoustic density (fish m"^-3*")"),
       caption = sprintf(paste0("Lower TS limit -60 dB; %d tows. Lines: log10 density ~ log10 catch per minute + age ",
                                "group;\nage-1+ / age-0 density at equal catch %.2f (%.2f-%.2f)."),
                         nrow(d60), 10^off$estimate, 10^off$lo, 10^off$hi)) +
  theme_bw() + theme(panel.grid = element_blank(), legend.position = "top")
ggsave(here("review", "acoustic_vs_trawl_density_age.png"), p_age, width = 6.5, height = 5, dpi = 150)
