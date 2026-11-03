"""Step 01: the run list. From the tow list (data/raw/LM_tow_list_2005_2024.csv; alewife >= 90% of the catch and >= 5
fish, R/create_mwt_location_list_for_python.R) drop the tows excluded by the user (2026-11-01; config/project.yaml):
FISHING_DEPTH < 5 m, Steelhead 2004 (dual-beam), Baird 2016 / 2017 (no calibration session).
Writes data/derived/LM_tow_list_alewife_run.csv (211 tows).

    python scripts/01_make_run_list.py
"""
import pandas as pd

from _project import Project, args


def main():
    a = args(__doc__)
    p = Project(a.derived)
    t = pd.read_csv(p.tow_list)
    keep = t.FISHING_DEPTH >= p.cfg["min_fishing_depth_m"]
    print(f"{len(t)} tows; FISHING_DEPTH < {p.cfg['min_fishing_depth_m']:g} m: {(~keep).sum()}")
    for vessel, year, why in p.cfg["exclude_vessel_years"]:
        hit = (t.VESSEL == vessel) & (t.YEAR == year)
        print(f"{why}: {(hit & keep).sum()} more")
        keep &= ~hit
    t[keep].to_csv(p.run_list, index=False)
    print(f"{keep.sum()} tows -> {p.run_list}")
    p.log("01_make_run_list", f"{keep.sum()} tows")


if __name__ == "__main__":
    main()
