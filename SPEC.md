# NIDHIPATI — SPEC v0.1

**Дата:** 24.10.2026  
**Рабочее имя:** Nidhipati (nidhi — сокровище, pati — владыка; эпитет Куберы).  
**Статус:** спецификация и первый слайс; имя/домен не зарегистрированы, юридическая проверка впереди.  
**Скрижали:** `/media/Sruti/iamthat/work/sales/ИТОГИ(ЭТАЛОНЫ)` (14FINAL, roadmapFINAL, ПЛАН-ПРОДВИЖЕНИЯ-И-МОНЕТИЗАЦИИ, ПРОТОКОЛ-РАБОТЫ).

---

## 0. МИССИЯ

Дать миру **проверяемый слой денег для AI-агентов**: доказать, что агент потратил в рамках мандата, вернуть переплату и не дать агенту выйти за границы. Не кастоди, не токен, не рельс. Технология на благо: меньше слепых списаний, меньше потерь, больше доверия между человеком и агентом.

**Обещание:** «Рельсы двигают деньги. Nidhipati доказывает, что движение было правильным».

---

## 1. ПРИНЦИПЫ (14 ПЕЧАТЕЙ)

1. **Единый исток** — один факт = один файл/SPEC; никаких дублей.
2. **Ближний** — нет тёмных паттернов, страха, манипуляций; приватность по умолчанию.
3. **Покой** — пауза/отказ — законный ответ; не перегружать.
4. **Мера бремени** — scope ≤ возможностей; «не знаю» вместо выдумки.
5. **Сантоша** — «достаточно» — законченная ценность.
6. **Действие без плодов** — качество и усилие, не витрина.
7. **Ум — семя мира** — внимание = дизайн, тексты, порядок.
8. **Ахимса** — никакого насилия в коде/процессе.
9. **Благое слово или тишина** — без шума в логах/сообщениях.
10. **Единый свидетель** — аудит-лог, который нельзя тихо переписать.
11. **Ригпа** — не усложнять; изначальная простота.
12. **У-вэй** — не делать лишнего; удаление > добавление.
13. **Неокрашенное полотно** — не тащить чужие догмы; проверять.
14. **Истина на весах** — любое публичное утверждение проверяемо; иначе молчим.

**DoD слайса:** боль + тест + коммит + запись в PROGRESS + метрика денег. Без этого слайс не закрыт.

---

## 2. ПРОБЛЕМА

AI-агенты получили кошельки: LLM/API, MCP, x402, USDC, stablecoin, agentic commerce. Но:

- агент может выйти за мандат (Reuters: 1 200 попыток взлома, 100+ сайтов, ~$5K API);
- агент может сжечь бюджет (73% AI-бюджетов в overrun; кейс Accenture $29/чел в обсуждении);
- дашборд показывает **сколько**, но не **за что**;
- receipt = 200 OK, а не доказательство;
- refund/duplicate/price escalation теряются;
- мерчант не может проверить мандат агента до поставки.

**Следствие:** деньги уходят, доверие не растёт. Нужен независимый слой доказательства.

---

## 3. ICP И JOBS-TO-BE-DONE

| Сегмент | Боль | Что покупает |
|---|---|---|
| AI-agent стартапы с оплатой API/x402 | не знают, где переплатили; нет receipt | Spend Audit, Proof of Spend |
| Крипто-фонды/DAOs с агентами | агент тратит без границ; нет аудита | Guard, Reconcile |
| API/MCP-провайдеры | не могут доказать честность цены | Proof of Spend для мерчанта |
| RWA-эмитенты/фонды | нет независимого proof-of-reserve/NAV | Reserve report |
| Prediction market creators/traders | спор об исходе | Resolve evidence |
| Merchant/agentic commerce | не доверяют агенту | Proof of Spend + mandate check |

**Не ICP:** тот, кто хочет «ещё один дашборд», кастоди, эмиссию токена, маркет-мейкинг.

