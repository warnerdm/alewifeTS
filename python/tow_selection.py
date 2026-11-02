"""Tow selection from the reviewer's decisions (config/tow_review.csv) -> data/derived/tow_selection.csv,
one row per reviewed tow: OP_ID, lake, year, vessel, transect, fishing_depth_m, acoustic_format, decision, reason,
targets_used, fish, status (used / excluded / set aside: config/set_aside.csv, if present), why. As bloaterTS review/tow_selection.py.

No count threshold is applied here: the number of targets and of fish are columns, to filter when the data are set
up for the models, where the threshold is an analysis choice.
targets_used = the tow's single targets (data/derived/tow_single_targets, TS_comp -60 to -30 dB, tow band, bad-data
regions removed). fish = gap-0 fish tracks holding a target used + targets used that belong to no track (each counted
as one fish; an upper count). A target used is matched to the whole-column tracking run
(data/derived/whole_column/tracks/targets/<OP_ID>_tracked.csv) by file, ping and range.

    python python/tow_selection.py      (alewifeTS root; echopype env)
"""
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = os.path.join(ROOT, "data", "derived", "tow_single_targets")
TRACKED = os.path.join(ROOT, "data", "derived", "whole_column", "tracks", "targets")
RESULTS = os.path.join(ROOT, "data", "derived", "tow_results.csv")
TOW_LIST = os.path.join(ROOT, "data", "derived", "LM_tow_list_alewife_run.csv")
KEY = ["file", "ping_index_in_file", "r"]


def fish_count(op_id):
    """(targets used, fish, targets used not found in the tracking run) for one tow; None if it has no targets file."""
    f = os.path.join(TARGETS, f"{op_id}_single_targets.csv")
    if not os.path.exists(f):
        return None
    u = pd.read_csv(f, usecols=["file", "ping_index_in_file", "Target_range"])
    if u.empty:
        return 0, 0, 0
    t = os.path.join(TRACKED, f"{op_id}_tracked.csv")
    if not os.path.exists(t):
        return len(u), len(u), len(u)
    tr = pd.read_csv(t, usecols=["file", "ping_index_in_file", "Target_range", "track"])
    for d in (u, tr):
        d["file"] = d.file.map(lambda p: p.replace("\\", "/").rsplit("/", 1)[-1])   # the runs write / and \ differently
        d["r"] = d.Target_range.round(3)
    m = u.merge(tr[KEY + ["track"]].drop_duplicates(KEY), on=KEY, how="left")
    tracked = m.track.notna() & (m.track >= 0)
    return len(u), m.loc[tracked, "track"].nunique() + int((~tracked).sum()), int(m.track.isna().sum())


def main():
    rv = pd.read_csv(os.path.join(ROOT, "config", "tow_review.csv"), encoding="utf-8-sig", dtype=str,
                     keep_default_na=False)
    rv["OP_ID"] = rv.OP_ID.astype(int)
    rv["decision"] = rv.decision.str.strip().str.lower()
    bad = rv[~rv.decision.isin(["include", "exclude"])]
    if len(bad):
        raise ValueError(f"decision must be include or exclude: {bad[['OP_ID', 'decision']].to_dict('records')}")
    if rv.OP_ID.duplicated().any():
        raise ValueError(f"duplicate OP_IDs in tow_review.csv: {sorted(rv.OP_ID[rv.OP_ID.duplicated()])}")
    res = pd.read_csv(RESULTS, usecols=["OP_ID", "status"]).drop_duplicates("OP_ID", keep="last")
    d = rv.merge(res.rename(columns={"status": "run_status"}), on="OP_ID", how="left")
    d = d.merge(pd.read_csv(TOW_LIST, usecols=["OP_ID", "acoustic_format"]), on="OP_ID", how="left")
    counts = {op: fish_count(op) for op in d.OP_ID}
    d["targets_used"] = d.OP_ID.map(lambda o: counts[o][0] if counts[o] else pd.NA)
    d["fish"] = d.OP_ID.map(lambda o: counts[o][1] if counts[o] else pd.NA)
    unmatched = sum(c[2] for c in counts.values() if c)
    d["status"] = d.decision.map({"include": "used", "exclude": "excluded"})
    d["why"] = d.apply(lambda r: "" if r.decision == "include" else f"review: {r.decision} ({r.reason})", axis=1)
    # vessel-years set aside for a documented system issue (config/set_aside.csv, as bloaterTS; optional): the review
    # decisions are left as they are
    sa_csv = os.path.join(ROOT, "config", "set_aside.csv")
    sa = pd.read_csv(sa_csv, dtype=str) if os.path.exists(sa_csv) else pd.DataFrame(columns=["vessel", "year", "format", "reason"])
    for r in sa.itertuples():
        hit = (d.vessel == r.vessel) & (d.year == r.year) & (d.acoustic_format == r.format) & (d.status == "used")
        d.loc[hit, "status"] = "set aside"
        d.loc[hit, "why"] = f"set aside: {r.reason}"
    # a tow marked include must have a tow run row that is ok and a targets file
    odd = d[(d.decision == "include") &((d.run_status != "ok") | d.targets_used.isna())]
    if len(odd):
        raise ValueError(f"included tows without an ok tow run / targets: {odd.OP_ID.tolist()}")
    cols = ["OP_ID", "lake", "year", "vessel", "transect", "fishing_depth_m", "acoustic_format", "decision", "reason",
            "targets_used", "fish", "status", "why"]
    out = os.path.join(ROOT, "data", "derived", "tow_selection.csv")
    d[cols].to_csv(out, index=False)
    print(d.status.value_counts().to_string())
    u = d[d.status == "used"]
    print(f"used: {len(u)} tows ({u.acoustic_format.value_counts().to_dict()}), "
          f"{int(u.targets_used.sum())} targets, {int(u.fish.sum())} fish")
    print(f"targets used not found in the tracking run (counted as one fish each): {unmatched}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
