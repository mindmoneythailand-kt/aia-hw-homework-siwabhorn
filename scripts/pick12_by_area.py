"""Round-1 step 3c: pick 3 drugs in each of 4 chosen disease areas (= 12) with a transparent rule,
and record how approval status was checked.

Areas chosen by the user (2026-11-02): Oncology, Obesity / diabetes / metabolic, Neurology / psychiatry,
Immunology / inflammation.

Per area, in order (skipping drugs verified as ALREADY APPROVED, see VERIFIED_APPROVED):
  R1  eligible drug with the largest total planned enrollment
  R2  largest-enrollment eligible drug from a China / HK-listed company (if the area has one)
  R3  next largest-enrollment eligible drug from a company not yet picked in this area
'Eligible' = >= 1 Phase 3 trial in the window, no openFDA label found, not on the small old-molecule list.
This rule is about COVERAGE and DATA AVAILABILITY. It is NOT a ranking of blockbuster potential.

Approval checks:
  - every pick is looked up on DailyMed (US labels incl. biologics, NLM): https://dailymed.nlm.nih.gov
  - China approvals are NOT checked against NMPA. For HK-listed companies the company's own FY2025 annual
    report was searched; hits are recorded in VERIFIED_APPROVED with the PDF page.
Writes data/deepdive_12.csv and data/approval_checks_round1.csv
"""
import csv
import importlib.util
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
spec = importlib.util.spec_from_file_location("areas", os.path.join(os.path.dirname(os.path.abspath(__file__)), "areas_and_pick12.py"))
areas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(areas)

CHOSEN = ["Oncology", "Obesity / diabetes / metabolic", "Neurology / psychiatry", "Immunology / inflammation"]
DM = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name="
VERIFIED_APPROVED = {
    "KarXT": ("US", "DailyMed label COBENFY (xanomeline and trospium chloride)", DM + "xanomeline"),
    "efgartigimod": ("US", "DailyMed labels VYVGART and VYVGART HYTRULO", DM + "efgartigimod"),
    "AK112": ("China (+US BLA filed by partner)", "Akeso AR FY2025 p14: ivonescimab has two approved indications in China; p10: BLA submitted by Summit", "data/raw/hk/09926/2026-04-29_AR_FY2025.pdf"),
    "SHR-A1811": ("China", "Hengrui AR FY2025 p80: NMPA approval, new indication of trastuzumab rezetecan", "data/raw/hk/01276/2026-03-26_AR_FY2025.pdf"),
}


def dailymed(name):
    url = DM + urllib.parse.quote(name)
    req = urllib.request.Request(url, headers={"User-Agent": "aia-homework-research (student project)"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            d = json.loads(r.read().decode("utf-8"))
        n = d["metadata"]["total_elements"]
        t = d["data"][0]["title"][:80] if d.get("data") else ""
        return n, t, url
    except Exception as ex:
        return "ตรวจไม่สำเร็จ", type(ex).__name__, url


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def main():
    with open(os.path.join(DATA, "drug_facts_round1.csv"), encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["area"] = areas.area_of(r["conditions"])
        r["eligible"] = int(r["n_phase3_trials"] or 0) >= 1 and r["openfda_label"] != "พบฉลาก" and not areas.OLD.search(r["drug_clean"])
    verified = lambda r: any(r["drug_clean"].lower().startswith(k.lower()) for k in VERIFIED_APPROVED)
    picks, excluded = [], []
    for a in CHOSEN:
        pool = sorted((r for r in rows if r["area"] == a and r["eligible"]), key=lambda r: -num(r["total_planned_enrollment"]))
        for r in pool:
            if verified(r):
                excluded.append(r)
        pool = [r for r in pool if not verified(r)]
        chosen = []

        def take(r, rule):
            r = dict(r)
            r["rule"] = rule
            chosen.append(r)

        if pool:
            take(pool[0], "R1 ใหญ่สุดในกลุ่ม")
        hk = [r for r in pool if r["market"].startswith("HK") and r["company"] not in {c["company"] for c in chosen}]
        if hk:
            take(hk[0], "R2 ใหญ่สุดจากบริษัทจีน/HK")
        for r in pool:
            if len(chosen) >= 3:
                break
            if r["company"] not in {c["company"] for c in chosen}:
                take(r, "R3 ถัดไป คนละบริษัท")
        for c in chosen:
            c["area"] = a
        picks += chosen
    out, checks = [], []
    for p in picks:
        n, title, url = dailymed(p["drug_clean"])
        time.sleep(0.5)
        out.append({"area": p["area"], "rule": p["rule"], "market": p["market"], "ticker_or_code": p["ticker_or_code"],
                    "company": p["company"], "drug": p["drug"], "conditions": p["conditions"], "n_phase3_trials": p["n_phase3_trials"],
                    "total_planned_enrollment": p["total_planned_enrollment"], "competition_n_phase3_trials": p["competition_n_phase3_trials"],
                    "dailymed_labels_found": n, "approval_note": "ยังไม่ได้ตรวจ NMPA/ตลาดอื่น" if p["market"].startswith("HK") else "ยังไม่ได้ตรวจตลาดนอกสหรัฐ",
                    "ct_source": p["ct_source"], "retrieved": date.today().isoformat()})
        checks.append({"drug": p["drug"], "company": p["company"], "check": "DailyMed (US labels)", "result": f"labels={n} {title}", "source": url})
    for e in excluded:
        k = next(k for k in VERIFIED_APPROVED if e["drug_clean"].lower().startswith(k.lower()))
        mk, note, src = VERIFIED_APPROVED[k]
        checks.append({"drug": e["drug"], "company": e["company"], "check": "ตัดออก: อนุมัติแล้ว (" + mk + ")", "result": note, "source": src})
    with open(os.path.join(DATA, "deepdive_12.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    with open(os.path.join(DATA, "approval_checks_round1.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(checks[0].keys()))
        w.writeheader()
        w.writerows(checks)
    for o in out:
        print(f'{o["area"][:12]:12} | {o["rule"][:26]:26} | {o["ticker_or_code"]:6} {o["company"][:22]:22} | {o["drug"][:26]:26} | enr={o["total_planned_enrollment"]:>6} | DailyMed={o["dailymed_labels_found"]}')
    print("EXCLUDED (verified approved):", [e["drug"] for e in excluded])


if __name__ == "__main__":
    main()
