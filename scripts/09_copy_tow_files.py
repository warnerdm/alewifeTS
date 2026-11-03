"""Step 09: copy the used tows' acoustic files from the archive into data/raw/acoustic/<year>/<vessel>/<transect>/
(python/copy_tow_files.py; SHA-256 of source and copy in data/raw/acoustic/tow_files.csv). The copies are git-ignored
and archived with the project. Reads the acoustic archive. Safe to rerun (files already copied are skipped).

    python scripts/09_copy_tow_files.py
"""
import os
import sys

from _project import ROOT, Project

sys.path.insert(0, os.path.join(ROOT, "python"))


def main():
    p = Project()
    import copy_tow_files
    copy_tow_files.main()
    p.log("09_copy_tow_files")


if __name__ == "__main__":
    main()
