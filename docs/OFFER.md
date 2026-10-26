# Nidhipati — offer

**What it is.** An independent audit of what your AI agents spent: where money left without a
permission, a reason, or a refund. Not a dashboard, not a payment rail, not a token, not custody.

**Who buys.** Teams running agents with real budgets — x402 paid APIs, metered model calls,
tool marketplaces — where the monthly bill is bigger than the team's ability to read it line
by line.

---

## Free scan (no card; browser tool needs no account)

You send records (CSV or JSON, one row per charge), we return the audit report as Markdown
and JSON within two working days. Records are never posted publicly.

- **Do it yourself first:** `nidhipati-spend audit your.csv` or the browser tool
  <https://mrpkk.github.io/nidhipati/free-spend-audit.html> — same checks, nothing uploaded,
  no account. If the tool already answers your question, you do not need us.
- **Ask for the human review:** email <maxim.pkk@gmail.com> or Telegram <https://t.me/mrpkk>
  with the downloaded report (not raw rows). No GitHub account needed. If you prefer GitHub,
  [open a private scan request](https://github.com/mrpkk/nidhipati/issues/new?template=free-spend-audit.yml);
  that issue is public, so ask the question only and never paste records, invoices, keys, or
  customer data.
- **What you get free:** the findings, the row numbers, the three amounts, and the list of
  what could not be checked from your records.

We publish no client names and no numbers from a free scan without written permission. If a
scan finds nothing, we say it found nothing.

## First 3 paid audits — $1,250, in exchange for a case

The first three paid audits are **$1,250 instead of $2,500**. In exchange we ask for a
public case study with anonymized numbers, published only if the audit finds something
worth publishing. If you do not want the case, the price stays $2,500.

After the first three, the price returns to $2,500.

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

### The $5,000 finding guarantee

If the paid audit does **not identify at least $5,000 in documented overcharges or refund
opportunities** from the records and invoices you provide within 10 working days, we refund
the audit fee.

**"Documented"** means each amount has a row number, a receipt/invoice or transaction hash,
and a written basis. Estimates and "could be" do not count. The guarantee is about
**identified amounts**, not what a provider actually returns; the provider decides recovery.
The refund is in the same asset and network you paid, minus network fees.

**How to pay:** request an invoice at maxim.pkk@gmail.com or Telegram @mrpkk. USDC on Base
works now; the address comes only from the signed invoice. Bank transfer only if an
entity/IBAN is available. Card checkout is **not live as of 26.10.2026**; ask for a card
link and we will say plainly whether one is available. The invoice is a signed JSON
document; the receipt is verifiable with `nidhipati-proof verify`.

## Monthly retainer — $1,500/mo

The same audit every month, plus alerting on the rules you choose (for example: any charge
above a quote, any failed-but-billed row, any new payee). 30 days notice, no auto-renewal.

## Share of verified savings — 20 %

No fixed fee: we take 20 % of what is actually returned to you by providers as a result of
the audit. Requires the fixed audit first, or the free scan as evidence. If nothing comes
back, you owe nothing.

**India (PPP):** $1,250 for the audit, $750/mo retainer, same scope.

## Enterprise — first step $250, then first 3 at $1,250; white-label from $50,000

- **Reserve disclosure review — $250** (credited toward a full report): a 2-page
  review of your public reserve or NAV page against the 12-question checklist.
  Public data only; no private files; 3 working days. If you proceed to a full
  single-asset report, the $250 is credited. Sample:
  <https://mrpkk.github.io/nidhipati/sample-reserve-review.html>.
- **First 3 single-asset reports: $1,250** (instead of $5,000), in exchange for a public
  case study with anonymized numbers. The case is published only if the report verifies
  and you approve the wording. After the first 3, the price returns to $5,000.
- **Productized** ($5,000+): one RWA asset/date, NAV + source hashes, signed report.
- **Issuer / white-label** ($50,000+): multi-asset, custom methodology, ZK predicate,
  white-label, buyer verification pack.
- **Verification guarantee:** if the signed report does not verify offline with the
  published key, the fee is refunded. That is a statement about the file, not about the
  issuer's solvency or the accuracy of its source data.
- Sample: <https://mrpkk.github.io/nidhipati/sample-reserve-report.html> — synthetic,
  not a client, not a statutory audit.

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
