"""Step 4 (obesity / diabetes group): market-size check against the USD 1 billion peak-sales line.

Method (kept deliberately simple and assumption-light):
  TAM (US)      = adults with obesity = prevalence x adult population            [CDC; Census via secondary site]
  Reverse sizing = patients needed for USD 1,000 million = 1,000,000,000 / net price per patient-year
                  -> as % of TAM, and as % of Zepbound's current annualized revenue (Lilly 8-K)
  Probability   = published phase success rates (BIO / Informa / QLS 2021), class averages - NOT drug specific
No penetration or market-share forecast is invented here. China / ex-US are left 'ยังไม่ยืนยัน'.

Writes data/step4_obesity_inputs.csv and data/step4_obesity_sizing.csv
"""
import csv
import os
from datetime import date

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
TODAY = date.today().isoformat()

INPUTS = [
    # id, input, value, unit, source, source_type, status
    ("I1", "US adults aged 20+ with obesity (BMI>=30), Aug 2021-Aug 2023", 0.403, "fraction", "https://www.cdc.gov/nchs/products/databriefs/db508.htm", "primary (CDC NCHS)", "ยืนยันจากหน้าต้นทาง (age-adjusted)"),
    ("I2", "US severe obesity (BMI>=40), adults 20+", 0.094, "fraction", "https://www.cdc.gov/nchs/products/databriefs/db508.htm", "primary (CDC NCHS)", "ยืนยันจากหน้าต้นทาง (age-adjusted = 9.7%)"),
    ("I3", "US resident population aged 18+, 1 Jul 2025", 269763509, "persons", "https://www.census.gov/newsroom/press-kits/2026/national-state-population-estimates.html (ตัวเลขจากเว็บรอง usahousinginformation.com / legalunitedstates.com)", "secondary", "ยังไม่ยืนยัน: ไม่พบตัวเลขในหน้า Census ที่เปิดได้; ใช้ 18+ กับอัตรา 20+ จึงคลาดเคลื่อนเล็กน้อย"),
    ("I4", "Zepbound self-pay price per month (low / mid / high tiers)", "299 / 399 / 449", "USD per month", "รายงานข่าว/บล็อกปี 2026 (เช่น weightwatchers.com, singlecare.com) อ้าง LillyDirect", "secondary", "ยังไม่ยืนยัน: เปิดหน้า LillyDirect ไม่ได้ (404) ราคาสุทธิที่บริษัทได้รับไม่ทราบ"),
    ("I5", "Eli Lilly Q3 2026 worldwide revenue: Mounjaro", 10723, "USD million", "https://www.sec.gov/Archives/edgar/data/0000059478/000005947826000104/q326lillysalesandearningsp.htm", "primary (8-K)", "ยืนยัน"),
    ("I6", "Eli Lilly Q3 2026 worldwide revenue: Zepbound", 5352, "USD million", "https://www.sec.gov/Archives/edgar/data/0000059478/000005947826000104/q326lillysalesandearningsp.htm", "primary (8-K)", "ยืนยัน"),
    ("I7", "Eli Lilly nine-month 2026 revenue: Mounjaro / Zepbound", "29328 / 14440", "USD million", "https://www.sec.gov/Archives/edgar/data/0000059478/000005947826000104/q326lillysalesandearningsp.htm", "primary (8-K)", "ยืนยัน"),
    ("I8", "Lilly Q3 2026 realized price change worldwide / outside US", "-15% / -29%", "percent", "https://www.sec.gov/Archives/edgar/data/0000059478/000005947826000104/q326lillysalesandearningsp.htm", "primary (8-K)", "ยืนยัน; ราคาที่รับรู้จริงลดลง"),
    ("I9", "Novo Nordisk H1 2026 sales: Ozempic / Wegovy injectable / Wegovy pill", "59200 / 37719 / 5474", "DKK million", "https://www.sec.gov/Archives/edgar/data/0000353278/000035327826000023/caq22026.htm", "primary (6-K)", "ยืนยัน; เป็นเงินโครนเดนมาร์ก ไม่ได้แปลงสกุลเงิน"),
    ("I10", "Phase II->III success, Metabolic / Endocrine", "45.0% / 26.6%", "percent", "https://go.bio.org/rs/490-EHZ-999/images/ClinicalDevelopmentSuccessRates2011_2020.pdf (Figure 2, PDF p.8)", "primary (BIO/Informa/QLS, Feb 2021)", "ยืนยันจากตาราง; ข้อมูลปี 2011-2020"),
    ("I11", "Phase III->NDA/BLA, Metabolic / Endocrine", "63.6% / 66.2%", "percent", "same, Figure 2", "primary (BIO/Informa/QLS)", "ยืนยันจากตาราง"),
    ("I12", "NDA/BLA->Approval, Metabolic / Endocrine", "87.5% / 86.3%", "percent", "same, Figure 2", "primary (BIO/Informa/QLS)", "ยืนยันจากตาราง"),
    ("I13", "China adult obesity prevalence", "", "", "ไม่พบตัวเลขที่ยืนยันได้ในการค้นหารอบนี้", "-", "ยังไม่ยืนยัน (เกณฑ์ BMI ของจีน >=28 ต่างจากสากล >=30)"),
    ("I14", "China net price per patient-year of GLP-1 (NRDL)", "", "", "Lilly 8-K ระบุว่า Mounjaro เข้า NRDL ไตรมาส 1/2026 และราคาที่รับรู้นอกสหรัฐลด 29% แต่ไม่ระบุราคา", "-", "ยังไม่ยืนยัน"),
]


