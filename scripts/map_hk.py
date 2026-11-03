"""Round-1 China track: match sponsors without an SEC match to Hong Kong-listed equities (HKEX).

Sources (public):
  https://www.hkex.com.hk/eng/services/trading/securities/securitieslists/ListOfSecurities.xlsx
Reads  data/sponsor_tickers.csv, data/candidates.csv
Writes data/china_track_round1.csv

Method: compare the DISTINCTIVE words of each HKEX English short name with the sponsor name
(generic words and place names removed). All matches are 'needs_review' - HKEX short names are
abbreviated and a word can match the wrong company. A-share (Shanghai / Shenzhen) listings are NOT mapped
here (their lists have Chinese names only). Financial data is NOT fetched (HKEX annual reports are PDFs in
RMB/HKD) -> every row carries 'ต้องโหลดเอง' until a human downloads the report.
"""
import csv
import io
import os
import re
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
URL = "https://www.hkex.com.hk/eng/services/trading/securities/securitieslists/ListOfSecurities.xlsx"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
GENERIC = {"pharma", "pharmaceutical", "pharmaceuticals", "biopharma", "biopharmaceutical", "biopharmaceuticals",
           "bio", "biotech", "biotechnology", "biosciences", "biologics", "medicine", "medicines", "medical", "health",
           "healthcare", "therapeutics", "group", "holding", "holdings", "co", "ltd", "limited", "inc", "corp",
           "company", "international", "the", "and", "of", "technology", "technologies", "science", "sciences",
           "life", "intl", "gp", "hk", "pharm", "med", "bioscience", "pharmacy", "drug", "drugs", "china", "sino",
           "shanghai", "beijing", "jiangsu", "zhejiang", "guangdong", "guangzhou", "shenzhen", "sichuan", "hunan",
           "hubei", "shandong", "suzhou", "hangzhou", "wuhan", "chengdu", "tianjin", "hainan", "chongqing", "fujian",
           "anhui", "henan", "hebei", "nanjing", "xiamen", "taizhou", "hong", "kong", "global", "united", "new", "asia"}


# Manual name review 2026-11-01 (by AI from the company names only; NOT verified against HKEX filings).
# Sponsors NOT in this set were judged false matches from a shared common word (e.g. 'Corporation', 'Innovation').
ACCEPT = {
    "Akeso", "Jiangsu HengRui Medicine Co., Ltd.", "Guangdong Hengrui Pharmaceutical Co., Ltd",
    "Shanghai Hengrui Pharmaceutical Co., Ltd.", "RemeGen Co., Ltd.", "Innovent Biologics (Suzhou) Co. Ltd.",
    "Innovent Biopharmaceutical Technology (Hangzhou) Co., LTD.",
    "Innovent Biologics Technology Limited (Shanghai R&D Center)", "Hutchmed",
    "Jiangsu Simcere Pharmaceutical Co., Ltd.", "Shanghai Henlius Biotech",
    "CSPC ZhongQi Pharmaceutical Technology Co., Ltd.", "CSPC Baike (Shandong) Biopharmaceutical Co., Ltd.",
    "CSPC Mingfule Pharmaceutical (Guangzhou) Co., Ltd.", "CSPC Zhongnuo Pharmaceutical (Shijiazhuang) Co., Ltd.",
    "Luye Pharma Group Ltd.", "DualityBio Inc.", "Mabwell (Shanghai) Bioscience Co., Ltd.",
    "TransThera Sciences (Nanjing), Inc.", "Ascletis Pharma (China) Co., Limited",
    "Genfleet Therapeutics (Shanghai) Inc.", "Hansoh BioMedical R&D Company", "Lepu Biopharma Co., Ltd.",
    "SUNHO（China）BioPharmaceutical CO., Ltd.", "Shaanxi Micot Pharmaceutical Technology Co., Ltd.",
    "Suzhou Alphamab Co., Ltd.", "Cloudbreak Therapeutics, LLC",
}
UNSURE = {"Cloudbreak Therapeutics, LLC"}  # US-named subsidiary of a HK-listed group? keep but flag


