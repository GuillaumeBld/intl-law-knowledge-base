# Demo output — Federal tax for a single filer earning $75,000 wages (TY 2025)

_Generated from the knowledge base on 2026-04-19. Every figure traces to a source in `raw/` via a file in `wiki/` or `data/`._

## Scenario
- Filing status: single
- Wages: $75,000
- No other income, no above-the-line adjustments, no itemized deductions
- Taxes year 2025 (return filed 2026)

## Step 1 — Taxable income
Standard deduction for single filer, TY 2025: **$15,000**
→ taxable income = 75,000 − 15,000 = **$60,000**
_Source: [[us-fed-2025-standard-deduction]] → `raw/irs-ir-2024-273-tax-year-2025-inflation-adjustments.md`_

## Step 2 — Apply 2025 single brackets
_Source: [[us-fed-2025-marginal-rates]] → `data/us-fed-2025-brackets.csv`_

| Slice | Income in slice | Rate | Tax |
|---|---:|---:|---:|
| $0 – $11,925 | $11,925 | 10% | $1,192.50 |
| $11,925 – $48,475 | $36,550 | 12% | $4,386.00 |
| $48,475 – $60,000 | $11,525 | 22% | $2,535.50 |
| **Total** | | | **$8,114.00** |

- **Marginal rate:** 22%
- **Effective rate:** 8,114 / 75,000 ≈ **10.8%**

## Step 3 — AMT check
AMT exemption for an unmarried filer, TY 2025: **$88,100**, phase-out begins at $626,350.
At $60,000 AMTI, the exemption fully offsets AMT income → **no AMT due**.
_Source: [[us-fed-2025-amt]]_

## Answer
**Federal income tax owed: $8,114.00** (before withholding, credits, or other adjustments).

---

## What this demo proves the KB can do
1. **Ground a numeric answer.** Every rate, threshold, and deduction cites a wiki page, which cites the raw IRS release.
2. **Separate prose from tables.** Narrative lives in `wiki/*.md`; rate schedules live in `data/*.csv` so a program (or an LLM doing text-to-SQL) can query them directly.
3. **Keep sources immutable.** `raw/` is untouched; if the IRS updates guidance, we drop a new file in `raw/` and rebuild the wiki.
4. **Stay auditable.** Every claim in this output points back to the 56-line scraped IRS release — no hallucinated numbers.