---

## 4. РЫНОК И КОНКУРЕНТЫ

- **Agent payment rails:** Skyfire, Nevermined, Payman, Coinbase x402/AgentKit, Mastercard Agent Pay, Visa Intelligent Commerce, Composio Instant. Рынок: 112 стартапов (Dealroom), $115M в 2026. **Не конкурируем.**
- **AI FinOps:** Vantage, CloudZero, Amnic, Finout, CloudQuell — показывают spend, не проверяют correctness.
- **LLM observability:** Langfuse, Helicone, LiteLLM — трейсы/токены, не recovery.
- **Crypto AP:** Bitwave, Request Finance, Cryptio — учёт/платежи, не audit overcharge.
- **x402 trust/analytics:** x402scan, Kertivo, Agent402 — объём/trust endpoint, не spend покупателя.
- **RWA:** Securitize, Tokeny, Brickken, DigiShares, ADDX, Taurus — issuance, не независимый proof-of-reserve для малых эмитентов.

**Щель:** независимый cross-rail **audit + receipt + recovery**. Не рельс, не дашборд.

Полный разбор: `/media/Sruti/iamthat/research/2026/2026-10-24/AGENT-SPEND-AUDIT-КОНКУРЕНТЫ.md`, `NIDHIPATI-ПРОДУКТ.md`.

---

## 5. ПРОДУКТ

### 5.1 Модули

| Модуль | Боль | Вход | Выход | Цена |
|---|---|---|---|---|
| **Proof** | «чем доказать, что платёж правильный?» | JSON receipt | verify OK/errors + signed report | free spec; paid verify API |
| **Spend** | «где переплатили?» | CSV/API/tx | отчёт: дубли, escalation, refunds | $2 500 / 20% savings |
| **Guard** | «как не выйти за границы?» | policy/mandate | allow/deny/approval + kill switch | $1 500/мес |
| **Reserve** | «чем обеспечен RWA?» | reserve data/NAV | signed proof-of-reserve report | $2 500–5 000 |
| **Resolve** | «какой исход рынка?» | rules/sources | signed evidence report | $500–2 000 |
| **Reconcile** | «сошлись ли USDC-платежи?» | invoices/tx | reconciliation report | $1 500/мес |

### 5.2 MVP (30 дней)

**S1 — Proof validator** (главное):
- JSON Schema v0.1.
- Canonical JSON + Ed25519 verify.
- Checks: schema, signature, mandate expiry, amount, asset/network/payee, usage×price, refund ≤ payment, verdict=allow, replay id.
- CLI + JSON output + 10 tests.
- No on-chain RPC in v0.1; mark `onchain_verified=false` honestly.

**S2 — Spend audit CLI**:
- CSV/JSON input: calls, quotes, settlements.
- Rules: duplicate, price escalation, failed-but-billed, runaway loop, refund missing, model overpay.
- Markdown/JSON report.
- 8 tests.

**S3 — Reserve report**:
- Input: reserve composition, NAV inputs, source hashes.
- Output: signed JSON/Markdown; disclaimers.
- 6 tests.

**S4 — Resolve report**:
- Input: market rules, sources, timestamps, evidence hashes.
- Output: signed evidence report.
- 6 tests.

**S5 — Reconcile**:
- Input: invoices + tx list.
- Output: matched/unmatched/duplicates/refunds.
- 8 tests.

### 5.3 Non-goals

- Кастоди, money transmission, эмиссия, токен.
- Свой платёжный рельс/OS.
- Дашборд до 5 платных.
- Маркет-мейкинг/арбитраж.
- Юридический/финансовый аудит как лицензированная услуга.

---

## 6. АРХИТЕКТУРА

```
nidhipati-proof/
  nidhipati_proof/
    __init__.py
    canonical.py      # deterministic JSON
    verify.py         # schema + signature + checks
    sign.py           # dev helper, Ed25519
    cli.py            # verify / keygen / sign
  schemas/
    proof-of-spend.schema.json
  examples/
    proof-of-spend.example.json
  tests/
  .github/workflows/test.yml
  pyproject.toml
  README.md
  SPEC.md
  PROGRESS.md
```

