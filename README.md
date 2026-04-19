# intl-law-knowledge-base

A grounded, source-traceable knowledge base for **international law** — designed to feed LLMs verifiable legal facts with deterministic answers.

> **Determinism principle:** the same legal question + same facts + same grounded KB must produce the same answer every time. Every claim traces to a primary source in `raw/`.

[![verify](https://github.com/GuillaumeBld/intl-law-knowledge-base/actions/workflows/verify.yml/badge.svg)](https://github.com/GuillaumeBld/intl-law-knowledge-base/actions/workflows/verify.yml)

## Browse the KB

**→ [guillaumebld.github.io/intl-law-knowledge-base](https://guillaumebld.github.io/intl-law-knowledge-base/)** — live viewer on GitHub Pages.

Sidebar groups articles by Wiki / Outputs / Data / Raw. Every `.md` renders with wiki links clickable; every `.csv` renders as a table.

<details>
<summary>Run locally (optional)</summary>

```bash
python3 -m http.server 8080
# open http://localhost:8080/
```

</details>

## Structure

| Folder | Contents | Format rule |
|---|---|---|
| `raw/` | Immutable primary sources (treaty texts, judgments, official gazettes) | `.md` (converted from HTML) or original `.pdf` + `.md` summary |
| `wiki/` | Narrative articles, one per instrument/concept/case, cross-linked | `.md` only |
| `data/` | Ratification tables, reservations, rates, coverage configs | `.csv` for tabular, `.yaml` for config |
| `outputs/` | Generated answers, reports, demo analyses | `.md` |

**Why this matters:** wrapping prose in JSON degrades LLM reasoning by 27–49 points (EMNLP 2024). This KB keeps prose as Markdown, tables as CSV, configs as YAML — so an LLM can either read prose with full fidelity or run text-to-SQL against clean structured data.

## Scope

Progressive coverage across international legal regimes:

1. **Public international law** — UN Charter, ICJ Statute, VCLT, state responsibility
2. **Human rights** — UDHR, ICCPR, ICESCR, regional systems (ECHR, IACHR, ACHPR)
3. **Humanitarian / criminal law** — Geneva Conventions, Rome Statute, ad hoc tribunals
4. **International economic law** — WTO (GATT/GATS/TRIPS/DSU), BITs, ICSID, international tax (OECD/UN Models, MLI, Pillar One/Two, bilateral tax treaties)
5. **Law of the sea, environment, space** — UNCLOS, UNFCCC/Paris, Outer Space Treaty
6. **Private international law** — Hague Conventions, recognition/enforcement
7. **Domestic implementations** — included where they illustrate treaty interpretation or cross-border effect

See [`CLAUDE.md`](./CLAUDE.md) for the full schema.

## Current coverage

**Seed (proof of pattern):** US federal tax, tax year 2025. Computes grounded tax calculations for a US single filer from authoritative IRS sources.

See [`wiki/INDEX.md`](./wiki/INDEX.md), [`data/jurisdictions.yaml`](./data/jurisdictions.yaml), [`data/instruments.yaml`](./data/instruments.yaml), [`data/tax-years.yaml`](./data/tax-years.yaml) for what's grounded today.

## Demo

[`outputs/demo-single-filer-75k-2025.md`](./outputs/demo-single-filer-75k-2025.md) — computes US federal tax on $75K wages for a 2025 single filer: **$8,114**. Every rate and threshold cites a wiki page, which cites the IRS release in `raw/`.

This demo proves the grounding loop: **raw source → structured data + wiki → traceable answer**. The same loop scales to any treaty, judgment, or body of law.

## Grounding rules for LLM use

- Every factual claim must trace to a source in `raw/`.
- Cite the source file for every number, date, article reference, or legal proposition.
- Flag jurisdiction + instrument + effective date on every rule.
- Uncertain/outdated content carries `> STATUS: needs-verification`.
- Prefer primary sources (treaty texts, judgments, official publications) over secondary commentary.

**Using this KB with an LLM:** paste [`GROUNDING_PROMPT.md`](./GROUNDING_PROMPT.md) as the system prompt. It encodes the citation contract so the model refuses out-of-coverage questions instead of hallucinating.

## Verification

`scripts/verify.py` runs four determinism checks and is wired into CI (see badge above):

1. Every file referenced by `index.html` exists on disk.
2. Every `[[wiki-link]]` and `raw/|wiki/|data/|outputs/` path reference resolves.
3. The demo tax calculation reproduces from CSV data (prevents prose/data drift).
4. Every numeric value in `data/us-fed-2025-*.csv` appears literally in the raw IRS source.

Run locally:

```bash
python3 scripts/verify.py
```

Exit 0 = KB is internally consistent. CI blocks any PR that fails.

## Workflow

1. **Scrape** an authoritative source into `raw/` (immutable, append-only).
2. **Compile** a wiki article in `wiki/` that summarizes and cross-links it.
3. **Extract** any tabular data (ratifications, rates, deadlines) into `data/*.csv`.
4. **Ask questions** against the wiki; save answers to `outputs/`.
5. **Update** `data/jurisdictions.yaml`, `data/instruments.yaml`, and `data/tax-years.yaml` as coverage grows.

## License

Source material in `raw/` retains its original copyright (government works, UN documents, court judgments are generally in the public domain or freely reproducible for legal research; verify per source). This repository's schema, wiki, and code are provided for research and LLM-grounding purposes.
