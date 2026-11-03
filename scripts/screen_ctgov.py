"""Round-1 screen: Phase 2/3 industry drug trials from ClinicalTrials.gov (public API v2).

Outputs (all regenerate from this script):
  data/candidates.csv          one row per (sponsor, intervention)
  data/candidate_sponsors.csv  one row per sponsor
  data/screen_meta.json        query, fetch date, counts

Limits (keep in the dashboard footnote):
  - Covers ClinicalTrials.gov only. ChiCTR / CDE (China) are not included in round 1.
  - 'markets' is a hint from trial site countries, not the company's listing venue.
  - Listing ticker is NOT assigned here (needs SEC / HKEX lists) -> 'ยังไม่ยืนยัน'.
  - A candidate is a starting list, not a recommendation.
"""
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date

API = "https://clinicaltrials.gov/api/v2/studies"
UA = {"User-Agent": "aia-homework-research (student project)"}
FIELDS = "|".join([
    "NCTId", "BriefTitle", "OverallStatus", "PrimaryCompletionDate", "LeadSponsorName",
    "Phase", "Condition", "InterventionType", "InterventionName", "LocationCountry",
    "ArmGroupLabel", "ArmGroupType", "InterventionArmGroupLabel",
])
STATUS = "RECRUITING|ACTIVE_NOT_RECRUITING|ENROLLING_BY_INVITATION"
WINDOW = ("2026-11-01", "2028-12-31")  # primary completion window
DRUG_TYPES = {"DRUG", "BIOLOGICAL", "GENETIC", "COMBINATION_PRODUCT"}
SKIP_NAMES = ("placebo", "saline", "standard of care", "best supportive care", "vehicle", "sham",
              "investigator's choice", "investigators choice", "physician's choice", "chemotherapy")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def get(url):
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 4:
                time.sleep(5 * (attempt + 1))
                continue
            raise
        except (ConnectionError, TimeoutError, urllib.error.URLError, OSError):
            if attempt < 4:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable")


def fetch(phase):
    adv = (f"AREA[Phase]{phase} AND AREA[StudyType]INTERVENTIONAL AND AREA[LeadSponsorClass]INDUSTRY "
           f"AND AREA[PrimaryCompletionDate]RANGE[{WINDOW[0]},{WINDOW[1]}]")
    params = {"filter.advanced": adv, "filter.overallStatus": STATUS, "fields": FIELDS,
              "pageSize": "300", "countTotal": "true"}
    studies, token, total = [], None, None
    while True:
        p = dict(params)
        if token:
            p["pageToken"] = token
        d = get(API + "?" + urllib.parse.urlencode(p))
        total = d.get("totalCount", total)
        studies += d.get("studies", [])
        token = d.get("nextPageToken")
        if not token:
            break
        time.sleep(1)
    return studies, total


def norm(name):
    return " ".join(name.lower().split())


def main():
    today = date.today().isoformat()
    meta = {"fetched": today, "source": "https://clinicaltrials.gov/api/v2/studies",
            "window_primary_completion": WINDOW, "status": STATUS, "counts": {}}
    by_key = {}
    seen_trials = {}
    for phase in ("PHASE3", "PHASE2"):
        studies, total = fetch(phase)
        meta["counts"][phase] = {"api_total": total, "fetched": len(studies)}
        for s in studies:
            ps = s["protocolSection"]
            nct = ps["identificationModule"]["nctId"]
            sponsor = ps["sponsorCollaboratorsModule"]["leadSponsor"]["name"]
            phases = ps.get("designModule", {}).get("phases", [])
            pcd = ps.get("statusModule", {}).get("primaryCompletionDateStruct", {}).get("date", "")
            conds = ps.get("conditionsModule", {}).get("conditions", [])
            countries = {l.get("country", "") for l in ps.get("contactsLocationsModule", {}).get("locations", [])}
            seen_trials[nct] = 1
            arms = ps.get("armsInterventionsModule", {})
            exp_labels = {a.get("label") for a in arms.get("armGroups", []) if a.get("type") == "EXPERIMENTAL"}
            for iv in arms.get("interventions", []):
                if iv.get("type") not in DRUG_TYPES:
                    continue
                # Keep only drugs given in an EXPERIMENTAL arm (drops comparator-only arms).
                # If the record has no arm info at all, keep it (cannot tell).
                if arms.get("armGroups") and not (set(iv.get("armGroupLabels", [])) & exp_labels):
                    continue
                n = norm(iv.get("name", ""))
                if not n or any(k in n for k in SKIP_NAMES):
                    continue
                k = (sponsor, n)
                row = by_key.setdefault(k, {"sponsor": sponsor, "intervention": iv.get("name", ""), "type": iv.get("type"),
                                            "conditions": set(), "phases": set(), "trials": {}, "countries": set()})
                row["conditions"].update(conds[:3])
                row["phases"].update(phases)
                row["trials"][nct] = pcd
                row["countries"].update(countries)
    meta["unique_trials"] = len(seen_trials)

    rows = []
    for (sponsor, _), r in by_key.items():
        ph = r["phases"]
        tier = "A: ระยะ 3 (รวม 2/3)" if "PHASE3" in ph else "B: ระยะ 2"
        c = r["countries"]
        hint = [m for m, flag in (("US", "United States" in c), ("CN", "China" in c or "Hong Kong" in c)) if flag]
        nct_sorted = sorted(r["trials"].items(), key=lambda kv: kv[1])
        rows.append({
            "tier": tier, "sponsor": sponsor, "intervention": r["intervention"], "intervention_type": r["type"],
            "conditions": "; ".join(sorted(r["conditions"]))[:200], "phases": "/".join(sorted(ph)),
            "n_trials": len(r["trials"]), "earliest_primary_completion": nct_sorted[0][1],
            "latest_primary_completion": nct_sorted[-1][1],
            "markets_hint": "+".join(hint) if hint else "other",
            "first_nct_ids": " ".join(n for n, _ in nct_sorted[:3]),
            "source_url": "https://clinicaltrials.gov/study/" + nct_sorted[0][0],
            "ticker": "ยังไม่ยืนยัน", "retrieved": today,
        })
    rows.sort(key=lambda r: (r["tier"], r["sponsor"].lower(), -r["n_trials"]))

    os.makedirs(OUT, exist_ok=True)
    cols = list(rows[0].keys())
    with open(os.path.join(OUT, "candidates.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    sp = defaultdict(lambda: {"drugs": set(), "tierA": set(), "markets": set(), "trials": 0})
    for r in rows:
        s = sp[r["sponsor"]]
        s["drugs"].add(r["intervention"].lower())
        if r["tier"].startswith("A"):
            s["tierA"].add(r["intervention"].lower())
        s["markets"].add(r["markets_hint"])
        s["trials"] += r["n_trials"]
    srows = [{"sponsor": k, "n_drugs": len(v["drugs"]), "n_drugs_phase3": len(v["tierA"]),
              "n_trial_links": v["trials"], "markets_hint": "|".join(sorted(v["markets"])),
              "ticker": "ยังไม่ยืนยัน", "retrieved": today} for k, v in sp.items()]
    srows.sort(key=lambda r: (-r["n_drugs_phase3"], -r["n_drugs"], r["sponsor"].lower()))
    with open(os.path.join(OUT, "candidate_sponsors.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(srows[0].keys()))
        w.writeheader()
        w.writerows(srows)

    meta["candidate_rows"] = len(rows)
    meta["sponsors"] = len(srows)
    with open(os.path.join(OUT, "screen_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