def words(s):
    return [w for w in re.split(r"[^a-z0-9]+", s.lower()) if w]


def distinctive(s):
    return {w for w in words(s) if w not in GENERIC and len(w) >= 4}


def read_xlsx(blob):
    z = zipfile.ZipFile(io.BytesIO(blob))
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in sheet.iter("{%s}row" % NS["m"]):
        cells = {}
        for c in row.findall("m:c", NS):
            col = re.match(r"[A-Z]+", c.get("r")).group()
            v = c.find("m:v", NS)
            if v is None:
                t = c.find("m:is", NS)
                val = "".join(x.text or "" for x in t.iter("{%s}t" % NS["m"])) if t is not None else ""
            else:
                val = shared[int(v.text)] if c.get("t") == "s" else v.text
            cells[col] = val
        rows.append(cells)
    return rows


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        rows = read_xlsx(r.read())
    header_i = next(i for i, r in enumerate(rows) if any("Stock Code" in v for v in r.values()))
    header = rows[header_i]
    col = {v.strip(): k for k, v in header.items()}
    code_c, name_c, cat_c = col["Stock Code"], col["Name of Securities"], col["Category"]
    sub_c = col.get("Sub-Category")
    hk = []
    for r in rows[header_i + 1:]:
        if r.get(cat_c, "").strip() != "Equity":
            continue
        n = r.get(name_c, "")
        d = distinctive(n)
        if d:
            hk.append((r.get(code_c, "").zfill(5), n, d, r.get(sub_c, "") if sub_c else ""))

    with open(os.path.join(DATA, "sponsor_tickers.csv"), encoding="utf-8-sig", newline="") as f:
        spons = [s for s in csv.DictReader(f) if s["match_quality"] not in ("exact", "manual", "partial")]
    with open(os.path.join(DATA, "candidates.csv"), encoding="utf-8-sig", newline="") as f:
        cands = [c for c in csv.DictReader(f) if c["tier"].startswith("A")]
    by_sp = defaultdict(list)
    for c in cands:
        by_sp[c["sponsor"]].append(c)

    out = []
    for s in spons:
        if s["sponsor"] not in by_sp:
            continue
        sd = distinctive(s["sponsor"])
        hits = [h for h in hk if h[2] <= sd]
        if len(hits) != 1:
            continue
        code, name, _, sub = hits[0]
        drugs = sorted(by_sp[s["sponsor"]], key=lambda d: (d["fda_known_name"] == "Y", -int(d["n_trials"])))
        out.append({
            "sponsor": s["sponsor"], "hkex_code": code, "hkex_name": name, "hkex_subcategory": sub,
            "match_quality": ("rejected_false_match" if s["sponsor"] not in ACCEPT else
                              "name_match_unsure" if s["sponsor"] in UNSURE else "name_match_reviewed"),
            "n_tierA_drugs": len(drugs),
            "sample_drugs": " | ".join(d["intervention"][:40] for d in drugs[:5]),
            "financials": "ต้องโหลดเอง (รายงานประจำปี HKEXnews)",
            "where_to_download": "https://www.hkexnews.hk/index.htm (ค้นด้วยรหัสหุ้น " + code.lstrip("0") + ")",
            "source": URL, "retrieved": date.today().isoformat(),
        })
    out.sort(key=lambda r: (r["match_quality"] == "rejected_false_match", -r["n_tierA_drugs"], r["sponsor"].lower()))
    with open(os.path.join(DATA, "china_track_round1.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print({"hk_equities": len(hk), "sponsors_without_sec_with_tierA": sum(1 for s in spons if s["sponsor"] in by_sp),
           "matched_to_hkex": len(out)})


if __name__ == "__main__":
    main()
