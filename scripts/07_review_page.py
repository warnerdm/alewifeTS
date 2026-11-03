"""Step 07: the tow review page, review/tow_review.html (review/build_tow_review.py; git-ignored, rebuild instead).
The reviewer then records include / exclude and a reason for each tow in config/tow_review.csv (created with empty
decisions if missing; never overwritten). No acoustic files needed. Reads data/derived only (no --derived).

    python scripts/07_review_page.py
"""
import os
import runpy

from _project import ROOT, Project


def main():
    p = Project()
    runpy.run_path(os.path.join(ROOT, "review", "build_tow_review.py"), run_name="__main__")
    p.log("07_review_page")


if __name__ == "__main__":
    main()
