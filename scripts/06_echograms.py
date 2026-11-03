"""Step 06: Sv echograms with the tow region and single targets, and each tow's bottom line (pydt4 plot_all_echograms.py,
run in this process so the project's instrument settings apply; bad-data regions are not drawn; the Sv calibration
offset from the project's ECS table). Reads the project's copies of the tows' files (dt4; Simrad tows use the files in
step 05's results), or with --from-archive matches the dt4 tows against the archive.
Writes data/derived/echograms/<OP_ID>_*.png (git-ignored) and echograms/bottom/<OP_ID>_bottom.csv.

    python scripts/06_echograms.py [--op-ids ...] [--from-archive]
"""
import os
import runpy
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))
from project import Project, args


def main():
    a = args(__doc__)
    p = Project(a.derived)
    out = os.path.join(p.derived, "echograms")
    argv = ["plot_all_echograms.py", "--tows", p.run_list, "--root", p.acoustic_root, "--corrections", p.corrections,
            "--ecs", p.ecs_csv, "--results", os.path.join(p.derived, "tow_results.csv"),
            "--st-dir", os.path.join(p.derived, "tow_single_targets"), "--out-dir", out,
            "--bottom-dir", os.path.join(out, "bottom")]
    if a.op_ids:
        argv += ["--op-ids", *map(str, a.op_ids)]
    if not a.from_archive:
        argv += ["--file-list", p.file_list, "--file-list-base", "."]
    sys.argv = argv
    runpy.run_path(os.path.join(p.pydt4, "plot_all_echograms.py"), run_name="__main__")
    p.log("06_echograms", f"op_ids={a.op_ids or 'all'}" + (" from the archive" if a.from_archive else " from the copies"))


if __name__ == "__main__":
    main()
