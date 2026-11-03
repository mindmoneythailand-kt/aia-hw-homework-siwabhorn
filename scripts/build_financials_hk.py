"""Round-1 China track: gate G2 (cash survival) from HKEX reports.

Values below were READ from data/hk_candidate_lines.csv (text of the PDFs; page numbers = PDF pages) and
5 of them (Akeso, HUTCHMED, TransThera, Alphamab, Akeso OCF) were spot-checked against the page text.
They are NOT converted to USD: runway is a ratio inside one currency, so no FX is needed.

cash_total = cash and cash equivalents (or 'cash and bank balances') + time deposits (>3 months).
             Pledged / restricted cash and FVTPL financial assets are EXCLUDED (conservative).
ocf_fy2025 = net cash from operating activities, first column of the FY2025 annual report.
runway_years = cash_total / -ocf_fy2025 when OCF < 0   [คำนวณ]
G2 passes when runway >= 2 years or FY2025 OCF > 0 (same rule as the SEC track).
Missing items stay empty with 'ยังไม่ยืนยัน'. 'ต้องยืนยันกับ PDF' = read from text, not yet checked visually.
"""
import csv
import os
from datetime import date

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
AR = "AR_FY2025"
IR = "IR_H1-2026"

# code, name, unit, cash, cash_date, cash_basis, cash_src, ocf_fy2025, ocf_src, ocf_h1_2026, note
ROWS = [
    ("00013", "HUTCHMED", "US$'000", 1374817, "2026-06-30", "cash+short-term investments (company total)", f"{IR} p13", -64657, f"{AR} p148 (cols 2025/2024/2023)", 12223, "H1-2026 OCF เป็นบวก"),
    ("01093", "CSPC PHARMA", "RMB'000", 10001506, "2026-06-30", "bank deposits, balances and cash", f"{IR} p34", 5831641, f"{AR} p92", 10889512, ""),
    ("01276", "HENGRUI PHARMA", "RMB'000", 38721633, "2026-06-30", "cash and bank balances", f"{IR} p53", 11235378, f"{AR} p115", 1987004, ""),
    ("01672", "ASCLETIS-B", "RMB'000", 593371 + 1616939, "2026-06-30", "cash 593,371 + time deposits>3m 1,616,939", f"{IR} p43", -416776, f"{AR} p25", -327349, "OCF ครึ่งแรก 2026 ติดลบ 327,349 (ครึ่งปีเดียว) runway จริงอาจสั้นกว่า"),
    ("01801", "INNOVENT BIO", "RMB'000", "", "", "", "ไม่พบบรรทัดเงินสดรวมในข้อความ", 10001012, f"{AR} p117", 3588344, "OCF บวกแรง ผ่าน G2 โดยไม่ต้องใช้เงินสด (เงินสดยังไม่ยืนยัน)"),
    ("02096", "SIMCERE PHARMA", "RMB'000", "", "", "", "ยังไม่รวมยอดเงินสดรวม", 2013530, f"{AR} p124", 1605160, "เงินสดยังไม่ยืนยัน"),
    ("02157", "LEPU BIO", "RMB'000", 684568, "2026-06-30", "cash and cash equivalents (ไม่พบ time deposits)", f"{IR} p33", -12229, f"{AR} p172", -100321, "OCF ครึ่งแรก 2026 ติดลบ 100,321 (ครึ่งปีเดียว) runway จริงอาจสั้นกว่า"),
    ("02186", "LUYE PHARMA", "RMB'000", "", "", "", "", 1783155, f"{AR} p74", 441419, "เงินสดยังไม่ยืนยัน"),
    ("02335", "MICOT PHARMA-B", "RMB'000", "", "", "", "", "", "ไม่มีรายงานประจำปี", "", "ไม่มีข้อมูลพอ (ไม่พบบรรทัด OCF/เงินสด)"),
    ("02493", "MABWELL-B", "RMB'000", 2226259, "2026-06-30", "cash and bank balances", f"{IR} p54", "", "ไม่มีรายงานประจำปี", -508938, "ไม่มี AR: ครึ่งแรก 2026 OCF ติดลบ 508,938 ถ้าคูณ 2 [คำนวณ] runway ราว 2.2 ปี ใช้แทนรายปีไม่ได้"),
    ("02592", "CLOUDBREAK-B", "US$'000", 40150, "2025-12-31", "cash and cash equivalents", f"{AR} p141", "", "ไม่พบบรรทัด OCF ในข้อความ", "", "ไม่มีรายงานกลางปี 2026"),
    ("02595", "GENFLEET-B", "RMB'000", 1197440 + 877221, "2025-12-31", "cash 1,197,440 + time deposits 877,221", f"{AR} p143", -135702, f"{AR} p146", -283682, "OCF ครึ่งแรก 2026 ติดลบ 283,682 (เร็วกว่าปี 2025) เงินสด ณ กลางปี 2026 ยังไม่ได้อ่าน"),
    ("02617", "TRANSTHERA-B", "RMB'000", 415408 + 73729, "2025-12-31", "cash 415,408 + time deposits>3m 73,729", f"{AR} p74", -253511, f"{AR} p77", -106332, "เงินสด ณ กลางปี 2026 ยังไม่ได้อ่าน"),
    ("02696", "HENLIUS", "RMB'000", 818383, "2026-06-30", "cash and bank balances", f"{IR} p50", 1305620, f"{AR} p112", 559410, ""),
    ("02898", "SUNHO BIO-B", "RMB'000", "", "", "", "", "", "", "", "ไม่มีรายงานปี 2025/2026 ใน HKEXnews"),
    ("03692", "HANSOH PHARMA", "RMB'000", 31548668, "2025-12-31", "cash and bank balances", f"{AR} p85", 6738246, f"{AR} p88", 2337103, ""),
    ("09606", "DUALITYBIO-B", "RMB'000", 1276399 + 1998421, "2025-12-31", "cash 1,276,399 + term deposits>3m 1,998,421", f"{AR} p129", 194583, f"{AR} p56", -423702, "OCF ปี 2025 บวก แต่ครึ่งแรก 2026 ติดลบ 423,702"),
    ("09926", "AKESO", "RMB'000", 8822414, "2025-12-31", "cash and bank balances", f"{AR} p122", -947628, f"{AR} p126", 290277, "ครึ่งแรก 2026 OCF กลับเป็นบวก"),
    ("09966", "ALPHAMAB-B", "RMB'000", 258819 + 1091500, "2025-12-31", "cash 258,819 + time deposits>3m 1,091,500", f"{AR} p111", -121889, f"{AR} p115", -61184, ""),
    ("09995", "REMEGEN", "RMB'000", "", "", "", "", 52342, f"{AR} p114", 4213823, "OCF ปี 2025 บวกเล็กน้อย 52,342 (ปี 2024 ติดลบ 1,176,596) เงินสดยังไม่ยืนยัน"),
]


