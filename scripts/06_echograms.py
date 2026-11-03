"""Step 06: Sv echograms with the tow region and single targets, and each tow's bottom line (pydt4 plot_all_echograms.py,
run as a subprocess; bad-data regions are not drawn). Reads the acoustic archive.
Writes data/derived/echograms/<OP_ID>_*.png (git-ignored) and echograms/bottom/<OP_ID>_bottom.csv.

    python scripts/06_echograms.py [--op-ids ...]
"""
import os
import subprocess
import sys

from _project import Project, args


def main():
    a = args(__doc__)
    p = Project(a.derived)
    out = os.path.join(p.derived, "echograms")
    cmd = [sys.executable, os.path.join(p.pydt4, "plot_all_echograms.py"), "--tows", p.run_list,
           "--root", p.acoustic_root, "--corrections", p.corrections,
           "--results", os.path.join(p.derived, "tow_results.csv"),
           "--st-dir", os.path.join(p.derived, "tow_single_targets"), "--out-dir", out,
           "--bottom-dir", os.path.join(out, "bottom")]
    if a.op_ids:
        cmd += ["--op-ids", *map(str, a.op_ids)]
    subprocess.run(cmd, check=True, cwd=p.pydt4)
    p.log("06_echograms", f"op_ids={a.op_ids or 'all'}")


if __name__ == "__main__":
    main()