**Стек:** Python 3.10+, stdlib + `jsonschema` + `cryptography`. Никаких серверов, баз, Docker. CLI работает офлайн. Позже — HTTP API, но только после 5 платных.

**Данные:** JSON только. Никаких ключей/секретов в отчётах. Публичная схема; подпись Ed25519; приватный ключ у эмитента/клиента.

---

## 7. PROOF OF SPEND v0.1

Поля: `version, receipt_id, issued_at, agent{id,operator,key_id}, mandate{hash,policy_id,expires_at}, action{type,resource,quote_id}, payment{amount,asset,network,payee,tx_hash,settled_at}, usage{unit,quantity,unit_price}, refund{amount,tx_hash}, verdict{decision,policy_version,reasons}, evidence{artifact_hash,attestation_id}, signature{alg,key_id,value}`.

**Подпись:** canonical JSON документа, где `signature.value` заменён на `""`. Ed25519. Публичный ключ передаётся отдельно (`--pubkey` base64url/hex), не внутри документа (v0.1).

**Проверки:**
1. Schema.
2. Signature.
3. `mandate.expires_at >= payment.settled_at`.
4. `payment.amount > 0`.
5. `usage.quantity × usage.unit_price` == amount (±1e-9).
6. `refund.amount <= payment.amount`.
7. `verdict.decision == "allow"` для settled payment.
8. `receipt_id` не пустой; replay store — v0.2.
9. `asset/network/payee` — строки; allowlist — v0.2.
10. `onchain_verified=false` — честно, пока нет RPC.

**Выход:** `{ok, receipt_id, errors[], warnings[], checks{}}`.

---

## 8. SEO

**Правило:** бренд — вторым, задача — первой. «Nidhipati» никто не ищет; ищут «AI agent spend audit», «x402 receipt verification», «proof of spend», «RWA proof of reserve».

### 8.1 Страницы

| URL | H1 | Запрос |
|---|---|---|
| `/` | «Proof of Spend: verify what your AI agent paid» | proof of spend |
| `/agent-spend-audit` | «AI agent spend audit: find duplicates and overcharges» | AI agent spend audit |
| `/x402-receipt` | «x402 receipt verification» | x402 receipt |
| `/rwa-proof-of-reserve` | «RWA proof of reserve and NAV reporting» | RWA proof of reserve |
| `/prediction-resolution` | «Prediction market resolution evidence» | prediction market resolution |
| `/stablecoin-reconciliation` | «Stablecoin reconciliation for DAOs and SMBs» | stablecoin reconciliation |
| `/spec` | «Proof of Spend spec v0.1» | proof of spend spec |
| `/security` | «Agent wallet security review» | agent wallet security |

### 8.2 Техническая база

- `robots.txt`, `sitemap.xml`, canonical, OG, JSON-LD (`SoftwareApplication`, `FAQPage`, `TechArticle`).
- Статический сайт на GitHub Pages; <100KB HTML/CSS, без тяжёлых шрифтов.
- `llms.txt` с описанием продукта и API.
- Внутренние ссылки: каждая страница → spec, free scan, pricing.
- Никаких фейковых отзывов/цифр; только проверяемые факты и пометка «draft».

### 8.3 Контент (6 статей)

1. «Почему 200 OK — не доказательство оплаты x402».
2. «AI agent spend audit: 8 проверок до счёта».
3. «RWA proof-of-reserve: что должен доказывать эмитент».
4. «Prediction market resolution: evidence, не мнение».
5. «Stablecoin reconciliation для DAO: где теряются refunds».
6. «Agent wallet security: 10 проверок до запуска».

Каждая — боль → пример → чек-лист → один CTA. Публикация: GitHub Pages + (когда будут аккаунты) HN/Reddit/dev.to.

