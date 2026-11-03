"""Round-1 China track: pull candidate lines for cash and operating cash flow out of the HKEX report text.

Reads  data/raw/hk/<code>/*.txt   (from extract_hk_text.py)
Writes data/hk_candidate_lines.csv   - one row per matching line, with PDF page number and a unit hint

This script only FINDS lines. Values are read and checked by a person (or by the AI with the page open)
before they go into financials_hk.csv. It never converts currency.
"""
import csv
import glob
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
PAGE = re.compile(r"\[\[หน้า (\d+)\]\]")
UNIT = re.compile(r"(RMB|US\$|USD|HK\$|HKD)\s*[’'‘]?\s*(000|million|billion)", re.I)
HEAD_CF = re.compile(r"consolidated statements? of cash flows?", re.I)
HEAD_FP = re.compile(r"consolidated statements? of financial position|consolidated balance sheets?", re.I)
LINES = {
    "ocf": re.compile(r"^\s*net cash[^0-9]{0,70}operating activities", re.I),
    "cash": re.compile(r"^\s*cash and cash equivalents|^\s*cash and bank balances|^\s*time deposits|^\s*term deposits|^\s*short-term deposits|^\s*bank deposits|^\s*financial assets at fair value through profit or loss|^\s*restricted cash|^\s*pledged", re.I),
}
NUM = re.compile(r"\(?-?\d[\d,]*\.?\d*\)?")


def main():
    rows = []
    for path in sorted(glob.glob(os.path.join(ROOT, "raw", "hk", "*", "*.txt"))):
        code = os.path.basename(os.path.dirname(path))
        fname = os.path.basename(path)
        text = open(path, encoding="utf-8").read()
        chunks = PAGE.split(text)
        pages = {int(chunks[i]): chunks[i + 1] for i in range(1, len(chunks) - 1, 2)}
        cover = " ".join(pages.get(1, "").split())[:160]
        rows.append({"code": code, "file": fname, "page": 1, "kind": "cover", "unit_hint": "", "line": cover})
        for p, body in pages.items():
            # unit hint: this page, else the previous page (statements often state the unit in the header only)
            unit = UNIT.search(body) or UNIT.search(pages.get(p - 1, ""))
            uh = unit.group(0) if unit else ""
            is_fp = bool(HEAD_FP.search(body))
            for ln in body.splitlines():
                s = " ".join(ln.split())
                if LINES["ocf"].search(s) and len(NUM.findall(s)) >= 2:
                    rows.append({"code": code, "file": fname, "page": p, "kind": "ocf", "unit_hint": uh, "line": s[:220]})
                if is_fp and LINES["cash"].search(s) and len(NUM.findall(s)) >= 2:
                    rows.append({"code": code, "file": fname, "page": p, "kind": "cash", "unit_hint": uh, "line": s[:220]})
    with open(os.path.join(ROOT, "hk_candidate_lines.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["code", "file", "page", "kind", "unit_hint", "line"])
        w.writeheader()
        w.writerows(rows)
    print({"rows": len(rows), "files_with_ocf": len({(r["code"], r["file"]) for r in rows if r["kind"] == "ocf"}),
           "files_with_cash": len({(r["code"], r["file"]) for r in rows if r["kind"] == "cash"})})


if __name__ == "__main__":
    main()