def main():
    tiers = {}
    with open(os.path.join(DATA, "china_track_round1.csv"), encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["match_quality"] != "rejected_false_match":
                tiers[r["hkex_code"]] = tiers.get(r["hkex_code"], 0) + int(r["n_tierA_drugs"])
    out = []
    for code, name, unit, cash, cdate, cbasis, csrc, ocf, osrc, ocf_h1, note in ROWS:
        runway = ""
        if cash != "" and ocf != "" and ocf < 0:
            runway = round(cash / -ocf, 2)
        if ocf != "" and ocf > 0:
            g2 = "ผ่าน (OCF ปี 2025 > 0)"
        elif runway != "":
            g2 = "ผ่าน (runway >= 2 ปี)" if runway >= 2 else "ไม่ผ่าน (runway < 2 ปี)"
        else:
            g2 = "ข้อมูลไม่พอ (ยังไม่ยืนยัน)"
        out.append({"hkex_code": code, "hkex_name": name, "currency_unit": unit, "n_tierA_drugs": tiers.get(code, ""),
                    "cash_total": cash, "cash_date": cdate, "cash_basis": cbasis, "cash_source": csrc,
                    "ocf_fy2025": ocf, "ocf_source": osrc, "ocf_h1_2026": ocf_h1,
                    "runway_years_calc": runway, "G2": g2, "note": note,
                    "status": "ต้องยืนยันกับ PDF", "retrieved": date.today().isoformat(),
                    "source_index": "data/hk_reports_index.csv"})
    with open(os.path.join(DATA, "financials_hk.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    from collections import Counter
    print(Counter(o["G2"] for o in out))


if __name__ == "__main__":
    main()
