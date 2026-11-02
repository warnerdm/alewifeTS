"""
show_flagged.py - one figure per tow for selected flagged fish tracks (flagged_tracks.py output).

Per tow: (left) every whole-column single target of the tow window, time vs depth, coloured by TS_comp, with the tow
band and the flagged tracks circled and labelled with their mean TS; (top right) the TS of the tow's fish tracks in the
band (track means) with the tow median, median + 13 dB, -35 dB and the TS of the tow's largest alewife caught; (bottom
right) the alewife lengths caught and the tow's catch by species (code: N).

    python show_flagged.py WHOLE_COLUMN_DIR TRAWL_DIR TOW_LIST OUT_DIR [selection]
selection: "rel13_not_abs35" (default; flagged by the 13 dB rule but not above -35 dB), "comb_not_abs35" (flagged by
the combined rule, -35 dB or largest alewife + 3 dB, but not above -35 dB) or "all".
"""
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from flagged_tracks import alewife_sizes, ts_warner  # noqa: E402


def main(wc, trawl_dir, tow_list, out, selection="rel13_not_abs35"):
    os.makedirs(out, exist_ok=True)
    fl = pd.read_csv(os.path.join(wc, "flags", "flagged_tracks.csv"))
    sel = {"rel13_not_abs35": fl[fl.rel13 & ~fl.abs35], "comb_not_abs35": fl[fl.comb & ~fl.abs35]}.get(selection, fl)
    tows = pd.read_csv(tow_list).set_index("OP_ID")
    a, b, per = alewife_sizes(trawl_dir, set(tows.index))
    ca = pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(trawl_dir, "L_2_Y_*_Acoustic_tr_catch.csv"))]).rename(columns=str.upper)
    tracks = pd.read_csv(os.path.join(wc, "tracks", "tracks.csv"))
    for op, fsel in sel.groupby("OP_ID"):
        tg = pd.read_csv(os.path.join(wc, "tracks", "targets", f"{op}_tracked.csv"))
        t = tows.loc[op]
        t0 = tg.time_s.min()
        tg["min"] = (tg.time_s - t0) / 60
        tb = tracks[(tracks.OP_ID == op) & (tracks.n_in_band > 0)]
        med = tb.ts_mean.median()
        fig = plt.figure(figsize=(13, 6.5))
        ax = fig.add_axes([0.06, 0.1, 0.56, 0.8])
        sc = ax.scatter(tg["min"], tg.depth, c=tg.TS_comp, s=4, cmap="viridis", vmin=-60, vmax=-30)
        ax.axhspan(t.FISHING_DEPTH, t.FISHING_DEPTH + t.trawl_ht, color="tab:orange", alpha=.12, label="tow band")
        allflag = fl[fl.OP_ID == op]
        for _, r in allflag.iterrows():
            m = tg[tg.track == r.track]
            col = "red" if r.track in set(fsel.track) else "tab:pink"
            ax.scatter(m["min"], m.depth, s=60, facecolors="none", edgecolors=col, lw=1.2)
            ax.annotate(f"{r.ts_mean:.1f} dB ({int(r.n_targets)})", (m["min"].mean(), m.depth.min()), xytext=(4, -10),
                        textcoords="offset points", color=col, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("minutes from the first target of the tow window"); ax.set_ylabel("depth (m)")
        ax.set_title(f"{op}  {int(t.YEAR)} vessel {int(t.VESSEL)} {t.TRANSECT}  {str(t.datetime)[:16]}  fishing depth "
                     f"{t.FISHING_DEPTH} m  (red: selected; pink: other flagged)", fontsize=9)
        fig.colorbar(sc, ax=ax, pad=0.01, label="TS_comp (dB)")
        ax2 = fig.add_axes([0.7, 0.57, 0.28, 0.33])
        ax2.hist(tb.ts_mean, bins=np.arange(-61, -20, 1), color="0.4")
        ts_big = ts_warner(a * per[op].max() ** b) if op in per else np.nan
        for x, c, lab in ((med, "k", "median"), (med + 13, "tab:blue", "median + 13"), (-35, "tab:red", "-35 dB"),
                          (ts_big, "tab:green", "largest alewife"), (ts_big + 3, "darkgreen", "largest alewife + 3")):
            ax2.axvline(x, color=c, lw=1, label=f"{lab} {x:.1f}")
        ax2.set_xlabel("track mean TS in the band (dB)", fontsize=8); ax2.legend(fontsize=7)
        ax2.set_title(f"{len(tb)} tracks in the band", fontsize=9)
        ax3 = fig.add_axes([0.7, 0.1, 0.28, 0.33])
        if op in per:
            ax3.hist(per[op], bins=np.arange(0, 260, 5), color="tab:green")
        ax3.set_xlabel("alewife length caught (mm)", fontsize=8)
        c = ca[ca.OP_ID == op].groupby("SPECIES").N.sum().sort_values(ascending=False)
        ax3.set_title("catch (species: N): " + ", ".join(f"{int(s)}: {int(n)}" for s, n in c.items()), fontsize=8)
        fig.savefig(os.path.join(out, f"flagged_{op}.png"), dpi=110)
        plt.close(fig)
        print(op, "done")


if __name__ == "__main__":
    main(*sys.argv[1:6])
