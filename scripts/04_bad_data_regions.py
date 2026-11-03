"""Step 04: automatic bad-data regions from the fish tracks (user rule, 2026-11-01): a track with a target in the tow
band and mean TS above -35 dB gets a rectangle around its detections, padded 2 s and 1 m (python/make_regions.py).
python/flagged_tracks.py first tabulates the flag rules compared (whole_column/flags/; figures there too).
Writes config/bad_data_regions/regions.csv (read by the tow run, step 05). No acoustic files needed.

    python scripts/04_bad_data_regions.py
"""
import os
import sys

from _project import ROOT, Project, args

sys.path.insert(0, os.path.join(ROOT, "python"))


def main():
    a = args(__doc__)
    p = Project(a.derived)
    import flagged_tracks
    import make_regions
    flagged_tracks.main(os.path.join(p.wc, "tracks", "tracks.csv"), p.trawl_dir, p.run_list, os.path.join(p.wc, "flags"))
    make_regions.main(p.wc, p.regions)
    p.log("04_bad_data_regions")


if __name__ == "__main__":
    main()
