"""Round-1 step 2a: match ClinicalTrials.gov sponsors to SEC-listed companies (US).

Reads  data/candidate_sponsors.csv
Needs  env SEC_CONTACT  (contact text SEC requires in User-Agent; NEVER written to any file in this repo)
Writes data/sponsor_tickers.csv

match_quality:
  exact   - normalized names are equal (suffixes like Inc/Corp/LLC/Ltd removed)  -> usable, still spot-check
  partial - one normalized name starts with the other                            -> MUST be verified by a human
Unmatched sponsors keep ticker 'ยังไม่ยืนยัน' (private, non-US, or name differs). China / HK listings
are NOT mapped here (needs HKEX list; separate step).
"""
import csv
import json
import os
import re
import sys
import urllib.request
from datetime import date

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
SUFFIX = {"inc", "incorporated", "corp", "corporation", "co", "company", "ltd", "limited", "llc", "plc", "lp",
          "sa", "ag", "nv", "se", "gmbh", "the", "holdings", "holding", "group", "de", "ma", "ca", "ny", "nj", "pa"}


# Manual review 2026-11-01. Partial matches that are different companies -> rejected.
REJECT = {"Everest Medicines (China) Co.,Ltd.", "Frontier Medicines Corporation", "Navigator Medicines, Inc.",
          "GE Healthcare", "Medtronic Spinal and Biologics"}
# Subsidiary / trade names of an SEC registrant. Each ticker is looked up in the SEC file (must exist there).
MANUAL = {"Merck Sharp & Dohme LLC": "MRK", "Janssen Research & Development, LLC": "JNJ",
          "Novartis Pharmaceuticals": "NVS", "GlaxoSmithKline": "GSK"}


def norm(name):
    t = re.sub(r"[^a-z0-9 ]+", " ", name.lower().replace("&", " and "))
    words = [w for w in t.split() if w not in SUFFIX]
    return " ".join(words)


def main():
    contact = os.environ.get("SEC_CONTACT", "").strip()
    if not contact:
        sys.exit("ตั้ง SEC_CONTACT ก่อน (ข้อความติดต่อที่ SEC กำหนด) ห้ามเขียนลงไฟล์ใน repo")
    req = urllib.request.Request("https://www.sec.gov/files/company_tickers.json",
                                 headers={"User-Agent": "aia-homework-research " + contact})
    with urllib.request.urlopen(req, timeout=60) as r:
        tickers = json.loads(r.read().decode("utf-8"))
    sec = []
    for v in tickers.values():
        sec.append((norm(v["title"]), v["ticker"], int(v["cik_str"]), v["title"]))
    exact = {}
    for n, tk, cik, title in sec:
        exact.setdefault(n, (tk, cik, title))

    by_ticker = {tk: (tk, cik, title) for _, tk, cik, title in sec}
    with open(os.path.join(DATA, "candidate_sponsors.csv"), encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        n = norm(r["sponsor"])
        hit, q = None, ""
        if r["sponsor"] in REJECT:
            out.append({**r, "sec_ticker": "ยังไม่ยืนยัน", "sec_cik": "", "sec_title": "", "match_quality": "rejected",
                        "source": "manual review: name match was wrong", "retrieved": date.today().isoformat()})
            continue
        if r["sponsor"] in MANUAL and MANUAL[r["sponsor"]] in by_ticker:
            hit, q = by_ticker[MANUAL[r["sponsor"]]], "manual"
        elif n in exact:
            hit, q = exact[n], "exact"
        elif len(n) >= 6:
            cands = [(tk, cik, title) for sn, tk, cik, title in sec
                     if len(sn) >= 6 and (sn.startswith(n + " ") or n.startswith(sn + " "))]
            if len(cands) == 1:
                hit, q = cands[0], "partial"
        out.append({**r, "sec_ticker": hit[0] if hit else "ยังไม่ยืนยัน", "sec_cik": hit[1] if hit else "",
                    "sec_title": hit[2] if hit else "", "match_quality": q,
                    "source": "https://www.sec.gov/files/company_tickers.json", "retrieved": date.today().isoformat()})
    with open(os.path.join(DATA, "sponsor_tickers.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print({"sponsors": len(out), "exact": sum(o["match_quality"] == "exact" for o in out),
           "partial": sum(o["match_quality"] == "partial" for o in out)})


if __name__ == "__main__":
    main()
