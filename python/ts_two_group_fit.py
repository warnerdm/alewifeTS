"""TS decomposition of the user's two-size-group tows, as Warner et al. (2002): each alewife size group is a normal
distribution in dB (user, 2026-11-03), beside a weak group (skew-normal). Targets: detected
down to -77 dB (step 10), all components truncated to -77 to -30 dB. Two stages: the weak group's shape from the
single-alewife mixture of python/mixture_fit.py, then, with it fixed, the two alewife groups and the weights by maximum
likelihood (L-BFGS-B, bounded) from a
grid of starts (no TS-length relation used). The alewife groups are ordered (small mean < large mean) and their SDs kept
within 1-6 dB. Each fitted group mean is paired with the matching length group of python/length_mixture.py.

    python python/ts_two_group_fit.py
Writes data/derived/ts_two_group/ts_two_group.csv (one row per tow) and ts_two_group.png.
"""
import itertools
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm, skewnorm

import mixture_fit
from project import Project

LO, HI = -77.0, -30.0
SD_MIN, SD_MAX = 1.0, 6.0


def trunc_norm(ts, mu, sd):
    return norm.pdf(ts, mu, sd) / (norm.cdf(HI, mu, sd) - norm.cdf(LO, mu, sd))


def trunc_skew(ts, loc, scale, a):
    return skewnorm.pdf(ts, a, loc, scale) / (skewnorm.cdf(HI, a, loc, scale) - skewnorm.cdf(LO, a, loc, scale) + 1e-300)


def sd_of(z):
    return SD_MIN + (SD_MAX - SD_MIN) / (1 + np.exp(-z))


def unpack(th):
    mu1, z1, gap, z2, loc, ls, a, w1, w2 = th
    e = np.exp([0.0, w1, w2])
    pw = e / e.sum()                         # weak, small, large
    return mu1, sd_of(z1), mu1 + np.exp(gap), sd_of(z2), loc, np.exp(ls), a, pw


def components(ts, th):
    mu1, s1, mu2, s2, loc, sc, a, pw = unpack(th)
    return (pw[0] * trunc_skew(ts, loc, sc, a), pw[1] * trunc_norm(ts, mu1, s1), pw[2] * trunc_norm(ts, mu2, s2))


def nll(th, ts):
    return -np.log(sum(components(ts, th)) + 1e-300).sum()


# bounds of the free parameters: small mean, its SD (logit), log gap to the large mean, large SD (logit), log weights of
# the two alewife groups relative to the weak group
BOUNDS = [(-75, -32), (-6, 6), (np.log(1), np.log(30)), (-6, 6), (-7, 4), (-7, 4)]


def fit(ts):
    """Stage 1: the weak group's shape from the single-alewife mixture (python/mixture_fit.py). Stage 2: that shape fixed,
    the two normal alewife groups and the weights fitted. Returns (full parameter vector, nll, converged)."""
    m = mixture_fit.fit(ts)
    _, loc, scale, a, _ = mixture_fit.unpack(m.x)
    weak = [loc, np.log(scale), a]
    full = lambda f: np.r_[f[:4], weak, f[4:]]
    best = None
    w0 = np.log(max(0.02, (ts > -55).mean()))
    for mu1, gap, (w1, w2) in itertools.product((-58, -54, -50, -46, -42), (4, 8, 12),
                                              ((w0, w0), (w0 - 1, w0), (w0, w0 - 1))):
        r = minimize(lambda f: nll(full(f), ts), [mu1, 0.0, np.log(gap), 0.0, w1, w2], method="L-BFGS-B", bounds=BOUNDS)
        if best is None or r.fun < best.fun:
            best = r
    return full(best.x), best.fun, bool(best.success)


def main():
    p = Project(apply_settings=False)
    out = os.path.join(p.derived, "ts_two_group")
    os.makedirs(out, exist_ok=True)
    lm = pd.read_csv(os.path.join(p.derived, "length_mixture", "length_mixture.csv"))
    rows, keep = [], {}
    for r in lm.itertuples():
        ts = pd.read_csv(os.path.join(p.derived, "ts_floor", "single_targets_st77", f"{r.OP_ID}_single_targets.csv"),
                         usecols=["TS_comp"]).TS_comp.to_numpy()
        ts = ts[(ts >= LO) & (ts <= HI)]
        th, fun, ok = fit(ts)
        mu1, s1, mu2, s2, loc, sc, a, pw = unpack(th)
        c = components(ts, th)
        tot = sum(c)
        rows.append(dict(OP_ID=r.OP_ID, n_targets=len(ts), converged=ok,
                         L_small=r.mean_small, L_large=r.mean_large, fish_small=r.n_small, fish_large=r.n_large,
                         ts_small=mu1, sd_small=s1, ts_large=mu2, sd_large=s2,
                         targets_small=(c[1] / tot).sum(), targets_large=(c[2] / tot).sum(), targets_weak=(c[0] / tot).sum(),
                         weak_loc=loc, weak_scale=sc, weak_shape=a, nll=fun))
        keep[r.OP_ID] = (ts, th)
        print(f"{r.OP_ID}: small {mu1:.1f} dB, large {mu2:.1f} dB", flush=True)
    d = pd.DataFrame(rows)
    d["slope_within"] = (d.ts_large - d.ts_small) / np.log10(d.L_large / d.L_small)
    d.to_csv(os.path.join(out, "ts_two_group.csv"), index=False)

    ncol = 3
    nrow = int(np.ceil(len(d) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(12, 2.5 * nrow))
    for ax in axes.flat[len(d):]:
        ax.axis("off")
    x = np.arange(LO, HI, 0.1)
    for ax, r in zip(axes.flat, d.itertuples()):
        ts, th = keep[r.OP_ID]
        ax.hist(ts, bins=np.arange(LO, HI + 1, 1.0), color="0.75")
        n = len(ts)
        cw, cs, cl = components(x, th)
        ax.plot(x, n * cw, color="tab:blue", lw=1)
        ax.plot(x, n * cs, color="tab:orange", lw=1.5)
        ax.plot(x, n * cl, color="tab:red", lw=1.5)
        ax.set_yscale("log")
        ax.set_ylim(0.3, 3 * np.histogram(ts, bins=np.arange(LO, HI + 1, 1.0))[0].max())
        ax.set_title(f"{r.OP_ID}: {r.L_small:.0f} mm -> {r.ts_small:.1f} dB ({r.targets_small:.0f} targets); "
                     f"{r.L_large:.0f} mm -> {r.ts_large:.1f} dB ({r.targets_large:.0f})", fontsize=7)
        ax.tick_params(labelsize=6)
    for ax in axes[-1]:
        ax.set_xlabel("TS_comp (dB)", fontsize=7)
    fig.suptitle("Blue: weak group (skew-normal); orange: small alewife; red: large alewife (normal, as Warner et al. 2002)", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(os.path.join(out, "ts_two_group.png"), dpi=130)
    pd.set_option("display.width", 250)
    print(d.drop(columns=["nll", "weak_loc", "weak_scale", "weak_shape"]).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
