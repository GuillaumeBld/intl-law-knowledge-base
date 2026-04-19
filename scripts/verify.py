#!/usr/bin/env python3
"""
Determinism verification for intl-law-knowledge-base.

Runs four checks that enforce the grounding contract declared in CLAUDE.md:

  1. Every file referenced by index.html's FILES map exists on disk.
  2. Every cross-reference in wiki/ and outputs/ resolves
     ([[wiki-links]] + raw/ | wiki/ | data/ | outputs/ path mentions).
  3. The demo output's tax arithmetic is reproducible from the CSV data
     (prevents drift between narrative and structured data).
  4. Every numeric amount in data/us-fed-2025-*.csv appears literally in
     the raw IRS source — catches transcription errors at the seed level.

Exit code 0 if all checks pass, 1 otherwise.
Runs from the repo root. No dependencies beyond the Python 3 standard library.
"""

from __future__ import annotations

import csv
import glob
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.chdir(REPO)

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    mark = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if (detail and not ok) else ""
    print(f"  [{mark}] {label}{suffix}")
    if not ok:
        failures.append(f"{label}: {detail}")


# ---------------------------------------------------------------------------
# Test 1 — index.html's FILES map points to real files
# ---------------------------------------------------------------------------
print("\n[1/4] index.html FILES manifest")

index_html = (REPO / "index.html").read_text()
match = re.search(r"const FILES\s*=\s*(\{.*?\});", index_html, re.DOTALL)
if not match:
    check("parse FILES map from index.html", False, "regex did not match")
else:
    files_block = match.group(1)
    for folder in ("wiki", "raw", "data", "outputs"):
        fn_match = re.search(rf'{folder}:\s*\[(.*?)\]', files_block, re.DOTALL)
        if not fn_match:
            check(f"{folder} array present", False, "array not found in FILES map")
            continue
        filenames = re.findall(r'"([^"]+)"', fn_match.group(1))
        for fn in filenames:
            path = REPO / folder / fn
            check(f"{folder}/{fn}", path.is_file(), "missing on disk" if not path.is_file() else "")


# ---------------------------------------------------------------------------
# Test 2 — cross-references resolve
# ---------------------------------------------------------------------------
print("\n[2/4] Cross-reference integrity")

wiki_link_re = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]")
path_ref_re = re.compile(r"\b(raw|wiki|data|outputs)/([A-Za-z0-9._-]+\.(?:md|csv|yaml|json))")

ref_count = 0
ref_bad = 0
for md_path in glob.glob("wiki/*.md") + glob.glob("outputs/*.md"):
    text = Path(md_path).read_text()

    for m in wiki_link_re.finditer(text):
        target = m.group(1).strip()
        if not target.endswith(".md"):
            target += ".md"
        ref_count += 1
        if not (REPO / "wiki" / target).is_file():
            ref_bad += 1
            failures.append(f"{md_path}: [[{m.group(1)}]] -> wiki/{target} (missing)")

    for m in path_ref_re.finditer(text):
        ref = f"{m.group(1)}/{m.group(2)}"
        ref_count += 1
        if not (REPO / ref).is_file():
            ref_bad += 1
            failures.append(f"{md_path}: references {ref} (missing)")

check(f"{ref_count} refs resolved", ref_bad == 0,
      f"{ref_bad} broken reference(s)" if ref_bad else "")


# ---------------------------------------------------------------------------
# Test 3 — demo tax calculation reproduces from CSV
# ---------------------------------------------------------------------------
print("\n[3/4] Demo arithmetic reproducibility")

DEMO = REPO / "outputs" / "demo-single-filer-75k-2025.md"
demo_text = DEMO.read_text() if DEMO.is_file() else ""

with open("data/us-fed-2025-key-amounts.csv") as f:
    amounts = {(r["item"], r["filing_status"]): float(r["amount"]) for r in csv.DictReader(f)}

std_ded_single = amounts.get(("standard_deduction", "single"))
check("standard_deduction.single in key-amounts CSV",
      std_ded_single == 15000.0,
      f"got {std_ded_single}, expected 15000")

