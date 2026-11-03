# alewifeTS

Target strength (TS) of alewife in Lake Michigan, from acoustic single targets recorded at the same time, place and
depth as trawl tows in which alewife were >= 90% of the catch (and >= 5 fish). Tow-based, as bloaterTS
(`D:\pyprojects\bloaterTS`).

All acoustic processing is done with pydt4 (`D:\pyprojects\pydt4`, github.com/warnerdm/pydt4), with no Echoview.
The manuscript will be R Markdown in `manuscript/`. The step-by-step process, with the decisions behind each step, is
in `docs/PROCESS.md`.

## Steps

Run from the project root in the `echopype` conda env, in this order. Each script reads `config/project.yaml`, calls
pydt4 or `python/`, writes its outputs to their standard places, and adds a line to `data/derived/run_log.csv` (step,
time, pydt4 commit).

| Step | Needs | Reads | Writes |
|---|---|---|---|
| `R/create_mwt_location_list_for_python.R` | R, trawl database exports | EchoNet2Fish_LM trawl files | `data/raw/LM_tow_list_2005_2024.csv` |
| `scripts/01_make_run_list.py` | - | tow list | `data/derived/LM_tow_list_alewife_run.csv` (the run list, 211 tows) |
| `scripts/02_whole_column_targets.py` | acoustic archive | run list, start corrections | `data/derived/whole_column/` (targets for fish tracking) |
| `scripts/03_fish_tracks.py` | acoustic archive | step 02 | `data/derived/whole_column/tracks/` |
| `scripts/04_bad_data_regions.py` | - | step 03, trawl catch | `config/bad_data_regions/regions.csv`, `whole_column/flags/` |
| `scripts/05_tow_run.py` | acoustic archive | run list, start corrections, regions | `data/derived/tow_results.csv`, `tow_single_targets/` |
| `scripts/06_echograms.py` | acoustic archive | step 05 | `data/derived/echograms/` (PNG, bottom lines) |
| `scripts/07_review_page.py` | - | steps 02-06, trawl catch | `review/tow_review.html` |
| reviewer | a browser | `review/tow_review.html` | `config/tow_review.csv` (include / exclude, reason) |
| `scripts/08_tow_selection.py` | - | `config/tow_review.csv`, `config/set_aside.csv`, step 05 | `data/derived/tow_selection.csv` |
| `scripts/09_copy_tow_files.py` | acoustic archive | step 08, step 05 | `data/raw/acoustic/` (used tows' files) |
| `python/within_fish.py data/derived/within_fish` | - | step 08, tracks | within-fish TS figures and tables (exploratory) |
| `python/track_summary.py data/derived/track_summary` | - | step 08, tracks, step 05 | per-tow track figures, `tow_track_summary.csv` (exploratory) |
| analysis, figures, tables (to do) | - | `data/derived/`, `data/raw/trawl/` | `manuscript/` |

Words used here: the **run list** is the tow list after the exclusions; a **run** is one pass of pydt4 over the run
list. The **tow run** (step 05) gives the results used; the **whole-column run** (step 02) finds single targets over the
whole water column for fish tracking only. The **tow region** is the tow's time window from the fishing depth to the
fishing depth + trawl height.

Steps 02, 05 and 06 take `--op-ids` to rerun selected tows (their rows are replaced). Every step from 01 to 06 takes
`--derived DIR` to write to another folder, to check that the steps reproduce the committed outputs.

## Project layout

| Folder | What it holds |
|---|---|
| `config/` | Settings and decisions: `project.yaml` (paths, exclusions, run settings), `tow_start_corrections.csv` (corrected tow start times, each with its evidence), `match_decisions.csv` (accepted / rejected file matches), `bad_data_regions/` (step 04), `tow_review.csv` (the reviewer's decisions), `set_aside.csv` (vessel-years set aside) |
| `data/raw/` | Inputs, never edited: the tow list, trawl files (`trawl/`), copies of the used tows' acoustic files (`acoustic/`, git-ignored; `tow_files.csv` lists them with SHA-256) |
| `data/derived/` | Tables produced by the steps |
| `python/` | The project's own functions (flag rules, regions, tow selection, file copies) |
| `scripts/` | One short file per step, numbered in run order |
| `review/` | The tow review page builder and template; the page is rebuilt, not committed |
| `R/` | Tow list from the trawl data |
| `docs/` | `PROCESS.md` |
| `manuscript/` | The R Markdown manuscript (to come) |

## Setup

pydt4 and the `echopype` conda env (Python 3.12, echopype 0.11.1; see pydt4's notes). In Windows Git Bash, put the
env's DLL folders first on PATH (pydt4 CLAUDE.md), then for example:

```
python scripts/01_make_run_list.py
```

Edit `config/project.yaml` if pydt4 or the acoustic archive is somewhere else.

## Not yet self-contained

- With `--from-copies` (steps 02, 05, 06) the used tows run from the copies in `data/raw/acoustic/`, without the
  archive; checked 2026-11-02: identical results, targets, tracks and regions for all 129 used tows. Only the used tows
  are copied (user), so the excluded tows, the review page (step 07) and the exclusion evidence still need the archive.
- Calibration values (pydt4 `data/ecs_parameters_usgs_steelhead.csv`, `tow_echograms.SIMRAD_CAL`), transducer depths,
  clock offsets and whitelisted matches live in pydt4.
- Output tables hold absolute paths to the archive (`files_used`, `st_csv`).
- `R/create_mwt_location_list_for_python.R` reads the trawl files outside the project.
