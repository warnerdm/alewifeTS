###############################
# create-tow-sizes.R
#
# Alewife length and weight per used tow, from the project's copies of the trawl files (data/raw/trawl), as bloaterTS
# R/create-lm-tow-sizes.R. Tows = the used tows of data/derived/tow_selection.csv (step 08).
# Writes data/derived/tow_sizes.csv (one row per tow) and data/derived/tow_lengths.csv (the measured alewife behind it).
###############################
library(tidyverse)
library(here)

trawl <- here("data", "raw", "trawl")
used <- read_csv(here("data", "derived", "tow_selection.csv"), show_col_types = FALSE) %>%
  filter(status == "used") %>%
  select(OP_ID, year, vessel, fishing_depth_m, acoustic_format)

catch_data <- read_csv(list.files(trawl, pattern = "Acoustic_tr_catch", full.names = TRUE),
                       show_col_types = FALSE) %>%
  filter(OP_ID %in% used$OP_ID)

lf <- read_csv(list.files(trawl, pattern = "Acoustic_tr_lf", full.names = TRUE), show_col_types = FALSE) %>%
  filter(OP_ID %in% used$OP_ID & SPECIES == 106 & LENGTH >= 5 & LENGTH < 300)   # alewife; drops impossible lengths

alewife_catch <- catch_data %>%
  filter(SPECIES == 106) %>%
  summarise(.by = OP_ID, N_catch = sum(N), WEIGHT = sum(WEIGHT))   # WEIGHT in g

all_catch <- catch_data %>%
  summarise(.by = OP_ID, N_all = sum(N))

sizes <- lf %>%
  summarise(.by = OP_ID,
            Length     = sum(LENGTH * N) / sum(N),                                   # mean length, mm
            sd_length  = sqrt(sum(N * (LENGTH - sum(LENGTH * N) / sum(N))^2) / (sum(N) - 1)),
            min_length = min(LENGTH),
            max_length = max(LENGTH),
            n_measured = sum(N)) %>%
  mutate(se_length = sd_length / sqrt(n_measured),
         rel_se = se_length / Length)

tow_sizes <- used %>%
  left_join(sizes, by = "OP_ID") %>%
  left_join(alewife_catch, by = "OP_ID") %>%
  left_join(all_catch, by = "OP_ID") %>%
  mutate(meanW = WEIGHT / N_catch,          # mean alewife weight, g
         prop_alewife = N_catch / N_all)

stopifnot(nrow(tow_sizes) == nrow(used))
write_csv(tow_sizes, here("data", "derived", "tow_sizes.csv"))
write_csv(lf %>% select(OP_ID, LENGTH, N), here("data", "derived", "tow_lengths.csv"))
