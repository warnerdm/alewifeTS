###############################
# acoustic-trawl-screen.R
#
# Which alewife tows disagree most between the acoustics and the trawl? (user, 2026-11-24, after tow 78795: the
# largest catch of any tow, 1,919 alewife, but a nearly empty tow region.) As bloaterTS R/acoustic-trawl-screen.R
# (2026-11-11; lm since 2026-11-17):
#   lm(log10 sv ~ log10(alewife per minute) + log10(L))
# Region Sv (not acoustic density, which divides by the tow's mean sigma_bs and so carries TS) against alewife caught per
# minute, with tow mean length as a covariate (larger fish backscatter more). Tows beyond 2 residual SDs are flagged
# and listed with their tow review note. Flag only; nothing is dropped.
# Differences from bloaterTS: region Sv is pydt4's (data/derived/tow_results.csv mean_sv_db: background noise removed,
# bad-data regions excluded, empty samples as sv = 0), bloaterTS's is Echoview's; Michigan only.
# Inputs: data/derived/analysis_tows.csv (analysis == TRUE: catch, mean length), tow_results.csv (region Sv),
#   LM_tow_list_alewife_run.csv (TOW_TIME), config/tow_review.csv.
# Outputs: data/derived/acoustic_trawl_screen.csv (per tow), review/acoustic_trawl_screen.png.
###############################
library(tidyverse)
library(here)

FLAG_SD <- 2   # residuals beyond this many residual SDs are flagged

analysis_tows <- read_csv(here("data", "derived", "analysis_tows.csv"), show_col_types = FALSE) %>%
  filter(analysis) %>%
  select(OP_ID, year, vessel, fishing_depth_m, acoustic_format, Length, N_catch)
region_sv <- read_csv(here("data", "derived", "tow_results.csv"), show_col_types = FALSE) %>%
  select(OP_ID, sv_mean_db = mean_sv_db)
tow_minutes <- read_csv(here("data", "derived", "LM_tow_list_alewife_run.csv"), show_col_types = FALSE) %>%
  select(OP_ID, TOW_TIME)
review_notes <- read_csv(here("config", "tow_review.csv"), show_col_types = FALSE) %>%
  select(OP_ID, review_reason = reason, review_note = note)

screen_data <- analysis_tows %>%
  left_join(region_sv, by = "OP_ID") %>%
  left_join(tow_minutes, by = "OP_ID") %>%
  mutate(log_sv   = sv_mean_db / 10,                 # log10 of the linear sv
         log_cpue = log10(N_catch / TOW_TIME),
         log_L    = log10(Length / 10))
stopifnot(!anyNA(screen_data$log_sv), !anyNA(screen_data$log_cpue), n_distinct(screen_data$OP_ID) == nrow(screen_data))

m_screen <- lm(log_sv ~ log_cpue + log_L, data = screen_data)
print(summary(m_screen)$coefficients)
cat("R2", round(summary(m_screen)$r.squared, 2), "; tows", nrow(screen_data), "\n")

screen_data <- screen_data %>%
  mutate(resid     = residuals(m_screen),
         resid_std = resid / sigma(m_screen),
         flagged   = abs(resid_std) > FLAG_SD) %>%
  left_join(review_notes, by = "OP_ID")
write_csv(screen_data %>% select(OP_ID, vessel, year, acoustic_format, fishing_depth_m, Length, N_catch, TOW_TIME,
                                 sv_mean_db, log_cpue, resid, resid_std, flagged, review_reason, review_note),
          here("data", "derived", "acoustic_trawl_screen.csv"))

cat("\nResidual SD (log10 sv):", round(sigma(m_screen), 3), "; flagged:", sum(screen_data$flagged), "of",
    nrow(screen_data), "\n")
screen_data %>%
  filter(flagged) %>%
  arrange(resid_std) %>%
  select(OP_ID, year, vessel, fishing_depth_m, Length, N_catch, TOW_TIME, sv_mean_db, resid_std, review_note) %>%
  mutate(across(c(Length, sv_mean_db, resid_std), ~ round(.x, 1)), review_note = str_trunc(review_note, 60)) %>%
  print(n = Inf, width = 200)

# figure: region Sv against catch rate, coloured by mean length, flagged tows labelled
p_screen <- screen_data %>%
  ggplot(aes(N_catch / TOW_TIME, sv_mean_db)) +
  geom_point(aes(colour = Length, shape = flagged), size = 2) +
  geom_text(data = ~ filter(.x, flagged | OP_ID == 78795), aes(label = OP_ID), size = 2.6, vjust = -0.8) +
  scale_x_log10() +
  scale_colour_viridis_c(name = "Mean length (mm)") +
  scale_shape_manual(values = c(`FALSE` = 16, `TRUE` = 17), guide = "none") +
  labs(x = "Alewife caught per minute", y = "Region Sv (dB)",
       caption = paste0("Triangles, labelled: residual beyond ", FLAG_SD,
                        " SD from log10 sv ~ log10 catch rate + log10 length (78795 labelled too).")) +
  theme_bw() + theme(panel.grid = element_blank(), legend.position = "top")
ggsave(here("review", "acoustic_trawl_screen.png"), p_screen, width = 6.5, height = 5, dpi = 150)
