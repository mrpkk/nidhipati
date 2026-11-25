"""Витрина оплаты прямого рельса: страница чека для первого продукта.

Зачем. Аудит за $199 принимался вручную: покупатель отправлял USDC, писал
владельцу письмо с хешем и ждал ответа. Проверка перевода — работа машины,
а не человека, и она уже сделана: `DirectBaseAdapter.confirm` читает цепочку.
Страница делает ровно три вещи — создаёт заказ, показывает адрес и сумму,
принимает хеш и отдаёт квитанцию. Никаких аккаунтов, карт и писем.

Чего страница не делает: не выдаёт сама продукт. Выдача остаётся ручной
(`ManualFulfillment`) — оплата подтверждена, но отчёт по логам пишет человек.
"""
from __future__ import annotations

import os
from pathlib import Path

#: Продукты, которые можно оплатить этой витриной. Цена — в долларах, актив
#: USDC считается один к одному; адрес приходит из конфигурации сервиса.
#: «Founding-цена для первых 10» — обещание на витринах. Пока счётчик не проверяется,
#: 11-й покупатель платил бы $19 при закрытом оффере: обещание без кода (26.11.2026).
FOUNDING_PRODUCT = "agent-spend-audit-founding"
FULL_PRODUCT = "agent-spend-audit"
FOUNDING_SEATS = 10


def founding_seats_left(store) -> int | None:
    """Сколько мест по founding-цене осталось. None — счётчик недоступен (не врём цифрой)."""
    try:
        return max(0, FOUNDING_SEATS - store.count_paid(FOUNDING_PRODUCT))
    except Exception:  # noqa: BLE001 — сломанный счётчик не должен блокировать продажу
        return None


