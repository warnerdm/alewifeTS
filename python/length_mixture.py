"""Two-group normal mixtures of the alewife catch lengths in tows chosen by the user from the length-frequency plots
(python/lf_plots.py) as having two size groups (2026-11-03). Each tow's measured lengths (with their counts) are fitted
by EM with 2 normal components from several starts; BIC for 1, 2 and 3 components is given for comparison. Groups are
numbered from the smaller to the larger mean.

    python python/length_mixture.py [OP_ID ...]          (default: the user's 13 tows)
Writes data/derived/length_mixture/length_mixture.csv and length_mixture.png.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from project import Project

# the user's choice, 2026-11-03 (119389 given as 119289, which is not a used tow)
TOWS = [106432, 106431, 124044, 112431, 89418, 127535, 93784, 105054, 81845, 58070, 58066, 119389, 81764]
MIN_SD = 2.0      # mm; keeps a component from collapsing onto one length


def em(x, w, k, starts=20, seed=0):
    """Weighted EM for a k-component normal mixture; returns (loglik, props, means, sds)."""
    rng = np.random.default_rng(seed)
    best = None
    for s in range(starts):
        if s == 0:
            mu = np.quantile(np.repeat(x, w.astype(int)), np.linspace(0.15, 0.85, k))
        else:
            mu = rng.choice(x, k, replace=False, p=w / w.sum()).astype(float)
        sd = np.full(k, max(MIN_SD, np.sqrt(np.average((x - np.average(x, weights=w)) ** 2, weights=w)) / k))
        pi = np.full(k, 1 / k)
        for _ in range(2000):
            dens = pi * np.exp(-0.5 * ((x[:, None] - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
            tot = dens.sum(axis=1, keepdims=True) + 1e-300
            r = dens / tot * w[:, None]
            nk = r.sum(axis=0) + 1e-12
            mu_new = (r * x[:, None]).sum(axis=0) / nk
            sd = np.maximum(MIN_SD, np.sqrt((r * (x[:, None] - mu_new) ** 2).sum(axis=0) / nk))
            pi = nk / w.sum()
            if np.allclose(mu, mu_new, atol=1e-6):
                mu = mu_new
                break
            mu = mu_new
        ll = float((w * np.log(tot[:, 0])).sum())
        if best is None or ll > best[0]:
            o = np.argsort(mu)
            best = (ll, pi[o], mu[o], sd[o])
    return best


def main(ops):
    p = Project(apply_settings=False)
    out = os.path.join(p.derived, "length_mixture")
    os.makedirs(out, exist_ok=True)
    lf = pd.read_csv(os.path.join(p.derived, "tow_lengths.csv"))
    rows = []
    ncol = 3
    nrow = int(np.ceil(len(ops) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(11, 2.4 * nrow))
    for ax in axes.flat[len(ops):]:
        ax.axis("off")
    for ax, op in zip(axes.flat, ops):
        g = lf[lf.OP_ID == op].groupby("LENGTH").N.sum()
        x, w = g.index.to_numpy(float), g.to_numpy(float)
        n = w.sum()
        bic = {}
        fits = {}
        for k in (1, 2, 3):
            if len(x) <= k:
                continue
            fits[k] = em(x, w, k)
            bic[k] = -2 * fits[k][0] + (3 * k - 1) * np.log(n)
        ll, pi, mu, sd = fits[2]
        rows.append(dict(OP_ID=op, n_measured=int(n), p_small=pi[0], mean_small=mu[0], sd_small=sd[0],
                         p_large=pi[1], mean_large=mu[1], sd_large=sd[1], ratio=mu[1] / mu[0],
                         n_small=pi[0] * n, n_large=pi[1] * n, bic1=bic.get(1), bic2=bic.get(2), bic3=bic.get(3)))
        ax.hist(x, bins=np.arange(15, 215, 5), weights=w, color="tab:green", alpha=0.6)
        xx = np.linspace(15, 210, 400)
        for j, c in enumerate(("tab:blue", "tab:red")):
            ax.plot(xx, n * 5 * pi[j] * np.exp(-0.5 * ((xx - mu[j]) / sd[j]) ** 2) / (sd[j] * np.sqrt(2 * np.pi)), color=c)
        best_k = min(bic, key=bic.get)
        ax.set_title(f"{op} n={int(n)}: {mu[0]:.0f} mm ({pi[0]:.0%}), {mu[1]:.0f} mm ({pi[1]:.0%}); "
                     f"ratio {mu[1] / mu[0]:.2f}; BIC best k={best_k}", fontsize=7)
        ax.tick_params(labelsize=6)
    for ax in axes[-1]:
        ax.set_xlabel("length (mm)", fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "length_mixture.png"), dpi=130)
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(out, "length_mixture.csv"), index=False)
    pd.set_option("display.width", 220)
    print(d.round(2).to_string(index=False))


if __name__ == "__main__":
    main([int(v) for v in sys.argv[1:]] or TOWS)
