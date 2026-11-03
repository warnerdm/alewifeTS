"""Shared setup for the step scripts and the project's modules: reads config/project.yaml, puts pydt4 on the path,
applies the project's own instrument settings to pydt4 (calibration/instrument_settings.csv, pydt4
project_settings.apply: transducer depths, Simrad file clocks, dt4 clock offsets and Simrad calibrations from the
project, not pydt4's tables), works from the project root with project-relative paths (so the output tables hold
paths relative to the project), and logs each step's run (data/derived/run_log.csv: step, time, pydt4 commit, whether
pydt4 had uncommitted changes). Warns when pydt4 is not at the commit config/project.yaml names (pydt4_commit).

Step options (args()): --derived DIR writes the outputs somewhere other than data/derived (reproduction checks; the
bad-data regions then go to DIR/bad_data_regions/regions.csv); --op-ids reruns selected tows; --from-archive matches
the tows against the acoustic archive (pydt4 tow matching) instead of reading the project's copies
(data/raw/acoustic/tow_files.csv, the default since 2026-11-03).
"""
import argparse
import datetime
import os
import subprocess
import sys
import warnings

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _path(p):
    """Absolute config paths stay absolute; project paths are kept relative to the project root (the working folder)."""
    return os.path.normpath(p) if os.path.isabs(p) else os.path.normpath(p)


class Project:
    def __init__(self, derived=None, apply_settings=True):
        os.chdir(ROOT)
        with open(os.path.join(ROOT, "config", "project.yaml"), encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)
        c = self.cfg
        self.pydt4 = c["pydt4"]
        if self.pydt4 not in sys.path:
            sys.path.insert(0, self.pydt4)
        self.acoustic_root = c["acoustic_root"]
        self.ecs_csv = _path(c["ecs_csv"])
        self.instrument_settings = _path(c["instrument_settings"])
        self.tow_list = _path(c["tow_list"])
        self.trawl_dir = _path(c["trawl_dir"])
        self.corrections = _path(c["start_corrections"])
        self.derived = os.path.abspath(derived) if derived else _path(c["derived_dir"])
        self.run_list = os.path.join(self.derived, os.path.basename(c["run_list"])) if derived else _path(c["run_list"])
        self.regions = (os.path.join(self.derived, "bad_data_regions", "regions.csv") if derived
                        else _path(c["bad_data_regions"]))
        self.wc = os.path.join(self.derived, "whole_column")
        self.file_list = os.path.join(_path(c["acoustic_copies_dir"]), "tow_files.csv")
        os.makedirs(self.derived, exist_ok=True)
        head = self._git("rev-parse", "--short", "HEAD")
        if c.get("pydt4_commit") and not head.startswith(str(c["pydt4_commit"])):
            warnings.warn(f"pydt4 is at {head}, config/project.yaml names {c['pydt4_commit']}")
        if apply_settings:
            import project_settings
            project_settings.apply(self.instrument_settings)

    def _git(self, *a):
        return subprocess.run(["git", "-C", self.pydt4, *a], capture_output=True, text=True).stdout.strip()

    def files_kw(self, from_archive=False):
        """Keyword arguments for pydt4 run_batch / run_simrad_tows: the copies' file list (default), or none (archive)."""
        return {} if from_archive else dict(file_list_csv=self.file_list, file_list_base=".")

    def log(self, step, note=""):
        """Record that a step ran, with the pydt4 commit."""
        dirty = bool(self._git("status", "--porcelain", "--untracked-files=no"))
        line = (f'{step},{datetime.datetime.now().isoformat(timespec="seconds")},{self._git("rev-parse", "--short", "HEAD")},'
                f'{dirty},"{note}"\n')
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
    ap.add_argument("--from-archive", action="store_true",
                    help="match the tows against the acoustic archive instead of reading the project's copies")
    if extra:
        extra(ap)
    return ap.parse_args()
