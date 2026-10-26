# Enterprise: private reserve attestation for RWA / stablecoin issuers

**One line:** prove that reserves back the token without publishing every wallet, every line, or the full NAV inputs.

**Price:** a **$250 reserve disclosure review** of your public page (credited toward a
full report); first 3 single-asset reports **$1,250** (instead of $5,000) in exchange for an
anonymized public case study; then productized reports from **$5,000**; custom
issuer/white-label engagement from **$50,000**. If the signed report does not verify
offline with the published key, the fee is refunded.
**Buyer:** issuer, fund, treasury, or platform with a tokenized asset and a reserve question it cannot answer with a screenshot.

---

## 1. The problem

An issuer says "1 token = $1 of reserves". A buyer asks:

- what exactly backs it,
- how NAV is calculated,
- which sources were used,
- what happens if one line has no price,
- can we verify it without trusting the issuer's dashboard.

A PDF and a custodian letter do not answer the last question. A full disclosure answers it but exposes positions, counterparties, and strategy.

**Nidhipati proves the claim, not the portfolio.**

---

## 2. What we deliver

| Deliverable | Detail |
|---|---|
| Methodology | formulas, haircuts, source policy, stale-price rule, exclusions |
| Signed JSON | every line has a `sha256:` proof, source and timestamp; Ed25519 signature |
| Human report | 6–10 pages: composition, NAV, ratio, what could not be checked |
| Verification key | the buyer verifies offline; no trust in our server |
| Source hashes | custodian statement, price feeds, on-chain supply |
| One retest | after agreed fixes |
| Optional ZK predicate | "reserves ≥ liabilities" without revealing the amount (Ṛta/Groth16) |

**What it is not:** statutory audit, legal opinion, custody, token issuance, investment advice, or a promise that a buyer will accept the report.

---

## 3. Scope

- One issuer, one asset, one reporting date.
- Up to 25 reserve lines; more by change order.
- Sources: custodian statement, issuer NAV file, public price feeds, on-chain supply.
- 10 business days from complete data.
- Written Q&A only; no calls required.

**Refusal is part of the product:** if a line has no price, the verdict is `incomplete` and `backing_ratio: null`. We do not exclude the line to make the ratio look better, and we do not invent a price.

---

## 4. Why us

- `attest` — 585 tests, live verifier, signed verdicts, four independent layers.
- `nidhipati-reserve` — NAV, haircuts, source hashes, `incomplete` instead of a guess.
- `Ṛta` — Groth16 predicates: prove a threshold without revealing the amount.
- `drift` — mandate checks for the payment path.
- No custody, no token, no dashboard lock-in.

**Honest limit:** Ṛta is testnet/mainnet-ready in code, but the ceremony is one-sided and there is no external audit. We do not sell it as a trusted ZK guarantee until that changes. The signed NAV report works today.

---

## 5. Demo (10 minutes, written)

1. Run `nidhipati-reserve report examples/reserve.example.json --markdown`.
2. Show `NAV 1,017,900`, `ratio 1.0179`, `backed`, every line with a source hash.
3. Break one price → verdict `incomplete`, ratio `null`.
4. Verify the signature offline with `nidhipati-proof verify`.
5. Show the ZK predicate separately, labeled experimental.

No wallet access, no keys, no customer data in the demo.

---

## 6. Target list (public examples, not contacted)

| Segment | Public examples to verify | Why they fit |
|---|---|---|
| Tokenized treasuries | Ondo, Franklin BENJI, BlackRock BUIDL, Superstate | NAV + custodian + buyer trust |
| Private credit | Maple, Centrifuge, Goldfinch | illiquid lines, stale prices, disclosure tension |
| Tokenized gold | Paxos Gold, Backed, Hashnote | custodian + assay + chain supply |
| Stablecoin issuers | Circle, Tether, First Digital, Mountain | reserve attestation is the product |
| RWA platforms | Securitize, Tokeny, DigiFT | white-label reserve report for issuers |

**Rule:** names are public examples, not leads with verified contacts. Do not send without checking the current site, the right person, and owner approval.

---

## 7. First message (short, no attachment)

> Hi {name} — you publish a reserve or NAV claim for {asset}. We build a signed reserve attestation that a buyer can verify offline: every line has a source hash, missing prices fail closed, and the full portfolio is not disclosed.
>
> One question: who signs off on the reserve methodology today — the issuer, the custodian, or an outside auditor?
>
> If useful, I can send a 2-page scope and a synthetic sample. No call needed.

**Do not** claim a client, a partnership, or a regulatory approval. We have none yet.

---

## 8. Metrics

| Metric | Target |
|---|---:|
| Public targets verified | 10 |
| Personalized messages | 10 |
| Replies | 2–3 |
| Written demo | 1 |
| Paid pilot / LOI | 1 |

**This is the only path in the portfolio with a $50k+ cheque.** Audits and retainers are pipeline; enterprise is the $1M track.
