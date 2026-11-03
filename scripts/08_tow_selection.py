"""Step 08: the tow selection from the review decisions (config/tow_review.csv) and the set-aside vessel-years
(config/set_aside.csv): python/tow_selection.py -> data/derived/tow_selection.csv (status used / excluded / set aside,
targets used and fish per tow). Reads data/derived only (no --derived).

    python scripts/08_tow_selection.py
"""
import os
import sys

from _project import ROOT, Project

sys.path.insert(0, os.path.join(ROOT, "python"))


def main():
    p = Project()
    import tow_selection
    tow_selection.main()
    p.log("08_tow_selection")


if __name__ == "__main__":
    main()
