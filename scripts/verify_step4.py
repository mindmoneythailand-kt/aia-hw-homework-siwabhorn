"""Re-compute every number marked [คำนวณ] in output/step4_*.md and check enrollment sums against the registry.

Reads  data/drug_facts_round1.csv and the figures typed below (each from a primary page, see the .md files).
Prints OK / MISMATCH per line. Exit code 1 if any MISMATCH.
"""
import sys

bad = 0


def check(label, got, want, tol=0.0005):
    global bad
    ok = abs(got - want) <= max(tol * abs(want), 1e-9) if want else got == want
    print(("OK       " if ok else "MISMATCH ") + f"{label}: computed={got:,.4f} document={want:,.4f}")
    bad += (not ok)


# --- obesity ---
pop, prev, sev = 269_763_509, 0.403, 0.094
tam = pop * prev
check("US adults with obesity (M)", tam / 1e6, 108.7, 0.001)
check("US severe obesity (M)", pop * sev / 1e6, 25.4, 0.002)
for p, want in ((3588, 278_700), (4788, 208_900), (5388, 185_600)):
    check(f"patients for $1bn at ${p}/yr", 1e9 / p, want, 0.001)
for p, want in ((3588, 0.26), (4788, 0.19), (5388, 0.17)):
    check(f"% of TAM at ${p}", 100 * 1e9 / p / tam, want, 0.03)
check("Zepbound annualized (USD m)", 5352 * 4, 21_408, 0)
check("$1bn as % of Zepbound annualized", 100 * 1000 / (5352 * 4), 4.67, 0.002)
check("tirzepatide Q3 (USD m)", 10723 + 5352, 16_075, 0)
check("$1bn as % of tirzepatide annualized", 100 * 1000 / ((10723 + 5352) * 4), 1.56, 0.005)
check("PoS Metabolic from P3 (%)", 63.6 * 0.875, 55.7, 0.002)
check("PoS Endocrine from P3 (%)", 66.2 * 0.863, 57.1, 0.002)
# --- oncology ---
check("KEYTRUDA family Q3 (USD m)", 7771 + 830, 8_601, 0)
check("KEYTRUDA annualized", 8601 * 4, 34_404, 0)
check("$1bn as % of KEYTRUDA annualized", 100 * 1000 / 34_404, 2.9, 0.01)
check("Enhertu annualized from 9M", 4675 / 9 * 12, 6_233, 0.001)
check("$1bn as % of Enhertu annualized", 100 * 1000 / (4675 / 9 * 12), 16.0, 0.01)
check("PoS Oncology from P3 (%)", 47.7 * 0.92, 43.9, 0.002)
# --- neuro / psychiatry ---
check("treated MDD (M)", 21.0 * 0.61, 12.8, 0.01)
check("Cobenfy annualized (USD m)", 63 * 4, 252, 0)
check("$1bn / Cobenfy annualized (x)", 1000 / 252, 4.0, 0.02)
check("PoS Psychiatry from P3 (%)", 56.3 * 0.912, 51.3, 0.002)
check("PoS Neurology from P3 (%)", 53.1 * 0.867, 46.0, 0.002)
# --- immunology ---
check("Dupixent annualized (USD m)", 6540.5 * 4, 26_162, 0.001)
check("$1bn as % of Dupixent annualized", 100 * 1000 / (6540.5 * 4), 3.8, 0.01)
check("Dupixent Q3 growth (%)", 100 * (6540.5 / 4857.0 - 1), 35, 0.02)
check("PoS Autoimmune from P3 (%)", 65.3 * 0.941, 61.4, 0.002)
check("HS patients low (thousand) 0.10% x 341.8M", 0.001 * 341.8e6 / 1e3, 342, 0.002)
check("HS patients high (million) 0.40% x 341.8M", 0.004 * 341.8e6 / 1e6, 1.37, 0.01)
# --- enrollment sums typed in the .md files ---
sums = {
    "Opevesostat": ([1310, 1314], 2624),
    "HLX22": ([550, 706, 817], 2073),
    "Volrustomig": ([800, 1145, 895, 863], 3703),
    "Brenipatide": ([1000, 1000, 1100, 1100], 4200),
    "LB-102": ([456, 900], 1356),
    "NBI-1065845 (all 5)": ([200, 200, 200, 550, 850], 2000),
    "NBI-1065845 (4 in window)": ([200, 200, 200, 550], 1150),
    "Povorcitinib (8 trials)": ([346, 608, 450, 617, 467, 600, 349, 619], 4056),
    "SHR-1819": ([201, 423, 220, 652], 1496),
}
for k, (xs, want) in sums.items():
    check(f"enrollment {k}", sum(xs), want, 0)
print("RESULT:", "ALL OK" if not bad else f"{bad} MISMATCH")
sys.exit(1 if bad else 0)
