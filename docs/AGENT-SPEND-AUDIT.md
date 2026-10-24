# Agent spend audit — what it does and what it refuses to claim

## The problem

An agent with a budget written in a prompt does not have a budget. It has a sentence it can
argue with. The bill arrives anyway: a retry that was charged, a call that failed but settled,
an authorisation of 10 that used 4 and returned nothing.

## What it reads

CSV or JSON, one row per charge. Required: `ts`, `agent_id`, `tool`, `quote`, `settled`,
`status`. Optional: `model`, `actual`, `refund`, `asset`, `network`, `tx_hash`, `payee`.
A missing column is an error, not an empty value — a report built on blanks is a guess.

## What it finds

| Code | Severity | Rule |
|---|---|---|
| `duplicate_charge` | error | same `tx_hash` twice; or equal charge from the same agent, tool, amount and asset within 120s **where neither row has a receipt** |
| `price_escalation` | error | `settled > quote × 1.01` |
| `failed_but_billed` | error | `status` in failed/error/rejected/timeout/5xx and `settled > 0` |
| `missing_refund` | error | `settled > actual` and no refund recorded |
| `runaway_loop` | warning | more than 30 calls in any 60-second window for one agent |
| `model_overpay` | warning | above 3× the same agent's median for the same tool and model, with at least 3 rows |
| `unknown_asset`, `unknown_network`, `missing_payee` | warning | the record does not identify where the money went |
| `budget_bypass` | warning | no policy file given — the limit lives in a prompt |
| `budget_exceeded` | error | per-agent `limit_usd` from the policy file is exceeded |

Two receipts are two payments. The audit does not call equal amounts duplicates when each
has its own `tx_hash`: repeating a cheap call is not fraud, and a report that says otherwise
is noise. This was a real bug on 25.10.2026 — a 20-call loop produced 190 "duplicates" and
an "overpay" larger than the total spend. The regression test is
`test_two_receipts_are_two_payments_not_a_duplicate`.

## Three amounts, never one

| Field | Meaning | Can you act on it |
|---|---|---|
| `estimated_overpay_usd` | duplicates, escalation, failed-but-billed, refunds not returned | yes: this is money to ask back |
| `overpay_vs_median_usd` | above the agent's own usual price | as a question, not a claim |
| `budget_overrun_usd` | above the policy limit | yes, as a control failure — the money may have bought real work |

Adding them into a single "we saved you $X" number would be dishonest: only the first is money
that left without a reason.

## Policy file

```json
{"agents": {"agent-writer": {"limit_usd": "0.20"}}}
```

Without it the report says `budget_bypass`: not because the agent did anything wrong, but
because nothing was there to stop it.

## Limits, stated plainly

- v0.2 works on the records you provide. It does not query the chain, the provider or the
  invoice system. `onchain_verification` is false.
- A row that is missing from the file cannot be found. This is an audit of what was recorded.
- Amounts are estimates for a conversation with the provider, not a legal claim.
- No custody, no payment rails, no token: the product reads records and signs findings.

## Run

```bash
nidhipati-spend audit examples/spend-sample.csv --policy examples/spend-policy.example.json
nidhipati-spend audit records.csv --json > report.json
```

Exit code: `0` clean, `1` errors found, `2` bad input.
