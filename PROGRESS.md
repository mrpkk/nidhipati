# PROGRESS — NIDHIPATI

**Цель:** первые платные сканы/отчёты за 30 дней; $5–10k MRR — горизонт 90 дней.  
**Правило:** один слайс = боль + тест + коммит + запись + метрика денег.  
**Бюджет:** 0 до выручки. Домен/реклама/VPS — после первого платежа.

---

## P0 — Research / naming (закрыт)

- [x] Прочитаны скрижали: `14FINAL.md`, `roadmapFINAL.md`, `ПЛАН-ПРОДВИЖЕНИЯ-И-МОНЕТИЗАЦИИ.md`, `ПРОДАЖИ-И-ПРОДВИЖЕНИЕ.md`, `ПРОТОКОЛ-РАБОТЫ.md`.
- [x] Рынок: 112 agent-payment стартапов (Dealroom), Skyfire/Nevermined/Payman/Coinbase x402/Mastercard/Visa/Composio; FinOps/observability/x402 analytics.
- [x] Щель: независимый audit + receipt + recovery, не рельс/дашборд.
- [x] Имя: **Nidhipati** (nidhi + pati; эпитет Куберы). Предварительно: `nidhipati.com` whois no match, `.io` RDAP 404, npm/PyPI 404. Не юридическая проверка.
- [x] Бриф: `/media/Sruti/iamthat/research/2026/2026-10-24/NIDHIPATI-ПРОДУКТ.md`.

---

## S0 — SPEC, schema, example (закрыт)

- [x] `SPEC.md` — миссия, ICP, конкуренты, архитектура, SEO, монетизация, риски.
- [x] `schemas/proof-of-spend.schema.json`.
- [x] `examples/proof-of-spend.example.json`.
- [x] `docs/PROMPT-AND-IDEAS.md` — промпт/идеи для RAG.
- [x] `docs/SEO-MONETIZATION.md` — ключи, страницы, воронка.

**Критерий:** схема валидна, example проходит `jsonschema`.

---

## S1 — Proof validator MVP (главный слайс)

**Боль:** «200 OK — не доказательство оплаты; чем проверить receipt?»

### S1.01 — canonical + sign/verify
- [x] `canonical.py`: deterministic JSON (sort keys, UTF-8, no spaces).
- [x] `sign.py`: Ed25519 keygen/sign/verify (dev helper).
- [x] `verify.py`: schema + signature + mandate expiry + amount + usage×price + refund + verdict.
- [x] `ProofResult` with `ok/errors/warnings/checks`.
- [x] No on-chain RPC in v0.1; `onchain_verified=false` honest.

**DoD:** подписанный example проходит; tamper amount/expiry/refund/verdict падает.

### S1.02 — CLI
- [x] `nidhipati-proof verify file.json --pubkey <b64/hex>`.
- [x] `nidhipati-proof keygen --out-dir`.
- [x] `nidhipati-proof sign file.json --key private.pem`.
- [x] JSON/Markdown output; exit code 0/1/2.

**DoD:** CLI работает на example; ошибки понятны; нет секретов в выводе.

### S1.03 — tests + CI
- [x] 10 тестов: valid, bad schema, bad signature, expired mandate, amount mismatch, usage mismatch, refund > payment, denied verdict, wrong algo, replay id empty.
- [x] GitHub Actions Python 3.10/3.12.
- [x] `pytest -q` зелёный.

### S1.04 — docs + release
- [x] README quickstart.
- [x] `docs/PROOF-OF-SPEND.md` (spec v0.1).
- [x] GitHub repo `mrpkk/nidhipati`, push, tag `v0.1.0`.
- [x] Release notes: «draft, not a standard».

**Критерий S1:** clone → install → test → verify; 10 тестов; release.

---

## S2 — Spend audit CLI

**Боль:** «где переплатили?»

### S2.01 — input model
- [ ] CSV/JSON schema: timestamp, agent_id, model/tool, quote, settled, asset/network, tx_hash, status, refund.
- [ ] Sample data (synthetic, labelled).
- [ ] Parsing + validation.

