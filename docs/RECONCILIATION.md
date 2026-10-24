# Reconciliation — two files, one truth

## The problem

The treasury sheet says four clients owe money. The wallet export says money arrived. Neither
file answers the only question that matters: *which invoices are actually closed, and what is
this transfer nobody invoiced?*

## What it does

Input: invoices (CSV/JSON) and transfers (CSV/JSON). Output: matched pairs, invoices with no
transfer, transfers with no invoice, and findings.

Matching, in order:

1. **Memo** — the transfer memo contains the invoice id, inside the invoice window.
2. **Amount** — the exact amount and asset, inside the invoice window.

Window: from one day before the invoice date to the due date plus one day. Without `due_at`,
thirty days from creation. Anything outside the window is not a match, however convenient.

## Findings

| Code | Severity | Meaning |
|---|---|---|
| `duplicate_payment` | error | one invoice, more than one full-amount transfer |
| `amount_mismatch` | error | the memo names the invoice, the amount does not match |
| `unpaid_invoice` | error | no transfer inside the window |
| `duplicate_receipt` | error | the same `tx_hash` appears twice — a broken export |
| `late_payment` | warning | paid after the due date |
| `unmatched_receipt` | warning | money arrived with no invoice (counted once, never twice) |

A transfer that duplicates a payment is reported **once**, as a duplicate — it does not also
appear as "money without an invoice". Double counting the same transfer would inflate both
lists and make the totals meaningless.

## Output

- JSON: totals for matched and unpaid, every pair with its basis (`memo` or `amount`).
- Markdown: the same, readable.
- CSV: `invoice_id, tx_hash, amount, asset, status, basis` — for the accountant.
- Optional Ed25519 signature over the JSON (`--key`).

## Honest limits

- No chain read, no custody, no private keys, no funds moved.
- A match by amount and time is a strong hint, not proof of identity of the payer.
- Transfers outside the window are not "wrong", they are simply not matched: widen `due_at`
  rather than editing the tool's output.
- Assets are compared as symbols (`USDC`), not contract addresses; a wrapped variant looks
  like a different asset, which is safer than the opposite.

## Run

```bash
nidhipati-reconcile run examples/invoices.example.csv examples/transactions.example.csv \
  --csv matches.csv --markdown report.md --out report.json
```

Exit code: `0` everything closed, `1` findings, `2` bad input.