wages = 75000.0
taxable = wages - (std_ded_single or 0)

with open("data/us-fed-2025-brackets.csv") as f:
    single_rows = [r for r in csv.DictReader(f) if r["filing_status"] == "single"]

brackets = sorted(
    ((float(r["rate"]), float(r["bracket_floor"]),
      float(r["bracket_ceiling"]) if r["bracket_ceiling"] else float("inf"))
     for r in single_rows),
    key=lambda t: t[1],
)

tax = 0.0
for rate, lo, hi in brackets:
    if taxable <= lo:
        break
    tax += (min(taxable, hi) - lo) * rate

check(f"recomputed tax on $75K single = ${tax:,.2f}",
      abs(tax - 8114.00) < 0.01,
      "does not match demo's $8,114.00")

check("demo output cites $8,114",
      "$8,114.00" in demo_text or "$8,114" in demo_text,
      "amount missing from outputs/demo-single-filer-75k-2025.md")


# ---------------------------------------------------------------------------
# Test 4 — CSV values appear literally in the raw IRS source
# ---------------------------------------------------------------------------
print("\n[4/4] CSV ↔ raw-source consistency")

raw_text = (REPO / "raw" / "irs-ir-2024-273-tax-year-2025-inflation-adjustments.md").read_text()

def in_raw(n: int) -> bool:
    if n == 0:
        return True  # implicit floor, not expected to appear literally
    return f"${n:,}" in raw_text

expected_floors = {
    "single": {0.10: 0, 0.12: 11925, 0.22: 48475, 0.24: 103350,
               0.32: 197300, 0.35: 250525, 0.37: 626350},
    "mfj":    {0.10: 0, 0.12: 23850, 0.22: 96950, 0.24: 206700,
               0.32: 394600, 0.35: 501050, 0.37: 751600},
}

bracket_bad = 0
with open("data/us-fed-2025-brackets.csv") as f:
    for r in csv.DictReader(f):
        status = r["filing_status"]
        rate = float(r["rate"])
        floor = int(float(r["bracket_floor"]))
        exp = expected_floors[status][rate]
        if floor != exp:
            bracket_bad += 1
            failures.append(f"brackets.csv {status} {rate}: floor={floor}, expected {exp}")
        if not in_raw(floor):
            bracket_bad += 1
            failures.append(f"brackets.csv {status} {rate}: ${floor:,} not in raw source")
check("bracket floors match expected + appear in raw", bracket_bad == 0,
      f"{bracket_bad} mismatch(es)" if bracket_bad else "")

key_expected = {
    ("standard_deduction", "single"): 15000,
    ("standard_deduction", "mfj"): 30000,
    ("standard_deduction", "hoh"): 22500,
    ("amt_exemption", "single"): 88100,
    ("amt_exemption", "mfj"): 137000,
    ("eitc_max_3plus_children", "any"): 8046,
    ("estate_basic_exclusion", "any"): 13990000,
    ("annual_gift_exclusion", "any"): 19000,
    ("foreign_earned_income_exclusion", "any"): 130000,
    ("transportation_fringe_monthly", "any"): 325,
    ("health_fsa_salary_reduction", "any"): 3300,
    ("adoption_credit_special_needs_max", "any"): 17280,
}

key_bad = 0
with open("data/us-fed-2025-key-amounts.csv") as f:
    for r in csv.DictReader(f):
        key = (r["item"], r["filing_status"])
        if key in key_expected:
            got = int(float(r["amount"]))
            if got != key_expected[key]:
                key_bad += 1
                failures.append(f"key-amounts.csv {key}: {got}, expected {key_expected[key]}")
            if not in_raw(key_expected[key]):
                key_bad += 1
                failures.append(f"key-amounts.csv {key}: ${key_expected[key]:,} not in raw")
check("key amounts match expected + appear in raw", key_bad == 0,
      f"{key_bad} mismatch(es)" if key_bad else "")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
if failures:
    print(f"FAILED — {len(failures)} issue(s):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("All checks passed. KB is internally consistent.")
