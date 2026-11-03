"""Round-1 step 3: drug-level facts for the 45 companies (up to 2 lead Tier-A drugs per company).

Reads  data/round1_universe.csv, data/candidates.csv
Writes data/drug_facts_round1.csv , data/drug_facts_meta.json

Per drug (all from public registries, with source URLs):
  - Phase 3 / 2 trial list, conditions, total planned enrollment, dates, one primary endpoint  [ClinicalTrials.gov]
  - competition proxy: number of ongoing industry Phase 3 trials in the same main condition   [ClinicalTrials.gov]
  - US label check: does openFDA have a drug label for this name?                              [openFDA drug/label]

How the 'lead' drugs are picked (NOT a quality ranking): drugs whose name has no FDA-name match first,
then by number of Phase 3 trials, skipping generic comparator words. A person must review the pick.
openFDA label 'found' means the name is on a US label (approved product or a new indication of one);
'not found' does NOT prove the drug is unapproved (code names / spelling / non-US products).
This step does NOT estimate TAM/SAM/SOM or approval probability - that is step 4, with cited sources.

KNOWN GAP (spot-checked 2026-11-01): openFDA's label index does not contain every marketed product.
sotatercept (Winrevair), talquetamab (Talvey) and tarlatamab (Imdelltra) are FDA-approved but return nothing,
while nipocalimab (Imaavy) and tebentafusp (Kimmtrak) are found. So 'พบฉลาก' is a reliable POSITIVE signal
(drug is on a US label) but 'ไม่พบฉลาก' proves nothing. Approval status of each finalist is confirmed
from FDA / the company's filings in step 4 before any claim is written.
"""
import csv
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
CT = "https://clinicaltrials.gov/api/v2/studies"
UA = {"User-Agent": "aia-homework-research (student project)"}
STATUS = "RECRUITING|ACTIVE_NOT_RECRUITING|ENROLLING_BY_INVITATION"
WINDOW = "RANGE[2026-11-01,2028-12-31]"
SKIP = re.compile(r"rescue|placebo|standard|chemotherapy|best available|investigator|^arpi$|^pg4$|paclitaxel|carboplatin|cisplatin|"
                  r"gemcitabine|docetaxel|fluorouracil|5-fu|pembrolizumab|nivolumab|durvalumab|atezolizumab|ipilimumab|"
                  r"olanzapine|risperidone|aripiprazole|trametinib|dexamethasone|prednisone|rituximab|bevacizumab", re.I)


def get(url):
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt < 3:
                time.sleep(4 * (attempt + 1))
                continue
            raise
        except (ConnectionError, TimeoutError, urllib.error.URLError, OSError):
            if attempt < 3:
                time.sleep(4 * (attempt + 1))
                continue
            raise


def clean_name(n):
    n = re.sub(r"\(.*?\)|\[.*?\]", " ", n)
    n = re.sub(r"\b\d+(\.\d+)?\s?(mg|mcg|µg|g|ml|iu|%)\S*|\bdose\s?\d+|\bBID\b|\bQD\b|\bQW\b|\bQ\dW\b|injection|tablets?|capsules?|infusion|oral|subcutaneous|\biv\b|\bsc\b", " ", n, flags=re.I)
    n = re.sub(r"[^A-Za-z0-9\- ]+", " ", n)
    return " ".join(n.split()[:3]).strip()


def ct_trials(drug, sponsors):
    best = []
    for sp in sponsors:
        q = {"query.intr": drug, "query.lead": sp, "filter.overallStatus": STATUS,
             "filter.advanced": f"AREA[Phase]PHASE3 AND AREA[PrimaryCompletionDate]{WINDOW}",
             "fields": "NCTId|BriefTitle|Condition|Phase|EnrollmentCount|PrimaryOutcomeMeasure|PrimaryCompletionDate|StartDate|OverallStatus",
             "pageSize": "50"}
        d = get(CT + "?" + urllib.parse.urlencode(q))
        best += (d or {}).get("studies", [])
        time.sleep(0.4)
    return best


def competition(cond):
    q = {"query.cond": cond, "filter.overallStatus": STATUS,
         "filter.advanced": f"AREA[Phase]PHASE3 AND AREA[LeadSponsorClass]INDUSTRY AND AREA[PrimaryCompletionDate]{WINDOW}",
         "pageSize": "1", "countTotal": "true"}
    d = get(CT + "?" + urllib.parse.urlencode(q))
    time.sleep(0.4)
    return (d or {}).get("totalCount", ""), "https://clinicaltrials.gov/search?" + urllib.parse.urlencode({"cond": cond, "aggFilters": "phase:3,status:rec act"})


