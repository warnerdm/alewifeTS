"""Within-fish TS distributions of alewife (exploratory, 2026-11-02), as bloaterTS
echoview/experiments/fish_tracks_all_gap0/within_fish_summary.py (2026-10-08).

Question: for single fish, is the TS spread around the fish's own centre unimodal, and does it grow off-axis?
Data: the used tows (data/derived/tow_selection.csv), their targets used with the pydt4 gap-0 track each belongs to
(tow_selection.targets_with_track). Choices:
  - centre = the track's MEDIAN TS_comp (dB); deviation = TS_comp - track median; tracks with >= 5 targets used;
    for a track with an odd number of targets the one target that IS the median is dropped (deviation 0 by
    construction); deviations not rescaled for track length: all as bloaterTS
  - tows with >= 5 such tracks (user, 2026-11-02; bloaterTS: 20, which leaves 9 alewife tows: alewife tracks are short)
  - one group: no shallow / deep split (user, 2026-11-02: all qualifying tows are 5-24 m; bloaterTS split at 40 m)
  - Hartigan's dip test per tow only for tows with >= 20 such tracks (too little power below)
Panels: A pooled deviation density with a normal curve of the same SD; B one row per tow (sorted by fishing depth),
deviation density as colour; D (separate figure) SD of the deviations by off-axis angle, 95% CI from a bootstrap
resampling whole fish, bins with >= 30 targets.

    python python/within_fish.py OUT_DIR
Writes OUT_DIR/within_fish_summary.png, within_fish_vs_angle.png, within_fish_by_tow.csv, within_fish_vs_angle.csv,
within_fish_deviations.csv.
"""
import os
import sys

import diptest
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import gaussian_kde, kurtosis, norm, skew  # noqa: E402

from tow_selection import ROOT, targets_with_track  # noqa: E402

MIN_TARGETS, MIN_TRACKS, MIN_TRACKS_DIP = 5, 5, 20
X = np.linspace(-12, 12, 481)


def deviations():
    sel = pd.read_csv(os.path.join(ROOT, "data", "derived", "tow_selection.csv"))
    sel = sel[sel.status == "used"].set_index("OP_ID")
    t = pd.concat([targets_with_track(op) for op in sel.index], ignore_index=True)
    t = t[t.track >= 0].copy()
    key = ["OP_ID", "track"]
    t["n"] = t.groupby(key).TS_comp.transform("size")
    t = t[t.n >= MIN_TARGETS].copy()
    t["dev"] = t.TS_comp - t.groupby(key).TS_comp.transform("median")
    t["rank"] = t.groupby(key).TS_comp.rank(method="first")
    t = t[~((t.n % 2 == 1) & (t["rank"] == (t.n + 1) / 2))]          # odd n: drop the target that is the median
    t["off_axis_deg"] = np.hypot(t.Angle_minor_axis, t.Angle_major_axis)
    t["depth"] = t.OP_ID.map(sel.fishing_depth_m)
    return t


