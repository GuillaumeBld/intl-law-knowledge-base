# Knowledge Base Schema — International Law

## What This Is
A grounded knowledge base for **international law** — treaties, conventions, customary international law, ICJ/ECHR/WTO jurisprudence, and domestic implementations — structured to feed LLMs verifiable, source-traceable legal facts.

Initial seed: **US federal tax law (tax year 2025)** as proof of the grounding pattern. This will be generalized and expanded across international legal regimes.

## How It's Organized

- `raw/` — unprocessed source material. Primary sources only: treaty texts, court judgments, official gazettes, UN/OECD/WTO documents, state-party communications. Never modify these files.
- `wiki/` — organized narrative knowledge (.md), one article per concept/instrument/case. AI maintains this entirely.
- `outputs/` — generated reports, answers, analyses (.md). Each output cites sources back to `raw/`.
- `data/` — structured tabular and config files (.csv for tables, .yaml for coverage/config).

## Scope — International Legal Regimes

The KB is designed to cover (progressively):

1. **Public international law**
   - UN Charter, ICJ Statute
   - Vienna Convention on the Law of Treaties (VCLT 1969)
   - State responsibility, sovereignty, recognition
2. **Human rights**
   - UDHR, ICCPR, ICESCR
   - Regional: ECHR, IACHR, ACHPR
3. **International humanitarian / criminal law**
   - Geneva Conventions + Additional Protocols
   - Rome Statute (ICC)
   - Ad hoc tribunals (ICTY, ICTR, SCSL)
4. **International economic law**
   - WTO agreements (GATT, GATS, TRIPS, DSU)
   - Bilateral Investment Treaties (BITs), ICSID
   - **International tax law** (OECD Model Tax Convention, UN Model, MLI, Pillar One/Two, tax treaties) ← bridges from the US-Fed seed
5. **Law of the sea, environment, space**
   - UNCLOS, climate regime (UNFCCC/Paris), Outer Space Treaty
6. **Private international law / conflict of laws**
   - Hague Conventions
   - Recognition and enforcement of foreign judgments
7. **Domestic implementations**
   - US federal tax (seed — Rev. Proc. 2024-40 / IRC Title 26)
   - Other state practice as it illustrates treaty interpretation

## File Format Rules

- Narrative knowledge, treaty commentary, case law → `.md` in `wiki/`
- Tabular data (rates, thresholds, ratification dates, reservations, deadlines) → `.csv` in `data/`
- Coverage / jurisdiction / instrument metadata → `.yaml` in `data/`
- Well-defined nested schemas (e.g., treaty article structures) → `.json` in `data/`
- Never use `.md` for inherently tabular/structured config.
- Never wrap prose in JSON — degrades LLM reasoning by 27–49 points (EMNLP 2024).
- Web-scraped HTML → convert to `.md` before saving in `raw/`.
- Original PDFs (official gazettes, court judgments) → keep `.pdf` in `raw/` + add `.md` summary alongside.

## Wiki Rules

- Every topic/instrument/case gets its own `.md` file in `wiki/`.
- Every wiki file starts with a one-paragraph summary.
- Link related topics using `[[topic-name]]` (Obsidian-style wiki links).
- Maintain `wiki/INDEX.md` listing every article with a one-line description, grouped by regime.
- When new raw sources land, update the affected wiki articles.

## Grounding Rules for LLM Use

Every factual claim **must** be traceable to `raw/`. LLMs consuming this KB follow these rules:

- **Cite the source file** for every numeric figure, date, article number, or legal proposition.
- **Flag jurisdiction + instrument + effective date** on every rule (e.g., "VCLT art. 31, in force 27 Jan 1980" or "US-FED, tax year 2025").
- Mark uncertain/outdated content with `> STATUS: needs-verification`.
- Prefer **primary sources** (treaty texts, judgments, official tax-authority pubs) over secondary commentary.
- Keep `data/jurisdictions.yaml`, `data/instruments.yaml`, and `data/tax-years.yaml` current as coverage grows.

## Determinism Principle

"Legal determinism" here means: **the same legal question, asked with the same facts and the same grounded KB, must produce the same answer every time.** That requires:

1. **Source immutability** — `raw/` is append-only; never edit scraped sources.
2. **Explicit citation** — every answer in `outputs/` carries its trace to `raw/`.
3. **Separation of prose and data** — numeric reasoning runs against `.csv`, never against prose paragraphs.
4. **Versioned coverage** — `data/tax-years.yaml` and `data/instruments.yaml` declare what's known and what isn't, so the LLM refuses to answer outside coverage rather than hallucinating.

## Current Coverage

See `data/jurisdictions.yaml` and `data/tax-years.yaml`. As of initial seed:
- US-FED · tax year 2025 · partial (items in IR-2024-273)
