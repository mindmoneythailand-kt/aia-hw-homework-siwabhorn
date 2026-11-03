"""Round-1 China track: convert downloaded HKEX PDFs to page-tagged text (for reading and number lookup).

Reads  data/raw/hk/<code>/*.pdf
Writes data/raw/hk/<code>/*.txt   (git-ignored)   - each page starts with '[[หน้า N]]' (N = PDF page number)
       data/hk_extract_status.csv                 - pages, characters, pages with no text (scanned)
"""
import csv
import glob
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import pypdf

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def convert(path):
    out = path[:-4] + ".txt"
    reader = pypdf.PdfReader(path)
    parts, empty = [], 0
    for i, page in enumerate(reader.pages, 1):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        if len(t.strip()) < 20:
            empty += 1
        parts.append(f"[[หน้า {i}]]\n{t}\n")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(parts))
    return {"file": os.path.relpath(path, ROOT), "pages": len(reader.pages), "chars": sum(len(p) for p in parts),
            "pages_without_text": empty}


def main():
    pdfs = sorted(glob.glob(os.path.join(ROOT, "raw", "hk", "*", "*.pdf")))
    rows = []
    with ProcessPoolExecutor(max_workers=4) as ex:
        for r in ex.map(convert, pdfs):
            rows.append(r)
            print(r, flush=True)
    with open(os.path.join(ROOT, "hk_extract_status.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    sys.exit(main())
