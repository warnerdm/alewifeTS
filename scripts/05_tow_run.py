"""Step 05: the tow run (tow region = tow window x fishing depth to fishing depth + trawl height). pydt4
run_tow_batch.run_batch (dt4) then tow_echograms.run_simrad_tows (Simrad) on the run list, with the start corrections
and the bad-data regions of step 04: region mean Sv (background noise removed), bottom line, Nv and single targets
(Great Lakes SOP, TS_comp -60 to -30 dB). Reads the project's copies of the tows' files, or with
--from-archive matches the tows against the acoustic archive.
Writes data/derived/tow_results.csv (one row per tow, dt4 and Simrad) and tow_single_targets/<OP_ID>_single_targets.csv.

    python scripts/05_tow_run.py [--op-ids ...] [--from-archive]
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))
from project import Project, args


def main():
    a = args(__doc__)
    p = Project(a.derived)
    from run_tow_batch import run_batch
    from tow_echograms import run_simrad_tows
    out = os.path.join(p.derived, "tow_results.csv")
    st_dir = os.path.join(p.derived, "tow_single_targets")
    run_batch(p.run_list, p.acoustic_root, p.ecs_csv, out, st_dir=st_dir, regions_csv=p.regions,
              corrections=p.corrections, op_ids=a.op_ids, **p.files_kw(a.from_archive))
    run_simrad_tows(p.run_list, p.acoustic_root, results_csv=out, st_dir=st_dir, regions_csv=p.regions,
                    corrections=p.corrections, op_ids=a.op_ids, **p.files_kw(a.from_archive))
    p.log("05_tow_run", f"op_ids={a.op_ids or 'all'}" + (" from the archive" if a.from_archive else " from the copies"))


if __name__ == "__main__":
    main()
