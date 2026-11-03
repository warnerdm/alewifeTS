"""Alewife length frequency of every used tow (step 08), for choosing tows with a small and a large size group by eye
(user, 2026-11-03). 5-mm bins, the same length axis on every panel, ordered by the share of alewife below 85 mm; each
panel gives OP_ID, year, vessel, number measured and the tow's status in the TS-length model (model / outlier / tow rule).

    python python/lf_plots.py
Writes data/derived/length_frequency/lf_used_tows.pdf (30 tows per page).
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd

from project import Project

PER_PAGE, NCOL = 30, 5


def main():
    p = Project(apply_settings=False)
    out = os.path.join(p.derived, "length_frequency")
    os.makedirs(out, exist_ok=True)
    lf = pd.read_csv(os.path.join(p.derived, "tow_lengths.csv"))
    a = pd.read_csv(os.path.join(p.derived, "analysis_tows.csv")).set_index("OP_ID")
    o = pd.read_csv(os.path.join(p.derived, "ts_length_outliers.csv")).set_index("OP_ID")
    status = {}
    for op in a.index:
        if not a.at[op, "analysis"]:
            status[op] = "tow rule: length SE"
        elif o.at[op, "outlier"]:
            status[op] = "outlier"
        else:
            status[op] = "model"
    small = lf.groupby("OP_ID").apply(lambda g: (g.N * (g.LENGTH < 85)).sum() / g.N.sum(), include_groups=False)
    ops = small.sort_values().index.tolist()
    bins = np.arange(20, 215, 5)
    with PdfPages(os.path.join(out, "lf_used_tows.pdf")) as pdf:
        for start in range(0, len(ops), PER_PAGE):
            page = ops[start:start + PER_PAGE]
            fig, axes = plt.subplots(PER_PAGE // NCOL, NCOL, figsize=(11, 8.5), sharex=True)
            for ax in axes.flat[len(page):]:
                ax.axis("off")
            for ax, op in zip(axes.flat, page):
                g = lf[lf.OP_ID == op]
                ax.hist(g.LENGTH, bins=bins, weights=g.N, color="tab:green")
                ax.axvline(100, color="k", ls=":", lw=0.7)
                r = a.loc[op]
                ax.set_title(f"{op}  {int(r.year)} v{int(r.vessel)}  n={int(g.N.sum())}  {status[op]}", fontsize=6.5)
                ax.tick_params(labelsize=6)
            for ax in axes[-1]:
                ax.set_xlabel("length (mm)", fontsize=7)
            fig.suptitle(f"Alewife length frequency, used tows {start + 1}-{start + len(page)} of {len(ops)} "
                         "(ordered by the share below 85 mm; dotted line 100 mm)", fontsize=9)
            fig.tight_layout(rect=(0, 0, 1, 0.97))
            pdf.savefig(fig)
            plt.close(fig)
    print(f"{len(ops)} tows -> {os.path.join(out, 'lf_used_tows.pdf')}")


if __name__ == "__main__":
    main()
