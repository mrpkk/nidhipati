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

## S2 — Spend audit CLI (закрыт 25.10.2026)

**Боль:** «где переплатили?»

### S2.01 — input model
- [x] CSV/JSON: `ts, agent_id, tool, quote, settled, status` обязательны; `model, actual, refund, asset, network, tx_hash, payee` — по наличию. Пропущенная колонка — ошибка, а не пустое значение (`load_records`).
- [x] Синтетический пример `examples/spend-sample.csv` (44 строки, помечен как синтетика): каждая находка ровно один раз. Политика — `examples/spend-policy.example.json`.
- [x] Разбор и валидация: ISO-8601, Decimal (не float) для денег.

### S2.02 — rules
- [x] `duplicate_charge` — тот же `tx_hash`; либо равный платёж в 120 с **при отсутствии квитанции у обеих строк**. Две квитанции — два платежа: 25.10 аудит считал цикл из 20 вызовов 190 дублями и давал «переплату» больше самих расходов; есть регрессионный тест.
- [x] `price_escalation` — `settled > quote × 1.01`, сумма превышения в находке.
- [x] `failed_but_billed` — статус failed/error/rejected/timeout/5xx при `settled > 0`.
- [x] `runaway_loop` — больше 30 вызовов в любом окне 60 с на агента.
- [x] `missing_refund` — `settled > actual` и возврат не записан.
- [x] `model_overpay` — выше 3× медианы **самого агента** по тому же инструменту и модели (не по чужим агентам: у них другая задача).
- [x] `unknown_asset` / `unknown_network` / `missing_payee` — запись не говорит, куда ушли деньги.
- [x] `budget_bypass` (нет файла политики) и `budget_exceeded` (превышен `limit_usd`).

### S2.03 — report
- [x] Markdown + JSON, доказательство в каждой находке (номер строки + `tx_hash`).
- [x] Три суммы раздельно: `estimated_overpay` (деньги без основания), `overpay_vs_median` (оценка), `budget_overrun` (лимит). Складывать их в одно «мы вернули $X» — нечестно.
- [x] 14 тестов (`tests/test_spend.py`), включая тест на ложные дубли.

**Критерий S2:** пример даёт 10 типов находок, 5 из них — ошибки; CLI `nidhipati-spend audit`; код возврата 0/1/2. `docs/AGENT-SPEND-AUDIT.md`, README.

---

## S3 — Reserve / RWA report (закрыт 25.10.2026)

**Боль:** «чем обеспечен токен и верен ли NAV?»

- [x] Вход: состав резерва, хеш выписки кастодиана, входы NAV, источники цен, обязательства. Всё в JSON, деньги — Decimal-строки, `as_of` обязателен.
- [x] Формулы явные и опубликованы: `value = quantity × price × (1 − haircut)`, `NAV = Σ резерв − Σ обязательства`, `ratio = NAV / supply`.
- [x] **Отказ вместо догадки:** если хоть одна строка без цены — вердикт `incomplete`, `backing_ratio: null`. Исключить строку молча — занизить NAV; подставить цену — выдумать.
- [x] Подписанный JSON + Markdown, `sha256:` доказательство на каждую строку, хеш выписки сверяется с файлом (расхождение — ошибка `statement_hash_mismatch`).
- [x] Дисклеймер внутри подписанного документа: «не статутарный аудит, на цепи не проверялось», вынести его из подписи нельзя.
- [x] 14 тестов: backed/underbacked/incomplete, отсутствие источника, устаревшая цена старше 3 дней, хеш выписки (совпал/не совпал), haircut вне [0,1), подпись и её поломка при подмене NAV, коды возврата CLI.
- [x] Партнёрско-юридический чеклист — `docs/RESERVE-REPORT.md`: юрлицо и юрисдикция, канал подтверждения кастодиана, разрешение называть кастодиана, методология NAV, отказы (нет юрлица, нет источника, «сделайте чтобы сошлось»).

**Критерий:** синтетический отчёт собран и подписан — NAV `1 017 900.00`, ratio `1.0179`, вердикт `backed`; каждая строка с источником и хешем. Ни одного выдуманного числа.

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

## S6 — SEO site (закрыт 25.10.2026)

- [x] Страницы: `/` (index), `agent-spend-audit`, `x402-receipt`, `rwa-proof-of-reserve`, `prediction-resolution`, `stablecoin-reconciliation`. Опубликованы GitHub Pages из `/docs`: https://mrpkk.github.io/nidhipati/
- [x] `robots.txt`, `sitemap.xml` (6 адресов), canonical, OG, JSON-LD (FAQPage) — на месте.
- [x] `llms.txt` есть.
- [x] Внутренние ссылки: **были битые** — все кнопки «Free scan» вели на `scan-request.yml`, которого нет; исправлено на `free-spend-audit.yml` (6 файлов), форма отвечает 200.
- [x] Без выдуманных отзывов: на странице аудита стояла «illustrative report» с придуманными процентами и суммой $4,510. Заменено на настоящий вывод `nidhipati-spend` по синтетическому примеру + команда, которой его получить. Цена ретейнера на странице stablecoin приведена к офферу (без минимального срока).
- [x] GitHub Pages уже включён (ветка `main`, папка `/docs`); домен — после выручки, как и записано.

**Критерий:** Pages 200, sitemap валиден, битых ссылок нет, ни одного придуманного числа на сайте.

---

## S7 — Monetization / launch

- [x] Free scan form: `.github/ISSUE_TEMPLATE/free-spend-audit.yml`, метка `free-scan`, форма открывается (200). Просит записи без ключей и прямо говорит: те же проверки можно запустить самому — если инструмент отвечает, мы не нужны.
- [x] Оффер `docs/OFFER.md`: бесплатный скан → $2,500 фикс (10 рабочих дней) → $1,500/мес → 20 % подтверждённой экономии; Индия $1,250 / $750. Отдельным блоком «чего нет»: не юруслуга, возврат не гарантирован, кастоди нет.
- [x] Счёт `docs/INVOICE-USDC.md`: подписанный JSON, проверяется `nidhipati-proof verify`; адрес только из счёта, никогда из чата; правила возврата.
- [x] Action `action.yml` (v0.2.0): аудит в пайплайне, отчёт в `$GITHUB_STEP_SUMMARY`, сборка падает на ошибках.
- [ ] 10 partner messages (ClawRouter, x402scan, Kertivo, Composio, Langfuse, Helicone, Bitwave, Request Finance, RWA data, prediction data). **Пауза:** холодные обращения в attest — 0 ответов из 76; сначала проверить, что оффер вообще открывается и читается.
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

1. S1/S2/S6 closed.
2. S3 Reserve report, S4 Resolve, S5 Reconcile.
3. S7 partner letters are paused: 0 responses from 76 cold outreach; first verify the offer is readable.
4. First paid audit/retainer.

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


## S6 closed — 25.10.2026

- 6 SEO pages, `robots.txt`, `sitemap.xml`, `llms.txt`, JSON-LD, canonical, GitHub Pages 200.
- Site: https://mrpkk.github.io/nidhipati/
- Pages are hand-edited after generation; do not run `tools/build_site.py` without diff.
