"""Tow mean TS from tracked targets only (exploratory, user 2026-11-03): weak echoes that do not form gap-0 fish tracks
drop out, the same way in every tow. For each analysis tow, the tow-region targets of step 05 are matched to the gap-0
tracks of step 03 (tow_selection.targets_with_track; tracks >= 2 targets); targets in no track are left out.

  mean_ts_all      mean sigma_bs of all the tow's targets, in dB (= tow_ts.csv)
  mean_ts_tracked  mean sigma_bs of the tracked targets (each detection counts once)
  mean_ts_fish     each track's mean sigma_bs, then the mean over tracks (each fish counts once)
  tracked_<bin>    share of the targets in each TS bin that are in a track

    python python/tracked_ts.py
Writes data/derived/tracked_ts/tow_tracked_ts.csv (R/tracked-ts-model.R fits the TS-length model to it).
"""
import os

import numpy as np
import pandas as pd

from project import Project
from tow_selection import targets_with_track

BINS = [(-60, -55), (-55, -50), (-50, -30)]


def mean_db(ts):
    return float(10 * np.log10(np.mean(10 ** (np.asarray(ts) / 10)))) if len(ts) else np.nan


def main():
    p = Project(apply_settings=False)
    out = os.path.join(p.derived, "tracked_ts")
    os.makedirs(out, exist_ok=True)
    a = pd.read_csv(os.path.join(p.derived, "analysis_tows.csv"))
    rows = []
    for op in a.OP_ID[a.analysis]:
        m = targets_with_track(int(op))
        tracked = m.track.notna() & (m.track >= 0)
        t = m[tracked]
        r = dict(OP_ID=int(op), n_targets=len(m), n_tracked=int(tracked.sum()), n_not_found=int(m.track.isna().sum()),
                 n_fish=t.track.nunique(), mean_ts_all=mean_db(m.TS_comp), mean_ts_tracked=mean_db(t.TS_comp),
                 mean_ts_fish=mean_db(t.groupby("track").TS_comp.apply(mean_db)) if len(t) else np.nan)
        for lo, hi in BINS:
            b = (m.TS_comp >= lo) & (m.TS_comp < hi)
            r[f"tracked_{-lo}_{-hi}"] = tracked[b].mean() if b.any() else np.nan
        rows.append(r)
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(out, "tow_tracked_ts.csv"), index=False)
    print(f"{len(d)} tows; targets {d.n_targets.sum()}, tracked {d.n_tracked.sum()} "
          f"({d.n_tracked.sum() / d.n_targets.sum():.2f}), not found in the tracking run {d.n_not_found.sum()}")
    print("share tracked by TS bin (median over tows):",
          {c: round(d[c].median(), 2) for c in d.columns if c.startswith("tracked_")})


if __name__ == "__main__":
    main()
