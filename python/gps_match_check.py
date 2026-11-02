"""
gps_match_check.py - does each matched tow's data show the logged trawl? (user, 2026-11-02: worry about match accuracy)

For every tow with status ok in data/derived/tow_results.csv: the vessel track from the matched files' GPS (pydt4
tow_fish_tracks: dt4 fixes timed as Echoview, Simrad GGA else RMC + GLL with the 15 kn rule), over the tow window
(corrected start .. + TOW_TIME, on the data-file clock):
  - start_km / end_km: distance from the vessel at the window start / end to the tow list's BEG / END coordinate;
  - closest_start_km and its time offset from the window start (min): where the track passes nearest the BEG coordinate
    (within the window +- 30 min of data), i.e. how far the window may be shifted;
  - speed_kn: straight-line start-to-end distance / tow time; frac_trawl: share of the window's minutes at 1.5-3.5 kn
    (gps_trawl_check's trawl speed); n_fixes in the window.
Changes no results; writes data/derived/gps_match_check.csv, worst first.

    python gps_match_check.py
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

PYDT4 = r"D:\pyprojects\pydt4"
sys.path.insert(0, PYDT4)
import grid  # noqa: E402
import tow_matching as tm  # noqa: E402
from run_tow_batch import apply_tow_corrections  # noqa: E402
from tow_fish_tracks import file_pings_dt4, file_pings_simrad  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "derived")
TRAWL_KN = (1.5, 3.5)


def km(la1, lo1, la2, lo2):
    p = np.radians
    a = np.sin(p(la2 - la1) / 2) ** 2 + np.cos(p(la1)) * np.cos(p(la2)) * np.sin(p(lo2 - lo1) / 2) ** 2
    return 2 * 6371.0088 * np.arcsin(np.sqrt(a))


def check(op, t, res):
    paths = str(res.files_used).split(";")
    simrad = paths[0].lower().endswith(".raw")
    fs = file_pings_simrad(paths) if simrad else file_pings_dt4(paths, int(res.channel_used))
    ft = np.concatenate([f.fix_time_s for f in fs]); la = np.concatenate([f.fix_lat for f in fs]); lo = np.concatenate([f.fix_lon for f in fs])
    ok = np.isfinite(ft) & np.isfinite(la) & np.isfinite(lo) & (np.abs(la) <= 90) & (np.abs(lo) <= 180) & (la != 0)
    ft, la, lo = ft[ok], la[ok], lo[ok]
    o = np.argsort(ft, kind="stable"); ft, la, lo = ft[o], la[o], lo[o]
    if simrad and len(ft):
        g = grid.good_fixes(ft, la, lo, 15.0); ft, la, lo = ft[g], la[g], lo[g]
    off_h = tm.raw_to_tow_hours(int(t.VESSEL), int(t.YEAR)) if simrad else 0.0      # tow clock = file clock + off_h
    t0 = (pd.Timestamp(t.datetime) - pd.Timedelta(hours=off_h)).value / 1e9
    t1 = t0 + float(t.TOW_TIME) * 60
    out = dict(OP_ID=op, format="Simrad" if simrad else "dt4", year=int(t.YEAR), vessel=int(t.VESSEL), transect=t.TRANSECT,
               tow_min=float(t.TOW_TIME), n_fixes=int(((ft >= t0) & (ft <= t1)).sum()))
    if len(ft) < 2 or ft[-1] < t0 or ft[0] > t1:
        out["problem"] = "no GPS over the window"
        return out
    pos = lambda tt: (np.interp(tt, ft, la), np.interp(tt, ft, lo))
    (la0, lo0), (la1, lo1) = pos(t0), pos(t1)
    out.update(start_km=km(la0, lo0, t.BEG_LATITUDE_DD, t.BEG_LONGITUDE_DD),
               end_km=km(la1, lo1, t.END_LATITUDE_DD, t.END_LONGITUDE_DD) if pd.notna(t.END_LATITUDE_DD) else np.nan,
               speed_kn=km(la0, lo0, la1, lo1) * 1000 / (t1 - t0) * 3600 / 1852)
    m = np.arange(t0, t1 + 1, 60.0)
    mla, mlo = pos(m)
    sp = km(mla[:-1], mlo[:-1], mla[1:], mlo[1:]) * 1000 / 60 * 3600 / 1852
    out["frac_trawl"] = float(np.mean((sp >= TRAWL_KN[0]) & (sp <= TRAWL_KN[1]))) if len(sp) else np.nan
    s = np.arange(max(t0 - 1800, ft[0]), min(t1 + 1800, ft[-1]), 5.0)
    if len(s):
        sla, slo = pos(s)
        dk = km(sla, slo, t.BEG_LATITUDE_DD, t.BEG_LONGITUDE_DD)
        j = int(np.argmin(dk))
        out.update(closest_start_km=float(dk[j]), closest_start_shift_min=round((s[j] - t0) / 60, 1))
    out["data_span_min"] = round((ft[-1] - ft[0]) / 60, 1)
    return out


def main(argv=None):
    """Default: the alewife run. Other projects: --results R.csv --tows LIST.csv --corrections C.csv|none|default
    --coords LIST_WITH_COORDS.csv --out OUT.csv [--lake-filter Michigan] (e.g. bloaterTS: pydt4 tow_results.csv,
    LM_tow_list_for_python.csv, default corrections, LM_tow_list_2005_2024.csv for the coordinates)."""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(D, "tow_results.csv"))
    ap.add_argument("--tows", default=os.path.join(D, "LM_tow_list_alewife_run.csv"))
    ap.add_argument("--corrections", default=os.path.join(ROOT, "config", "tow_start_corrections.csv"))
    ap.add_argument("--coords", default=None)
    ap.add_argument("--out", default=os.path.join(D, "gps_match_check.csv"))
    ap.add_argument("--lake-filter", default=None, help="keep tows whose files_used path contains this text")
    a = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    res = pd.read_csv(a.results)
    if a.lake_filter:
        res = res[res.files_used.astype(str).str.contains(a.lake_filter)]
    res = res.drop_duplicates("OP_ID", keep="last").set_index("OP_ID")
    corr = None if a.corrections == "default" else ("" if a.corrections == "none" else a.corrections)
    tows = apply_tow_corrections(pd.read_csv(a.tows), corr)
    if a.coords:
        c = pd.read_csv(a.coords)[["OP_ID", "YEAR", "BEG_LATITUDE_DD", "BEG_LONGITUDE_DD", "END_LATITUDE_DD", "END_LONGITUDE_DD"]]
        tows = tows.drop(columns=[x for x in c.columns if x != "OP_ID" and x in tows.columns]).merge(c, on="OP_ID", how="left")
    tows = tows.set_index("OP_ID")
    rows = []
    ids = [int(o) for o in res.index[res.status == "ok"] if int(o) in tows.index]
    for i, op in enumerate(ids, 1):
        try:
            rows.append(check(op, tows.loc[op], res.loc[op]))
        except Exception as e:
            rows.append(dict(OP_ID=op, problem=f"{type(e).__name__}: {e}"))
        r = rows[-1]
        print(f"[{i}/{len(ids)}] {op}: start {r.get('start_km', np.nan):.2f} km, end {r.get('end_km', np.nan):.2f} km, "
              f"{r.get('speed_kn', np.nan):.1f} kn, trawl {r.get('frac_trawl', np.nan):.2f} {r.get('problem', '')}", flush=True)
    d = pd.DataFrame(rows)
    d["worst_km"] = d[["start_km", "end_km"]].max(axis=1)
    d = d.sort_values(["worst_km"], ascending=False, na_position="first")
    d = d.merge(res[["match_level"]].reset_index(), on="OP_ID", how="left")
    d.round(3).to_csv(a.out, index=False)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
