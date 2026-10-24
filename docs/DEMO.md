# DEMO — Nidhipati

Everything below runs locally; no account, no keys, no network.

## 1. Spend audit

```bash
python3 -m pip install -e ".[dev]"
python3 -m nidhipati_proof.spend_cli audit examples/spend-sample.csv
```

Real output (abridged):

```
# Agent spend audit

Rows read: 44 · settled $0.661 · spent without a reason $0.14 ·
above the usual price $0.36 · over the limit $0 · errors 4, warnings 7

| row | code | severity | agent | $ | detail | evidence |
| 5 | duplicate_charge | error | agent-writer | 0.02 | same tx_hash as row 2 | 0xaaa1 |
| 7 | price_escalation | error | agent-writer | 0.03 | settled 0.05 above quote 0.02 | 0xaaa5 |
| 8 | failed_but_billed | error | agent-writer | 0.03 | status 'failed' with 0.03 charged | 0xaaa6 |
| 9 | missing_refund | error | agent-writer | 0.06 | charged 0.10 for actual 0.04, refund not recorded | 0xaaa7 |
| 9 | model_overpay | warning | agent-writer | 0.08 | paid 0.10 against a median 0.02 | 0xaaa7 |
| 45 | runaway_loop | warning | agent-loop | 0 | 31 calls in 60s (threshold 30) | 0xccc30 |

> Estimates from the records provided. Nothing was recovered; nothing was verified
> on-chain in v0.2. Confirm each row against the provider's invoice before acting.
```

The three amounts are deliberately separate. Adding them into one “we saved $X” would be
dishonest.

## 2. Proof of Spend

```bash
nidhipati-proof keygen --out-dir keys
nidhipati-proof sign examples/proof-of-spend.example.json --key keys/private.pem --out /tmp/signed.json
nidhipati-proof verify /tmp/signed.json --pubkey keys/public.pem
```

Expected: `OK`, all checks true, and `warning: onchain_verified=false`.

## 3. Reserve report

```bash
python3 -m nidhipati_proof.reserve_cli report examples/reserve.example.json --key keys/private.pem
```

The report refuses to compute if a reserve row has no price; it marks the verdict `incomplete`
and `backing_ratio: null`. That is intentional.

## 4. Resolve / prediction evidence

```bash
python3 -m nidhipati_proof.resolve_cli report examples/resolve.example.json --key keys/private.pem
```

It returns `supported`, `disputed`, `single_source` or `insufficient`; it never picks a winner.

## 5. Reconcile

```bash
python3 -m nidhipati_proof.reconcile_cli report examples/invoices.example.csv examples/transactions.example.csv
```

One transfer is one entry; a duplicate is reported once, not twice.

## Honest limits

- v0.2 reads only the records you provide; missing rows cannot be found.
- No on-chain verification; every report says `onchain_verified=false`.
- No custody, no private keys, no money movement.
- Not a statutory audit, legal, tax, or investment advice.
