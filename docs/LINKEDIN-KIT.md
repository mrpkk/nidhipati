# LinkedIn kit — 3 posts + DM

**Правило:** один факт/цифра на пост, один вопрос в конце. Без «мы лучшие», без выдуманных клиентов, без обещаний recovery.

**Ссылка для постов:** https://mrpkk.github.io/nidhipati/free-spend-audit.html

---

## Пост 1 — «Не модель, а утечки»

> Your AI agent bill is usually not a model-choice problem.
>
> Four leaks I see in agent spend:
> 1. retries replaying the full context,
> 2. tool results dumped whole into the next call,
> 3. fan-out copying the same context N times,
> 4. no per-task cost attribution, so a retry storm and a bloated result look identical on the invoice.
>
> Design fixes prevent the next one. They do not tell you what was already billed.
>
> That is why I built a local audit: paste a CSV, get duplicates, failed-but-billed, quote-vs-settled and missing refunds. It runs in the browser, nothing is uploaded, no account.
>
> If it finds nothing, it says it found nothing.
>
> What would you need to see before trusting a third-party check in your payment pipeline?

---

## Пост 2 — «160 упоров, 0 оплат»

> A small number that explains a lot about agent payments:
>
> 160 paywall hits. 0 payment attempts.
>
> Not because the price was high. Because the 402 challenge reached an agent that had no wallet, and the human who could pay never saw the page.
>
> x402 is a good rail. It is not a checkout.
>
> If you run agents with a real budget: where does the payment decision actually happen — inside the agent, or with a person who can approve it?
>
> We are building the audit side: proof that a charge was allowed, priced correctly, and refunded when it should be. No custody, no token, no dashboard.

---

## Пост 3 — «Что показывает скан»

> A 6-row synthetic spend export produced 9 findings:
>
> - 4 errors, 5 warnings
> - $0.13 spent without a reason
> - $0.08 above the usual price
> - 1 duplicate
> - 1 failed-but-billed row
>
> This is not a client case. It is a sample I can rerun in front of you. The point is not the amount — it is that each finding has a row number, a rule and evidence you can send to the provider.
>
> A single “we saved $X” number is what makes finance stop trusting the report. Keep the categories separate.
>
> Free browser audit, no upload, no account: https://mrpkk.github.io/nidhipati/free-spend-audit.html
>
> If you have a month of agent spend, what would you want checked first?

---

## DM — 5 в день

**Кому:** CTO / VP Engineering / Head of AI / Finance lead в компаниях 10–200 человек, которые публично говорят об агентах, x402, MCP или AI-бюджетах.

**Текст (короткий, без вложения):**

> Hi {name} — you wrote about running agents with real budgets. I built a local CSV audit that flags duplicate charges, failed-but-billed calls, quote-vs-settled and missing refunds. Nothing is uploaded; no signup. If it finds nothing, it says so. Want the 10-check list, no call?

**Если ответили «да»:** отправить ссылку на бесплатный аудит и один вопрос: «How do you attribute spend per task today?»

**Если ответили «нет»:** не догонять. Один follow-up через 7 дней максимум, и только с новым фактом/кейсом.

---

## Чего не делать

- Не писать «мы сэкономили $X» без кейса.
- Не выдавать синтетический пример за клиента.
- Не обещать возврат денег от провайдера.
- Не ставить ссылку в первом сообщении незнакомому человеку — сначала вопрос/разрешение.
- Не отправлять календарь/созвон: только письменный формат.
