###############################
# create-analysis-tows.R
#
# The tows of the TS-length analysis: the used tows' sizes (create-tow-sizes.R) and mean TS (create-tow-ts.R) with the
# bloaterTS tow rule (user, 2026-11-03): >= 10 targets, >= 5 alewife measured, relative SE of the mean length <= 10%.
# Writes data/derived/analysis_tows.csv (all used tows; analysis = TRUE for those kept, why = the rule they fail).
###############################
library(tidyverse)
library(here)

MIN_TARGETS <- 10
MIN_MEASURED <- 5
MAX_REL_SE <- 0.10

tows <- read_csv(here("data", "derived", "tow_sizes.csv"), show_col_types = FALSE) %>%
  inner_join(read_csv(here("data", "derived", "tow_ts.csv"), show_col_types = FALSE), by = "OP_ID") %>%
  mutate(why = case_when(Ntargs < MIN_TARGETS ~ "fewer than 10 targets",
                         n_measured < MIN_MEASURED ~ "fewer than 5 alewife measured",
                         rel_se > MAX_REL_SE ~ "relative SE of mean length > 10%",
                         TRUE ~ ""),
         analysis = why == "")

write_csv(tows, here("data", "derived", "analysis_tows.csv"))
print(count(tows, analysis, why))