### 8.4 Каналы

- GitHub/Pages/SEO — основные.
- Партнёры: ClawRouter, x402scan, Kertivo, Composio, Langfuse/Helicone, Bitwave/Request Finance, RWA data, prediction data.
- Product Hunt / HN / Reddit — только через владельца; агент не создаёт аккаунты.
- Никакой рекламы до выручки.

---

## 9. МОНЕТИЗАЦИЯ

| Продукт | Цена | Условие |
|---|---|---|
| Free scan | 0 | 1 поток/1 неделя |
| Spend audit | $2 500 или 20% verified savings | 6 мес |
| Proof verify API | $0.01/вызов, $49/мес | позже |
| Reserve report | $2 500–5 000 | за отчёт |
| Resolve report | $500–2 000 | за отчёт |
| Reconcile retainer | $1 500/мес | 3 мес min |
| Guard retainer | $1 500/мес | 3 мес min |

**Правило:** success fee только от подтверждённой экономии; если нет — отчёт говорит «нет». Без кастоди.

**Оплата:** USDC на Base/Solana, 50% предоплата; card on-ramp по запросу; MoR/Stripe — после non-RF юрлица и выручки. Домен/реклама — после первого платежа.

**Воронка:** SEO/партнёр → free scan → audit → retainer. Метрики: `scan_requests`, `scans_done`, `paid_audits`, `mrr`, `channel`.

---

## 10. 30/60/90

**30 дней**
- S1 validator + 10 тестов + GitHub release.
- S2 spend audit CLI + 8 тестов.
- 6 SEO-страниц (MVP: 3).
- 10 партнёрских писем, 5 сканов, 1 платный.

**60 дней**
- S3 Reserve report, S4 Resolve.
- 10 платных сканов/2 ретейнера.
- 3 партнёрские интеграции.

**90 дней**
- S5 Reconcile.
- $5–10k MRR-цель (осторожно).
- 5 кейсов, 3 SEO-кластера.

---

## 11. МЕТРИКИ

- **Деньги:** paid audits, MRR, success fee.
- **Воронка:** scan requests, scans done, audit conversion.
- **Продукт:** verify calls, errors, time-to-verify.
- **SEO:** impressions, clicks, ranking pages, organic scans.
- **Партнёры:** referrals, co-marketing.
- **Просмотры без оплат — не результат.**

---

## 12. РИСКИ

| Риск | Смягчение |
|---|---|
| Конкуренты добавят audit | скорость, open spec, независимость, recovery |
| Нет доверия к новому имени | open-source validator, примеры, честные ограничения |
| RWA/NAV — юридический риск | партнёр-юрист, дисклеймер, не статутный аудит |
| Prediction — gambling-риск | только evidence, не организация рынка |
| Stablecoin — money transmission | read-only, без кастоди |
| Нет данных для аудита | free scan на публичных tx/CSV |
| Нет бюджета | только бесплатные каналы |
| Имя занято/ТМ | финальная проверка до регистрации; рабочий вариант — Nidhipati |

---

## 13. RAG / PROMPT

Полный промпт и идеи: `docs/PROMPT-AND-IDEAS.md`.  
Ключевые тезисы: агенты получили кошельки, но не получили доказательств; Proof of Spend — cross-rail receipt; RWA — attestation, не эмиссия; stablecoin — reconcile, не эмиссия; prediction — evidence, не MM; не строить OS/дашборд; SEO — задача первой; бюджет 0.

---

## 14. DoD

- [ ] S1 validator: 10 тестов, CLI, README, CI.
- [ ] S2 spend audit: 8 тестов, sample report.
- [ ] 3 SEO-страницы + sitemap/robots/JSON-LD.
- [ ] 10 партнёрских писем, 5 сканов.
- [ ] 1 платный аудит/ретейнер.
- [ ] Obsidian + RAG + git + backup.
