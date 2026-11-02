"""
make_regions.py - automatic bad-data regions for the alewife tows from fish tracks (user decision 2026-11-01).

Rule (user, 2026-11-01): a fish track with at least one target in the tow band and a mean TS above -35 dB (the upper
end of alewife TS; flagged_tracks.py rule abs35) gets a rectangle around all its detections, padded 2 s in time and
1 m in depth (as bloaterTS). Rectangles in bloaterTS's regions.csv format (times on the data FILE clock, depths =
echogram depth = target range + transducer depth), read by pydt4 bad_data.py (run_tow_batch --regions / run_simrad_tows
regions_csv=).

    python make_regions.py WHOLE_COLUMN_DIR OUT_CSV
"""
import os
import sys

import pandas as pd

PAD_S, PAD_M, TS_LIMIT_DB = 2.0, 1.0, -35.0


def main(wc, out_csv):
    fl = pd.read_csv(os.path.join(wc, "flags", "flagged_tracks.csv"))
    fl = fl[fl.abs35]
    res = pd.concat([pd.read_csv(os.path.join(wc, f)) for f in ("tow_results_column.csv", "tow_results_column_simrad.csv")])
    sys.path.insert(0, r"D:\pyprojects\pydt4")
    from track_tows import transducer_depth                       # the run's depth (file's own if not tabulated)
    res = res.drop_duplicates("OP_ID", keep="last").set_index("OP_ID")
    rows = []
    for op, g in fl.groupby("OP_ID"):
        tg = pd.read_csv(os.path.join(wc, "tracks", "targets", f"{op}_tracked.csv"))
        for k, r in enumerate(g.sort_values("time_s_start").itertuples(), 1):
            m = tg[tg.track == r.track]
            d = m.Target_range + transducer_depth(res.loc[op])
            t0 = pd.to_datetime(m.time_s.min() - PAD_S, unit="s")
            t1 = pd.to_datetime(m.time_s.max() + PAD_S, unit="s")
            rows.append(dict(OP_ID=op, region=f"bad data {k}", start_time=t0.strftime("%Y-%m-%d %H:%M:%S.%f")[:-2],
                             end_time=t1.strftime("%Y-%m-%d %H:%M:%S.%f")[:-2],
                             depth_top_m=round(d.min() - PAD_M, 3), depth_bottom_m=round(d.max() + PAD_M, 3),
                             masks=f"track {int(r.track)}", detections=len(m), ts_mean_db=round(r.ts_mean, 2),
                             reason=f"fish track mean TS {r.ts_mean:.1f} dB, above {TS_LIMIT_DB:g} dB (max alewife TS)",
                             source="Claude from pydt4 gap-0 tracks (track_tows.py); margins 2 s and 1 m; user rule 2026-11-01"))
    out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    out.to_csv(out_csv, index=False)
    print(f"{len(out)} regions in {out.OP_ID.nunique()} tows -> {out_csv}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
