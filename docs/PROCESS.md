# alewifeTS process

What each step does and the decisions behind it, with who decided and when. The dated session notes are in pydt4's
`STATUS_log.md` (2026-11-01 b to 2026-11-02 m). Settled pydt4 conventions (clocks, depths, calibration, single-target
settings, noise removal, bottom line) are in pydt4's `CLAUDE.md`.

## 0. Tow list

`R/create_mwt_location_list_for_python.R` builds `data/raw/LM_tow_list_2005_2024.csv` from the Lake Michigan acoustic
trawl files: tows with alewife >= 90% of the catch and >= 5 fish caught (user; no further catch filter). 260 tows,
2004-2024 (despite the name): 210 dt4, 50 Simrad raw. Times are local EDT; depths below the surface.

## 1. Run list (`scripts/01_make_run_list.py`)

Excluded (user, 2026-11-01): FISHING_DEPTH < 5 m (31 tows; 5.0 kept); Steelhead 2004 (dual-beam; 13); Baird 2016 and
2017 (no calibration session on disk; 5). 211 tows remain (181 dt4, 30 raw).

## Calibration (in pydt4)

Each vessel-year uses the calibration table row in pydt4 (dt4) or `tow_echograms.SIMRAD_CAL` (Simrad). Added for
alewifeTS (user, 2026-11-01): Sturgeon 2004 = the Tobermory values (the Port Washington session was weak and ~0.5 dB
off); Baird 2012 file values, 2013 ER60 utility values, 2021 EK80 calibration XML. Open: the Sturgeon 2005 row has no
recorded source (16 tows use it).

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

The 129 used tows' files (672, 16.2 GB) are in `data/raw/acoustic/` (user, 2026-11-02: used tows only).
