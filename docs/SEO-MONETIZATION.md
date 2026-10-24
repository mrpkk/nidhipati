# SEO & MONETIZATION — NIDHIPATI

**Date:** 24.10.2026. **Budget:** 0. **Rule:** task first, brand second; no ads until revenue.

---

## 1. Positioning

**One-liner:** «Рельсы двигают деньги. Nidhipati доказывает, что движение было правильным.»

**Who:** AI-agent teams, DAOs/funds, API/MCP sellers, RWA issuers, prediction market creators, stablecoin SMBs.

**Not:** another payment rail, dashboard, custodian, token, market maker.

---

## 2. Keyword map

| Query | Page | Intent |
|---|---|---|
| AI agent spend audit | `/agent-spend-audit` | commercial |
| proof of spend | `/` | informational/commercial |
| x402 receipt verification | `/x402-receipt` | technical |
| agent payment receipt | `/` | commercial |
| AI agent cost control | `/agent-spend-audit` | commercial |
| RWA proof of reserve | `/rwa-proof-of-reserve` | commercial |
| tokenized treasury NAV report | `/rwa-proof-of-reserve` | commercial |
| prediction market resolution evidence | `/prediction-resolution` | niche |
| stablecoin reconciliation | `/stablecoin-reconciliation` | commercial |
| agent wallet security review | `/security` | commercial |

**Brand queries** (`nidhipati`) — second priority; no one searches yet.

---

## 3. Site map

```
/
├── /agent-spend-audit
├── /x402-receipt
├── /rwa-proof-of-reserve
├── /prediction-resolution
├── /stablecoin-reconciliation
├── /security
├── /spec
├── /pricing
├── /free-scan
├── /docs/proof-of-spend
└── /llms.txt
```

Every page: H1 with task, 1,000–1,800 words, example, checklist, one CTA, links to spec/free scan/pricing.

---

## 4. Technical SEO

- Static GitHub Pages; <100KB HTML/CSS; no heavy fonts.
- `robots.txt`, `sitemap.xml`, canonical, OG/Twitter meta.
- JSON-LD: `SoftwareApplication`, `FAQPage`, `TechArticle`, `BreadcrumbList`.
- `llms.txt` for agents.
- No fake reviews, no fake client logos, no “100% safe”.
- All claims link to source or are marked “draft”.
- Internal links: hub-and-spoke (money pages ↔ spec ↔ examples).
- Page speed: system fonts, no JS frameworks, no trackers; one lightweight analytics later (Umami/Plausible self-hosted after revenue).

---

## 5. Content plan (6 articles)

| # | Title | Query | CTA |
|---|---|---|---|
| 1 | «Почему 200 OK — не доказательство оплаты x402» | x402 receipt | free scan |
| 2 | «AI agent spend audit: 8 проверок до счёта» | agent spend audit | free scan |
| 3 | «RWA proof-of-reserve: что должен доказывать эмитент» | RWA proof of reserve | reserve report |
| 4 | «Prediction market resolution: evidence, не мнение» | resolution evidence | resolve report |
| 5 | «Stablecoin reconciliation для DAO: где теряются refunds» | stablecoin reconciliation | reconcile retainer |
| 6 | «Agent wallet security: 10 проверок до запуска» | agent wallet security | security review |

**Distribution:** GitHub Pages + owner posts to HN/Reddit/Product Hunt when accounts ready; no agent-created accounts. Dev.to only if API key appears; otherwise no.

---

## 6. Partner bridge list

| Partner | Why | Ask |
|---|---|---|
| ClawRouter | routes to cheapest model; cost is the product | add-on/referral |
| x402scan | x402 volume/endpoints | spend view/referral |
| Kertivo | x402 endpoint trust grades | combine trust + spend |
| Composio Instant | agents pay for tools | receipt/spend integration |
| Langfuse | LLM traces/cost | referral/integration |
| Helicone | LLM cost observability | referral/integration |
| LiteLLM | proxy/cost | referral |
| Bitwave | crypto accounting/AP | reconcile partnership |
| Request Finance | crypto invoicing | invoice/reconcile |
| RWA data (RWA.xyz/Chainstack/RedStone) | reserve/NAV data | data partner |
| Prediction data (Kalshi/Polymarket/Tatum/Codex) | resolution data | data partner |

**Rule:** 5 first, not all. One specific fact per message. No calls.

---

## 7. Pricing

| Offer | Price | Notes |
|---|---|---|
| Free scan | 0 | one flow/week, 48h |
| Spend audit | $2,500 or 20% verified savings | 6 months; success fee only if verified |
| Proof verify API | $0.01/call, $49/mo | after 5 paid |
| Reserve report | $2,500–5,000 | per report |
| Resolve report | $500–2,000 | per report |
| Reconcile retainer | $1,500/mo | 3 months min |
| Guard retainer | $1,500/mo | 3 months min |

**Guarantee:** if no finding, say so; no fake savings. 50% upfront for new clients.

---

## 8. Payment rails

- **Primary:** USDC on Base (eip155:8453) or Solana; invoice with amount, address, memo, expiry; verify tx hash.
- **Card:** on-ramp via Transak/Banxa/Guardarian; client pays card → USDC; KYC/fees; no custody.
- **MoR/Stripe:** Paddle/Lemon Squeezy block RF; only after non-RF entity and revenue.
- **Telegram Stars:** micro-payments only; not B2B.
- **No custody, no money transmission.**

---

## 9. Funnel & metrics

```
SEO/partner/GitHub
  → free scan request
  → scan done
  → audit paid
  → retainer
```

Track:
- `scan_requests`, `scans_done`, `paid_audits`, `mrr`, `channel`, `source_query`.
- Organic impressions/clicks (after analytics).
- Partner referrals.
- **Views without paid scans are not a result.**

---

## 10. 30-day SEO/monetization plan

| Day | Action |
|---|---|
| 1–3 | Publish 3 pages (money, x402, RWA), sitemap, JSON-LD |
| 4–7 | Publish spec/validator, GitHub release |
| 8–10 | 5 partner messages |
| 11–14 | 5 free scans |
| 15–18 | 1 paid audit/retainer |
| 19–21 | Case study, 3 more pages |
| 22–25 | Launch kit for owner (HN/Reddit/PH) |
| 26–30 | Review metrics, kill weak ICP, double down |

**No ads, no bought traffic, no fake urgency.**
