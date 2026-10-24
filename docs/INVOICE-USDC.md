# Invoice for a spend audit — USDC on Base

No account, no dashboard. The invoice is a signed JSON document: the client keeps it and can
verify it with the same tool that verifies a receipt.

## What we send

```json
{
  "invoice": {
    "id": "NID-2026-0001",
    "issued_at": "2026-10-26T10:00:00Z",
    "due_at": "2026-11-02T10:00:00Z",
    "seller": "Nidhipati (working name)",
    "buyer": "<client legal name as given>",
    "service": "Agent spend audit, up to 12 months of records",
    "amount": {"value": "2500.00", "asset": "USDC", "network": "eip155:8453"},
    "pay_to": "<address from the signed invoice, never from chat>",
    "terms": "Payment in full before delivery. No refund after the report is delivered.",
    "signature": {"alg": "Ed25519", "key_id": "<fingerprint>", "value": "<base64url>"}
  }
}
```

`nidhipati-proof verify invoice.json --pubkey <fingerprint key>` checks the signature, the
amount and the payee. A payment instruction in a chat message is not an invoice.

## What we do not do

- No custody: the client pays the address in the invoice directly, we never hold funds.
- No card details over chat; if a card is required, the client uses a provider that accepts
  the entity, and we invoice the provider's reference.
- No auto-renewal and no stored payment method for the retainer: each month is a new
  signature.

## Confirmation

A transfer is considered paid when the transaction is visible on the block explorer and the
amount and asset match the invoice. We reply with a signed receipt (the same `proof-of-spend`
document) and the report follows.

## Refund

- Client cancels before we start: full refund, same asset.
- We cannot deliver in 10 working days: full refund, no discussion.
- After delivery: no refund; the report stands on its own evidence.
