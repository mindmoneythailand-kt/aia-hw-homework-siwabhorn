"""Round-1 step 2b: cash and operating cash flow for SEC-mapped sponsors (survival gate input).

Reads  data/sponsor_tickers.csv
Needs  env SEC_CONTACT (never written to any file)
Writes data/financials.csv   (values only; raw companyfacts JSON is NOT kept)

Method (all numbers are as reported in XBRL; derived ones are marked):
  cash_total      = latest 'CashCashEquivalentsAndShortTermInvestments' if reported, else
                    CashAndCashEquivalents + max(short-term investment tags) on the same end date
  ocf_annual      = latest fiscal-year (350-380 day) NetCashProvidedByUsedInOperatingActivities
  runway_years    = cash_total / -ocf_annual when ocf_annual < 0   [คำนวณ]
Gaps: foreign private issuers (20-F / IFRS) may lack us-gaap tags -> empty + 'ยังไม่ยืนยัน'.
Cash excludes long-term investments and committed financing. Runway is a rough screen, NOT a forecast.
"""
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
CASH_COMBINED = ["CashCashEquivalentsAndShortTermInvestments"]
CASH = ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "CashAndCashEquivalents"]
STI = ["MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesCurrent", "ShortTermInvestments",
       "AvailableForSaleSecuritiesCurrent"]
OCF = ["NetCashProvidedByUsedInOperatingActivities", "CashFlowsFromUsedInOperatingActivities"]


def get(url, ua):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 403, 500, 502, 503) and attempt < 3:
                time.sleep(10 * (attempt + 1))
                continue
            raise
        except (ConnectionError, TimeoutError, urllib.error.URLError, OSError):
            if attempt < 3:
                time.sleep(5 * (attempt + 1))
                continue
            raise


def facts_for(facts, tags):
    """Yield (tag, taxonomy, unit, entry) for USD entries of the given tags."""
    for tax in ("us-gaap", "ifrs-full"):
        for tag in tags:
            node = facts.get("facts", {}).get(tax, {}).get(tag)
            if not node:
                continue
            for unit, entries in node.get("units", {}).items():
                for e in entries:
                    yield tag, tax, unit, e


def latest_instant(facts, tags):
    best = None
    for tag, tax, unit, e in facts_for(facts, tags):
        if "start" in e or unit != "USD":
            continue
        if best is None or e["end"] > best[3]["end"] or (e["end"] == best[3]["end"] and e.get("filed", "") > best[3].get("filed", "")):
            best = (tag, tax, unit, e)
    return best


def latest_annual(facts, tags):
    best = None
    for tag, tax, unit, e in facts_for(facts, tags):
        if "start" not in e or unit != "USD":
            continue
        days = (datetime.fromisoformat(e["end"]) - datetime.fromisoformat(e["start"])).days
        if not 350 <= days <= 380:
            continue
        if best is None or e["end"] > best[3]["end"] or (e["end"] == best[3]["end"] and e.get("filed", "") > best[3].get("filed", "")):
            best = (tag, tax, unit, e)
    return best


def value_at(facts, tags, end):
    vals = [e["val"] for tag, tax, unit, e in facts_for(facts, tags) if "start" not in e and unit == "USD" and e["end"] == end]
    return max(vals) if vals else None


def main():
    contact = os.environ.get("SEC_CONTACT", "").strip()
    if not contact:
        sys.exit("ตั้ง SEC_CONTACT ก่อน ห้ามเขียนลงไฟล์ใน repo")
    ua = "aia-homework-research " + contact
    with open(os.path.join(DATA, "sponsor_tickers.csv"), encoding="utf-8-sig", newline="") as f:
        sponsors = [r for r in csv.DictReader(f) if r["match_quality"] in ("exact", "partial", "manual")]
    out = []
    for i, s in enumerate(sponsors, 1):
        cik = int(s["sec_cik"])
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
        row = {"sponsor": s["sponsor"], "ticker": s["sec_ticker"], "cik": cik, "match_quality": s["match_quality"],
               "cash_total_usd": "", "cash_end": "", "cash_basis": "", "ocf_annual_usd": "", "ocf_fy_end": "",
               "runway_years_calc": "", "note": "", "source_url": url, "retrieved": date.today().isoformat()}
        try:
            facts = get(url, ua)
        except Exception as ex:  # keep going; record the failure
            facts = None
            row["note"] = f"ดึงไม่สำเร็จ: {type(ex).__name__}"
        if facts is None:
            row["note"] = row["note"] or "ไม่มี companyfacts (ยังไม่ยืนยัน)"
        else:
            comb = latest_instant(facts, CASH_COMBINED)
            cash = latest_instant(facts, CASH)
            if comb and (not cash or comb[3]["end"] >= cash[3]["end"]):
                row.update(cash_total_usd=comb[3]["val"], cash_end=comb[3]["end"], cash_basis=comb[0])
            elif cash:
                end = cash[3]["end"]
                sti = value_at(facts, STI, end) or 0
                row.update(cash_total_usd=cash[3]["val"] + sti, cash_end=end,
                           cash_basis=cash[0] + (" + short-term investments" if sti else " (ไม่พบเงินลงทุนระยะสั้น)"))
            ocf = latest_annual(facts, OCF)
            if ocf:
                row.update(ocf_annual_usd=ocf[3]["val"], ocf_fy_end=ocf[3]["end"])
                if row["cash_total_usd"] != "" and ocf[3]["val"] < 0:
                    row["runway_years_calc"] = round(row["cash_total_usd"] / -ocf[3]["val"], 2)
                elif ocf[3]["val"] >= 0:
                    row["note"] = "OCF ปีล่าสุดเป็นบวก"
            if row["cash_total_usd"] == "" and not row["note"]:
                row["note"] = "ไม่พบแท็กเงินสดเป็น USD (ยังไม่ยืนยัน)"
            if not ocf and not row["note"]:
                row["note"] = "ไม่พบ OCF รายปีเป็น USD (ยังไม่ยืนยัน)"
        out.append(row)
        if i % 25 == 0:
            print(f"{i}/{len(sponsors)}", flush=True)
        time.sleep(0.25)
    with open(os.path.join(DATA, "financials.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print({"companies": len(out), "with_cash": sum(r["cash_total_usd"] != "" for r in out),
           "with_ocf": sum(r["ocf_annual_usd"] != "" for r in out),
           "with_runway": sum(r["runway_years_calc"] != "" for r in out)})


if __name__ == "__main__":
    main()
