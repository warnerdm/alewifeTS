"""Build the alewife tow review page: review/tow_review.html (local, read-only; records nothing).

Same layout and purpose as bloaterTS's review page (bloaterTS review/build_tow_review.py, user 2026-10-08): a person
decides include / exclude for each tow, with a fixed reason category, in config/tow_review.csv (created here with empty
decision columns if missing; never overwritten). Findings only: no flags, no thresholds.

Everything comes from pydt4 (no Echoview), for the tows with status ok in data/derived/tow_results.csv:
  - data/derived/tow_results.csv: the tow-region run with the bad-data regions (region Sv, Nv, bottom checks, timing);
  - data/derived/whole_column/: whole-column single targets (5 m to the bottom line, TS >= -60 dB, no ceiling) and their
    fish tracks (pydt4 track_tows.py; tracks/targets/<OP_ID>_tracked.csv, tracks/tracks.csv), BEFORE the regions:
    the target plot, targets used (tow region, TS <= -30 dB, outside the regions) and fish (tracks holding targets used);
  - config/bad_data_regions/regions.csv (python/make_regions.py): the regions and the targets they remove (red layer);
  - data/derived/echograms/: pydt4 Sv echograms (PNG, linked) and bottom lines (bottom/<OP_ID>_bottom.csv);
  - data/raw/trawl/: the catch (species counts, alewife lengths). No length-to-TS conversion on the page (user,
    2026-11-01: the available alewife TS equation, Warner, Rudstam and Klumb 2002, is for 70 kHz; these data are 120 kHz).
Images are linked by relative path: open the page from review/ on this computer. Plotly loads from cdnjs (internet).

    python review/build_tow_review.py        (alewifeTS root or anywhere; echopype env)
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "python"))
from project import Project  # noqa: E402

PYDT4 = Project().pydt4                    # pydt4 on the path, the project's instrument settings applied
from bad_data import load_regions, target_mask  # noqa: E402
from track_tows import transducer_depth  # noqa: E402
from flagged_tracks import alewife_sizes  # noqa: E402

D = os.path.join(ROOT, "data", "derived")
WC = os.path.join(D, "whole_column")
TOWS_CSV = os.path.join(D, "LM_tow_list_alewife_run.csv")
REGIONS_CSV = os.path.join(ROOT, "config", "bad_data_regions", "regions.csv")
REVIEW_CSV = os.path.join(ROOT, "config", "tow_review.csv")
CORRECTIONS_CSV = os.path.join(ROOT, "config", "tow_start_corrections.csv")
CORR = {}      # OP_ID -> (new start, reason): the tow start corrections (filled in build_records)
TRAWL = os.path.join(ROOT, "data", "raw", "trawl")
REASONS = ["bottom detection", "large targets", "small targets", "crowding", "target number", "tow timing/coverage",
           "wrong habitat/depth", "other"]   # wrong habitat/depth: user 2026-11-02 (bloater tows too deep for alewife)
TS_MAX_USED = -30.0
r = lambda x, n=2: None if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x) else round(float(x), n)
lin_mean = lambda x: float(10 * np.log10(np.mean(10 ** (np.asarray(x) / 10)))) if len(x) else None


def tow_record(op, t, res, tracks, regions, sizes, catch):
    a, b, per = sizes
    p = os.path.join(WC, "tracks", "targets", f"{op}_tracked.csv")
    tg = pd.read_csv(p) if os.path.exists(p) else pd.DataFrame(      # no whole-column targets (e.g. bottom in the region)
        columns=["ping_time", "time_s", "Target_range", "TS_comp", "track", "in_band"])
    tg["in_band"] = tg.in_band.astype(bool)
    zt = transducer_depth(res)                                               # the run's (file's own if not tabulated)
    # clocks: ping_time = tow-list clock, time_s = data-file clock; window = corrected tow start (tow-list clock)
    off = (pd.to_datetime(tg.ping_time) - pd.to_datetime(tg.time_s, unit="s")).median() if len(tg) else pd.Timedelta(0)
    t0 = pd.Timestamp(t.datetime) - off                                      # window start, file clock
    t1 = t0 + pd.Timedelta(minutes=float(t.TOW_TIME))
    mins = lambda ts: (ts - t0).total_seconds() / 60
    tg["t"] = (pd.to_datetime(tg.time_s, unit="s") - t0).dt.total_seconds() / 60
    tg["z"] = tg.Target_range + zt                                           # on-axis depth (echogram)
    lo, hi = float(t.FISHING_DEPTH), float(t.FISHING_DEPTH) + float(t.trawl_ht)
    regs = load_regions(op, REGIONS_CSV)
    masked = target_mask(pd.to_datetime(tg.time_s, unit="s").values.astype("datetime64[us]"), tg.z.values, regs) \
        if regs else np.zeros(len(tg), bool)
    tg["masked"] = masked
    used = tg[tg.in_band & (tg.TS_comp <= TS_MAX_USED) & ~tg.masked]
    # fish: tracks holding targets used, statistics over their targets used
    g = used[used.track >= 0].groupby("track").TS_comp
    fish = pd.DataFrame({"n": g.size(), "ts": g.apply(lin_mean), "tsmax": g.max()})
    trk_all = tracks[tracks.OP_ID == op].set_index("track")
    fish_med = float(fish.ts.median()) if len(fish) else np.nan
    strong = fish.sort_values("ts", ascending=False).head(6)
    tz = used.groupby("track").agg(z=("z", "mean"), t=("t", "mean"))
    strongest = [dict(ts=r(x.ts), tsmax=r(x.tsmax, 1), n=int(x.n), depth=r(tz.loc[k, "z"], 1), t=r(tz.loc[k, "t"], 1))
                 for k, x in strong.iterrows()]
    # masked layer: regions and the targets inside them (before masking)
    mk = None
    rg = regions[regions.OP_ID == op]
    if len(rg):
        m = tg[tg.masked]
        lab = [f"track {int(k)}" if k >= 0 else "untracked" for k in m.track]
        fl = []
        for k, gm in m[m.track >= 0].groupby("track"):
            tk = trk_all.loc[k] if k in trk_all.index else None
            fl.append(dict(fish=f"track {int(k)}", region="", masked=f"{len(gm)} of {int(tk.n_targets) if tk is not None else len(gm)}",
                           ts=r(tk.ts_mean if tk is not None else lin_mean(gm.TS_comp)),
                           above=r((tk.ts_mean if tk is not None else lin_mean(gm.TS_comp)) - fish_med, 1) if np.isfinite(fish_med) else None,
                           depth=r(gm.z.mean(), 1), t=r(gm.t.mean(), 1)))
        mk = dict(regions=[dict(name=x.region, t0=r(mins(pd.Timestamp(x.start_time)), 3), t1=r(mins(pd.Timestamp(x.end_time)), 3),
                                z0=r(x.depth_top_m, 2), z1=r(x.depth_bottom_m, 2),
                                n=int(target_mask(pd.to_datetime(tg.time_s, unit="s").values.astype("datetime64[us]"), tg.z.values,
                                                  [(np.datetime64(pd.Timestamp(x.start_time)), np.datetime64(pd.Timestamp(x.end_time)),
                                                    x.depth_top_m, x.depth_bottom_m)]).sum()),
                                reason=f"{x.masks}: {x.reason}") for x in rg.itertuples()],
                  t=[r(v, 3) for v in m.t], z=[r(v, 2) for v in m.z], ts=[r(v, 1) for v in m.TS_comp], lab=lab, fish=fl)
    # bottom line (pydt4 Maximum Sv pick, as the tow run), ping timing and data coverage
    bpath = os.path.join(D, "echograms", "bottom", f"{op}_bottom.csv")
    bline, bstats = dict(t=[], z=[]), {}
    if os.path.exists(bpath):
        bl = pd.read_csv(bpath)
        bt = pd.to_datetime(bl.time)
        win = (bt >= t0) & (bt <= t1)
        show = (bt >= t0 - pd.Timedelta(minutes=2)) & (bt <= t1 + pd.Timedelta(minutes=2))
        step = max(1, int(show.sum()) // 700)
        bline = dict(t=[r(mins(x), 3) for x in bt[show].iloc[::step]], z=[r(v, 2) for v in bl.depth_m[show].iloc[::step]])
        zb = bl.depth_m[win]
        dt = np.diff(bt[win].values).astype("timedelta64[ms]").astype(float) / 1000
        med = float(np.median(dt)) if len(dt) else np.nan
        bstats = dict(bottom_min_window=r(zb.min(), 2), bottom_median_window=r(zb.median(), 2),
                      bottom_clearance=r(zb.min() - hi, 2), bottom_max_jump=r(np.nanmax(np.abs(np.diff(zb.values))), 2) if len(zb) > 1 else None,
                      no_pick_pings=int(zb.isna().sum()), data_before_min=r(mins(bt.min()) * -1, 1), data_after_min=r(mins(bt.max()) - float(t.TOW_TIME), 1),
                      pings_in_window=int(win.sum()), ping_interval_s=r(med, 3),
                      irregular_intervals=int((np.abs(dt - med) > 0.25 * med).sum()) if len(dt) else None,
                      max_interval_s=r(dt.max(), 2) if len(dt) else None)
    # vessel speed over the tow window: straight-line distance between the first and last vessel positions of pings with
    # targets (pydt4 navigation: GPS fixes interpolated as Echoview) / the time between them. Trawling ~2-3 kn; transects ~8-10 kn
    speed = None
    if "vessel_north" in tg and tg.t.between(0, float(t.TOW_TIME)).sum() > 1:
        w = tg[tg.t.between(0, float(t.TOW_TIME))].sort_values("time_s")
        dt_s = w.time_s.iloc[-1] - w.time_s.iloc[0]
        if dt_s > 30:
            speed = r(np.hypot(w.vessel_north.iloc[-1] - w.vessel_north.iloc[0], w.vessel_east.iloc[-1] - w.vessel_east.iloc[0])
                      / dt_s * 3600 / 1852, 2)
    # catch
    L = per.get(op, np.array([]))
    c = catch[catch.OP_ID == op].groupby("SPECIES").N.sum().sort_values(ascending=False)
    imgs = sorted(glob.glob(os.path.join(D, "echograms", f"{op}_*.png")))
    n_used_tr = int((used.track >= 0).sum())
    return dict(
        OP_ID=int(op), lake="Michigan", year=int(t.YEAR), vessel=int(t.VESSEL), transect=str(t.TRANSECT),
        format="Simrad" if str(t.acoustic_format).lower() == "raw" else "dt4",
        fishing_depth=r(lo, 1), region_bottom=r(hi, 1), transducer_depth=r(zt, 2),
        **{k: bstats.get(k) for k in ("bottom_min_window", "bottom_median_window", "bottom_clearance", "bottom_max_jump", "no_pick_pings")},
        p_bottom_min=r(res.get("bottom_min_m"), 2), p_bad_picks=None if pd.isna(res.get("bottom_n_bad_picks")) else int(res.get("bottom_n_bad_picks")),
        p_frac_masked=r(res.get("bottom_frac_region_masked"), 4),
        ts_mean=r(lin_mean(used.TS_comp)), ts_median=r(used.TS_comp.median()) if len(used) else None,
        mean_minus_median=r(lin_mean(used.TS_comp) - used.TS_comp.median()) if len(used) else None,
        ts_max_region=r(tg[tg.in_band & ~tg.masked].TS_comp.max(), 1), fish_median=r(fish_med),
        strongest_fish_above_median=r(fish.ts.max() - fish_med, 1) if len(fish) else None,
        strongest=strongest, hist_all=[r(v, 1) for v in used.TS_comp], hist_tracked=[r(v, 1) for v in used.TS_comp[used.track >= 0]],
        fish_ts=[r(v, 2) for v in fish.ts], fish_n=[int(v) for v in fish.n],
        masked=mk, masked_targets=len(mk["ts"]) if mk else None,
        nv_pydt4=r(res.get("nv"), 4), nv_frac_pings=r(res.get("nv_frac_pings_gt_flag"), 3),
        targets_per_ping=r(res.get("st_targets_per_ping"), 2), frac_in_tracks=r(n_used_tr / len(used), 3) if len(used) else None,
        sv_mean=r(res.get("mean_sv_db"), 2), st_n_targets_run=None if pd.isna(res.get("st_n_targets")) else int(res.get("st_n_targets")),
        st_mean_ts_run=r(res.get("st_mean_ts_db"), 2),
        targets_used=int(len(used)), fish_tracks=int(len(fish)), fish_1=int((fish.n == 1).sum()), fish_2=int((fish.n == 2).sum()),
        fish_3_4=int(fish.n.between(3, 4).sum()), fish_5_9=int(fish.n.between(5, 9).sum()), fish_10plus=int((fish.n >= 10).sum()),
        logged_start=str(t.get("datetime_logged", t.datetime)), tow_minutes=r(t.TOW_TIME, 1),
        # time corrected = a row of config/tow_start_corrections.csv (tow_results' tow_start_correction also carries the
        # vessel-year data-clock offsets, e.g. Sturgeon 2005 +301 min, which are not corrections of the tow's time)
        start_correction=(f"{str(t.get('datetime_logged', ''))[:16]} -> {CORR[op][0][:16]} ({CORR[op][1]})" if op in CORR else ""),
        clock_offset="; ".join(x.strip() for x in str(t.get("tow_start_correction", "")).split(";") if "CLOCK_OFFSET" in x),
        window_start_file_clock=str(t0)[:23], match_level=str(res.get("match_level", "")),
        n_files=None if pd.isna(res.get("n_files_used")) else int(res.get("n_files_used")),
        **{k: bstats.get(k) for k in ("data_before_min", "data_after_min", "pings_in_window", "ping_interval_s", "irregular_intervals", "max_interval_s")},
        speed_kn=speed,
        catch_text=", ".join(f"{int(s)}: {int(n)}" for s, n in c.items()), alewife_n=int(len(L)),
        alewife_len=[int(v) for v in L], alewife_len_max=int(L.max()) if len(L) else None,
        alewife_len_median=r(np.median(L), 0) if len(L) else None,
        bline=bline, pts=dict(t=[r(v, 3) for v in tg.t], z=[r(v, 2) for v in tg.z], ts=[r(v, 1) for v in tg.TS_comp],
                              tr=[int(v >= 0) for v in tg.track]),
        window_min=r(float(t.TOW_TIME), 3),
        img_sv=os.path.relpath(imgs[0], HERE).replace("\\", "/") if imgs else "")


def build_records(tow_ids=None):
    res = pd.read_csv(os.path.join(D, "tow_results.csv")).set_index("OP_ID")
    raw = pd.read_csv(TOWS_CSV).set_index("OP_ID")
    sys.path.insert(0, PYDT4)
    from run_tow_batch import apply_tow_corrections
    tows = apply_tow_corrections(pd.read_csv(TOWS_CSV), os.path.join(ROOT, "config", "tow_start_corrections.csv")).set_index("OP_ID")
    tows["datetime_logged"] = raw.datetime
    c = pd.read_csv(CORRECTIONS_CSV)
    CORR.update({int(o): (str(n), str(w)) for o, n, w in zip(c.OP_ID, c.new_start, c.reason)})
    tracks = pd.read_csv(os.path.join(WC, "tracks", "tracks.csv"))
    regions = pd.read_csv(REGIONS_CSV)
    sizes = alewife_sizes(TRAWL, set(tows.index))
    catch = pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(TRAWL, "L_2_Y_*_Acoustic_tr_catch.csv"))]).rename(columns=str.upper)
    ok = [int(o) for o in res.index[res.status == "ok"]]
    missing = [o for o in ok if not os.path.exists(os.path.join(WC, "tracks", "targets", f"{o}_tracked.csv"))]
    if missing:
        print("no whole-column targets / tracks (shown without target plots):", missing)
    ids = [o for o in ok if tow_ids is None or o in set(tow_ids)]
    recs = []
    for op in ids:
        recs.append(tow_record(op, tows.loc[op], res.loc[op], tracks, regions, sizes, catch))
        print(op, "done", flush=True)
    recs.sort(key=lambda x: (x["year"], x["OP_ID"]))
    return recs


def write_page(recs, path):
    with open(os.path.join(HERE, "tow_review_template.html"), encoding="utf-8") as f:
        html = f.read()
    html = html.replace("/*__DATA__*/null", json.dumps(recs, separators=(",", ":")))
    html = html.replace("/*__REASONS__*/null", json.dumps(REASONS))
    html = html.replace("__BUILT__", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{os.path.relpath(path, ROOT)}: {len(recs)} tows, {os.path.getsize(path) / 1e6:.1f} MB")


def main():
    recs = build_records()
    write_page(recs, os.path.join(HERE, "tow_review.html"))
    if not os.path.exists(REVIEW_CSV):
        pd.DataFrame([dict(OP_ID=x["OP_ID"], lake=x["lake"], year=x["year"], vessel=x["vessel"], transect=x["transect"],
                           fishing_depth_m=x["fishing_depth"], decision="", reason="", note="", reviewer="", date="")
                      for x in recs]).to_csv(REVIEW_CSV, index=False)
        print("config/tow_review.csv created (decision: include/exclude; reason: " + "; ".join(REASONS) + ")")
    else:
        print("config/tow_review.csv exists: not changed")


if __name__ == "__main__":
    main()
