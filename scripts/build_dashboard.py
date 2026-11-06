"""Build output/dashboard.html (one self-contained page, no external libraries) from the CSV files in data/.

Reads  data/deepdive_12.csv, data/approval_checks_round1.csv, data/screen_meta.json, data/candidates.csv,
       data/candidate_sponsors.csv, data/gate_round1.csv, data/shortlist_round1.csv, data/financials_hk.csv,
       data/round1_universe.csv, data/drug_facts_round1.csv, data/step4_obesity_sizing.csv
Template scripts/dashboard_template.html  ->  output/dashboard.html

Everything shown on the page is either read from a CSV or typed below with its source. Nothing is invented:
numbers typed here are the ones already written (with sources) in output/step4_*.md and checked by
scripts/verify_step4.py.
"""
import csv
import json
import os
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "output", "dashboard.html")


def read(name):
    with open(os.path.join(DATA, name), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ---- typed inputs (source in comment; same values as output/step4_*.md) ----
AREA_TH = {"Oncology": "มะเร็ง", "Obesity / diabetes / metabolic": "อ้วน/เบาหวาน",
           "Neurology / psychiatry": "ประสาท/จิตเวช", "Immunology / inflammation": "ภูมิคุ้มกัน/อักเสบ"}
# BIO/Informa/QLS Feb 2021, Figure 2 (PDF p.8): P(III->NDA) x P(NDA->approval). Class averages 2011-2020.
POS = {"Oncology": ("Oncology", 47.7, 92.0), "Obesity / diabetes / metabolic": ("Metabolic", 63.6, 87.5),
       "Neurology / psychiatry": ("Psychiatry", 56.3, 91.2), "Immunology / inflammation": ("Autoimmune", 65.3, 94.1)}
# benchmark drug used to size the USD 1 bn line, per area (see output/step4_*.md)
BENCH = {
    "Obesity / diabetes / metabolic": {"name": "Zepbound", "annual_usd_m": 5352 * 4, "basis": "ไตรมาส 3 ปี 2026 × 4", "src": "Eli Lilly 8-K ไตรมาส 3 ปี 2026", "kind": "pct"},
    "Oncology": {"name": "KEYTRUDA (รวม Qlex)", "annual_usd_m": (7771 + 830) * 4, "basis": "ไตรมาส 3 ปี 2026 × 4", "src": "Merck 8-K ไตรมาส 3 ปี 2026", "kind": "pct"},
    "Immunology / inflammation": {"name": "Dupixent", "annual_usd_m": 6540.5 * 4, "basis": "ไตรมาส 3 ปี 2026 × 4", "src": "Regeneron 8-K ไตรมาส 3 ปี 2026", "kind": "pct"},
    "Neurology / psychiatry": {"name": "Cobenfy", "annual_usd_m": 63 * 4, "basis": "ไตรมาส 2 ปี 2026 × 4", "src": "ผลค้นหาสรุปผลประกอบการ BMS (แหล่งรอง)", "kind": "mult"},
}
EVIDENCE = {
    "Maridebart cafraglutide": ("ระยะ 2: น้ำหนักลด 12.3–16.2% ที่ 52 สัปดาห์ (ตามที่ได้รับยา) ฉีดเดือนละครั้ง", "แหล่งรอง (รายงานข่าวอ้าง Amgen/NEJM)"),
    "Elecoglipron": ("ระยะ 2: น้ำหนักลด ≈10.5% ที่ 26 สัปดาห์ (75 มก.) เทียบยาหลอก 0.6%", "แหล่งรอง (รายงานข่าวอ้าง AZ/Lancet)"),
    "ASC30": ("ระยะ 2 (13 สัปดาห์): ลดสุทธิเทียบยาหลอก 5.4–7.7% ที่ 20–60 มก. (n=125)", "รายงานประจำปี Ascletis 2025 หน้า 9 (คำกล่าวบริษัท)"),
    "Povorcitinib": ("ระยะ 3 ผ่านเป้าหมายหลัก HiSCR50 สัปดาห์ 12: ยา 40–42% เทียบยาหลอก 29–30%", "บทความ Nature Medicine ก.ค. 2026 · NDA: ตามรายงานบริษัทผ่านผลค้นหา"),
}
STAGE = {"Povorcitinib": "ขออนุมัติแล้ว (FDA รับ NDA ไตรมาส 1 ปี 2026 ตามรายงานบริษัท)"}
NSOURCES = [
    ("ClinicalTrials.gov API v2", "https://clinicaltrials.gov/data-api/api"),
    ("SEC EDGAR / data.sec.gov", "https://www.sec.gov/edgar"),
    ("HKEXnews", "https://www.hkexnews.hk"),
    ("openFDA / DailyMed (US labels)", "https://dailymed.nlm.nih.gov"),
    ("BIO/Informa/QLS: Clinical Development Success Rates 2011-2020", "https://go.bio.org/rs/490-EHZ-999/images/ClinicalDevelopmentSuccessRates2011_2020.pdf"),
    ("CDC NCHS Data Brief 508 (US obesity)", "https://www.cdc.gov/nchs/products/databriefs/db508.htm"),
    ("NIMH: major depression statistics", "https://www.nimh.nih.gov/health/statistics/major-depression"),
    ("Eli Lilly 8-K Q3 2026", "https://www.sec.gov/Archives/edgar/data/0000059478/000005947826000104/q326lillysalesandearningsp.htm"),
    ("Merck 8-K Q3 2026", "https://www.sec.gov/Archives/edgar/data/0000310158/000110465926119825/tm2628203d1_ex99-2.htm"),
    ("Regeneron 8-K Q3 2026 (Dupixent)", "https://www.sec.gov/Archives/edgar/data/0000872589/000087258926000032/exhibit991q32026.htm"),
    ("Povorcitinib STOP-HS1/2, Nature Medicine 2026", "https://www.nature.com/articles/s41591-026-04534-z"),
]
GAPS = [
    "ตลาดจีนทั้งหมด: ความชุกโรค ราคาหลังเข้าบัญชียาแห่งชาติ (NRDL) สถานะ NMPA",
    "ราคาสุทธิต่อผู้ป่วย (ใช้ได้เฉพาะกลุ่มอ้วน จากราคาจ่ายเงินสดแหล่งรอง)",
    "สัดส่วนผู้ป่วยที่เข้าเกณฑ์ของยามะเร็งและภูมิคุ้มกัน → ย้อนคำนวณจำนวนผู้ป่วยไม่ได้",
    "สิทธิบัตรและวันหมดสิทธิ์ผูกขาดของทั้ง 12 ยา",
    "ผลระยะ 2 ต้นฉบับของยาอ้วน (ใช้รายงานข่าว) · ผลระยะ 3 ของ Volrustomig (ฉบับปอด) และ SHR-1819",
    "ตัวเลข Cobenfy และ Bimzelx มาจากแหล่งรอง ยังไม่ได้เปิดเอกสารต้นทาง",
]


def main():
    d12 = read("deepdive_12.csv")
    sizing = read("step4_obesity_sizing.csv")
    meta = json.load(open(os.path.join(DATA, "screen_meta.json"), encoding="utf-8"))
    cand = read("candidates.csv")
    spons = read("candidate_sponsors.csv")
    gate = read("gate_round1.csv")
    short = read("shortlist_round1.csv")
    hk = read("financials_hk.csv")
    uni = read("round1_universe.csv")
    facts = read("drug_facts_round1.csv")
    appr = {r["drug"]: r for r in read("approval_checks_round1.csv") if r["check"].startswith("ตัดออก")}

    funnel = [
        ("การทดลองระยะ 2-3 ของบริษัทยา ที่ยังดำเนินอยู่ (ClinicalTrials.gov)", meta["unique_trials"], "data/screen_meta.json"),
        ("แถว บริษัท × ยา (เฉพาะยาในแขนทดลอง)", len(cand), "data/candidates.csv"),
        ("บริษัทผู้ให้ทุน", len(spons), "data/candidate_sponsors.csv"),
        ("…ที่มียาระยะ 3 (ประเมินประตู G1-G3)", len(gate), "data/gate_round1.csv"),
        ("…ผ่านทั้ง 3 ประตู (ฝั่ง SEC)", sum(g["gate_result"] == "ผ่าน" for g in gate), "data/gate_round1.csv"),
        ("รายชื่อรอบแรก: SEC 30 + HK 15", len(uni), "data/round1_universe.csv"),
        ("ยาหลัก (ไม่เกิน 2 ตัวต่อบริษัท)", len(facts), "data/drug_facts_round1.csv"),
        ("ยาที่ลงลึกขั้น 4 (4 กลุ่มโรค × 3)", len(d12), "data/deepdive_12.csv"),
    ]
    pos_rows = []
    for area, (label, p3, ap) in POS.items():
        pos_rows.append({"area": area, "area_th": AREA_TH[area], "bio_group": label, "p3_to_nda": p3, "nda_to_approval": ap,
                         "p3_to_approval": round(p3 * ap / 100 + 1e-9, 1)})  # half-up, same as the .md files
    bench = []
    for area, b in BENCH.items():
        if b["kind"] == "pct":
            val = round(100 * 1000 / b["annual_usd_m"], 2)
        else:
            val = round(1000 / b["annual_usd_m"], 2)
        bench.append({"area": area, "area_th": AREA_TH[area], **b, "value": val, "annual_usd_m": round(b["annual_usd_m"])})

    drugs = []
    for r in d12:
        key = next((k for k in EVIDENCE if r["drug"].lower().startswith(k.lower())), None)
        stage = next((v for k, v in STAGE.items() if r["drug"].lower().startswith(k.lower())), "ระยะ 3")
        pos = next(p for p in pos_rows if p["area"] == r["area"])
        pos_v = 94.1 if stage.startswith("ขออนุมัติ") else pos["p3_to_approval"]
        drugs.append({
            "area": r["area"], "area_th": AREA_TH[r["area"]], "rule": r["rule"], "market": r["market"],
            "ticker": r["ticker_or_code"], "company": r["company"], "drug": r["drug"].split("(")[0].strip(),
            "conditions": r["conditions"], "n_p3": int(r["n_phase3_trials"]), "enrollment": int(float(r["total_planned_enrollment"])),
            "competition": int(float(r["competition_n_phase3_trials"])) if r["competition_n_phase3_trials"] else None,
            "dailymed": r["dailymed_labels_found"], "approval_note": r["approval_note"], "ct_source": r["ct_source"],
            "stage": stage, "pos_pct": pos_v,
            "pos_basis": ("Autoimmune ยื่นขอ→อนุมัติ 94.1%" if stage.startswith("ขออนุมัติ") else f"{pos['bio_group']} ระยะ 3→ยื่นขอ {pos['p3_to_nda']}% × ยื่นขอ→อนุมัติ {pos['nda_to_approval']}%"),
            "evidence": EVIDENCE[key][0] if key else "ยังไม่พบผลทดลองที่เผยแพร่จากการค้นหารอบนี้", "evidence_src": EVIDENCE[key][1] if key else "-",
        })
    excluded = [{"drug": k, "why": v["check"], "result": v["result"]} for k, v in appr.items()]
    payload = {"generated": date.today().isoformat(), "funnel": funnel, "drugs": drugs, "pos": pos_rows, "bench": bench,
               "excluded": excluded, "gaps": GAPS, "sources": NSOURCES,
               "sizing": [{k: r[k] for k in ("scenario", "price_usd_per_patient_year", "patients_needed_for_USD_1bn", "pct_of_US_obesity_population_TAM")} for r in sizing]}
    html = open(os.path.join(HERE, "dashboard_template.html"), encoding="utf-8").read()
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = html.replace("/*__DATA__*/null", blob)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print("wrote", os.path.abspath(OUT), len(html), "bytes;", len(drugs), "drugs;", len(funnel), "funnel steps")


if __name__ == "__main__":
    main()
