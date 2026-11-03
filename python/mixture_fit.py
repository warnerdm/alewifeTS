"""Two-component mixture of each tow's TS distribution (exploratory, user 2026-11-03): the alewife component is the
ex situ distribution of Brooking and Rudstam (2009) (python/brooking_fit.py, shape fixed, position = TS mode fitted);
the weak component is a skew-normal in dB (location, scale, shape fitted). Both are truncated to the detected range,
-77 to -30 dB (step 10 targets), and fitted together by maximum likelihood with the mixing share, from several starts.

  alewife_share      fitted share of the tow's targets (-77 to -30 dB) that are alewife
  mean_ts_component  mean sigma_bs of the fitted alewife component over -77 to -30 dB, in dB
  mean_ts_posterior  mean sigma_bs of the observed targets, each weighted by its posterior probability of being alewife
  n_alewife          expected alewife targets (sum of the posterior probabilities)

    python python/mixture_fit.py [OP_ID ...]          (default: the six example tows)
Writes data/derived/mixture_fit/mixture_fit.csv and mixture_fit.png.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import skewnorm

from brooking_fit import EXAMPLES, brooking_pdf
from project import Project

LO, HI, STEP = -77.0, -30.0, 0.01
GRID = np.arange(LO, HI, STEP) + STEP / 2


def alewife_density(ts, mode):
    return brooking_pdf(ts - mode) / (brooking_pdf(GRID - mode).sum() * STEP)


def weak_density(ts, loc, scale, a):
    return skewnorm.pdf(ts, a, loc, scale) / (skewnorm.cdf(HI, a, loc, scale) - skewnorm.cdf(LO, a, loc, scale))


def unpack(th):
    mode, loc, log_scale, a, logit_w = th
    return mode, loc, np.exp(log_scale), a, 1 / (1 + np.exp(-logit_w))


def nll(th, ts):
    mode, loc, scale, a, w = unpack(th)
    f = w * alewife_density(ts, mode) + (1 - w) * weak_density(ts, loc, scale, a)
    return -np.log(f + 1e-300).sum()


def fit(ts):
    best = None
    for mode0 in (-46, -43, -40, -37):
        for w0 in (0.05, 0.2):
            th0 = [mode0, -65, np.log(4), 2.0, np.log(w0 / (1 - w0))]
            r = minimize(nll, th0, args=(ts,), method="Nelder-Mead",
                         options=dict(maxiter=20000, maxfev=20000, xatol=1e-4, fatol=1e-6))
            if best is None or r.fun < best.fun:
                best = r
    return best


def main(ops):
    p = Project(apply_settings=False)
    out = os.path.join(p.derived, "mixture_fit")
    os.makedirs(out, exist_ok=True)
    a_tows = pd.read_csv(os.path.join(p.derived, "analysis_tows.csv")).set_index("OP_ID")
    rows, keep = [], {}
    for op in ops:
        ts = pd.read_csv(os.path.join(p.derived, "ts_floor", "single_targets_st77", f"{op}_single_targets.csv"),
                         usecols=["TS_comp"]).TS_comp.to_numpy()
        ts = ts[(ts >= LO) & (ts <= HI)]
        r = fit(ts)
        mode, loc, scale, sk, w = unpack(r.x)
        fa = w * alewife_density(ts, mode)
        post = fa / (fa + (1 - w) * weak_density(ts, loc, scale, sk))
        sig = 10 ** (ts / 10)
        ga = alewife_density(GRID, mode)
        L = a_tows.at[op, "Length"]
        rows.append(dict(OP_ID=op, length_mm=L, n=len(ts), converged=bool(r.success), alewife_mode=mode,
                         weak_loc=loc, weak_scale=scale, weak_shape=sk, alewife_share=w, n_alewife=post.sum(),
                         n_alewife_ge60=post[ts >= -60].sum(), n_ge60=int((ts >= -60).sum()),
                         mean_ts_60=10 * np.log10(sig[ts >= -60].mean()),
                         mean_ts_component=10 * np.log10((ga * 10 ** (GRID / 10)).sum() / ga.sum()),
                         mean_ts_posterior=10 * np.log10((post * sig).sum() / post.sum()),
                         brooking_mode_ts=19.1 * np.log10(L / 10) - 62.2, brooking_mean_ts=13.1 * np.log10(L / 10) - 58.2,
                         warner_ts=20.53 * np.log10(L / 10) - 64.25, nll=r.fun))
        keep[op] = (ts, mode, loc, scale, sk, w)
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(out, "mixture_fit.csv"), index=False)

    fig, axes = plt.subplots(len(ops), 1, figsize=(8, 2.4 * len(ops)), sharex=True)
    bins = np.arange(LO, HI + 1, 1.0)
    for ax, r in zip(np.atleast_1d(axes), rows):
        ts, mode, loc, scale, sk, w = keep[r["OP_ID"]]
        ax.hist(ts, bins=bins, color="0.75")
        x = np.arange(LO, HI, 0.1)
        n = len(ts)
        ax.plot(x, n * w * alewife_density(x, mode), color="tab:red", label="alewife (Brooking & Rudstam 2009 shape)")
        ax.plot(x, n * (1 - w) * weak_density(x, loc, scale, sk), color="tab:blue", label="weak group (skew-normal)")
        ax.plot(x, n * (w * alewife_density(x, mode) + (1 - w) * weak_density(x, loc, scale, sk)), color="k", lw=0.8,
                label="sum")
        ax.set_yscale("log")
        ax.set_ylim(0.3, None)
        ax.axvline(-60, color="k", ls=":", lw=0.8)
        ax.set_title(f"{r['OP_ID']}: alewife {r['length_mm']:.0f} mm; fitted mode {mode:.1f} dB (Brooking eq. "
                     f"{r['brooking_mode_ts']:.1f}); alewife {r['n_alewife']:.0f} of {n} targets; mean TS -60: "
                     f"{r['mean_ts_60']:.1f}, alewife: {r['mean_ts_posterior']:.1f} dB", fontsize=8, loc="left")
        ax.set_ylabel("targets per dB")
    np.atleast_1d(axes)[0].legend(fontsize=7, loc="upper right")
    np.atleast_1d(axes)[-1].set_xlabel("TS_comp (dB)")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "mixture_fit.png"), dpi=130)
    pd.set_option("display.width", 250)
    print(d.drop(columns="nll").round(2).to_string(index=False))


if __name__ == "__main__":
    main([int(x) for x in sys.argv[1:]] or EXAMPLES)
