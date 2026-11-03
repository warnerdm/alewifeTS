# alewifeTS

Target strength (TS) of alewife in Lake Michigan, from acoustic single targets recorded at the same time, place and
depth as trawl tows in which alewife were >= 90% of the catch (and >= 5 fish). Tow-based, as bloaterTS
(`D:\pyprojects\bloaterTS`).

All acoustic processing is done with pydt4 (`D:\pyprojects\pydt4`, github.com/warnerdm/pydt4), with no Echoview.
The manuscript will be R Markdown in `manuscript/`. The step-by-step process, with the decisions behind each step, is
in `docs/PROCESS.md`.

## Steps

Run from the project root in the conda env of `environment.yml`, in this order. Each script reads
`config/project.yaml`, applies the project's calibration and instrument settings to pydt4 (`python/project.py`), calls
pydt4 or `python/`, writes its outputs to their standard places, and adds a line to `data/derived/run_log.csv` (step,
time, pydt4 commit).

| Step | Needs | Reads | Writes |
|---|---|---|---|
| `R/create_mwt_location_list_for_python.R` | R | `data/raw/trawl/` | `data/raw/LM_tow_list_2005_2024.csv` |
| `scripts/01_make_run_list.py` | - | tow list | `data/derived/LM_tow_list_alewife_run.csv` (the run list, 211 tows) |
| `scripts/02_whole_column_targets.py` | copies | run list, start corrections, `calibration/` | `data/derived/whole_column/` (targets for fish tracking) |
| `scripts/03_fish_tracks.py` | copies | step 02 | `data/derived/whole_column/tracks/` |
| `scripts/04_bad_data_regions.py` | - | step 03, trawl catch | `config/bad_data_regions/regions.csv`, `whole_column/flags/` |
| `scripts/05_tow_run.py` | copies | run list, start corrections, regions, `calibration/` | `data/derived/tow_results.csv`, `tow_single_targets/` |
| `scripts/06_echograms.py` | copies | step 05 | `data/derived/echograms/` (PNG, bottom lines) |
| `scripts/07_review_page.py` | - | steps 02-06, trawl catch | `review/tow_review.html` |
| reviewer | a browser | `review/tow_review.html` | `config/tow_review.csv` (include / exclude, reason) |
| `scripts/08_tow_selection.py` | - | `config/tow_review.csv`, `config/set_aside.csv`, step 05 | `data/derived/tow_selection.csv` |
| `R/create-tow-sizes.R` | R | step 08, `data/raw/trawl/` | `data/derived/tow_sizes.csv`, `tow_lengths.csv` (alewife length and weight per used tow) |
| `R/create-tow-ts.R` | R | step 08, step 05 | `data/derived/tow_ts.csv`, `tow_targets.csv` (mean TS per used tow) |
| `R/create-analysis-tows.R` | R | the two above | `data/derived/analysis_tows.csv` (the tow rule; 121 tows in the analysis) |
| `R/ts-length-model.R` | R | `analysis_tows.csv` | `data/derived/ts_length_model.txt` (TS-length lmer, as bloaterTS) |
| `scripts/10_ts_floor_run.py` | copies | step 08, as step 05 | `data/derived/ts_floor/` (single targets down to -77 dB) |
| `R/ts-floor-models.R` | R | step 10, `analysis_tows.csv` | `data/derived/ts_floor/ts_floor_models.csv` (the model at floors -60 to -77 dB) |
| `python/within_fish.py data/derived/within_fish` | - | step 08, tracks | within-fish TS figures and tables (exploratory) |
| `python/track_summary.py data/derived/track_summary` | - | step 08, tracks, step 05 | per-tow track figures, `tow_track_summary.csv` (exploratory) |
| analysis, figures, tables (to do) | - | `data/derived/`, `data/raw/trawl/` | `manuscript/` |

"copies" = the project's copies of every ok tow's acoustic files (`data/raw/acoustic/`, listed with SHA-256 in
`tow_files.csv`). Building the project the first time needed the acoustic archive: steps 02, 05 and 06 with
`--from-archive` match the tows to the archive's files, `scripts/09_copy_tow_files.py` copies the ok tows' files, and
`python/export_calibration.py` took the calibration and instrument settings from pydt4 (2026-11-03). From then on
nothing outside the project is read except the pydt4 code.

Words used here: the **run list** is the tow list after the exclusions; a **run** is one pass of pydt4 over the run
list. The **tow run** (step 05) gives the results used; the **whole-column run** (step 02) finds single targets over the
whole water column for fish tracking only. The **tow region** is the tow's time window from the fishing depth to the
fishing depth + trawl height.

Steps 02, 05 and 06 take `--op-ids` to rerun selected tows (their rows are replaced). Every step from 01 to 06 takes
`--derived DIR` to write to another folder, to check that the steps reproduce the committed outputs. Output tables
hold paths relative to the project root.

## Project layout

| Folder | What it holds |
|---|---|
| `config/` | Settings and decisions: `project.yaml` (paths, pydt4 commit, exclusions, run settings), `tow_start_corrections.csv` (corrected tow start times, each with its evidence), `match_decisions.csv` (accepted / rejected file matches), `bad_data_regions/` (step 04), `tow_review.csv` (the reviewer's decisions), `set_aside.csv` (vessel-years set aside) |
| `calibration/` | `ecs_parameters.csv` (dt4 calibrations, rows of pydt4's ECS table, with their sources), `instrument_settings.csv` (per vessel-year: transducer depth, Simrad file clock, dt4 clock offset, Simrad calibration), `simrad_reports/` (the EK80 calibration reports behind the Simrad values) |
| `data/raw/` | Inputs, never edited: the tow list, trawl files (`trawl/`), copies of the ok tows' acoustic files (`acoustic/`, git-ignored, archived separately; `tow_files.csv` lists them with SHA-256) |
| `data/derived/` | Tables produced by the steps |
| `python/` | The project's own functions (setup, flag rules, regions, tow selection, file copies, analyses) |
| `scripts/` | One short file per step, numbered in run order |
| `review/` | The tow review page builder and template; the page is rebuilt, not committed |
| `R/` | Tow list from the trawl data |
| `docs/` | `PROCESS.md` |
| `manuscript/` | The R Markdown manuscript (to come) |

## Setup

```
conda env create -f environment.yml
conda activate alewifets
python scripts/01_make_run_list.py
```

pydt4 is not installed as a package: clone it (github.com/warnerdm/pydt4), check out the commit in
`config/project.yaml` (`pydt4_commit`; the steps warn when it differs) and set `pydt4:` to its folder. On Windows, when
running python.exe directly rather than from an activated prompt, put the env's DLL folders first on PATH (pydt4
CLAUDE.md).

## Still outside the project

- The pydt4 code (a separate repository, pinned by commit).
- Copies of the acoustic files are git-ignored (25 GB): archive `data/raw/acoustic/` with the project.
- Tow matching and the GPS checks behind the start corrections (`--from-archive`, `python/gps_match_check.py`,
  pydt4 `gps_trawl_check` / `map_review`) need the acoustic archive; their outcomes are recorded in `config/`.
