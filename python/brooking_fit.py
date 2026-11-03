"""Alewife share of the weak targets by the ex situ TS distribution of Brooking and Rudstam (2009), variant B of their
field methods (exploratory, user 2026-11-03). Their PDF of TS - TS_mode for alewife (70 kHz net-cage, 58-159 mm):

  f = 0.183 {P1 exp(-0.5 K1^2) + (1 - P1) exp(-0.5 K2^2) [1 + (k/2) s2^1.5 (K2 - K2^3/3)]},
  K1 = (dTS - mu1)/s1, K2 = (dTS - mu2)/s2, P1 0.176, mu1 -11.27, s1 3.46, mu2 -0.89, s2 1.88, k 0.57 (curve 2)

The printed equation has a minus before (k/2); with a plus it reproduces their Figure 5 (peak 17.8% at the mode), so the
plus is used. The few negative values above +3.3 dB (1.4% of the area) are set to 0 and the curve rescaled to 1.

For each tow: the targets detected down to -77 dB (step 10). The curve's position (TS mode) is fitted by maximum
likelihood to the targets from -50 to -30 dB (the range unlikely to hold non-fish targets), the curve truncated to that
range. The fitted curve then gives the number of alewife targets expected from -60 to -50 dB, p = expected / observed
there (capped at 1), and the tow's alewife mean TS:
  mean_ts_hybrid  observed sigma_bs: all targets >= -50 dB plus the -60 to -50 dB targets weighted by p
  mean_ts_model   the fitted curve's own mean sigma_bs over -60 to -30 dB

    python python/brooking_fit.py [OP_ID ...]          (default: the six example tows of weak_targets_examples.py)
Writes data/derived/brooking_fit/brooking_fit.csv and brooking_fit.png.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from project import Project

P1, MU1, S1, MU2, S2, K = 0.176, -11.27, 3.46, -0.89, 1.88, 0.57
FIT_LO, TS_MAX, FLOOR = -50.0, -30.0, -60.0
EXAMPLES = [78795, 124048, 93790, 79158, 127542, 124159]
STEP = 0.01


def brooking_pdf(dts):
    """Density of TS - TS_mode (per dB), negative tail set to 0, rescaled to integrate to 1."""
    grid = np.arange(-40, 20, STEP)
    def raw(x):
        k1, k2 = (x - MU1) / S1, (x - MU2) / S2
        y = P1 * np.exp(-.5 * k1 ** 2) + (1 - P1) * np.exp(-.5 * k2 ** 2) * (1 + (K / 2) * S2 ** 1.5 * (k2 - k2 ** 3 / 3))
        return np.clip(y, 0, None)
    return raw(np.asarray(dts, float)) / (raw(grid).sum() * STEP)


def share(mode, lo, hi):
    """Share of the alewife distribution (mode = TS_mode) between lo and hi dB."""
    x = np.arange(lo, hi, STEP) + STEP / 2
    return brooking_pdf(x - mode).sum() * STEP


def fit_mode(ts):
    """ML TS_mode from targets in [FIT_LO, TS_MAX], the curve truncated to that range."""
    modes = np.arange(-60, -30, 0.05)
    ll = [np.log(brooking_pdf(ts - m) / share(m, FIT_LO, TS_MAX) + 1e-300).sum() for m in modes]
    i = int(np.argmax(ll))
    # approximate 95% interval: modes within 1.92 log-likelihood units of the best
    ok = modes[np.array(ll) >= ll[i] - 1.92]
    return modes[i], ok.min(), ok.max()


def mean_db(sig):
    return 10 * np.log10(sig)


def fit_tow(ts):
    up = ts[(ts >= FIT_LO) & (ts <= TS_MAX)]
    mid = ts[(ts >= FLOOR) & (ts < FIT_LO)]
    mode, lo, hi = fit_mode(up)
    expected_mid = len(up) * share(mode, FLOOR, FIT_LO) / share(mode, FIT_LO, TS_MAX)
    p = min(1.0, expected_mid / len(mid)) if len(mid) else 1.0
    s_up, s_mid = 10 ** (up / 10), 10 ** (mid / 10)
    hybrid = (s_up.sum() + p * s_mid.sum()) / (len(up) + p * len(mid))
    x = np.arange(FLOOR, TS_MAX, STEP) + STEP / 2
    w = brooking_pdf(x - mode)
    model = (w * 10 ** (x / 10)).sum() / w.sum()
    return dict(n_up=len(up), n_mid=len(mid), n_weak=int((ts < FLOOR).sum()), mode=mode, mode_lo=lo, mode_hi=hi,
                expected_mid=expected_mid, p_alewife_mid=p, mean_ts_60=mean_db(np.mean(10 ** (ts[ts >= FLOOR] / 10))),
                mean_ts_hybrid=mean_db(hybrid), mean_ts_model=mean_db(model))


def main(ops):
    p = Project(apply_settings=False)
    out = os.path.join(p.derived, "brooking_fit")
    os.makedirs(out, exist_ok=True)
    a = pd.read_csv(os.path.join(p.derived, "analysis_tows.csv")).set_index("OP_ID")
    rows, data = [], {}
    for op in ops:
        ts = pd.read_csv(os.path.join(p.derived, "ts_floor", "single_targets_st77", f"{op}_single_targets.csv"),
                         usecols=["TS_comp"]).TS_comp.to_numpy()
        r = dict(OP_ID=op, length_mm=a.at[op, "Length"], **fit_tow(ts))
        r["warner_ts"] = 20.53 * np.log10(r["length_mm"] / 10) - 64.25
        r["brooking_mode_ts"] = 19.1 * np.log10(r["length_mm"] / 10) - 62.2
        r["brooking_mean_ts"] = 13.1 * np.log10(r["length_mm"] / 10) - 58.2
        rows.append(r)
        data[op] = ts
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(out, "brooking_fit.csv"), index=False)

    fig, axes = plt.subplots(len(ops), 1, figsize=(8, 2.3 * len(ops)), sharex=True)
    bins = np.arange(-77, -29, 1.0)
    for ax, r in zip(np.atleast_1d(axes), rows):
        ts = data[r["OP_ID"]]
        ax.hist(ts, bins=bins, color="0.7")
        x = np.arange(-77, -30, 0.1)
        scale = r["n_up"] / share(r["mode"], FIT_LO, TS_MAX)       # expected alewife targets per dB
        ax.plot(x, scale * brooking_pdf(x - r["mode"]), color="tab:red", lw=1.5, label="alewife (Brooking & Rudstam 2009), fitted >= -50 dB")
        for v, ls in [(FLOOR, ":"), (FIT_LO, "--")]:
            ax.axvline(v, color="k", ls=ls, lw=0.8)
        ax.set_ylim(0, max(5, 1.15 * np.histogram(ts[ts >= FLOOR], bins=bins)[0].max()))
        ax.set_title(f"{r['OP_ID']}: alewife {r['length_mm']:.0f} mm; mode {r['mode']:.1f} dB; share of -60 to -50 dB "
                     f"targets that are alewife {r['p_alewife_mid']:.2f}; mean TS -60: {r['mean_ts_60']:.1f}, "
                     f"alewife: {r['mean_ts_hybrid']:.1f} dB", fontsize=8, loc="left")
        ax.set_ylabel("targets")
    np.atleast_1d(axes)[0].legend(fontsize=7, loc="upper left")
    np.atleast_1d(axes)[-1].set_xlabel("TS_comp (dB); y axis cut at the highest bin >= -60 dB")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "brooking_fit.png"), dpi=130)
    pd.set_option("display.width", 220)
    print(d.round(2).to_string(index=False))


if __name__ == "__main__":
    main([int(x) for x in sys.argv[1:]] or EXAMPLES)