PRODUCTS = {
    "agent-spend-audit": {
        "title": "Agent Spend Audit",
        "price_usd": "199",
        "summary": ("One month of agent logs in, a written report out: duplicates, "
                    "failed-but-billed calls, quote-vs-settled, missing refunds, "
                    "and the order to fix them."),
        "delivery": "5 working days from complete data. Written report, one round of questions.",
        "email_subject": "Nidhipati audit $199 — payment confirmed",
    },
    # 21.11.2026: «founding»-цена для первых 10 — демпинг, чтобы получить
    # первые продажи, отзывы и обратную связь. После 10 мест — обычные $199.
    "agent-spend-audit-founding": {
        "title": "Agent Spend Audit — founding price (first 10)",
        "price_usd": "19",
        "summary": ("Same audit as the $199 one: one month of agent logs in, a written report out — "
                    "duplicates, failed-but-billed calls, quote-vs-settled, missing refunds, "
                    "and the order to fix them. Founding price for the first 10 teams."),
        "delivery": "5 working days from complete data. Written report, one round of questions.",
        "email_subject": "Nidhipati founding audit $19 — payment confirmed",
    },
    # 21.11.2026: четыре «скучных» продукта для стабильного пополнения (см.
    # work/sales/STABLE-INCOME-PRODUCTS-2026-11-21.md). Год/разово — без подписки.
    "site-guard-year": {
        "title": "Site Guard — uptime, SSL и домен на год",
        "price_usd": "49",
        "summary": ("Проверка сайта каждые 5 минут, срок SSL и домена, алерт в Telegram или на почту. "
                    "Один сайт, 12 месяцев."),
        "delivery": "24 часа после оплаты: добавляем сайт, присылаем тестовый алерт.",
        "email_subject": "Site Guard $49 — оплата получена",
    },
    "channel-vault-export": {
        "title": "Channel Vault — бэкап Telegram-канала",
        "price_usd": "19",
        "summary": ("Полный экспорт постов, медиа и списка участников в ZIP. Один канал, один экспорт; "
                    "восстановление по запросу."),
        "delivery": "24 часа после оплаты: ZIP в чат или на почту.",
        "email_subject": "Channel Vault $19 — оплата получена",
    },
    "doc-answer-box": {
        "title": "Doc Answer Box — RAG для одной папки",
        "price_usd": "49",
        "summary": ("Загрузите документы — получите ссылку, где можно спрашивать свои файлы и видеть цитаты. "
                    "Первый месяц, один отдел."),
        "delivery": "48 часов: папка + 5 контрольных вопросов, затем доступ по ссылке.",
        "email_subject": "Doc Answer Box $49 — оплата получена",
    },
    "sheet-doctor": {
        "title": "Sheet Doctor — чистка Excel/CSV",
        "price_usd": "19",
        "summary": ("Дубли, пробелы, форматы дат, битые строки: чистый файл + отчёт, что было исправлено. "
                    "Один файл до 50 000 строк."),
        "delivery": "24 часа: чистый файл и отчёт на почту.",
        "email_subject": "Sheet Doctor $19 — оплата получена",
    },
    "root-check": {
        "title": "Root Check — idea and portfolio audit",
        "price_usd": "199",
        "summary": ("Before you spend a year: ten sourced checks on the idea, the market, "
                    "the unit economics and the fit with what you already run. A written "
                    "go / no-go with the root of the problem named."),
        "delivery": ("5 working days. Written report with sources and confidence, a written "
                     "walkthrough with async Q&A, and a 30/60/90 plan. If the first three "
                     "checks fail, we stop and return half."),
        "email_subject": "Root Check $199 — payment confirmed",
    },
    "drift-kill-switch": {
        "title": "Drift — spend limit and kill switch",
        "price_usd": "79",
        "summary": ("A hard per-task budget, an allowlist of payees and a kill switch "
                    "in front of your agent. Setup in your stack, a signed refusal "
                    "receipt for every blocked call, and a short runbook."),
        "delivery": "48 hours after access. Config, tests on a dry run, and a written runbook.",
        "email_subject": "Drift kill switch $79 — payment confirmed",
    },
    "karta-report": {
        "title": "KARTA — agent spend report 72/2500",
        "price_usd": "19",
        "summary": ("The written report: 72 money-moving MCP servers scanned, 2 500 tools, "
                    "which ones can spend without a ceiling, and what to fix first."),
        "delivery": "Instant PDF + JSON. One round of questions by email.",
        "email_subject": "KARTA report $19 — payment confirmed",
    },
    "aibiz-review": {
        "title": "AIBiz — one business card, reviewed",
        "price_usd": "49",
        "summary": ("One business model card reviewed against 69 live cards: unit economics, "
                    "risks, first three steps to revenue, and what to drop."),
        "delivery": "3 working days. Written review with sources, async questions.",
        "email_subject": "AIBiz review $49 — payment confirmed",
    },
    "crypto-mcp-month": {
        "title": "Crypto MCP — 30 days of market data",
        "price_usd": "19",
        "summary": ("One key, 30 days: prices, pools, on-chain balances and DeFi positions "
                    "through the Crypto MCP server. For agents and scripts that need live numbers."),
        "delivery": "Key by email within 1 hour, 30 days, 100k calls. No auto-renew.",
        "email_subject": "Crypto MCP $19 — key issued",
    },
    "data-rescue-kit": {
        "title": "Data Rescue Kit — CSV/Excel cleaner",
        "price_usd": "29",
        "summary": ("The script behind the 24-hour cleanup service: remove duplicates and empty rows, "
                    "normalize dates and amounts, merge files, get a JSON report. Python CLI, MIT-style use."),
        "delivery": "Archive by email within 1 hour: CLI, tests, samples, README.",
        "email_subject": "Data Rescue Kit $29 — files",
    },
    "sok-2026": {
        "title": "SOK 2026 — the year's evidence pack",
        "price_usd": "199",
        "summary": ("The juice of the year: 20 project cards, 12 evidence artifacts, "
                    "6 lessons, 3 bets and a 90-day plan. What is proven, what is not, "
                    "and what to build next — with a path to every claim."),
        "delivery": ("5 working days. Written 100–140 page report, sources and dates, "
                     "written walkthrough with async Q&A. No calls."),
        "email_subject": "SOK 2026 $199 — payment confirmed",
    },
}

