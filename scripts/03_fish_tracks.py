"""Step 03: gap-0 fish tracks of the whole-column targets (pydt4 track_tows.py; Echoview 4D alpha-beta tracker, maximum
gap 0, minimum 2 targets / 2 pings, as bloaterTS). All tows of the step-02 results.
Writes data/derived/whole_column/tracks/tracks.csv (one row per track; n_in_band = targets in the tow band) and
tracks/targets/<OP_ID>_tracked.csv. Reads the files listed in step 02's results (ping times and GPS): the archive's,
or the copies' when step 02 ran with --from-copies.

    python scripts/03_fish_tracks.py
"""
import os

from _project import Project, args


def main():
    a = args(__doc__)
    if a.op_ids:
        raise SystemExit("03_fish_tracks runs all tows (tracks.csv is rewritten)")
    p = Project(a.derived)
    import track_tows
    c = p.cfg
    track_tows.main(["--results", os.path.join(p.wc, "tow_results_column.csv"),
                     os.path.join(p.wc, "tow_results_column_simrad.csv"),
                     "--targets", os.path.join(p.wc, "single_targets_column"), "--tows", p.run_list,
                     "--out", os.path.join(p.wc, "tracks"), "--min-depth", str(c["whole_column_min_depth_m"]),
                     "--max-gap", str(c["track_max_gap"]), "--min-targets", str(c["track_min_targets"]),
                     "--min-pings", str(c["track_min_pings"])])
    p.log("03_fish_tracks")


if __name__ == "__main__":
    main()
