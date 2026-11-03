"""Round-1 universe: SEC shortlist (30) + HKEX companies that passed G2 (15) = 45 companies.

Reads  data/shortlist_round1.csv, data/financials_hk.csv, data/china_track_round1.csv
Writes data/round1_universe.csv   (one row per company; 'sponsors' = names used in ClinicalTrials.gov)
"""
import csv
import os
from collections import defaultdict
from datetime import date

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def read(n):
    with open(os.path.join(DATA, n), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    rows = []
    for r in read("shortlist_round1.csv"):
        rows.append({"market": "US (SEC)", "ticker_or_code": r["ticker"], "company": r["sponsor"],
                     "sponsors_ctgov": r["sponsor"], "n_tierA_drugs": r["n_tierA_drugs"],
                     "size_group": r["size_group"], "G2_basis": f"runway={r['runway_years_calc'] or '-'} ocf_fy={r['ocf_annual_usd'] or '-'} USD",
                     "name_match": r["match_quality"], "source": "data/shortlist_round1.csv"})
    sp = defaultdict(list)
    for r in read("china_track_round1.csv"):
        if r["match_quality"] != "rejected_false_match":
            sp[r["hkex_code"]].append(r["sponsor"])
    for r in read("financials_hk.csv"):
        if not r["G2"].startswith("ผ่าน"):
            continue
        rows.append({"market": "HK (HKEX)", "ticker_or_code": r["hkex_code"], "company": r["hkex_name"],
                     "sponsors_ctgov": " ;; ".join(sp[r["hkex_code"]]), "n_tierA_drugs": r["n_tierA_drugs"],
                     "size_group": "", "G2_basis": r["G2"] + f" [{r['currency_unit']}]",
                     "name_match": "name_match_reviewed (ยังไม่ยืนยันกับ HKEX)", "source": "data/financials_hk.csv"})
    for r in rows:
        r["retrieved"] = date.today().isoformat()
    with open(os.path.join(DATA, "round1_universe.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print({"companies": len(rows), "US": sum(r["market"].startswith("US") for r in rows),
           "HK": sum(r["market"].startswith("HK") for r in rows)})


if __name__ == "__main__":
    main()
