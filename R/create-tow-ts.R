###############################
# create-tow-ts.R
#
# Mean TS per used tow from the tow run's single targets (data/derived/tow_single_targets/, step 05), as bloaterTS
# R/create-tow-ts.R: mean of sigma_bs over the targets, in dB. Tows = the used tows of data/derived/tow_selection.csv.
# Writes data/derived/tow_ts.csv (one row per tow) and data/derived/tow_targets.csv (the targets behind it).
###############################
library(tidyverse)
library(here)

used <- read_csv(here("data", "derived", "tow_selection.csv"), show_col_types = FALSE) %>%
  filter(status == "used")

files <- here("data", "derived", "tow_single_targets", paste0(used$OP_ID, "_single_targets.csv"))
stopifnot(all(file.exists(files)))
targets <- map_dfr(files, ~ read_csv(.x, show_col_types = FALSE,
                                     col_select = c(OP_ID, Target_range, TS_comp)))

tow_ts <- targets %>%
  mutate(sigbs = 10^(TS_comp / 10)) %>%
  summarise(.by = OP_ID, mean_sigbs = mean(sigbs), Ntargs = n(), median_TS = median(TS_comp)) %>%
  mutate(meanTS = 10 * log10(mean_sigbs)) %>%
  select(-mean_sigbs)

stopifnot(nrow(tow_ts) == nrow(used))
write_csv(tow_ts, here("data", "derived", "tow_ts.csv"))
write_csv(targets %>% select(OP_ID, TS_comp), here("data", "derived", "tow_targets.csv"))
