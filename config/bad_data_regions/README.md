# Bad-data regions (alewife tows)

`regions.csv` is the record: one rectangle per row (OP_ID, region, start/end time on the data FILE clock, echogram
depth top/bottom = target range + transducer depth, what it masks, detections, track mean TS, reason, source), in
bloaterTS's format. pydt4 applies it (`bad_data.py`; `run_tow_batch --regions`, `tow_echograms.run_simrad_tows(regions_csv=)`):
samples inside are left out of region Sv / Nv, targets inside are dropped.

Made automatically, never drawn by hand (user, 2026-11-01): `python/make_regions.py` from pydt4 fish tracks.
- Fish tracks: pydt4 `track_tows.py` (Echoview's 4D alpha-beta tracker, validated against Echoview's gap-0 exports;
  maximum gap 0, minimum 2 targets, minimum 2 pings) on whole-column single targets (5 m to the bottom line, TS >= -60 dB,
  NO -30 dB ceiling) in `data/derived/whole_column/`.
- Rule (user, 2026-11-01): a track with a target in the tow band and a mean TS above -35 dB (the upper end of alewife TS)
  gets a rectangle around all its detections, padded 2 s and 1 m. Compared first (python/flagged_tracks.py,
  data/derived/whole_column/flags/): bloaterTS's 13 dB-above-the-tow-median rule also flagged large alewife in tows where
  weak uncaught targets set the median; a "largest alewife caught + 3 dB" rule flagged ordinary fish wherever the
  acoustic fish were stronger than the catch predicted (most tows of small alewife). That prediction used Warner, Rudstam
  and Klumb (2002), a 70 kHz TS-weight relation, on 120-129 kHz data (not adjusted; user 2026-11-01), so part of the
  difference may be frequency. The -35 dB rule does not depend on it.
- First set: 37 regions in 26 tows; all 161 targets of the flagged tracks masked; also 25 other targets in 7 tows
  (strong untracked echoes of the same fish, and 5 ordinary fish whole plus 1 fish partly: 78795 -35.6 dB, 87237 -40.8 dB
  outside the band, 106378 -38.4 and -46.5 dB, 124048 -50.4 dB; 87243 -45.8 dB 1 of 2 targets).

Rebuild after any change to the tracks: `python python/flagged_tracks.py ...`, then `python python/make_regions.py
data/derived/whole_column config/bad_data_regions/regions.csv`, then rerun the affected tows (tow-band run).