def main():
    pop, prev = 269763509, 0.403
    tam = pop * prev
    sev = pop * 0.094
    rows = []
    prices = {"low": 299 * 12, "base": 399 * 12, "high": 449 * 12}
    zep_ann = 5352 * 4  # USD million, Q3 x4 (annualized run-rate, not a forecast)
    tirz_ann = (10723 + 5352) * 4
    for k, p in prices.items():
        pts = 1_000_000_000 / p
        rows.append({"scenario": f"net price per patient-year = {k}", "price_usd_per_patient_year": p,
                     "patients_needed_for_USD_1bn": round(pts), "pct_of_US_obesity_population_TAM": round(100 * pts / tam, 3),
                     "pct_of_US_severe_obesity_population": round(100 * pts / sev, 3),
                     "implied_zepbound_annualized_patients_at_this_price": round(zep_ann * 1e6 / p),
                     "formula_note": "[คำนวณ] 1,000,000,000 / price; TAM = 269,763,509 x 40.3%; Zepbound annualized = Q3 x 4 (USD 21,408 m), สมมติว่าราคาเท่ากันทั้งหมด"})
    summary = {
        "US_obesity_population_TAM": round(tam), "US_severe_obesity_population": round(sev),
        "USD_1bn_as_pct_of_Zepbound_annualized_Q3x4": round(100 * 1000 / zep_ann, 2),
        "USD_1bn_as_pct_of_tirzepatide_annualized_Q3x4": round(100 * 1000 / tirz_ann, 2),
        "PoS_from_phase3_metabolic": round(0.636 * 0.875, 4), "PoS_from_phase3_endocrine": round(0.662 * 0.863, 4),
    }
    with open(os.path.join(DATA, "step4_obesity_inputs.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "input", "value", "unit", "source", "source_type", "status", "retrieved"])
        for r in INPUTS:
            w.writerow(list(r) + [TODAY])
    with open(os.path.join(DATA, "step4_obesity_sizing.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(summary)
    for r in rows:
        print(r["scenario"], r["patients_needed_for_USD_1bn"], r["pct_of_US_obesity_population_TAM"], r["implied_zepbound_annualized_patients_at_this_price"])


if __name__ == "__main__":
    main()
