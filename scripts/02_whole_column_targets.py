"""Step 02: whole-column single targets, the input for fish tracking (user, 2026-11-01). pydt4 run_tow_batch.run_batch
(dt4) then tow_echograms.run_simrad_tows (Simrad), on the run list with the start corrections and NO bad-data regions:
targets from 5 m below the surface to the bottom line, TS_comp >= -60 dB and no -30 dB ceiling (strong fish must be
tracked to be flagged); otherwise the Great Lakes SOP settings of the tow run.
Writes data/derived/whole_column/: tow_results_column.csv (dt4), tow_results_column_simrad.csv, single_targets_column/.
Reads the acoustic archive (tow matching), or with --from-copies the project's copies of the used tows' files.

    python scripts/02_whole_column_targets.py [--op-ids ...] [--from-copies]
"""
import os
from dataclasses import replace

from _project import Project, args


def main():
    a = args(__doc__)
    p = Project(a.derived)
    from run_tow_batch import DEFAULT_ST_PARAMS, run_batch
    from tow_echograms import run_simrad_tows
    st = replace(DEFAULT_ST_PARAMS, ts_max_db=None)
    st_dir = os.path.join(p.wc, "single_targets_column")
    zmin = p.cfg["whole_column_min_depth_m"]
    run_batch(p.run_list, p.acoustic_root, p.ecs_csv, os.path.join(p.wc, "tow_results_column.csv"), st_dir=st_dir,
              st_params=st, regions_csv="", corrections=p.corrections, st_min_depth_m=zmin, op_ids=a.op_ids,
              **p.files_kw(a.from_copies))
    run_simrad_tows(p.run_list, p.acoustic_root, results_csv=os.path.join(p.wc, "tow_results_column_simrad.csv"),
                    st_dir=st_dir, st_params=st, regions_csv="", corrections=p.corrections, st_min_depth_m=zmin,
                    op_ids=a.op_ids, **p.files_kw(a.from_copies))
    p.log("02_whole_column_targets", f"op_ids={a.op_ids or 'all'}" + (" from copies" if a.from_copies else ""))


if __name__ == "__main__":
    main()
