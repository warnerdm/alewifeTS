"""
flagged_tracks.py - which fish tracks would the bad-data rule flag in the alewife tows, at several thresholds?

Input: pydt4 track_tows.py output (tracks.csv: one row per fish track, mean TS = linear mean of its targets;
n_in_band = targets in the tow band) from whole-column single targets without the -30 dB ceiling, and the
acoustic trawl catch files (data/raw/trawl/L_2_Y_*_Acoustic_tr_lf.csv / _tr_catch.csv; alewife = species 106).
Only tracks with at least one target in the tow band count (as bloaterTS: tracks holding a target used).

Rules compared (a track is flagged when its mean TS is):
  relative: >= the tow's median track mean TS + 10, 13 (bloaterTS) or 16 dB
  absolute: > -40, -35 or -30 dB
  big3: > the TS of the tow's largest alewife caught + 3 dB; comb: abs35 or big3
Expected alewife TS: Warner, Rudstam and Klumb (2002) log10(W) = 6.79 + 0.13 TS (W in g, fitted 0.2-25.4 g), with
W from a length-weight relation fitted to the tows' catch (tow mean weight = a mean(L^b)); for each tow, the TS
of its largest alewife measured is also given.

    python flagged_tracks.py TRACKS_CSV TRAWL_DIR TOW_LIST OUT_DIR
Writes OUT_DIR/flag_summary_by_tow.csv, flagged_tracks.csv, flag_rules_overview.csv and figures flag_*.png.
"""
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REL = (10.0, 13.0, 16.0)
ABS = (-40.0, -35.0, -30.0)
BIG_MARGIN_DB = 3.0
ts_warner = lambda w: (np.log10(w) - 6.79) / 0.13


def alewife_sizes(trawl_dir, ids):
    rd = lambda pat: pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(trawl_dir, pat))]).rename(columns=str.upper)
    lf, ca = rd("L_2_Y_*_Acoustic_tr_lf.csv"), rd("L_2_Y_*_Acoustic_tr_catch.csv")
    lf = lf[(lf.SPECIES == 106) & lf.OP_ID.isin(ids)]
    ca = ca[(ca.SPECIES == 106) & ca.OP_ID.isin(ids)]
    c = ca.groupby("OP_ID").agg(N=("N", "sum"), W=("WEIGHT", "sum"))
    c = c[(c.W > 0) & (c.N > 0)]
    per = {op: np.repeat(d.LENGTH.values, d.N.astype(int).values) for op, d in lf.groupby("OP_ID")}
    rows = [(c.loc[op, "W"] / c.loc[op, "N"], L) for op, L in per.items() if op in c.index]
    best = None
    for b in np.arange(2.5, 3.6, 0.01):
        x = np.log([np.mean(L ** b) for _, L in rows]); y = np.log([w for w, _ in rows])
        la = np.median(y - x); s = np.sum((y - la - x) ** 2)
        if best is None or s < best[0]:
            best = (s, b, np.exp(la))
    _, b, a = best
    return a, b, per


