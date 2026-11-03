"""Round-1 flag: mark candidates whose intervention name matches a drug already approved by FDA.

Source: openFDA Drugs@FDA bulk file (public)
  https://download.open.fda.gov/drug/drugsfda/drug-drugsfda-0001-of-0001.json.zip

Reads  data/candidates.csv   (from screen_ctgov.py)
Writes data/candidates.csv   (adds fda_known_name, fda_match) and data/fda_names_meta.json

Meaning of the flag (be careful):
  fda_known_name = Y  -> a word in the intervention name equals an FDA-listed active ingredient or brand.
                         The drug may still be a NEW INDICATION worth watching, or a comparator arm.
  fda_known_name = N  -> no match. Could be a new molecule, a code name (e.g. HRS9531), or a name
                         spelled differently from FDA's. NOT proof that the drug is new.
Only US approval is checked. China (NMPA) approvals are not checked in round 1.

KNOWN GAP (found by spot-check 2026-11-01): Drugs@FDA covers small-molecule NDAs well but misses many
biologics (BLA). Example: luspatercept and marstacimab are FDA-approved yet flagged N. So:
  - Y is fairly reliable for small molecules (already on the US market).
  - N must NOT be read as 'new drug'. Approval status of every shortlisted drug is re-checked
    against FDA / Purple Book directly in step 3 (FACTS).
"""
import csv
import io
import json
import os
import re
import urllib.request
import zipfile
from datetime import date

URL = "https://download.open.fda.gov/drug/drugsfda/drug-drugsfda-0001-of-0001.json.zip"
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
STOP = {"and", "with", "plus", "injection", "tablet", "tablets", "oral", "capsule", "capsules", "solution",
        "mg", "dose", "high", "low", "of", "in", "the", "for", "to", "or", "a", "cream", "gel", "acid",
        "sodium", "hydrochloride", "hcl", "sulfate", "acetate", "phosphate",
        "human", "cells", "cell", "allogeneic", "autologous", "vaccine", "protein", "recombinant",
        "antibody", "globulin", "immune", "placebo", "matching", "extended", "release", "infusion"}


def tokens(text):
    return {t for t in re.split(r"[^a-z0-9\-]+", text.lower()) if len(t) >= 5 and t not in STOP}


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "aia-homework-research (student project)"})
    with urllib.request.urlopen(req, timeout=180) as r:
        blob = r.read()
    z = zipfile.ZipFile(io.BytesIO(blob))
    data = json.loads(z.read(z.namelist()[0]).decode("utf-8"))
    names = set()
    for rec in data["results"]:
        for p in rec.get("products", []):
            names |= tokens(p.get("brand_name", ""))
            for ai in p.get("active_ingredients", []):
                names |= tokens(ai.get("name", ""))
    path = os.path.join(DATA, "candidates.csv")
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        hit = sorted(tokens(r["intervention"]) & names)
        r["fda_known_name"] = "Y" if hit else "N"
        r["fda_match"] = " ".join(hit[:3])
    cols = list(rows[0].keys())
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    meta = {"fetched": date.today().isoformat(), "source": URL, "fda_records": len(data["results"]),
            "name_tokens": len(names), "rows": len(rows),
            "flag_Y": sum(r["fda_known_name"] == "Y" for r in rows),
            "flag_N": sum(r["fda_known_name"] == "N" for r in rows)}
    with open(os.path.join(DATA, "fda_names_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
