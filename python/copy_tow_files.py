"""Copy the acoustic data files of the used tows (data/derived/tow_selection.csv, status "used") into the project,
as bloaterTS scripts/03_copy_tow_files.py (user, 2026-11-02: the 129 used tows only):

    data/raw/acoustic/<year>/<vessel>/<transect>/<file name>

The files are those the tow run used (data/derived/tow_results.csv, files_used). The archive is only read. Each file
is hashed (SHA-256) as it is read and the copy is hashed again; the two must agree. data/raw/acoustic/tow_files.csv
(committed; the copies are git-ignored): OP_ID, source_path, size_bytes, copy_path (relative to the project root),
sha256. A file used by two tows is copied once. Rerunning skips files whose copy exists with the recorded size and hash.

    python python/copy_tow_files.py      (alewifeTS root; echopype env)
"""
import hashlib
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPIES = os.path.join(ROOT, "data", "raw", "acoustic")
FILES_CSV = os.path.join(COPIES, "tow_files.csv")
VESSEL_NAMES = {17: "steelhead", 88: "sturgeon", 35: "baird", 37: "arcticus"}
CHUNK = 16 * 1024 * 1024


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def copy_with_hash(source, dest):
    """Copy source to dest (via a temporary name), hashing the bytes read from source. Returns the source's SHA-256."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".partial"
    h = hashlib.sha256()
    with open(source, "rb") as fin, open(tmp, "wb") as fout:
        for block in iter(lambda: fin.read(CHUNK), b""):
            h.update(block)
            fout.write(block)
    os.replace(tmp, dest)
    return h.hexdigest()


def file_list():
    sel = pd.read_csv(os.path.join(ROOT, "data", "derived", "tow_selection.csv"))
    sel = sel[sel.status == "used"].set_index("OP_ID")
    res = pd.read_csv(os.path.join(ROOT, "data", "derived", "tow_results.csv"))
    res = res[(res.status == "ok") & res.OP_ID.isin(sel.index)].drop_duplicates("OP_ID", keep="last")
    missing = sorted(set(sel.index) - set(res.OP_ID))
    if missing:
        raise ValueError(f"used tows without an ok tow run row: {missing}")
    rows = []
    for r in res.itertuples():
        t = sel.loc[r.OP_ID]
        for src in str(r.files_used).split(";"):
            dest = os.path.join(COPIES, str(t.year), VESSEL_NAMES[int(t.vessel)], str(t.transect).lower(),
                                os.path.basename(src))
            rows.append({"OP_ID": int(r.OP_ID), "source_path": src, "size_bytes": os.path.getsize(src),
                         "copy_path": os.path.relpath(dest, ROOT)})
    return pd.DataFrame(rows)


def main():
    files = file_list()
    old = pd.read_csv(FILES_CSV, dtype={"sha256": str}) if os.path.exists(FILES_CSV) else pd.DataFrame(columns=["copy_path", "sha256"])
    known = dict(zip(old.copy_path, old.sha256))
    files["sha256"] = ""
    done = {}                      # copy_path -> (source path, sha256), this run
    n_copied = n_skipped = 0
    for k, i in enumerate(files.index, 1):
        row = files.loc[i]
        rel, src = row.copy_path, row.source_path
        dest = os.path.join(ROOT, rel)
        if rel in done:
            if os.path.normcase(os.path.normpath(done[rel][0])) != os.path.normcase(os.path.normpath(src)):
                raise RuntimeError(f"{src} and {done[rel][0]} would both be copied to {rel}")
            digest = done[rel][1]
        elif os.path.exists(dest) and isinstance(known.get(rel), str) and os.path.getsize(dest) == row.size_bytes:
            digest = known[rel]                      # copied on an earlier run
            n_skipped += 1
        else:
            if os.path.exists(dest):
                raise RuntimeError(f"{dest} exists but is not recorded as this file's copy")
            digest = copy_with_hash(src, dest)
            if sha256_of(dest) != digest:
                os.remove(dest)
                raise RuntimeError(f"copy of {src} does not match the source; removed")
            n_copied += 1
            print(f"[{k}/{len(files)}] {rel}", flush=True)
        done[rel] = (src, digest)
        files.at[i, "sha256"] = digest
        if k % 50 == 0:
            files[files.sha256 != ""].to_csv(FILES_CSV, index=False)     # keep progress if interrupted
    files.to_csv(FILES_CSV, index=False)
    print(f"Done: {n_copied} files copied, {n_skipped} already present, {len(done)} distinct files for "
          f"{files.OP_ID.nunique()} tows, {files.drop_duplicates('copy_path').size_bytes.sum() / 1e9:.2f} GB.")


if __name__ == "__main__":
    main()
