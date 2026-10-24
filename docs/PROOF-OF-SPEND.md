# Proof of Spend — draft v0.1

**Status:** proposal, not a standard. Open for review.  
**Purpose:** a portable, verifiable receipt for an AI-agent payment. It answers four questions:

1. **Who** acted — agent, operator, key.
2. **What was authorized** — mandate, policy, limits.
3. **What was actually paid** — amount, asset, network, payee, tx hash.
4. **What was consumed / refunded** — usage, unit price, refund.

A dashboard shows spend. A Proof of Spend lets a merchant, wallet, auditor, or buyer verify that the charge was inside the mandate and matches the settlement.

---

## 1. Design rules

- **No custody.** The receipt describes a payment; it does not hold funds.
- **No token.** It is a signed JSON document, not an asset.
- **Verifiable offline.** Canonical JSON + signature; the chain is the settlement source.
- **Rail-agnostic.** x402/USDC, stablecoin transfer, card/on-ramp reference, or invoice.
- **Minimal.** Only fields needed to verify authorization, amount, and receipt.
- **Privacy-aware.** Hashes and IDs, not customer data or secrets.

---

## 2. Document

```json
{
  "version": "pos/0.1",
  "receipt_id": "pos_01J...",
  "issued_at": "2026-10-24T12:00:00Z",
  "agent": {
    "id": "agent://example/research-1",
    "operator": "did:web:example.com",
    "key_id": "ed25519:..."
  },
  "mandate": {
    "hash": "sha256:...",
    "policy_id": "policy://example/agent-spend-v3",
    "expires_at": "2026-10-25T00:00:00Z"
  },
  "action": {
    "type": "api.call",
    "resource": "https://api.example.com/v1/search",
    "quote_id": "quote_..."
  },
  "payment": {
    "amount": "0.05",
    "asset": "USDC",
    "network": "eip155:8453",
    "payee": "0x...",
    "tx_hash": "0x...",
    "settled_at": "2026-10-24T12:00:03Z"
  },
  "usage": {
    "unit": "request",
    "quantity": "1",
    "unit_price": "0.05"
  },
  "refund": {
    "amount": "0",
    "tx_hash": null
  },
  "verdict": {
    "decision": "allow",
    "policy_version": "3",
    "reasons": ["amount_within_daily_limit", "payee_allowlisted"]
  },
  "evidence": {
    "artifact_hash": "sha256:...",
    "attestation_id": "att_..."
  },
  "signature": {
    "alg": "Ed25519",
    "key_id": "ed25519:...",
    "value": "base64url..."
  }
}
```

---

## 3. v0.1 implementation

The reference validator lives in `nidhipati_proof/`.

- **Canonical form:** sorted-key, compact UTF-8 JSON (v0.1).
- **Signed payload:** the document with `signature.value` set to `""`.
- **Signature:** Ed25519, base64url.
- **Public key:** supplied separately (`--pubkey` PEM/base64url/hex); not embedded in the document.
- **On-chain check:** not implemented in v0.1; result explicitly says `onchain_verified=false`.
- **CLI:**

```bash
nidhipati-proof keygen --out-dir keys
nidhipati-proof sign receipt.json --key keys/private.pem --out signed.json
nidhipati-proof verify signed.json --pubkey keys/public.pem
```

## 4. Verification

A verifier MUST:

1. Parse canonical JSON (RFC 8785 or an agreed canonicalization).
2. Verify the signature with `agent.key_id`.
3. Hash the mandate document; compare with `mandate.hash`.
4. Check `mandate.expires_at` at `payment.settled_at`.
5. Check `payment.amount` against the mandate's per-tx/daily limit and allowlist.
6. Check `payment.asset`, `payment.network`, `payment.payee` against the allowlist.
7. Verify `payment.tx_hash` on-chain: amount, asset, network, payee.
8. Check `usage.quantity × usage.unit_price` is consistent with `payment.amount` (or an agreed formula).
9. Check `refund.amount` and `refund.tx_hash` if non-zero.
10. Reject if `receipt_id` or `(agent.id, mandate.hash, action.quote_id)` was already used (replay).

A verifier SHOULD return a short verdict:

```json
{"ok": true, "reason": "within_mandate", "receipt_id": "pos_01J..."}
```

---

## 5. What it is not

- Not a guarantee that the service was good.
- Not a legal audit or financial statement.
- Not a privacy tool that hides the transaction from the chain.
- Not a replacement for the payment rail's own receipt.

---

## 6. Roadmap

- **v0.1** — JSON schema, example, human verification checklist.
- **v0.2** — Ed25519/JWS signing, canonicalization test vectors.
- **v0.3** — x402 adapter: read `PAYMENT-REQUIRED`/`PAYMENT-SIGNATURE`, emit a receipt.
- **v0.4** — verifier CLI + GitHub Action.
- **v1.0** — stable schema after 3 implementations.

---

## 7. Why this can matter

- **Merchants** can verify an agent's mandate before fulfilling.
- **Wallets** can show a human-readable receipt, not just a tx hash.
- **Buyers** can audit agent spend and prove overcharge.
- **RWA/treasury** can reuse the pattern for proof-of-reserve/reporting (separate document).
- **Insurers/auditors** get a portable evidence trail.

Open a discussion or issue if you want to implement it: https://github.com/mrpkk/agent-trust-scan/issues
