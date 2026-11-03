"""Shared setup for the step scripts: reads config/project.yaml, puts pydt4 on the path, resolves the paths, and logs
each step's run (data/derived/run_log.csv: step, time, pydt4 commit, whether pydt4 had uncommitted changes).

Every step script takes --derived DIR to write its outputs somewhere other than data/derived (used to check that the
steps reproduce the committed outputs); the bad-data regions then go to DIR/bad_data_regions/regions.csv.
The steps that read acoustic data (02, 05, 06; 03 follows the files of step 02's results) take --from-copies to read
the project's copies (data/raw/acoustic/tow_files.csv) instead of searching the archive; only the copied (used) tows
are then processed, the others get status not_in_file_list.
"""
import argparse
import datetime
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _abs(p):
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(ROOT, p))


class Project:
    def __init__(self, derived=None):
        with open(os.path.join(ROOT, "config", "project.yaml"), encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)
        c = self.cfg
        self.pydt4 = c["pydt4"]
        if self.pydt4 not in sys.path:
            sys.path.insert(0, self.pydt4)
        self.acoustic_root = c["acoustic_root"]
        self.ecs_csv = c["ecs_csv"]
        self.tow_list = _abs(c["tow_list"])
        self.trawl_dir = _abs(c["trawl_dir"])
        self.corrections = _abs(c["start_corrections"])
        self.derived = _abs(derived) if derived else _abs(c["derived_dir"])
        self.run_list = (os.path.join(self.derived, os.path.basename(c["run_list"])) if derived else _abs(c["run_list"]))
        self.regions = (os.path.join(self.derived, "bad_data_regions", "regions.csv") if derived
                        else _abs(c["bad_data_regions"]))
        self.wc = os.path.join(self.derived, "whole_column")
        self.file_list = os.path.join(_abs(c["acoustic_copies_dir"]), "tow_files.csv")
        os.makedirs(self.derived, exist_ok=True)

    def files_kw(self, from_copies):
        """Keyword arguments for pydt4 run_batch / run_simrad_tows: the copies' file list, or none (archive)."""
        return dict(file_list_csv=self.file_list, file_list_base=ROOT) if from_copies else {}

    def log(self, step, note=""):
        """Record that a step ran, with the pydt4 commit."""
        git = lambda *a: subprocess.run(["git", "-C", self.pydt4, *a], capture_output=True, text=True).stdout.strip()
        dirty = bool(git("status", "--porcelain", "--untracked-files=no"))
        line = f'{step},{datetime.datetime.now().isoformat(timespec="seconds")},{git("rev-parse", "--short", "HEAD")},{dirty},"{note}"\n'
        path = os.path.join(self.derived, "run_log.csv")
        new = not os.path.exists(path)
        with open(path, "a", encoding="utf-8") as f:
            if new:
                f.write("step,time,pydt4_commit,pydt4_uncommitted_changes,note\n")
            f.write(line)


def args(doc, extra=None):
    ap = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--derived", default=None, help="output folder instead of data/derived (reproduction checks)")
    ap.add_argument("--op-ids", type=int, nargs="+", default=None, help="only these tows (rows replaced)")
    ap.add_argument("--from-copies", action="store_true",
                    help="read the project's copies (data/raw/acoustic/tow_files.csv), not the archive")
    if extra:
        extra(ap)
    return ap.parse_args()