def main(out):
    os.makedirs(out, exist_ok=True)
    d = deviations()
    ntr = d.groupby("OP_ID").track.nunique()
    d = d[d.OP_ID.isin(ntr[ntr >= MIN_TRACKS].index)].copy()
    d[["OP_ID", "track", "n", "TS_comp", "dev", "off_axis_deg", "depth"]].round(4).to_csv(
        os.path.join(out, "within_fish_deviations.csv"), index=False)

    rows = []
    for tow, g in d.groupby("OP_ID"):
        nf = g.track.nunique()
        dip, p = diptest.diptest(g.dev.values) if nf >= MIN_TRACKS_DIP else (np.nan, np.nan)
        rows.append(dict(OP_ID=tow, fishing_depth_m=g.depth.iloc[0], tracks=nf, n_dev=len(g), sd_db=g.dev.std(),
                         skewness=skew(g.dev), excess_kurtosis=kurtosis(g.dev), dip=dip, dip_p=p))
    by = pd.DataFrame(rows).sort_values("fishing_depth_m")
    by.round(4).to_csv(os.path.join(out, "within_fish_by_tow.csv"), index=False)
    tested = by.dip_p.notna()

    fig = plt.figure(figsize=(13, 7))
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.15])
    a = fig.add_subplot(gs[0, 0])
    v = d.dev.values
    a.plot(X, gaussian_kde(v)(X), color="tab:blue", lw=2,
           label=f"{len(by)} tows, {by.tracks.sum()} fish, {len(v)} targets")
    a.plot(X, norm.pdf(X, 0, v.std()), color="tab:blue", lw=1, ls="--")
    a.set_xlim(-10, 8); a.set_xlabel("TS_comp - track median (dB)"); a.set_ylabel("density")
    a.set_title("A  Pooled within-fish deviations (dashed: normal, same SD)", fontsize=10, loc="left")
    a.legend(fontsize=8)
    b = fig.add_subplot(gs[:, 1])
    edges = np.arange(-10, 8.25, 0.5)
    mat = np.array([np.histogram(d.dev[d.OP_ID == t], bins=edges, density=True)[0] for t in by.OP_ID])
    b.imshow(mat, aspect="auto", cmap="viridis", extent=[edges[0], edges[-1], len(by) - 0.5, -0.5],
             interpolation="nearest")
    b.set_yticks(range(len(by)))
    mark = lambda p: "" if np.isnan(p) else (" *" if p < 0.05 else " o")
    b.set_yticklabels([f"{t} ({z:.0f} m, {n} fish){mark(p)}" for t, z, n, p in
                       zip(by.OP_ID, by.fishing_depth_m, by.tracks, by.dip_p)], fontsize=6.5)
    b.axvline(0, color="w", lw=0.5, ls=":")
    b.set_xlabel("TS_comp - track median (dB)")
    b.set_title(f"B  Each tow by fishing depth; dip test (tows >= {MIN_TRACKS_DIP} fish, o): "
                f"p < 0.05 (*) in {int((by.dip_p < 0.05).sum())} of {int(tested.sum())}", fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "within_fish_summary.png"), dpi=130)
    plt.close(fig)

    # D: spread vs off-axis angle; bootstrap resamples whole fish within each angle bin (as bloaterTS)
    rng = np.random.default_rng(20261102)
    s = d.copy()
    s["bin"] = pd.cut(s.off_axis_deg, np.arange(0, 4.01, 0.5))
    rows_d = []
    for iv, g in s.groupby("bin", observed=True):
        if len(g) < 30:
            continue
        fish = [x.values for _, x in g.groupby(["OP_ID", "track"]).dev]
        boot = [np.std(np.concatenate([fish[i] for i in rng.integers(0, len(fish), len(fish))]), ddof=1)
                for _ in range(1000)]
        rows_d.append(dict(angle_mid=iv.mid, targets=len(g), fish=len(fish), sd_db=g.dev.std(),
                           ci_lo=np.percentile(boot, 2.5), ci_hi=np.percentile(boot, 97.5)))
    r = pd.DataFrame(rows_d)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.errorbar(r.angle_mid, r.sd_db, yerr=[r.sd_db - r.ci_lo, r.ci_hi - r.sd_db], fmt="o-", color="tab:blue",
                capsize=3)
    for x, hi, n, f in zip(r.angle_mid, r.ci_hi, r.targets, r.fish):
        ax.annotate(f"{n}/{f}", (x, hi), textcoords="offset points", xytext=(0, 5), ha="center", fontsize=6,
                    color="tab:blue")
    ax.set_ylim(0, max(2.9, r.ci_hi.max() + 0.4)); ax.set_xlim(0, 4)          # bloaterTS 0-2.9; alewife spreads more
    ax.set_xlabel("off-axis angle (deg)"); ax.set_ylabel("SD of deviations from track median (dB)")
    ax.set_title("Within-fish spread vs position in the beam (95% CI, fish resampled; n = targets/fish)",
                 fontsize=9, loc="left")
    fig.tight_layout(); fig.savefig(os.path.join(out, "within_fish_vs_angle.png"), dpi=130); plt.close(fig)
    r.round(3).to_csv(os.path.join(out, "within_fish_vs_angle.csv"), index=False)

    print(by.round(3).to_string(index=False))
    print(f"pooled: tows {len(by)}, fish {by.tracks.sum()}, deviations {len(v)}, SD {v.std():.2f} dB, "
          f"skewness {skew(v):.2f}, excess kurtosis {kurtosis(v):.2f}")
    print(r.round(3).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1])