def main(tracks_csv, trawl_dir, tow_list, out):
    os.makedirs(out, exist_ok=True)
    tr = pd.read_csv(tracks_csv)
    tows = pd.read_csv(tow_list).set_index("OP_ID")
    a, b, per = alewife_sizes(trawl_dir, set(tows.index))
    allL = np.concatenate(list(per.values()))
    L1, L99 = np.percentile(allL, [1, 99])
    ts_lo, ts_hi = ts_warner(a * L1 ** b), ts_warner(a * L99 ** b)
    band = tr[tr.n_in_band > 0].copy()
    med = band.groupby("OP_ID").ts_mean.median()
    band["tow_median"] = band.OP_ID.map(med)
    band["above_median_db"] = band.ts_mean - band.tow_median
    for r in REL:
        band[f"rel{int(r)}"] = band.above_median_db >= r
    for t in ABS:
        band[f"abs{int(-t)}"] = band.ts_mean > t
    lmax = {op: L.max() for op, L in per.items()}
    band["ts_largest_alewife_tow"] = band.OP_ID.map(lambda op: ts_warner(a * lmax[op] ** b) if op in lmax else np.nan)
    band["n_alewife_measured"] = band.OP_ID.map(lambda op: len(per[op]) if op in per else 0)
    # combined rule (user asked to compare, 2026-11-01): above -35 dB, or more than BIG_MARGIN_DB above the TS of the
    # tow's largest alewife caught (tows without lengths: -35 dB only)
    band["big3"] = band.ts_mean > band.ts_largest_alewife_tow + BIG_MARGIN_DB
    band["comb"] = band.abs35 | band.big3
    rules = [f"rel{int(r)}" for r in REL] + [f"abs{int(-t)}" for t in ABS] + ["big3", "comb"]
    g = band.groupby("OP_ID")
    summ = pd.DataFrame(dict(
        n_tracks=g.size(), median_track_ts=g.ts_mean.median(), max_track_ts=g.ts_mean.max(),
        ts_largest_alewife=g.ts_largest_alewife_tow.first(),
        **{f"n_{r}": g[r].sum() for r in rules}))
    summ.insert(0, "format", g.format.first())
    summ.join(tows[[c for c in ("YEAR", "VESSEL", "TRANSECT", "FISHING_DEPTH") if c in tows]]).round(2).to_csv(os.path.join(out, "flag_summary_by_tow.csv"))
    flag = band[band[rules].any(axis=1)]
    flag[["OP_ID", "format", "track", "n_targets", "n_in_band", "ts_mean", "ts_min", "ts_max", "tow_median",
          "above_median_db", "ts_largest_alewife_tow", "n_alewife_measured", "depth_mean", "time_s_start", "time_s_end"] + rules] \
        .round(3).to_csv(os.path.join(out, "flagged_tracks.csv"), index=False)
    ov = pd.DataFrame([dict(rule=r, tracks_flagged=int(band[r].sum()), tows_with_flag=int(g[r].any().sum()),
                            flagged_below_minus40=int((band[r] & (band.ts_mean <= -40)).sum()),
                            flagged_within_expected_alewife=int((band[r] & band.ts_mean.between(ts_lo, ts_hi)).sum()))
                       for r in rules])
    ov.to_csv(os.path.join(out, "flag_rules_overview.csv"), index=False)
    print(f"length-weight: W = {a:.3g} L^{b:.2f}; alewife 1-99% length {L1:.0f}-{L99:.0f} mm -> TS {ts_lo:.1f} to {ts_hi:.1f} dB")
    print(f"tows {band.OP_ID.nunique()}, tracks in band {len(band)}; tow median track TS: "
          f"{med.quantile(.05):.1f} / {med.median():.1f} / {med.quantile(.95):.1f} dB (p5/50/95)")
    print(ov.to_string(index=False))

    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.axvspan(ts_lo, ts_hi, color="tab:green", alpha=.15, label=f"alewife {L1:.0f}-{L99:.0f} mm (Warner et al. 2002)")
    ax.hist(band.ts_mean, bins=np.arange(-62, -10, 0.5), color="0.35")
    ax.set_yscale("log")
    for t in ABS:
        ax.axvline(t, color="tab:red", ls=":", lw=1)
    ax.set_xlabel("track mean TS (dB)"); ax.set_ylabel("tracks (log scale)")
    ax.set_title(f"Fish tracks in the tow band, {band.OP_ID.nunique()} alewife tows ({len(band)} tracks)", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(out, "flag_track_ts_histogram.png"), dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.axhspan(ts_lo, ts_hi, color="tab:green", alpha=.12)
    ax.scatter(band.tow_median, band.ts_mean, s=3, color="0.6", label="tracks")
    x = np.linspace(med.min() - 1, med.max() + 1, 2)
    for r, c in zip(REL, ("tab:orange", "tab:blue", "tab:purple")):
        ax.plot(x, x + r, color=c, lw=1, label=f"tow median + {r:g} dB")
    for t in ABS:
        ax.axhline(t, color="tab:red", ls=":", lw=1)
    ax.set_xlabel("tow median track TS (dB)"); ax.set_ylabel("track mean TS (dB)")
    ax.legend(fontsize=8, loc="upper left")
    ax.set_title("Track TS vs the tow's median track (green: expected alewife; red: -40 / -35 / -30 dB)", fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(out, "flag_track_vs_tow_median.png"), dpi=130); plt.close(fig)


if __name__ == "__main__":
    main(*sys.argv[1:5])
