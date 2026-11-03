"""Example tows: adult alewife catch, many weak targets (exploratory, 2026-11-03). For each tow, the TS distribution of
its single targets detected down to -77 dB (step 10) against the TS that Warner, Rudstam and Klumb (2002) predict for
each alewife measured in the catch (TS = 20.53 log10(L, cm) - 64.25; 70 kHz), and the targets' range in the tow region.
Candidates: model tows (ts_length_outliers.csv, not outliers) with mean length >= 12 cm, <= 2% of the measured alewife
< 9 cm and >= 50 targets, ranked by the share of targets below -55 dB.

    python python/weak_targets_examples.py [OP_ID ...]
Writes data/derived/weak_targets/candidates.csv and weak_targets_examples.png.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from project import Project

EXAMPLES = [78795, 124048, 93790, 79158, 127542, 124159]   # the last: a tow close to Warner et al. (2002), for contrast


def warner_ts(length_mm):
    return 20.53 * np.log10(length_mm / 10) - 64.25


def main(ops):
    p = Project(apply_settings=False)
    out = os.path.join(p.derived, "weak_targets")
    os.makedirs(out, exist_ok=True)
    o = pd.read_csv(os.path.join(p.derived, "ts_length_outliers.csv"))
    a = pd.read_csv(os.path.join(p.derived, "analysis_tows.csv"))
    lf = pd.read_csv(os.path.join(p.derived, "tow_lengths.csv"))
    t = pd.read_csv(os.path.join(p.derived, "tow_targets.csv"))
    d = a[a.OP_ID.isin(o.OP_ID[~o.outlier])]
    small = lf.assign(s=lf.N * (lf.LENGTH < 90)).groupby("OP_ID").agg(s=("s", "sum"), n=("N", "sum"))
    w = t.groupby("OP_ID").TS_comp.agg(n_targets="size", weak_share=lambda x: (x < -55).mean(), median_ts="median")
    c = d.merge((small.s / small.n).rename("small_share"), on="OP_ID").merge(w, on="OP_ID")
    c["warner_ts"] = warner_ts(c.Length)
    c = c[(c.Length >= 120) & (c.small_share <= 0.02) & (c.n_targets >= 50)].sort_values("weak_share", ascending=False)
    c.to_csv(os.path.join(out, "candidates.csv"), index=False)

    fig, axes = plt.subplots(len(ops), 2, figsize=(10, 2.3 * len(ops)), gridspec_kw=dict(width_ratios=[2, 1]))
    bins = np.arange(-77, -29, 1.0)
    for (ax, ax2), op in zip(axes, ops):
        st = pd.read_csv(os.path.join(p.derived, "ts_floor", "single_targets_st77", f"{op}_single_targets.csv"))
        fish = lf[lf.OP_ID == op]
        row = a.set_index("OP_ID").loc[op]
        ax.hist(st.TS_comp, bins=bins, color="0.6", label=f"targets ({len(st)}; {(st.TS_comp >= -60).sum()} >= -60 dB)")
        ax2_ = ax.twinx()
        ax2_.hist(warner_ts(np.repeat(fish.LENGTH.to_numpy(), fish.N.to_numpy())), bins=bins, histtype="step",
                  color="tab:red", lw=1.5, label=f"catch: Warner et al. 2002 ({int(fish.N.sum())} alewife)")
        ax2_.set_yticks([])
        ax.axvline(-60, color="k", ls=":", lw=1)
        ax.set_title(f"{op}  {int(row.year)} vessel {int(row.vessel)} {row.acoustic_format}, fishing depth "
                     f"{row.fishing_depth_m:.1f} m, alewife {row.min_length:.0f}-{row.max_length:.0f} mm "
                     f"(mean {row.Length:.0f})", fontsize=9, loc="left")
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2_.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper left")
        ax.set_ylabel("targets")
        ax2.scatter(st.TS_comp, st.Target_range, s=3, c=np.where(st.TS_comp >= -60, "k", "0.6"))
        ax2.invert_yaxis()
        ax2.set_ylabel("range (m)")
    axes[-1][0].set_xlabel("TS_comp (dB)")
    axes[-1][1].set_xlabel("TS_comp (dB)")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "weak_targets_examples.png"), dpi=130)
    print(c[["OP_ID", "year", "vessel", "acoustic_format", "Length", "n_targets", "weak_share", "median_ts", "meanTS",
             "warner_ts"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main([int(x) for x in sys.argv[1:]] or EXAMPLES)
