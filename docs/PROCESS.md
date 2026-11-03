# alewifeTS process

What each step does and the decisions behind it, with who decided and when. The dated session notes are in pydt4's
`STATUS_log.md` (2026-11-01 b to 2026-11-03). Settled pydt4 conventions (clocks, depths, calibration, single-target
settings, noise removal, bottom line) are in pydt4's `CLAUDE.md`.

## 0. Tow list

`R/create_mwt_location_list_for_python.R` builds `data/raw/LM_tow_list_2005_2024.csv` from the Lake Michigan acoustic
trawl files: tows with alewife >= 90% of the catch and >= 5 fish caught (user; no further catch filter). 260 tows,
2004-2024 (despite the name): 210 dt4, 50 Simrad raw. Times are local EDT; depths below the surface.

## 1. Run list (`scripts/01_make_run_list.py`)

Excluded (user, 2026-11-01): FISHING_DEPTH < 5 m (31 tows; 5.0 kept); Steelhead 2004 (dual-beam; 13); Baird 2016 and
2017 (no calibration session on disk; 5). 211 tows remain (181 dt4, 30 raw).

## Calibration and instrument settings (`calibration/`)

The project's own copies of the settings, taken from pydt4's tables by `python/export_calibration.py` (2026-11-03) and
applied to pydt4 by each step (`python/project.py`, pydt4 `project_settings.apply`): `ecs_parameters.csv` (the 34 dt4
calibration table rows the run list uses, Michigan or all-lake rows, with their sources), `instrument_settings.csv` (45
vessel-years: transducer depth, Simrad file clock, dt4 clock offset, Simrad calibration; EK80 reports resolved to values,
a blank value = taken from each file) and `simrad_reports/` (the 8 EK80 calibration reports behind the Simrad values).
Added for alewifeTS (user, 2026-11-01): Sturgeon 2004 = the Tobermory values (the Port Washington session was weak and
~0.5 dB off); Baird 2012 file values, 2013 ER60 utility values (psi from each file), 2021 EK80 calibration XML (transducer
depth from the file, 3.0 m). Sturgeon 2005 (user, 2026-11-03): the old row (a 2018 ECS by Kristy, no recorded source) had angle offsets relative to the
header entered as absolute (about 0.8 deg off on each axis). Replaced by pydt4's session on the sphere files the user named
(2005/no2 20265498-20415109, 25 Aug 2005): TS -0.220, Sv 0.583, absolute offsets +0.755 minor / -0.866 major; beam widths
kept from the old row (the session's off-axis coverage is poor). The 19 Sturgeon 2005 tows rerun: Sv +0.093 dB; the 8 used
tows' mean TS -0.87 to +1.76 dB (median +0.2; 58088, 704 targets, +0.04); selection 25,125 targets, 14,343 fish.

## Tow matching and start times (in the tow runs)

pydt4 matches each tow to its acoustic files by time (byte-identical copies dropped, the raw_data copy kept). Corrected
start times are in `config/tow_start_corrections.csv`, each with its cause and evidence (GPS trawl signature, raw-file
annotations): Baird 2012 months, Baird 2013 after-midnight dates, 85040 +1 day (2026-11-01); 34 tows accepted from the
GPS shift review (user, 2026-11-02: 2010 Steelhead tow list ~1 h early, Baird 2022/2023 dates a day late, Sturgeon 2004,
after-midnight +1 day, and 9 with no named cause). Rejected or unsure: 58600, 78779 (unmatched). Accepted / rejected
matches: `config/match_decisions.csv`. Sturgeon 2005 dt4 files run 5 h 01 min ahead of the tow list (pydt4
`DT4_CLOCK_OFFSET_MIN`).

## 2-4. Automatic bad-data regions

As bloaterTS, never drawn by hand (user, 2026-11-01). Whole-column single targets (step 02: 5 m to the bottom line, no
-30 dB ceiling), gap-0 fish tracks (step 03, pydt4's tracker, validated against Echoview's track exports), and a
rectangle around each tow-band track with mean TS above -35 dB, padded 2 s and 1 m (step 04; user, 2026-11-01:
-35 dB is about the largest alewife TS; bloaterTS's 13 dB above the tow median flagged large alewife where weak
targets set the median). Nothing shallower than 5 m is tracked. 50 regions in 32 tows.

## 5. Tow run

Region mean Sv with background noise removed, bottom line (Maximum Sv), Nv, and single targets (Echoview split-beam
method 2, Great Lakes SOP, TS_comp -60 to -30 dB; minimum normalized pulse length 0.5 for Simrad power data), with the
bad-data regions excluded. 204 of 211 tows ok. The committed outputs of steps 01-05 are those of the full rerun by
the step scripts at pydt4 07d57ce (2026-11-02; `data/derived/run_log.csv`); it reproduced steps 01-04 exactly and gave
24 dt4 tows pydt4's later dt4 ping timing (0-1 edge ping, mean Sv <= 0.022 dB).

## 6-7. Echograms and review page

The review page shows, per tow: bottom detection, large targets and the regions, crowding (Nv), target number, timing
and coverage (vessel speed over the window, GPS check), and the catch (alewife lengths; no length-to-TS conversion: the
available alewife equation, Warner, Rudstam and Klumb 2002, is for 70 kHz; user, 2026-11-01).

## Review (user, 2026-11-02)

`config/tow_review.csv`: 145 include, 59 exclude of 204. Reasons: target number 35 (sparse / no targets), large
targets 7, bottom detection 5, tow timing/coverage 5, wrong habitat/depth 3 (bloater tows too deep for alewife),
crowding 2, other 2. The user's free-text reasons are kept in the notes.

## 8. Tow selection

`data/derived/tow_selection.csv`. T120P076 vessel-years (Sturgeon 2017, 2019, 2021; Steelhead 2023, 2024) are set aside
as in bloaterTS (user, 2026-11-02; `config/set_aside.csv`): 16 tows. Used: 129 tows (106 dt4, 23 raw), 25,214 targets,
14,382 fish (gap-0 tracks holding a target used + untracked targets). No count threshold here: it is an analysis
choice.

## 9. Copies of the acoustic files

Every ok tow's files (204 tows, 1,150 files, 25.5 GB) are in `data/raw/acoustic/`, listed with SHA-256 in
`tow_files.csv` (used tows first, user 2026-11-02; the other 75 ok tows added, user 2026-11-03, as bloaterTS). Steps 02,
05 and 06 run from them by default (pydt4 `--file-list`); `--from-archive` matches the tows to the archive instead.

Full check (2026-11-03): steps 01-06 rerun from the copies with `calibration/` give the same numbers as the archive run
for all 204 ok tows (tow results, whole-column results, single targets, 30,090 tracks, flags, 50 regions; 203 of 204
bottom lines byte-identical). Differences, none in a result: source text (the Simrad calibration source names the
project's report copy; `vessel_name_in_path` blank), the 7 non-ok tows are `not_in_file_list`, and 80756's echogram ends
a few minutes earlier (three passive files after the tow are not copies). The rerun was adopted, so the committed tables
hold project-relative paths; the review page and tow selection rebuilt from it are unchanged (page: 80756's echogram
only).

## 10. Analysis tows (`R/create-tow-sizes.R`, `R/create-tow-ts.R`, `R/create-analysis-tows.R`)

Per used tow: alewife mean length (mm), its SD / SE, number measured, mean weight (catch weight / catch N; missing for
76956, 76957, 76959, no catch weight) from the trawl files; mean TS (mean sigma_bs of the tow run's single targets, in dB)
and the number of targets. Tow rule as bloaterTS (user, 2026-11-03): >= 10 targets, >= 5 alewife measured, relative SE
of the mean length <= 10%. 121 of the 129 used tows kept; 8 fail the length SE (mixed small and large alewife: 58062,
89418, 93784, 95507, 106403, 112431, 119389, 119394). `data/derived/analysis_tows.csv` (column `analysis`).

## 11. TS-length model and TS floor (2026-11-03)

`R/ts-length-model.R`: tow mean TS on LogL = log10(mean length, cm), lmer by ML with a calibration-unit (vessel-year)
intercept, as bloaterTS. 121 tows, 35 units: TS = 11.42 LogL - 58.77 (slope 95% CI 9.1-13.7), marginal R2 0.47; slope 20
fits much worse (b20 = -66.7 dB, LRT p = 1e-11). The user expected a very different slope. Outlier tows (TS or length
clearly wrong) are to be removed even if the slope barely changes (user; after the floor check).
Outliers (user, 2026-11-03): fit on all 121, drop tows with |scaled residual| > 2.5 once, refit; Cook's distance
(4/n) reported as an influence check (`data/derived/ts_length_outliers.csv`). Dropped: 76952, 78785, 106432 (adult
alewife catch, targets near the -60 dB floor) and 107724 (small alewife, 13 targets near -38 dB); Cook's also flags
124159 (1.7 SD, kept). 117 tows: TS = 13.05 LogL - 60.19 (slope 95% CI 11.3-14.8), R2m 0.66, R2c 0.75, residual SD
1.75 dB, calibration-unit SD 1.05 dB; slope 20 still fits much worse (b20 = -66.7 dB, LRT p = 4e-12).
TS floor (`scripts/10_ts_floor_run.py`, `R/ts-floor-models.R`): the 129 used tows rerun with detection down to -77 dB;
the -60 dB subset equals step 05 in all 121 analysis tows (same targets, mean TS within 1e-14 dB). Slope at floors -60 / -63
/ -66 / -70 / -77 dB: 11.4 / 10.3 / 9.3 / 7.5 / 4.7 (R2m 0.47 to 0.06). A lower floor flattens the line further: the weak
targets it adds pull the large-fish tows down more than the small-fish tows, so truncation of small alewife at -60 dB does
not explain the low slope.

## 12. Weak targets in adult-alewife tows (exploratory, 2026-11-03)

Every model tow has a group of weak targets (mode about -63 to -67 dB at the -77 dB detection) in the tow region; its
upper tail passes the -60 dB floor. In adult tows (alewife expected near -45 to -38 dB) it pulls the mean TS down: adults
sit 4-5 dB below Warner, Rudstam and Klumb (2002) on length (TS = 20.53 log10 L - 64.25, 70 kHz). Examples:
`python/weak_targets_examples.py`. Not specific to vessel, system or region; weak targets per ping are as high or higher in
small-alewife tows. bloaterTS escaped it because its adult tows were deep (>= 45 m: 0.003 weak targets per ping vs 0.13
in the alewife tows). A higher floor for adult tows rejected (user: statistically wrong; the mean keeps rising with the
floor up to -50 dB, no plateau). Tracked targets only (`python/tracked_ts.py`, `R/tracked-ts-model.R`): weak targets
track nearly as often as alewife-size ones (-60 to -55 dB: 60% in tracks; >= -50 dB: 73%), so the slope barely moves
(13.0 all, 13.2 tracked, 13.6 per fish) and adults stay about 4 dB below Warner.

## 13. Brooking and Rudstam (2009) and a mixture fit (exploratory, 2026-11-03)

Brooking and Rudstam (2009, TAFS 138:471-486; user's copy D:/journal_articles): ex situ (net-cage, 70 kHz) alewife mean
TS = 13.1 log10 L - 58.2 (the same slope as our 13.05), mode = 19.1 log10 L - 62.2; alewife TS distributions span ~25 dB,
negatively skewed; Warner et al. (2002) assumed unimodal normal distributions, which leaves out the low tail. Their field
surveys also had excess -61 to -50 dB targets. Their PDF of TS - TS_mode reproduces their Figure 5 only with a plus before
the skew term (printed minus; k = 0.57, the curve-2 skewness constant); negative values above +3.3 dB set to 0.
Variant B (`python/brooking_fit.py`: curve fitted to targets >= -50 dB) fails here: the -50 to -40 dB range holds a flat
spread of non-alewife targets. Mixture (`python/mixture_fit.py`: Brooking shape for alewife + skew-normal weak group,
-77 to -30 dB, ML): fitted alewife modes follow Brooking's mode equation. 117 tows: 11 fits put the alewife component in
the weak group (mostly small-fish tows, where the groups overlap); 66 tows with >= 20 alewife targets, a sound weak fit and
mode > -55 dB: mode = 18.6 LogL - 60.7 (slope 95% CI 16.5-20.7, R2m 0.83; lmer, calibration-unit intercept). Removing
fits by their mode is a cut on the response, so that subset is only indicative. The mean of the alewife component is the
mode shifted by a constant set by Brooking's shape.

## Exploratory: tracks and within-fish TS (2026-11-02)

As bloaterTS's fish-track experiment (`echoview/experiments/fish_tracks_all_gap0/`), from pydt4's gap-0 tracks of the
targets used, 129 used tows.
- `python/within_fish.py` -> `data/derived/within_fish/`. Deviation = TS_comp minus the track median (dB), tracks of >= 5
  targets used, median target dropped in odd tracks (as bloaterTS). Tows with >= 5 such fish (bloaterTS 20); one group,
  since no alewife tow is deep (user); dip test only in tows with >= 20 fish. 34 tows, 535 fish, 3,078 deviations:
  unimodality not rejected in any of the 9 tested tows (p >= 0.95); pooled SD 3.2 dB (robust 1.45 dB; heavy tails),
  flat with off-axis angle. User: alewife can have a wider within-fish TS distribution ex situ.
- `python/track_summary.py` -> `data/derived/track_summary/`: per tow, targets used per detection / per fish / within
  fish (tracks >= 4 targets, deviations from the track mean scaled by sqrt(n/(n-1)) for track length; user), and
  `tow_track_summary.csv`. Median share of targets in tracks 0.64, 2 targets per fish; per-fish minus per-detection mean
  TS +0.28 dB (large only in tows with few fish).
- 58614 and 85064 show two per-fish TS modes (about -58 and -50 dB) while the catch is one group of small
  alewife (58614: 42-71 mm); the caught fish are near the upper mode by Warner et al. (2002), a 70 kHz relation. Settled (user, 2026-11-03): "they are what they are"; both tows stay as they are, no change.
