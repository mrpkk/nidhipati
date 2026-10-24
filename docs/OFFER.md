# Nidhipati — offer

**What it is.** An independent audit of what your AI agents spent: where money left without a
permission, a reason, or a refund. Not a dashboard, not a payment rail, not a token, not custody.

**Who buys.** Teams running agents with real budgets — x402 paid APIs, metered model calls,
tool marketplaces — where the monthly bill is bigger than the team's ability to read it line
by line.

---

## Free scan (no card, no account)

You send records (CSV or JSON, one row per charge), we return the audit report as Markdown
and JSON within two working days.

- **Ask for it:** [open an issue](https://github.com/mrpkk/nidhipati/issues/new?template=free-spend-audit.yml)
- **Do it yourself first:** `nidhipati-spend audit your.csv` — same checks, same wording.
  If the tool already answers your question, you do not need us.
- **What you get free:** the findings, the row numbers, the three amounts, and the list of
  what could not be checked from your records.

We publish no client names and no numbers from a free scan without written permission. If a
scan finds nothing, we say it found nothing.

## Paid audit — $2,500 (fixed, 10 working days)

For teams that want the answer checked, not just computed:

| Included | Detail |
|---|---|
| Full audit of up to 12 months of records | every row, not a sample |
| Provider reconciliation | we match your records against provider invoices and, where you give read-only access to a block explorer export, against settlements |
| Evidence file | every finding with row number, receipt, and the rule it violates, in a form you can send to a provider |
| Recovery pack | a letter per provider: what was charged, what should have been, what to ask back |
| One call-free review session | written answers to your questions, 5 working days |

**Not included, stated plainly:** no legal advice, no recovery guaranteed, no custody of your
money, no statutory audit opinion. If a charge turns out to be correct, it stays correct.

**How to pay:** USDC on Base to the address in the invoice, or card through a payment
provider that accepts non-RF businesses. Invoice is issued as a signed JSON document; the
receipt is verifiable with `nidhipati-proof verify`.

## Monthly retainer — $1,500/mo

The same audit every month, plus alerting on the rules you choose (for example: any charge
above a quote, any failed-but-billed row, any new payee). 30 days notice, no auto-renewal.

## Share of verified savings — 20 %

No fixed fee: we take 20 % of what is actually returned to you by providers as a result of
the audit. Requires the fixed audit first, or the free scan as evidence. If nothing comes
back, you owe nothing.

**India (PPP):** $1,250 for the audit, $750/mo retainer, same scope.

---

## Honest limits of v0.2

- The audit reads the records you provide. Missing rows cannot be found.
- No on-chain verification yet: `onchain_verified` is false in every report.
- Amounts are estimates to discuss with a provider, not a legal claim.
- The rule set is public: 10 checks in `docs/AGENT-SPEND-AUDIT.md`. You can read exactly
  what we look for before paying anything.

## Why the price is fixed

An hourly rate rewards a slow auditor. A percentage of savings rewards an inflated number.
A fixed price is the only shape where our interest — find the real thing, say it in one
document — matches yours.

## Contact

Issues are fine: https://github.com/mrpkk/nidhipati/issues — written only, no calls.
