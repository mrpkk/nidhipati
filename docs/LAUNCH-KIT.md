# Launch kit — всё, что нужно нажать

Агент не создаёт аккаунты и не постит от твоего имени. Здесь готовые тексты и порядок.

**Screenshot:** `docs/screenshot-free-audit.png` — synthetic sample, no client data.

---

## 1. Hacker News (главный шанс)

**Статус 25.10.2026:** HN ответил `You're posting too fast` — это временный лимит на частоту
отправок с одного аккаунта. Он снимается сам (обычно от часа до суток). Повторять сразу нельзя:
повтор во время лимита продлевает его.

**Когда:** будни, 15:00–17:00 МСК (08:00–10:00 ET) — там в это время читают.

**Шаг 1.** https://news.ycombinator.com/submit

Title (ровно так):

```
Show HN: Nidhipati – proof that an AI agent's charge was allowed
```

URL:

```
https://mrpkk.github.io/nidhipati/
```

**Шаг 2.** Сразу после публикации — свой комментарий (HN это любит, иначе пост выглядит рекламой):

```
Author here. The starting point was a small annoyance: an agent receipt said 200 OK and a
charge went through, but nothing in that response proved the charge was allowed, priced
correctly, or refunded when it should have been.

So the tool does four independent checks and refuses to blur them:
- signature and schema of the receipt,
- whether the artifact has content or is just a well-formed shell,
- what conditions produced it (model, prompt, hash),
- whether the amount was inside a signed mandate.

Two things I decided against, and would like to be argued out of:

1. No score. A single trust number hides which question failed.
2. No "probably". The reserve module refuses to print a backing ratio when one line has no
   price — excluding the line understates NAV, inventing a price is a lie.

Everything runs locally: python3 -m pip install -e . && nidhipati-spend audit examples/spend-sample.csv
The rule set is public in docs/. Nothing is verified on-chain yet, and the reports say so
inside the signature.

What I do not know: who actually pays for this. If you run agents with a real budget, what
would you need to see before trusting a third-party check in your pipeline?
```

**Шаг 3.** Первые 3 часа отвечать на каждый комментарий. Не просить голосов и не постить
ссылку в другие треды — за это банят.

**После:** в форме заявки есть поле «Where did you find this?» — по нему и считаем канал.

---

## 2. Reddit

Правило: в большинстве сабреддитов самопиар режут. Работает другое — ответить по делу в
существующем треде и дать ссылку как продолжение мысли.

**r/RWA** — пост: https://www.reddit.com/r/RWA/submit

Title:

```
Turning an issuer's reserve numbers into a NAV anyone can recompute
```

Body:

```
Most "fully backed" claims are a PDF. A holder can't multiply a PDF by anything.

I built a small open tool that takes the issuer's own reserve lines (quantity, price, haircut,
source) and produces a NAV with explicit formulas and a sha256 evidence hash per line. If any
line has no price it refuses to give a ratio at all and says "incomplete" — excluding the line
would understate NAV, inventing a price would be a lie.

Example on synthetic data: NAV 1,017,900, ratio 1.0179, verdict backed.

Try: https://mrpkk.github.io/nidhipati/rwa-proof-of-reserve.html
Code: https://github.com/mrpkk/nidhipati

It's arithmetic with evidence, not an audit opinion — the disclaimer travels inside the signed
report. Where does this break for a real issuer?
```

**r/ethdev** — только ответы в тредах про x402 / agent payments. Не пост.

---

## 3. Product Hunt

Нужен аккаунт с историей и ассеты (логотип, обложка, GIF). Сейчас нет ни того, ни другого.
**Решение: отложить до первого платящего** — запуск на PH без аудитории даёт ноль и сжигает
одну попытку (повторный запуск того же продукта запрещён).

---

## 4. Что делать после любого поста

| Шаг | Время |
|---|---|
| Ответить на все комментарии | первые 3 часа |
| Записать: откуда пришли (поле в форме заявки) | сразу |
| Не постить ту же ссылку на другой площадке в тот же день | — |
| Через 48 часов: если 0 переходов и 0 заявок — канал закрыт, не повторяем | 2 дня |

## Чего не делать

- Не просить голоса и апвоуты — HN и Reddit это ловят, аккаунт теряет вес.
- Не постить один и тот же текст на 5 площадок — это видно и убивает доверие.
- Не обещать «гарантированный возврат денег»: оффер этого не обещает, и отчёт это повторяет.
- Не запускать Product Hunt до первого платежа.
