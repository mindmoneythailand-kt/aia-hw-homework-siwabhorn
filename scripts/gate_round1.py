"""Round-1 gate (spec: 'ประตูเกณฑ์'): reduce sponsors to a shortlist of at most 30.

Gates (all must pass):
  G1  at least one Tier-A drug (Phase 3, incl. 2/3) given in an EXPERIMENTAL arm   [candidates.csv]
  G2  cash survival: runway >= 2 years [คำนวณ] OR operating cash flow of last FY > 0  [financials.csv]
  G3  SEC match quality is 'exact' or 'manual' (partial matches wait for human check)  [sponsor_tickers.csv]
Missing data fails the gate with reason 'ข้อมูลไม่พอ (ยังไม่ยืนยัน)' - it is never guessed.

Trim to <= 30: this is NOT a quality ranking. Passing sponsors are split by company size using cash_total
as a proxy (large >= 5B USD, mid 0.5-5B, small < 0.5B) and the top 10 per group are taken by number of Tier-A
experimental drugs (ties: alphabetical). That choice only keeps all sizes represented.

Writes data/gate_round1.csv (every sponsor with a Tier-A drug + pass/fail reasons)
       data/shortlist_round1.csv (<= 30 rows)
"""
import csv
import os
from collections import defaultdict
from datetime import date

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def read(name):
    with open(os.path.join(DATA, name), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    cands = [r for r in read("candidates.csv") if r["tier"].startswith("A")]
    tick = {r["sponsor"]: r for r in read("sponsor_tickers.csv")}
    fin = {r["sponsor"]: r for r in read("financials.csv")}
    by_sp = defaultdict(list)
    for r in cands:
        by_sp[r["sponsor"]].append(r)

    rows = []
    for sp, drugs in by_sp.items():
        t = tick.get(sp, {})
        f = fin.get(sp)
        fails = []
        mq = t.get("match_quality", "")
        if mq not in ("exact", "manual"):
            fails.append("G3 ยังไม่มีคู่ SEC ที่ยืนยัน" if mq != "partial" else "G3 จับคู่ชื่อแบบบางส่วน รอตรวจ")
        runway = ocf = cash = None
        if f:
            runway, ocf, cash = fnum(f["runway_years_calc"]), fnum(f["ocf_annual_usd"]), fnum(f["cash_total_usd"])
            if not ((runway is not None and runway >= 2) or (ocf is not None and ocf > 0)):
                if runway is None and ocf is None:
                    fails.append("G2 ข้อมูลไม่พอ (ยังไม่ยืนยัน)")
                else:
                    fails.append("G2 runway < 2 ปีและ OCF ไม่เป็นบวก")
        elif mq in ("exact", "manual"):
            fails.append("G2 ข้อมูลไม่พอ (ยังไม่ยืนยัน)")
        ordered = sorted(drugs, key=lambda d: (d["fda_known_name"] == "Y", -int(d["n_trials"]), d["intervention"].lower()))
        rows.append({
            "sponsor": sp, "ticker": t.get("sec_ticker", "ยังไม่ยืนยัน"), "match_quality": mq,
            "n_tierA_drugs": len(drugs), "n_tierA_fda_name_N": sum(d["fda_known_name"] == "N" for d in drugs),
            "sample_drugs": " | ".join(d["intervention"][:40] for d in ordered[:5]),
            "sample_conditions": " | ".join(sorted({c.strip() for d in ordered[:5] for c in d["conditions"].split(";") if c.strip()})[:4]),
            "cash_total_usd": f["cash_total_usd"] if f else "", "cash_end": f["cash_end"] if f else "",
            "ocf_annual_usd": f["ocf_annual_usd"] if f else "", "runway_years_calc": f["runway_years_calc"] if f else "",
            "size_group": ("large" if cash is not None and cash >= 5e9 else "mid" if cash is not None and cash >= 5e8
                           else "small" if cash is not None else ""),
            "gate_result": "ผ่าน" if not fails else "ไม่ผ่าน", "gate_reasons": "; ".join(fails),
            "source_candidates": "data/candidates.csv", "source_financials": f["source_url"] if f else "",
            "retrieved": date.today().isoformat(),
        })
    rows.sort(key=lambda r: (r["gate_result"] != "ผ่าน", -r["n_tierA_drugs"], r["sponsor"].lower()))
    cols = list(rows[0].keys())
    with open(os.path.join(DATA, "gate_round1.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    passed = [r for r in rows if r["gate_result"] == "ผ่าน"]
    short = []
    for grp in ("large", "mid", "small"):
        g = sorted((r for r in passed if r["size_group"] == grp), key=lambda r: (-r["n_tierA_drugs"], r["sponsor"].lower()))
        short += g[:10]
    with open(os.path.join(DATA, "shortlist_round1.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(short)
    reasons = defaultdict(int)
    for r in rows:
        for x in r["gate_reasons"].split("; "):
            if x:
                reasons[x] += 1
    print({"sponsors_with_tierA": len(rows), "passed": len(passed),
           "passed_by_size": {g: sum(r["size_group"] == g for r in passed) for g in ("large", "mid", "small")},
           "shortlist": len(short), "fail_reasons": dict(reasons)})


if __name__ == "__main__":
    main()