def fda_label(name):
    if not name or len(name) < 4:
        return "", "", ""
    nm = name.replace('"', "")
    # openFDA: '+' means AND, so alternatives must be joined with '+OR+' (first version used AND by mistake)
    search = f'openfda.generic_name:"{nm}"+OR+openfda.brand_name:"{nm}"+OR+openfda.substance_name:"{nm}"'
    url = "https://api.fda.gov/drug/label.json?" + urllib.parse.urlencode({"search": search, "limit": "1"}, safe='":+')
    try:
        d = get(url)
    except Exception:
        return "ตรวจไม่สำเร็จ", "", url
    time.sleep(0.3)
    if not d or not d.get("results"):
        return "ไม่พบฉลาก", "", url
    r = d["results"][0]
    o = r.get("openfda", {})
    return "พบฉลาก", f"{','.join(o.get('brand_name', [])[:2])} / {','.join(o.get('generic_name', [])[:1])} / label {r.get('effective_time', '')[:4]}", url


def main():
    with open(os.path.join(DATA, "round1_universe.csv"), encoding="utf-8-sig", newline="") as f:
        comps = list(csv.DictReader(f))
    with open(os.path.join(DATA, "candidates.csv"), encoding="utf-8-sig", newline="") as f:
        cands = [r for r in csv.DictReader(f) if r["tier"].startswith("A")]
    by_sp = defaultdict(list)
    for r in cands:
        by_sp[r["sponsor"]].append(r)
    out, errors = [], 0
    for c in comps:
        sponsors = [s.strip() for s in c["sponsors_ctgov"].split(";;")]
        pool = [r for s in sponsors for r in by_sp.get(s, []) if not SKIP.search(r["intervention"])]
        pool.sort(key=lambda r: (r["fda_known_name"] == "Y", -int(r["n_trials"]), r["intervention"].lower()))
        seen, picks = set(), []
        for r in pool:
            key = clean_name(r["intervention"]).lower()
            if key and key not in seen:
                seen.add(key)
                picks.append(r)
            if len(picks) == 2:
                break
        for r in picks:
            name = clean_name(r["intervention"])
            row = {"market": c["market"], "ticker_or_code": c["ticker_or_code"], "company": c["company"], "sponsor_ctgov": r["sponsor"],
                   "drug": r["intervention"], "drug_clean": name, "pick_reason": "ชื่อไม่ตรง FDA + จำนวนการทดลองมาก" if r["fda_known_name"] == "N" else "ชื่อตรง FDA (อาจเป็นข้อบ่งใช้ใหม่) + จำนวนการทดลองมาก",
                   "conditions": r["conditions"], "n_phase3_trials": "", "nct_ids": "", "total_planned_enrollment": "", "earliest_start": "",
                   "latest_primary_completion": "", "example_primary_endpoint": "", "ct_source": "", "competition_main_condition": "",
                   "competition_n_phase3_trials": "", "competition_source": "", "openfda_label": "", "openfda_detail": "", "openfda_source": "",
                   "retrieved": date.today().isoformat()}
            try:
                studies = ct_trials(r["intervention"].split("(")[0].strip(), [r["sponsor"]])
                if studies:
                    ids, enr, starts, ends, conds = [], 0, [], [], []
                    for s in studies:
                        ps = s["protocolSection"]
                        ids.append(ps["identificationModule"]["nctId"])
                        enr += ps.get("designModule", {}).get("enrollmentInfo", {}).get("count", 0) or 0
                        starts.append(ps.get("statusModule", {}).get("startDateStruct", {}).get("date", ""))
                        ends.append(ps.get("statusModule", {}).get("primaryCompletionDateStruct", {}).get("date", ""))
                        conds += ps.get("conditionsModule", {}).get("conditions", [])
                    first = studies[0]["protocolSection"]
                    prim = first.get("outcomesModule", {}).get("primaryOutcomes", [])
                    row.update(n_phase3_trials=len(studies), nct_ids=" ".join(ids[:5]), total_planned_enrollment=enr,
                               earliest_start=min([x for x in starts if x] or [""]), latest_primary_completion=max([x for x in ends if x] or [""]),
                               example_primary_endpoint=(prim[0].get("measure", "")[:160] if prim else ""),
                               ct_source="https://clinicaltrials.gov/study/" + ids[0], conditions="; ".join(dict.fromkeys(conds))[:200])
                    main_cond = conds[0] if conds else r["conditions"].split(";")[0]
                else:
                    row["n_phase3_trials"] = 0
                    main_cond = r["conditions"].split(";")[0]
                if main_cond:
                    n, src = competition(main_cond.strip())
                    row.update(competition_main_condition=main_cond.strip(), competition_n_phase3_trials=n, competition_source=src)
                lab, det, url = fda_label(name)
                row.update(openfda_label=lab, openfda_detail=det, openfda_source=url)
            except Exception as ex:
                errors += 1
                row["ct_source"] = f"ดึงไม่สำเร็จ: {type(ex).__name__} (ยังไม่ยืนยัน)"
            out.append(row)
            print(c["ticker_or_code"], "|", r["intervention"][:35], "|", row["n_phase3_trials"], "|", row["openfda_label"], flush=True)
    with open(os.path.join(DATA, "drug_facts_round1.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    meta = {"fetched": date.today().isoformat(), "companies": len(comps), "drugs": len(out), "errors": errors,
            "sources": [CT, "https://api.fda.gov/drug/label.json"]}
    with open(os.path.join(DATA, "drug_facts_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(meta)


if __name__ == "__main__":
    main()