### S2.02 — rules
- [ ] duplicate (same agent/action within window).
- [ ] price escalation (settled > quote + tolerance).
- [ ] failed-but-billed (status failed/500, settlement exists).
- [ ] runaway loop (calls/min > threshold).
- [ ] missing refund (upto/actual < quote, no refund).
- [ ] model overpay (small task + frontier price).
- [ ] unknown asset/network/payee.
- [ ] budget bypass (limit in prompt only) — flag if no policy file.

### S2.03 — report
- [ ] Markdown + JSON; total estimated overpay; evidence per finding.
- [ ] Honest: estimates, not recovered until verified.
- [ ] 8 tests.

**Критерий S2:** sample report with 5+ findings; tests; CLI.

---

## S3 — Reserve / RWA report

**Боль:** «чем обеспечен токен и верен ли NAV?»

- [ ] Input: reserve composition, custodian/bank statement hash, NAV inputs, price sources.
- [ ] Compute NAV with explicit formulas; mark missing data.
- [ ] Signed JSON/Markdown report; `attest`-style evidence hashes.
- [ ] Disclaimer: not a statutory audit.
- [ ] 6 tests.
- [ ] Partner/legal checklist.

**Критерий:** synthetic reserve report; all inputs sourced; no fake numbers.

---

## S4 — Resolve / prediction evidence

**Боль:** «какой исход рынка и чем доказано?»

- [ ] Input: market rules, resolution sources, timestamps, evidence hashes.
- [ ] Check source agreement/conflict; output signed report.
- [ ] No market operation, no betting.
- [ ] 6 tests.

**Критерий:** sample market resolution report; conflicts flagged.

---

## S5 — Reconcile / stablecoin ops

**Боль:** «сошлись ли USDC-инвойсы и платежи?»

- [ ] Input: invoices + tx list.
- [ ] Match by amount/memo/payee/time; duplicates/unmatched/refunds.
- [ ] Report + CSV export.
- [ ] 8 tests.
- [ ] No custody/private keys.

---

## S6 — SEO site

- [ ] 6 pages: `/`, `/agent-spend-audit`, `/x402-receipt`, `/rwa-proof-of-reserve`, `/prediction-resolution`, `/stablecoin-reconciliation`.
- [ ] `robots.txt`, `sitemap.xml`, canonical, OG, JSON-LD.
- [ ] `llms.txt`.
- [ ] Internal links to spec/free scan/pricing.
- [ ] No fake reviews; “draft” labels.
- [ ] GitHub Pages + custom domain later (after revenue).

**Критерий:** Pages 200, sitemap valid, 3 pages indexed (later), no broken links.

---

## S7 — Monetization / launch

- [ ] Free scan form (GitHub issue template).
- [ ] Pricing page: free / $2,500 / 20% / $1,500/mo.
- [ ] USDC invoice template + card on-ramp instructions.
- [ ] 10 partner messages (ClawRouter, x402scan, Kertivo, Composio, Langfuse, Helicone, Bitwave, Request Finance, RWA data, prediction data).
- [ ] 5 free scans → 1–2 paid.
- [ ] Launch kit for owner: Show HN, Reddit, Product Hunt; agent does not create accounts.
- [ ] Channel attribution.

**Критерий:** first paid audit or retainer; if not, report why.

---

## S8 — Hygiene

- [ ] Obsidian daily/project note.
- [ ] RAG skill `nidhipati` + rebuild index.
- [ ] `soma_remember`.
- [ ] Git commit/push each slice.
- [ ] Backup local + GDrive after each major slice.
- [ ] Update `LATEST.md`/market feed if needed.

---

## Immediate next steps

1. S1.01–S1.04 validator.
2. S2 spend audit.
3. S6 3 SEO pages.
4. S7 5 partner messages.

---

## Commands

```bash
cd /media/Sruti/iamthat/work/sales/nidhipati
python3 -m pytest -q
python3 -m nidhipati_proof.cli verify examples/proof-of-spend.example.json --pubkey <...>
```


## S1 closed — 24.10.2026

- 10 tests green; CLI `keygen/sign/verify`; package install in clean venv verified.
- Schema/example validate; `onchain_verified=false` explicit.
- Next: S2 Spend audit CLI.
