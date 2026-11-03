"""Round-1 step 3b: group the 78 drugs by disease area and PROPOSE 12 drugs for the deep dive (step 4).

Reads  data/drug_facts_round1.csv
Writes data/disease_areas_round1.csv  (area summary)  and  data/proposed_deepdive_12.csv  (draft, needs approval)

Selection rule (about COVERAGE and DATA, not a ranking of who is most likely to be a blockbuster):
  E1  at least one Phase 3 trial in the 2026-11 .. 2028-12 window            (from the screen)
  E2  not already on a US label (openFDA 'พบฉลาก' is a reliable positive)    -> dropped
  E3  not an obviously old molecule (small manual list below)               -> dropped
  P1  areas ordered by number of eligible drugs
  P2  at most 2 drugs per area, chosen by LARGEST total planned enrollment (a size-of-programme proxy)
  P3  at least 4 of the 12 must be China / HK-listed companies (spec covers both markets)
Area is assigned by keywords in the registry's condition names (first match wins) - a rough label.
"""
import csv
import os
import re
from collections import defaultdict
from statistics import median

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
AREAS = [
    ("Oncology", r"cancer|carcinoma|tumou?r|lymphoma|leuk(a)?emia|myeloma|melanoma|neoplasm|sarcoma|glioma|metasta|malignan|nsclc|mesothelioma|myelofibrosis|myelodysplastic|gist"),
    ("Obesity / diabetes / metabolic", r"obes|overweight|diabet|glyc(a)?emi|mash|nash|steatohep|lipid|cholesterol|triglycer|gout|uric"),
    ("Immunology / inflammation", r"lupus|arthritis|psoria|dermatitis|colitis|crohn|hidradenitis|myasthenia|iga nephropathy|sj[oö]gren|asthma|copd|urticaria|alopecia|spondyl|nephritis|pemphig|itch|eosinophil"),
    ("Neurology / psychiatry", r"schizophren|depress|alzheimer|parkinson|epilep|seizure|migraine|narcolep|bipolar|huntington|neuropath|insomnia|anxiety|autism|dementia|sclerosis|dravet|developmental"),
    ("Cardio / renal / pulmonary", r"heart|cardi|hypertension|atrial|pulmonary arterial|kidney|renal|stroke|thrombo|embol|lipoprotein|ckd"),
    ("Infectious disease / vaccines", r"vaccin|virus|infection|hepatitis|hiv|influenza|rsv|pneumococ|covid|bacter|meningococ|sepsis|fung"),
    ("Rare / genetic / blood", r"cystic fibrosis|hemophilia|thalass|duchenne|fabry|gaucher|sickle|rare|anemia|hereditary"),
    ("Ophthalmology", r"macular|retin|eye|glaucoma|myopia|dry eye|uveitis"),
]
OLD = re.compile(r"etoposide|irinotecan|t-dm1|testosterone|doxorubicin|trastuzumab$", re.I)


def area_of(text):
    t = text.lower()
    for name, pat in AREAS:
        if re.search(pat, t):
            return name
    return "Other / unclassified"


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    with open(os.path.join(DATA, "drug_facts_round1.csv"), encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["area"] = area_of(r["conditions"])
        r["eligible"] = (int(r["n_phase3_trials"] or 0) >= 1 and r["openfda_label"] != "พบฉลาก" and not OLD.search(r["drug_clean"]))
    by = defaultdict(list)
    for r in rows:
        by[r["area"]].append(r)
    summ = []
    for a, rs in by.items():
        comp = [num(r["competition_n_phase3_trials"]) for r in rs if num(r["competition_n_phase3_trials"]) is not None]
        summ.append({"area": a, "drugs": len(rs), "eligible_drugs": sum(r["eligible"] for r in rs),
                     "companies": len({r["company"] for r in rs}),
                     "hk_drugs": sum(r["market"].startswith("HK") for r in rs),
                     "total_planned_enrollment": int(sum(num(r["total_planned_enrollment"]) or 0 for r in rs)),
                     "median_same_condition_phase3_trials_by_others": median(comp) if comp else ""})
    summ.sort(key=lambda s: -s["eligible_drugs"])
    with open(os.path.join(DATA, "disease_areas_round1.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summ[0].keys()))
        w.writeheader()
        w.writerows(summ)

    # P1-P2: up to 2 per area, areas ordered by eligible count
    order = [s["area"] for s in summ if s["area"] != "Other / unclassified" and s["eligible_drugs"] > 0]
    pick = []
    for a in order:
        el = sorted((r for r in by[a] if r["eligible"]), key=lambda r: -(num(r["total_planned_enrollment"]) or 0))
        pick += el[:2]
    pick = pick[:12] if len(pick) >= 12 else pick
    # P3: ensure >= 4 HK; swap out the smallest-enrollment non-HK picks for the largest unpicked HK drugs
    hk_extra = sorted((r for r in rows if r["eligible"] and r["market"].startswith("HK") and r not in pick),
                      key=lambda r: -(num(r["total_planned_enrollment"]) or 0))
    while sum(r["market"].startswith("HK") for r in pick) < 4 and hk_extra:
        non_hk = sorted((r for r in pick if not r["market"].startswith("HK")), key=lambda r: (num(r["total_planned_enrollment"]) or 0))
        pick.remove(non_hk[0])
        pick.append(hk_extra.pop(0))
    cols = ["area", "market", "ticker_or_code", "company", "drug", "conditions", "n_phase3_trials", "total_planned_enrollment",
            "competition_n_phase3_trials", "openfda_label", "ct_source"]
    pick.sort(key=lambda r: (r["area"], -(num(r["total_planned_enrollment"]) or 0)))
    with open(os.path.join(DATA, "proposed_deepdive_12.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(pick)
    print("AREAS")
    for s in summ:
        print(s)
    print("PICK", len(pick))
    for r in pick:
        print(r["area"], "|", r["ticker_or_code"], r["company"], "|", r["drug"][:30], "| enr", r["total_planned_enrollment"], "| comp", r["competition_n_phase3_trials"], "|", r["conditions"][:60])


if __name__ == "__main__":
    main()
