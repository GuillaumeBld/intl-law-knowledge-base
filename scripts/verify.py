#!/usr/bin/env python3
"""
Determinism verification for intl-law-knowledge-base.

Four generic checks, driven by data/manifests/*.yaml:

  1. index.html's FILES manifest matches the actual filesystem
     (every referenced file exists + every on-disk file is registered).
  2. Every cross-reference in wiki/ and outputs/ resolves
     ([[wiki-links]] + raw/ | wiki/ | data/ | outputs/ path mentions).
  3. Each dataset manifest's demo_outputs reproduces from CSV data
     (prevents drift between narrative and structured data).
  4. Each dataset manifest's CSV amounts appear literally in the
     declared raw source (catches transcription errors).

Exit 0 if all checks pass, 1 otherwise. Python 3 stdlib only — no YAML
library dependency; uses a tiny purpose-built parser for the simple
subset of YAML used in manifests.
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
# Minimal YAML parser — handles the subset used in our manifests.
# Supports: nested dicts, lists, scalar types (str/int/float/bool/null),
# flow-style dicts ({k: v, k: v}), quoted strings, and "# comments".
# Refuses anything else rather than silently misparsing.
# ---------------------------------------------------------------------------
def _scalar(v: str):
    v = v.strip()
    if not v:
        return None
    if v.startswith(('"', "'")) and v[-1] == v[0]:
        return v[1:-1]
    low = v.lower()
    if low in ("null", "~", ""):
        return None
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return v


def _parse_flow_dict(s: str) -> dict:
    inner = s.strip()[1:-1]
    out = {}
    for part in _split_flow(inner):
        if ":" not in part:
            raise ValueError(f"bad flow-dict entry: {part!r}")
        k, v = part.split(":", 1)
        out[k.strip()] = _scalar(v)
    return out


def _split_flow(s: str) -> list[str]:
    """Split top-level commas in a flow-dict body, respecting quotes and braces."""
    out, buf, depth, quote = [], "", 0, None
    for ch in s:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            buf += ch
            continue
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(buf)
            buf = ""
        else:
            buf += ch
    if buf.strip():
        out.append(buf)
    return out


def parse_yaml(text: str):
    """Parse the manifest subset of YAML."""
    # Strip comments + blank lines, keep indentation.
    lines = []
    for raw in text.splitlines():
        s = raw
        if s.lstrip().startswith("#"):
            continue  # whole-line comment
        if "#" in s:
            # Drop trailing ` # ...` outside quotes. Keep `#` inside strings
            # alone — our manifests don't embed `#` in values so a naive
            # split on " #" is safe here.
            s = re.sub(r"\s+#.*$", "", s)
        if not s.strip():
            continue
        lines.append(s)

    pos = [0]

    def peek_indent():
        if pos[0] >= len(lines):
            return -1
        ln = lines[pos[0]]
        return len(ln) - len(ln.lstrip())

    def parse_block(indent: int):
        # Detect list vs dict by first non-empty line at this indent.
        if pos[0] >= len(lines):
            return None
        first = lines[pos[0]]
        first_indent = len(first) - len(first.lstrip())
        if first_indent < indent:
            return None
        content = first[first_indent:]
        if content.startswith("- "):
            return parse_list(indent)
        return parse_dict(indent)

    def parse_dict(indent: int):
        out = {}
        while pos[0] < len(lines):
            line = lines[pos[0]]
            cur_indent = len(line) - len(line.lstrip())
            if cur_indent < indent:
                break
            if cur_indent > indent:
                raise ValueError(f"unexpected indent at line: {line!r}")
            body = line[indent:]
            if body.startswith("- "):
                break  # caller will dispatch to list
            m = re.match(r'^([A-Za-z_][\w.-]*)\s*:\s*(.*)$', body)
            if not m:
                raise ValueError(f"bad dict line: {line!r}")
            key, value = m.group(1), m.group(2).strip()
            pos[0] += 1
            if value == "":
                # Nested block.
                nxt_indent = peek_indent()
                if nxt_indent > indent:
                    out[key] = parse_block(nxt_indent)
                else:
                    out[key] = None
            elif value.startswith("{"):
                out[key] = _parse_flow_dict(value)
            elif value.startswith("["):
                raise ValueError("flow-list not supported")
            else:
                out[key] = _scalar(value)
        return out

    def parse_list(indent: int):
        out = []
        while pos[0] < len(lines):
            line = lines[pos[0]]
            cur_indent = len(line) - len(line.lstrip())
            if cur_indent < indent:
                break
            body = line[indent:]
            if not body.startswith("- "):
                break
            rest = body[2:]  # after "- "
            pos[0] += 1
            if rest == "":
                nxt_indent = peek_indent()
                if nxt_indent > indent:
                    out.append(parse_block(nxt_indent))
                else:
                    out.append(None)
            elif rest.startswith("{"):
                out.append(_parse_flow_dict(rest))
            elif re.match(r'^[A-Za-z_][\w.-]*\s*:\s*', rest):
                # Inline dict entry — reparse the rest as a single-key dict,
                # plus any further keys at indent+2.
                inline = rest
                item = {}
                m = re.match(r'^([A-Za-z_][\w.-]*)\s*:\s*(.*)$', inline)
                key, value = m.group(1), m.group(2).strip()
                if value == "":
                    nxt_indent = peek_indent()
                    if nxt_indent > indent + 2:
                        item[key] = parse_block(nxt_indent)
                    else:
                        item[key] = None
                elif value.startswith("{"):
                    item[key] = _parse_flow_dict(value)
                else:
                    item[key] = _scalar(value)
                # Collect siblings at (indent + 2).
                sibling_indent = indent + 2
                while pos[0] < len(lines):
                    ln = lines[pos[0]]
                    ci = len(ln) - len(ln.lstrip())
                    if ci != sibling_indent:
                        break
                    body2 = ln[sibling_indent:]
                    if body2.startswith("- "):
                        break
                    m2 = re.match(r'^([A-Za-z_][\w.-]*)\s*:\s*(.*)$', body2)
                    if not m2:
                        break
                    k2, v2 = m2.group(1), m2.group(2).strip()
                    pos[0] += 1
                    if v2 == "":
                        nxt_i = peek_indent()
                        if nxt_i > sibling_indent:
                            item[k2] = parse_block(nxt_i)
                        else:
                            item[k2] = None
                    elif v2.startswith("{"):
                        item[k2] = _parse_flow_dict(v2)
                    else:
                        item[k2] = _scalar(v2)
                out.append(item)
            else:
                out.append(_scalar(rest))
        return out

    if not lines:
        return {}
    # Top level is always a dict in our manifests.
    return parse_dict(0)


# ---------------------------------------------------------------------------
# Test 1 — index.html manifest matches the filesystem
# ---------------------------------------------------------------------------
print("\n[1/4] index.html FILES manifest")

index_html = (REPO / "index.html").read_text()
match = re.search(r"const FILES\s*=\s*(\{.*?\});", index_html, re.DOTALL)
manifest: dict[str, list[str]] = {}
if not match:
    check("parse FILES map from index.html", False, "regex did not match")
else:
    files_block = match.group(1)
    for folder in ("wiki", "raw", "data", "outputs"):
        fn_match = re.search(rf'{folder}:\s*\[(.*?)\]', files_block, re.DOTALL)
        if not fn_match:
            check(f"{folder} array present in FILES", False, "array not found")
            manifest[folder] = []
            continue
        manifest[folder] = re.findall(r'"([^"]+)"', fn_match.group(1))

    # Every registered file must exist.
    missing = []
    for folder, names in manifest.items():
        for fn in names:
            if not (REPO / folder / fn).is_file():
                missing.append(f"{folder}/{fn}")
    check(f"{sum(len(v) for v in manifest.values())} registered files exist",
          not missing, "missing: " + ", ".join(missing))

    # Every on-disk .md/.csv/.yaml file in wiki/raw/outputs/data must be
    # registered (except data/manifests/*, which is verifier config).
    disk_files = {
        "wiki":    sorted(p.name for p in (REPO / "wiki").glob("*.md")),
        "raw":     sorted(p.name for p in (REPO / "raw").glob("*.md"))
                   + sorted(p.name for p in (REPO / "raw").glob("*.pdf")),
        "outputs": sorted(p.name for p in (REPO / "outputs").glob("*.md")),
        "data":    sorted(p.name for p in (REPO / "data").glob("*.csv"))
                   + sorted(p.name for p in (REPO / "data").glob("*.yaml"))
                   + sorted(p.name for p in (REPO / "data").glob("*.json")),
    }
    unregistered = []
    for folder, names in disk_files.items():
        for fn in names:
            if fn not in manifest.get(folder, []):
                unregistered.append(f"{folder}/{fn}")
    check("every on-disk file is registered in FILES",
          not unregistered,
          "unregistered: " + ", ".join(unregistered))


# ---------------------------------------------------------------------------
# Test 2 — cross-references resolve
# ---------------------------------------------------------------------------
print("\n[2/4] Cross-reference integrity")

wiki_link_re = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]")
path_ref_re = re.compile(r"\b(raw|wiki|data|outputs)/([A-Za-z0-9._/-]+?\.(?:md|csv|yaml|json))")

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
      f"{ref_bad} broken reference(s)")


# ---------------------------------------------------------------------------
# Load dataset manifests
# ---------------------------------------------------------------------------
MANIFEST_DIR = REPO / "data" / "manifests"
manifest_files = sorted(MANIFEST_DIR.glob("*.yaml")) if MANIFEST_DIR.is_dir() else []
manifests = []
for mf in manifest_files:
    try:
        parsed = parse_yaml(mf.read_text())
        parsed["_path"] = str(mf.relative_to(REPO))
        manifests.append(parsed)
    except Exception as e:
        failures.append(f"parse {mf.relative_to(REPO)}: {e}")
        print(f"  [FAIL] parse {mf.relative_to(REPO)} — {e}")


def read_csv(path: str) -> list[dict]:
    with open(path) as f:
        return list(csv.DictReader(f))


def find_row(rows: list[dict], selector: dict) -> dict | None:
    for r in rows:
        if all(str(r.get(k, "")) == str(v) for k, v in selector.items()):
            return r
    return None


def in_text(amount: int | float, text: str) -> bool:
    if amount == 0:
        return True  # implicit zero-floor rows are skipped
    n = int(amount) if float(amount).is_integer() else amount
    return f"${n:,}" in text


# ---------------------------------------------------------------------------
# Test 3 — demo outputs reproduce from CSV data
# ---------------------------------------------------------------------------
print("\n[3/4] Demo arithmetic reproducibility")

if not manifests:
    check("at least one dataset manifest present", False,
          f"no files in {MANIFEST_DIR.relative_to(REPO)}/")

demos_checked = 0
for m in manifests:
    for demo in (m.get("demo_outputs") or []):
        demo_path = REPO / demo["file"]
        label = f"{m['id']} · {demo['file']}"
        if not demo_path.is_file():
            check(label, False, "demo file missing")
            continue

        demo_text = demo_path.read_text()
        claim = demo.get("claim_must_appear")
        if claim and claim not in demo_text:
            check(f"{label}: claim '{claim}' present", False, "not found in demo")
            continue

        comp = demo.get("computation") or {}
        if comp.get("type") == "progressive_tax":
            sd_ref = comp["standard_deduction_from"]
            sd_rows = read_csv(sd_ref["csv"])
            sd_row = find_row(sd_rows, sd_ref["row_selector"])
            if not sd_row:
                check(label, False, "standard deduction row not found")
                continue
            std_ded = float(sd_row[sd_ref["column"]])

            br_ref = comp["brackets_from"]
            br_rows = read_csv(br_ref["csv"])
            filtered = [r for r in br_rows
                        if all(r.get(k) == v for k, v in br_ref["row_filter"].items())]
            brackets = sorted(
                ((float(r[br_ref["rate_column"]]),
                  float(r[br_ref["floor_column"]]),
                  float(r[br_ref["ceiling_column"]]) if r[br_ref["ceiling_column"]] else float("inf"))
                 for r in filtered),
                key=lambda t: t[1],
            )

            taxable = float(comp["wages"]) - std_ded
            tax = 0.0
            for rate, lo, hi in brackets:
                if taxable <= lo:
                    break
                tax += (min(taxable, hi) - lo) * rate

            expected = float(comp["expected"])
            tol = float(comp.get("tolerance", 0.01))
            ok = abs(tax - expected) <= tol
            check(f"{label}: recomputed ${tax:,.2f} matches expected ${expected:,.2f}",
                  ok, f"|{tax:.2f} - {expected:.2f}| > {tol}")
        else:
            check(label, True)  # claim-only check already passed above
        demos_checked += 1

if demos_checked == 0 and manifests:
    check("at least one demo_output declared across manifests", False,
          "no demos found — add demo_outputs to a manifest to enable reproducibility checks")


# ---------------------------------------------------------------------------
# Test 4 — CSV values appear literally in each manifest's raw source
# ---------------------------------------------------------------------------
print("\n[4/4] CSV ↔ raw-source consistency")

for m in manifests:
    raw_path = REPO / m["raw_source"]
    if not raw_path.is_file():
        check(f"{m['id']}: raw source exists", False, f"{m['raw_source']} missing")
        continue
    raw_text = raw_path.read_text()

    for ds in (m.get("csv_datasets") or []):
        csv_path = REPO / ds["file"]
        if not csv_path.is_file():
            check(f"{m['id']} · {ds['file']}", False, "CSV missing")
            continue

        rows = read_csv(str(csv_path))
        amount_col = ds["amount_column"]
        bad = []

        if ds.get("all_amounts_must_appear_in_raw"):
            for r in rows:
                val = r.get(amount_col, "").strip()
                if not val:
                    continue
                try:
                    num = float(val)
                except ValueError:
                    bad.append(f"row {r}: non-numeric '{val}' in {amount_col}")
                    continue
                if not in_text(num, raw_text):
                    bad.append(f"{amount_col}={num:g} not in {m['raw_source']}")

        for ev in (ds.get("expected_values") or []):
            row = find_row(rows, ev["row_selector"])
            if row is None:
                bad.append(f"row {ev['row_selector']} not found")
                continue
            got = float(row[amount_col])
            want = float(ev["value"])
            if got != want:
                bad.append(f"row {ev['row_selector']}: got {got:g}, expected {want:g}")
            if not in_text(want, raw_text):
                bad.append(f"row {ev['row_selector']}: ${int(want):,} not in {m['raw_source']}")

        check(f"{m['id']} · {ds['file']}", not bad,
              "; ".join(bad) if bad else "")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
if failures:
    print(f"FAILED — {len(failures)} issue(s):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(f"All checks passed. Manifests: {len(manifests)}. KB is internally consistent.")