CHECKOUT_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pay {title} — {price} USDC</title>
<meta name="description" content="{summary}">
<meta name="robots" content="noindex">
<style>
 body{{margin:0;background:#0b0d12;color:#e8ecf4;font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
 main{{max-width:680px;margin:0 auto;padding:40px 20px 72px}}
 h1{{font-size:26px;margin:0 0 6px}} h2{{font-size:17px;margin:28px 0 8px}}
 p{{color:#c3c9d6}} .s{{color:#8f97a6}}
 .box{{border:1px solid #232a35;border-radius:12px;padding:16px;margin:14px 0;background:#11151d}}
 .addr{{font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;word-break:break-all;background:#0b0d12;border:1px solid #232a35;border-radius:8px;padding:10px}}
 button{{margin-top:10px;padding:10px 16px;border:0;border-radius:8px;background:#1c6b58;color:#eafff8;font:600 14px system-ui,sans-serif;cursor:pointer}}
 button[disabled]{{opacity:.5;cursor:default}}
 input{{width:100%;box-sizing:border-box;padding:10px;font:14px ui-monospace,monospace;background:#0b0d12;border:1px solid #232a35;border-radius:8px;color:#e8ecf4}}
 a{{color:#7fd1b9}} .ok{{color:#7fd1b9}} .bad{{color:#ff9a9a}}
 .row{{display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
</style></head><body><main>
<h1>{title}</h1>
<p>{summary}</p>
<p class="s">{delivery}</p>

<h2>1 — Create the order</h2>
<div class="box">
<p class="s" id="sum">Amount: {price} USDC on Base.</p>
<input id="email" type="email" placeholder="your email — the intake form comes here" autocomplete="email">
<button id="mk">Create order</button>
<p class="s" id="addrbox" style="display:none">Send exactly <b id="amount">{price} USDC</b> on <b>Base</b> to:<br><span class="addr" id="addr"></span></p>
<p class="s" id="orderline" style="display:none">Order: <b id="ordername"></b> — keep this page open, or come back to it.</p>
</div>

<h2>2 — Paste the transaction hash</h2>
<div class="box">
<input id="tx" placeholder="0x…" autocomplete="off" spellcheck="false">
<button id="cf" disabled>Check payment</button>
<p id="out" class="s">Nothing checked yet.</p>
</div>

<p class="s">The transfer is verified on-chain: amount and recipient are read from the
transaction receipt, not from this page. One transfer pays one order. After the
payment is confirmed you receive the intake form by email — no account, no card,
no subscription.</p>
<p class="s">Questions before you pay: <a href="mailto:maxim.pkk@gmail.com?subject=Nidhipati%20audit%20%24199%20—%20question">ask a question first</a>.</p>
</main>
<script>
const PRODUCT = "{product}";
const PRICE = "{price}";
const out = document.getElementById("out");
// Заказ переживает перезагрузку вкладки. Без этого человек, отправивший USDC и
// обновивший страницу, оставался с orderId = null и не мог подтвердить оплату
// (21.11.2026: подтверждение отправлялось с null и падало).
const STORE_KEY = "nidhipati.order." + PRODUCT;
let orderId = null;
try {{
  const saved = localStorage.getItem(STORE_KEY);
  if (saved) {{
    orderId = saved;
    document.getElementById("orderline").style.display = "";
    document.getElementById("ordername").textContent = saved;
    document.getElementById("cf").disabled = false;
    say("Order " + saved + " restored. Paste the transaction hash — nothing is charged twice.", "");
    // Адрес и сумму тоже возвращаем: иначе после перезагрузки человеку некуда платить,
    // а новый заказ на ту же покупку — лишний повод запутаться.
    fetch("/pay/order/" + encodeURIComponent(saved)).then(r => r.json()).then(d => {{
      const order = d.order || d;
      const meta = order.meta || {{}};
      if (!order.provider_ref || !meta.amount_usdc) return;
      document.getElementById("addr").textContent = order.provider_ref;
      document.getElementById("amount").textContent = meta.amount_usdc + " " + (meta.asset || "USDC");
      document.getElementById("addrbox").style.display = "";
    }}).catch(() => {{}});
  }}
}} catch (e) {{ /* приватный режим: просто работаем без сохранения */ }}

function say(text, cls) {{
  out.textContent = text;
  out.className = cls || "s";
}}

document.getElementById("mk").onclick = async () => {{
  const btn = document.getElementById("mk");
  const email = document.getElementById("email").value.trim();
  if (!email) {{ say("an email is required — the intake form comes there", "bad"); return; }}
  btn.disabled = true; say("Creating the order…");
  orderId = "audit-" + (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()));
  try {{
    const r = await fetch("/pay/create", {{
      method: "POST", headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{order_id: orderId, amount_fiat: PRICE, currency: "USD",
                             product_id: PRODUCT, customer_email: email}})
    }});
    const d = await r.json();
    if (!d.ok) {{ say(d.error || "could not create the order", "bad"); btn.disabled = false; return; }}
    document.getElementById("addr").textContent = d.payment.address;
    document.getElementById("amount").textContent = d.payment.amount + " " + d.payment.asset;
    document.getElementById("addrbox").style.display = "";
    document.getElementById("cf").disabled = false;
    document.getElementById("orderline").style.display = "";
    document.getElementById("ordername").textContent = orderId;
    try {{ localStorage.setItem(STORE_KEY, orderId); }} catch (e) {{}}
    say("Order " + orderId + " created. Send the transfer, then paste the hash.", "ok");
  }} catch (e) {{ say("network error: " + e.message, "bad"); btn.disabled = false; }}
}};

document.getElementById("cf").onclick = async () => {{
  const tx = document.getElementById("tx").value.trim();
  if (!tx) {{ say("paste the transaction hash first", "bad"); return; }}
  const btn = document.getElementById("cf");
  btn.disabled = true; say("Checking the chain…");
  try {{
    const r = await fetch("/pay/confirm", {{
      method: "POST", headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{order_id: orderId, tx_hash: tx}})
    }});
    const d = await r.json();
    if (r.status === 200 && d.paid) {{
      const mail = d.intake_email_sent
        ? "The intake form is on its way by email."
        : "The intake email did not go out — please write to us with this transaction hash and we will send it by hand.";
      say("Payment confirmed: " + d.amount_usdc + " USDC from " + d.payer +
          " (block " + d.block + ", " + d.confirmations + " confirmations). " + mail +
          " Receipt: " +
          (d.evidence && d.evidence.evidence_hash ? d.evidence.evidence_hash : ""), "ok");
      document.getElementById("tx").value = "";
    }} else {{
      say(d.error || "payment not confirmed", "bad");
    }}
  }} catch (e) {{ say("network error: " + e.message, "bad"); }}
  btn.disabled = false;
}};
</script>
</body></html>
"""


def checkout_page(product: str) -> tuple[str, str, str] | None:
    """HTML страницы чека. None — продукта нет."""
    spec = PRODUCTS.get(product)
    if not spec:
        return None
    html = CHECKOUT_HTML.format(
        title=spec["title"],
        price=spec["price_usd"],
        summary=spec["summary"],
        delivery=spec["delivery"],
        product=product,
    )
    return html, spec["title"], spec["price_usd"]


CARD_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pay by card — {title}</title>
<meta name="robots" content="noindex">
<style>
body{{font:16px/1.5 system-ui,sans-serif;max-width:640px;margin:6vh auto;padding:0 20px;color:#16181d}}
h1{{font-size:1.5rem;margin:0 0 8px}} .p{{font-size:2rem;font-weight:600;margin:16px 0}}
.s{{color:#5a6070;font-size:.92rem}} .box{{border:1px solid #dfe3ea;border-radius:12px;padding:16px;margin:16px 0}}
button{{font:inherit;padding:12px 18px;border-radius:10px;border:0;background:#1c5fd4;color:#fff;cursor:pointer}}
button[disabled]{{opacity:.5;cursor:default}} .bad{{color:#b3261e}} .ok{{color:#166b3c}}
input{{font:inherit;padding:10px;border:1px solid #cfd5df;border-radius:8px;width:100%;box-sizing:border-box}}
</style></head><body>
<main>
<h1>{title}</h1>
<p class="s">{summary}</p>
<p class="p">{price} USD</p>
<div class="box">
<input id="email" placeholder="email for the receipt (required)" autocomplete="email">
<p class="s">Card is processed by PayGate.to; the settlement arrives to us in USDC. We never see your card number.</p>
<button id="go">Pay {price} USD by card</button>
<p id="out" class="s">Nothing charged yet.</p>
</div>
<p class="s">{delivery}</p>
<p class="s">After payment you get a receipt by email and a signed payment record you can verify offline. Questions: <a href="mailto:maxim.pkk@gmail.com?subject=Payment%20question">ask first</a>.</p>
</main>
<script>
const PRODUCT = "{product}", PRICE = "{price}", RAIL = "paygate.to";
const out = document.getElementById("out");
function say(t, c) {{ out.textContent = t; out.className = c || "s"; }}
document.getElementById("go").onclick = async () => {{
  const btn = document.getElementById("go");
  const email = document.getElementById("email").value.trim();
  if (!email || !email.includes("@")) {{ say("email is required — the receipt goes there", "bad"); return; }}
  btn.disabled = true; say("Opening the secure card page…");
  const orderId = "card-" + (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()));
  try {{
    const r = await fetch("/pay/create", {{method:"POST", headers:{{"Content-Type":"application/json"}},
      body: JSON.stringify({{order_id:orderId, amount_fiat:PRICE, currency:"USD", product_id:PRODUCT,
                            customer_email:email, rail:RAIL}})}});
    const d = await r.json();
    const url = d.checkout_url || (d.order && d.order.checkout_url);
    if (!d.ok || !url) {{ say(d.error || "could not create the payment", "bad"); btn.disabled = false; return; }}
    window.location.href = url;
  }} catch (e) {{ say("network error: " + e.message, "bad"); btn.disabled = false; }}
}};
</script>
</body></html>
"""


FUNNEL_PATH = Path(os.environ.get("NIDHIPATI_FUNNEL")
                    or (Path.home() / ".config" / "nidhipati" / "funnel.json"))


def funnel_bump(kind: str, product: str) -> None:
    """Счётчик кассы: сколько раз открыли страницу оплаты и сколько создали заказ.

    Зачем: покупатель может остановиться на самой кассе — и мы об этом не знали,
    потому что считать умели только «заказ создан». Только числа, без адресов.
    """
    import json as _json
    try:
        data = _json.loads(FUNNEL_PATH.read_text())
        data = data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        data = {}
    key = f"{kind}:{product[:32]}"
    data[key] = int(data.get(key, 0)) + 1
    try:
        FUNNEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        FUNNEL_PATH.write_text(_json.dumps(data, ensure_ascii=False, sort_keys=True))
    except OSError:
        pass


def card_page(product: str, amount: str | None = None) -> tuple[str, str, str] | None:
    """Страница оплаты картой: одна кнопка → провайдерская форма → USDC нам.

    `amount` приходит из query и потому недоверенный: он задаёт только сумму
    заказа. Выдача продукта ручная, поэтому подменить цену и получить товар
    дешевле нельзя — владелец видит сумму в заказе до выдачи.
    """
    spec = PRODUCTS.get(product)
    if not spec:
        return None
    price = str(amount or spec["price_usd"])
    html = CARD_HTML.format(title=spec["title"], price=price, summary=spec["summary"],
                            delivery=spec["delivery"], product=product)
    return html, spec["title"], price
