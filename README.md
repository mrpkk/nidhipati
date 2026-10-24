# Nidhipati

**Proof of Spend for AI agents.** A signed receipt that proves what an agent was authorized to pay, what it actually paid, what it used and what was refunded. Not a token, not custody, not another payment rail.

> Рельсы двигают деньги. Nidhipati доказывает, что движение было правильным.

**Status:** draft v0.1. Spec + JSON Schema + example. Validator in progress.

## Quick start

```bash
python3 -m pip install -e .[dev]
python3 -m pytest -q
python3 -m nidhipati_proof.cli verify examples/proof-of-spend.example.json --pubkey <base64url>
```

## What it checks

- schema and canonical JSON;
- Ed25519 signature;
- mandate expiry vs settlement time;
- amount, asset, network, payee;
- `usage.quantity × usage.unit_price` vs payment;
- refund ≤ payment;
- verdict `allow` for a settled payment;
- receipt ID/replay (v0.2 store).

## Honest limits

- v0.1 does **not** verify the on-chain transaction; `onchain_verified=false` is explicit.
- It is not a statutory audit, legal, tax, or investment advice.
- It does not guarantee the service was good; it proves the payment was within mandate.
- No custody, no money transmission, no token.

## Docs

- `SPEC.md` — product, architecture, modules, SEO, monetization, 30/60/90.
- `PROGRESS.md` — slices, acceptance, metrics.
- `docs/PROMPT-AND-IDEAS.md` — prompt and decisions for RAG.
- `docs/SEO-MONETIZATION.md` — keywords, pages, funnel, pricing.
- `schemas/proof-of-spend.schema.json` — v0.1 schema.
- `examples/proof-of-spend.example.json` — example.

## License

Apache-2.0.
