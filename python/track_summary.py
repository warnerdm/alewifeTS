"""Per-tow fish-track summaries of the used alewife tows (2026-11-02), as bloaterTS
echoview/experiments/fish_tracks_all_gap0/summarize_tracks.py (2026-10-08), from pydt4's gap-0 tracks of the targets
used (tow_selection.targets_with_track) instead of Echoview's.

Per tow, figure tow_<OP_ID>.png with three panels:
  1 targets used, per detection: all, and those in tracks, overlaid
  2 per fish: track mean TS (linear mean of its targets used), tracks >= 2 targets used; >= 4 highlighted
  3 within fish: TS_comp - track dB mean, tracks >= 4 targets used (bloaterTS: >= 5), each deviation scaled by
    sqrt(n / (n - 1)) so short tracks do not understate the spread (user, 2026-11-02; bloaterTS: unscaled);
    density curve only with >= 20 deviations (bloaterTS: > 5)
Table tow_track_summary.csv, one row per tow: targets used, share in tracks, tracks by length, per-detection vs
per-fish mean TS and the two parts of their difference (untracked targets, counting each fish once), within- and
between-fish SD, strong fish (track mean of its targets used > -35 dB, descriptive), Nv (tow run).
Figure overview.png: share of targets in tracks vs Nv, and per-fish minus per-detection mean TS vs Nv.

    python python/track_summary.py OUT_DIR
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import gaussian_kde  # noqa: E402

from tow_selection import ROOT, targets_with_track  # noqa: E402

MIN_WITHIN, MIN_CURVE, STRONG_DB = 4, 20, -35.0


def lin_mean_db(x):
    return 10 * np.log10(np.mean(10 ** (np.asarray(x) / 10)))


def tow_figure(tow, depth, used, fish, dev, path):
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
    bins = np.arange(-60, -29, 1)
    tracked = used.TS_comp[used.track >= 0]
    ax[0].hist(used.TS_comp, bins=bins, color="0.7", label=f"all ({len(used)})")
    ax[0].hist(tracked, bins=bins, color="0.3", label=f"in tracks ({len(tracked)})")
    ax[0].legend(fontsize=8)
    ax[0].set_title("targets used, per detection", fontsize=10)
    if len(fish):
        ax[1].hist(fish.ts_lin, bins=bins, color="tab:blue", alpha=.5, label=f">=2 targets ({len(fish)})")
        ax[1].hist(fish.ts_lin[fish.n >= MIN_WITHIN], bins=bins, color="tab:blue",
                   label=f">={MIN_WITHIN} targets ({int((fish.n >= MIN_WITHIN).sum())})")
        ax[1].legend(fontsize=8)
    ax[1].set_title("per fish (track mean)", fontsize=10)
    if len(dev):
        ax[2].hist(dev, bins=np.arange(-12, 12.5, .5), density=True, color="tab:green", alpha=.6)
    if len(dev) >= MIN_CURVE:
        x = np.linspace(-12, 12, 200)
        ax[2].plot(x, gaussian_kde(dev)(x), color="tab:green")
    elif len(dev):
        ax[2].text(0.5, 0.9, "too few for a curve", transform=ax[2].transAxes, ha="center", fontsize=8, color="0.4")
    ax[2].set_xlim(-12, 12)
    ax[2].set_title(f"within fish, tracks >={MIN_WITHIN}, length-corrected (n={len(dev)})", fontsize=10)
    ax[0].set_xlabel("TS_comp (dB)"); ax[1].set_xlabel("TS_comp (dB)"); ax[2].set_xlabel("TS - track mean (dB)")
    fig.suptitle(f"Tow {tow} (fishing depth {depth:.0f} m), gap 0", fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=90); plt.close(fig)


def main(out):
    os.makedirs(out, exist_ok=True)
    d = os.path.join(ROOT, "data", "derived")
    sel = pd.read_csv(os.path.join(d, "tow_selection.csv"))
    sel = sel[sel.status == "used"].set_index("OP_ID")
    nv = pd.read_csv(os.path.join(d, "tow_results.csv")).drop_duplicates("OP_ID", keep="last").set_index("OP_ID")
    rows = []
    for tow, s in sel.iterrows():
        used = targets_with_track(tow)
        in_tr = used[used.track >= 0]
        g = in_tr.groupby("track").TS_comp
        fish = pd.DataFrame({"n": g.size(), "ts_lin": g.apply(lin_mean_db), "ts_db": g.mean()})
        dv = in_tr.merge(fish[fish.n >= MIN_WITHIN][["n", "ts_db"]], left_on="track", right_index=True)
        dev = (dv.TS_comp - dv.ts_db) * np.sqrt(dv.n / (dv.n - 1))
        k = g.size()
        ss_w = g.apply(lambda x: ((x - x.mean()) ** 2).sum()).sum()
        df_w = (k - 1).sum()
        r = nv.loc[tow]
        rows.append(dict(
            OP_ID=tow, fishing_depth_m=s.fishing_depth_m, targets_used=len(used),
            frac_in_tracks=(used.track >= 0).mean() if len(used) else np.nan, fish_tracks=len(fish),
            fish_2=int((fish.n == 2).sum()), fish_3=int((fish.n == 3).sum()), fish_4_9=int(fish.n.between(4, 9).sum()),
            fish_10plus=int((fish.n >= 10).sum()), median_targets_per_fish=fish.n.median() if len(fish) else np.nan,
            ts_per_ping_lin_mean=lin_mean_db(used.TS_comp) if len(used) else np.nan,
            ts_tracked_per_detection_lin_mean=lin_mean_db(in_tr.TS_comp) if len(in_tr) else np.nan,
            ts_per_fish_lin_mean=lin_mean_db(fish.ts_lin) if len(fish) else np.nan,
            ts_per_ping_median=used.TS_comp.median() if len(used) else np.nan,
            ts_per_fish_median=fish.ts_lin.median() if len(fish) else np.nan,
            sd_within_fish_db=np.sqrt(ss_w / df_w) if df_w else np.nan,
            sd_between_fish_db=fish.ts_db.std() if len(fish) > 1 else np.nan,
            n_within_dev=len(dev), strong_fish=int((fish.ts_lin > STRONG_DB).sum()),
            nv=r.get("nv", np.nan), nv_frac_pings_gt_0_1=r.get("nv_frac_pings_gt_flag", np.nan)))
        tow_figure(tow, s.fishing_depth_m, used, fish, dev, os.path.join(out, f"tow_{tow}.png"))
    summ = pd.DataFrame(rows)
    summ["fish_minus_ping_mean_db"] = summ.ts_per_fish_lin_mean - summ.ts_per_ping_lin_mean
    summ["untracked_effect_db"] = summ.ts_tracked_per_detection_lin_mean - summ.ts_per_ping_lin_mean
    summ["repeat_count_effect_db"] = summ.ts_per_fish_lin_mean - summ.ts_tracked_per_detection_lin_mean
    summ.round(4).to_csv(os.path.join(out, "tow_track_summary.csv"), index=False)

    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].scatter(summ.nv, summ.frac_in_tracks, s=12, c=summ.fishing_depth_m, cmap="viridis")
    ax[0].set_xscale("log"); ax[0].set_xlabel("Nv (fish per m$^3$, tow run)"); ax[0].set_ylabel("share of targets in tracks")
    sc = ax[1].scatter(summ.nv, summ.fish_minus_ping_mean_db, s=12, c=summ.fishing_depth_m, cmap="viridis")
    ax[1].axhline(0, color="0.5", lw=0.8)
    ax[1].set_xscale("log"); ax[1].set_xlabel("Nv (fish per m$^3$, tow run)")
    ax[1].set_ylabel("per-fish minus per-detection mean TS (dB)")
    fig.colorbar(sc, ax=ax[1], label="fishing depth (m)")
    fig.suptitle(f"{len(summ)} used alewife tows, pydt4 gap-0 tracks", fontsize=11)
    fig.tight_layout(); fig.savefig(os.path.join(out, "overview.png"), dpi=100); plt.close(fig)

    q = summ
    print(f"tows {len(q)}; fish tracks {q.fish_tracks.sum()}; share of targets in tracks median "
          f"{q.frac_in_tracks.median():.2f} ({q.frac_in_tracks.min():.2f}-{q.frac_in_tracks.max():.2f}); "
          f"median targets per fish {q.median_targets_per_fish.median():.1f}")
    print(f"per-fish minus per-detection mean TS: median {q.fish_minus_ping_mean_db.median():+.2f} dB "
          f"({q.fish_minus_ping_mean_db.min():+.2f}..{q.fish_minus_ping_mean_db.max():+.2f}); untracked "
          f"{q.untracked_effect_db.median():+.2f}, repeat count {q.repeat_count_effect_db.median():+.2f}")
    print(f"within-fish SD median {q.sd_within_fish_db.median():.2f} dB; between-fish SD median "
          f"{q.sd_between_fish_db.median():.2f} dB; tows with a curve in panel 3: {(q.n_within_dev >= MIN_CURVE).sum()}")
    print(f"strong fish (> {STRONG_DB:g} dB): {q.strong_fish.sum()} in {(q.strong_fish > 0).sum()} tows")


if __name__ == "__main__":
    main(sys.argv[1])
