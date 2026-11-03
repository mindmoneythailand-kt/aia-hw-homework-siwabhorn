"""Round-1 China track: download latest Annual Report (FY2025) and Interim Report (H1 2026) from HKEXnews.

Source (public, official): https://www1.hkexnews.hk/search/titlesearch.xhtml
Reads  data/china_track_round1.csv  (rows not 'rejected_false_match')
Writes data/raw/hk/<code>/YYYY-MM-DD_AR_FY2025.pdf , ..._IR_H1-2026.pdf   (data/raw/ is git-ignored)
       data/hk_reports_index.csv    (what was found / downloaded / missing, with source URLs)

Rules: one request at a time with a pause; English documents only; if nothing is found the row says
'ไม่พบ - ต้องโหลดเอง' (never guessed). Downloads are checked to start with %PDF.
"""
import csv
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import date

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
REF = "https://www1.hkexnews.hk/search/titlesearch.xhtml"
BASE = "https://www1.hkexnews.hk"
KINDS = [("AR", "40100", re.compile(r"annual report", re.I), re.compile(r"2025"), "FY2025"),
         ("IR", "40200", re.compile(r"interim report", re.I), re.compile(r"2026"), "H1-2026")]


def http(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": REF})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
                return data if binary else data.decode("utf-8")
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))


def search(stock_id, t2code):
    q = {"sortDir": "0", "sortByOptions": "DateTime", "category": "0", "market": "SEHK", "stockId": stock_id,
         "documentType": "-1", "fromDate": "20250101", "toDate": date.today().strftime("%Y%m%d"), "title": "",
         "searchType": "0", "t1code": "40000", "t2Gcode": "-2", "t2code": t2code, "rowRange": "50", "lang": "EN"}
    raw = json.loads(http(BASE + "/search/titleSearchServlet.do?" + urllib.parse.urlencode(q)))
    return json.loads(raw["result"]) if raw.get("result") else []


def main():
    active = json.loads(http("https://www.hkexnews.hk/ncms/script/eds/activestock_sehk_e.json"))
    sid = {a["c"]: a["i"] for a in active}
    with open(os.path.join(DATA, "china_track_round1.csv"), encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["match_quality"] != "rejected_false_match"]
    companies = {}
    for r in rows:
        companies.setdefault(r["hkex_code"], r["hkex_name"])
    out = []
    for code, name in sorted(companies.items()):
        for kind, t2, name_re, year_re, label in KINDS:
            rec = {"hkex_code": code, "hkex_name": name, "kind": kind, "title": "", "published": "", "url": "",
                   "local_file": "", "bytes": "", "status": "", "retrieved": date.today().isoformat()}
            try:
                hits = [h for h in search(sid[code], t2)
                        if name_re.search(h["TITLE"]) and year_re.search(h["TITLE"]) and h["FILE_LINK"].lower().endswith(".pdf")]
                if kind == "IR":
                    hits = [h for h in hits if h["DATE_TIME"][3:5] >= "07" and h["DATE_TIME"][6:10] == "2026"]
                hits.sort(key=lambda h: (h["DATE_TIME"][6:10], h["DATE_TIME"][3:5], h["DATE_TIME"][0:2]))
                if not hits:
                    rec["status"] = "ไม่พบ - ต้องโหลดเอง"
                else:
                    h = hits[-1] if kind == "IR" else hits[0]
                    d = h["DATE_TIME"][:10]
                    iso = f"{d[6:10]}-{d[3:5]}-{d[0:2]}"
                    folder = os.path.join(DATA, "raw", "hk", code)
                    os.makedirs(folder, exist_ok=True)
                    path = os.path.join(folder, f"{iso}_{kind}_{label}.pdf")
                    rec.update(title=h["TITLE"], published=iso, url=BASE + h["FILE_LINK"])
                    if os.path.exists(path):
                        rec["status"] = "มีอยู่แล้ว (ไม่เขียนทับ)"
                    else:
                        blob = http(rec["url"], binary=True)
                        if blob[:4] != b"%PDF":
                            rec["status"] = "ดึงแล้วไม่ใช่ PDF - ต้องโหลดเอง"
                        else:
                            with open(path, "wb") as fh:
                                fh.write(blob)
                            rec["status"] = "ดาวน์โหลดแล้ว"
                    rec["local_file"] = os.path.relpath(path, os.path.join(DATA, ".."))
                    rec["bytes"] = os.path.getsize(path) if os.path.exists(path) else ""
            except Exception as ex:
                rec["status"] = f"ล้มเหลว {type(ex).__name__} - ต้องโหลดเอง"
            out.append(rec)
            print(code, name, kind, rec["status"], rec["title"], flush=True)
            time.sleep(2)
    with open(os.path.join(DATA, "hk_reports_index.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)


if __name__ == "__main__":
    main()
