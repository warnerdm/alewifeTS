"""Write the project's own calibration and instrument settings from pydt4's tables (2026-11-03; run once, kept as the
record of where the values came from; the steps then use calibration/, not pydt4's tables):

  calibration/ecs_parameters.csv       the rows of pydt4's ECS table (data/ecs_parameters_usgs_steelhead.csv) that the
                                       run list's dt4 vessel-years use (Michigan or all-lake rows), unchanged
  calibration/instrument_settings.csv  pydt4 project_settings.export: transducer depth, Simrad file clock, dt4 clock
                                       offset and Simrad calibration per vessel-year (EK80 reports resolved to values)
  calibration/simrad_reports/          copies of the EK80 calibration reports (XML) behind those values

    python python/export_calibration.py PYDT4_ECS_CSV
"""
import os
import shutil
import sys

import pandas as pd

from project import ROOT, Project


def main(ecs_src):
    p = Project(apply_settings=False)
    import project_settings
    from tow_echograms import SIMRAD_CAL
    out = os.path.join(ROOT, "calibration")
    os.makedirs(os.path.join(out, "simrad_reports"), exist_ok=True)
    tows = pd.read_csv(p.run_list)
    vy = sorted({(int(r.VESSEL), int(r.YEAR), r.acoustic_format) for r in tows.itertuples()})

    ecs = pd.read_csv(ecs_src)
    lake = ecs["lake"].fillna("")
    dt4 = {(v, y) for v, y, f in vy if f == "dt4"}
    v, y = pd.to_numeric(ecs.VESSEL, errors="coerce"), pd.to_numeric(ecs.YEAR, errors="coerce")
    hit = pd.Series([(a, b) in dt4 for a, b in zip(v, y)], index=ecs.index)
    keep = ecs[hit & lake.isin(["", "Michigan"])]
    missing = dt4 - {(int(a), int(b)) for a, b in zip(keep.VESSEL, keep.YEAR)}
    if missing:
        raise ValueError(f"no ECS row for dt4 vessel-years {sorted(missing)}")
    keep.to_csv(os.path.join(out, "ecs_parameters.csv"), index=False)

    files = pd.read_csv(os.path.join(ROOT, "data", "raw", "acoustic", "tow_files.csv"))
    files["vy"] = files.OP_ID.map(tows.set_index("OP_ID").apply(lambda r: (int(r.VESSEL), int(r.YEAR)), axis=1))
    first = {k: os.path.join(ROOT, g.copy_path.iloc[0]) for k, g in files.groupby("vy")}
    st = project_settings.export(vy, first)
    for (v, y), entry in SIMRAD_CAL.items():
        xml = entry[0] if isinstance(entry, tuple) else entry if isinstance(entry, str) and entry != "file" else None
        if xml and (v, y, "raw") in vy and os.path.exists(xml):
            dest = os.path.join("calibration", "simrad_reports", f"{v}_{y}_{os.path.basename(xml)}")
            shutil.copy2(xml, os.path.join(ROOT, dest))
            hit = (st.vessel == v) & (st.year == y) & (st.format == "raw")
            st.loc[hit, "source"] = st.loc[hit, "source"] + f"; copy: {dest}"
    st.to_csv(os.path.join(out, "instrument_settings.csv"), index=False)
    print(f"{len(keep)} ECS rows, {len(st)} vessel-year settings -> {out}")
    print(st.drop(columns="source").to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1])
