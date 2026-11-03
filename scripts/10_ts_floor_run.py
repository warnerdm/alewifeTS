"""Step 10: TS floor sensitivity. The tow run of step 05 again (same tow regions, start corrections, bad-data regions,
noise removal, bottom line), but with single targets detected down to -77 dB compensated TS (Great Lakes SOP otherwise,
TS_comp max -30 dB), as pydt4 ts_floor_sensitivity.py; the mean TS at each floor is then taken from subsets
(R/ts-floor-models.R). Tows: the used tows of step 08 (the analysis tows are a subset). Step 05's outputs are not touched.
Writes data/derived/ts_floor/tow_results_st77.csv and data/derived/ts_floor/single_targets_st77/.

    python scripts/10_ts_floor_run.py [--op-ids ...] [--from-archive]
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))
from project import Project, args

DETECT_MIN_TS_DB = -77.0
MAX_TS_DB = -30.0


def main():
    a = args(__doc__)
    p = Project(a.derived)
    from run_tow_batch import run_batch
    from single_target import STDParams
    from tow_echograms import run_simrad_tows
    op_ids = a.op_ids
    if op_ids is None:
        sel = pd.read_csv(os.path.join(p.derived, "tow_selection.csv"))
        op_ids = sorted(int(x) for x in sel.OP_ID[sel.status == "used"])
    out_dir = os.path.join(p.derived, "ts_floor")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "tow_results_st77.csv")
    st_dir = os.path.join(out_dir, "single_targets_st77")
    prm = STDParams.great_lakes_sop(ts_threshold_db=DETECT_MIN_TS_DB, ts_max_db=MAX_TS_DB)
    run_batch(p.run_list, p.acoustic_root, p.ecs_csv, out, st_dir=st_dir, st_params=prm, regions_csv=p.regions,
              corrections=p.corrections, op_ids=op_ids, **p.files_kw(a.from_archive))
    run_simrad_tows(p.run_list, p.acoustic_root, results_csv=out, st_dir=st_dir, st_params=prm, regions_csv=p.regions,
                    corrections=p.corrections, op_ids=op_ids, **p.files_kw(a.from_archive))
    p.log("10_ts_floor_run", f"{len(op_ids)} tows, detection {DETECT_MIN_TS_DB} dB"
          + (" from the archive" if a.from_archive else " from the copies"))


if __name__ == "__main__":
    main()
