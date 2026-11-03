"""Catch-based correction of Brooking and Rudstam (2009) for every model tow (exploratory, user 2026-11-03). For each tow:
  1. the catch's 5-mm length groups, each given its TS mode (19.1 log10 L - 62.2) and their PDF of TS - TS_mode
     (python/brooking_fit.py), weighted by the group's count and summed: the TS distribution the catch should produce;
  2. that curve scaled to the tow's observed targets from -50 to -30 dB (step 10 targets, detected down to -77 dB);
  3. its count from -60 to -50 dB = the alewife expected there; p = expected / observed (capped at 1);
  4. mean_ts_corrected: mean sigma_bs of all observed targets >= -50 dB plus the -60 to -50 dB targets weighted by p
     (the tow's in situ alewife TS; the curve only decides how much of the -60 to -50 dB range is kept);
     mean_ts_predicted: the curve's own mean sigma_bs from -60 to -30 dB (from the catch alone, no acoustics).
The curve was measured on 58-159 mm alewife; share_in_range gives each tow's share of measured alewife in that range.
No selectivity correction of the trawl catch. Tows without targets >= -50 dB get no corrected value.

    python python/catch_based.py
Writes data/derived/catch_based/catch_based.csv (R/catch-based-model.R fits the TS-length model to it).
"""
import os

import numpy as np
import pandas as pd

from multimodal_examples import catch_pdf
from project import Project

FLOOR, CUT, TS_MAX, STEP = -60.0, -50.0, -30.0, 0.01


def main():
    p = Project(apply_settings=False)
    out = os.path.join(p.derived, "catch_based")
    os.makedirs(out, exist_ok=True)
    lf = pd.read_csv(os.path.join(p.derived, "tow_lengths.csv"))
    o = pd.read_csv(os.path.join(p.derived, "ts_length_outliers.csv"))
    x = np.arange(FLOOR, TS_MAX, STEP) + STEP / 2
    rows = []
    for op in o.OP_ID[~o.outlier]:
        g = lf[lf.OP_ID == op]
        grp = g.groupby((g.LENGTH // 5) * 5 + 2.5).N.sum()
        pc = catch_pdf(x, grp.index.to_numpy(), grp.to_numpy().astype(float))
        ts = pd.read_csv(os.path.join(p.derived, "ts_floor", "single_targets_st77", f"{op}_single_targets.csv"),
                         usecols=["TS_comp"]).TS_comp.to_numpy()
        up = ts[(ts >= CUT) & (ts <= TS_MAX)]
        mid = ts[(ts >= FLOOR) & (ts < CUT)]
        share_up, share_mid = pc[x >= CUT].sum() * STEP, pc[x < CUT].sum() * STEP
        expected_mid = len(up) * share_mid / share_up if share_up > 0 else np.nan
        pa = min(1.0, expected_mid / len(mid)) if len(mid) else 1.0
        if len(up):
            s_up, s_mid = 10 ** (up / 10), 10 ** (mid / 10)
            corrected = 10 * np.log10((s_up.sum() + pa * s_mid.sum()) / (len(up) + pa * len(mid)))
        else:
            corrected = np.nan
        sel = ts[ts >= FLOOR]
        rows.append(dict(OP_ID=int(op), n_measured=int(g.N.sum()),
                         share_in_range=g.N[g.LENGTH.between(58, 159)].sum() / g.N.sum(),
                         n_ge50=len(up), n_60_50=len(mid), expected_alewife_60_50=expected_mid, p_alewife_60_50=pa,
                         mean_ts_60=10 * np.log10(np.mean(10 ** (sel / 10))) if len(sel) else np.nan,
                         mean_ts_corrected=corrected,
                         mean_ts_predicted=10 * np.log10((pc * 10 ** (x / 10)).sum() / pc.sum())))
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(out, "catch_based.csv"), index=False)
    print(f"{len(d)} tows; no targets >= -50 dB: {d.mean_ts_corrected.isna().sum()}; share of -60 to -50 dB targets "
          f"kept as alewife: median {d.p_alewife_60_50.median():.2f}; corrected minus -60 dB mean TS: median "
          f"{(d.mean_ts_corrected - d.mean_ts_60).median():+.2f} dB")


if __name__ == "__main__":
    main()
