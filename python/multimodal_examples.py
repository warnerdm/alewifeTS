"""Tows whose alewife catch has both small and large fish (exploratory, user 2026-11-03): >= 15% of the measured alewife
< 90 mm and >= 15% >= 100 mm, among the 117 model tows. For each: the catch length frequency, and the TS distribution
of the targets detected down to -77 dB (step 10) with
  - the alewife TS distribution predicted from the catch (Brooking and Rudstam 2009: their PDF placed at each 5-mm
    length group's mode, TS_mode = 19.1 log10 L - 62.2, weighted by the catch), scaled to the targets above -50 dB
    (their third method);
  - the mixture fit's single alewife component (python/mixture_fit.py all).

    python python/multimodal_examples.py
Writes data/derived/multimodal/multimodal_tows.csv and multimodal_examples.png.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from brooking_fit import brooking_pdf
from mixture_fit import HI, LO, alewife_density
from project import Project

MIN_SHARE = 0.15


def catch_pdf(x, lengths, counts):
    """Expected alewife TS density (per dB) from the catch: Brooking's PDF at each length's mode, weighted by count."""
    y = np.zeros_like(x, dtype=float)
    for L, n in zip(lengths, counts):
        y += n * brooking_pdf(x - (19.1 * np.log10(L / 10) - 62.2))
    return y / counts.sum()


def main():
    p = Project(apply_settings=False)
    out = os.path.join(p.derived, "multimodal")
    os.makedirs(out, exist_ok=True)
    lf = pd.read_csv(os.path.join(p.derived, "tow_lengths.csv"))
    o = pd.read_csv(os.path.join(p.derived, "ts_length_outliers.csv"))
    mix = pd.read_csv(os.path.join(p.derived, "mixture_fit", "mixture_fit_all.csv")).set_index("OP_ID")
    rows = []
    for op, g in lf[lf.OP_ID.isin(o.OP_ID[~o.outlier])].groupby("OP_ID"):
        n = g.N.sum()
        rows.append(dict(OP_ID=op, n_measured=n, share_lt90=g.N[g.LENGTH < 90].sum() / n,
                         share_ge100=g.N[g.LENGTH >= 100].sum() / n))
    d = pd.DataFrame(rows)
    d = d[(d.share_lt90 >= MIN_SHARE) & (d.share_ge100 >= MIN_SHARE)].reset_index(drop=True)

    fig, axes = plt.subplots(len(d), 2, figsize=(11, 2.4 * len(d)), gridspec_kw=dict(width_ratios=[1, 2.2]))
    bins = np.arange(LO, HI + 1, 1.0)
    x = np.arange(LO, HI, 0.1)
    for (ax1, ax2), r in zip(np.atleast_2d(axes), d.itertuples()):
        g = lf[lf.OP_ID == r.OP_ID]
        b = (g.LENGTH // 5) * 5 + 2.5
        cnt = g.groupby(b).N.sum()
        ax1.bar(cnt.index, cnt.values, width=5, color="tab:green")
        ax1.set_title(f"{r.OP_ID}: {int(r.n_measured)} alewife measured", fontsize=8, loc="left")
        ax1.set_xlabel("length (mm)", fontsize=8)
        ts = pd.read_csv(os.path.join(p.derived, "ts_floor", "single_targets_st77", f"{r.OP_ID}_single_targets.csv"),
                         usecols=["TS_comp"]).TS_comp.to_numpy()
        ts = ts[(ts >= LO) & (ts <= HI)]
        ax2.hist(ts, bins=bins, color="0.75")
        pc = catch_pdf(x, cnt.index.to_numpy(), cnt.to_numpy())
        up = (ts >= -50).sum()
        scale = up / (pc[x >= -50].sum() * 0.1)
        ax2.plot(x, scale * pc, color="tab:green", label="alewife predicted from the catch (Brooking & Rudstam), scaled to targets >= -50 dB")
        m = mix.loc[r.OP_ID]
        ax2.plot(x, len(ts) * m.alewife_share * alewife_density(x, m.alewife_mode), color="tab:red",
                 label=f"mixture alewife component (mode {m.alewife_mode:.1f} dB)")
        ax2.set_yscale("log")
        ax2.set_ylim(0.3, None)
        ax2.axvline(-60, color="k", ls=":", lw=0.8)
        ax2.axvline(-50, color="k", ls="--", lw=0.8)
        ax2.set_title(f"{len(ts)} targets; < 90 mm {r.share_lt90:.0%}, >= 100 mm {r.share_ge100:.0%}", fontsize=8, loc="left")
        ax2.legend(fontsize=6, loc="upper right")
    np.atleast_2d(axes)[-1][1].set_xlabel("TS_comp (dB)")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "multimodal_examples.png"), dpi=130)
    d.to_csv(os.path.join(out, "multimodal_tows.csv"), index=False)
    print(d.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
