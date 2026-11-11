"""Витрина оплаты прямого рельса: страница чека для первого продукта.

Зачем. Аудит за $500 принимался вручную: покупатель отправлял USDC, писал
владельцу письмо с хешем и ждал ответа. Проверка перевода — работа машины,
а не человека, и она уже сделана: `DirectBaseAdapter.confirm` читает цепочку.
Страница делает ровно три вещи — создаёт заказ, показывает адрес и сумму,
принимает хеш и отдаёт квитанцию. Никаких аккаунтов, карт и писем.

Чего страница не делает: не выдаёт сама продукт. Выдача остаётся ручной
(`ManualFulfillment`) — оплата подтверждена, но отчёт по логам пишет человек.
"""
from __future__ import annotations

#: Продукты, которые можно оплатить этой витриной. Цена — в долларах, актив
#: USDC считается один к одному; адрес приходит из конфигурации сервиса.
PRODUCTS = {
    "agent-spend-audit": {
        "title": "Agent Spend Audit",
        "price_usd": "500",
        "summary": ("One month of agent logs in, a written report out: duplicates, "
                    "failed-but-billed calls, quote-vs-settled, missing refunds, "
                    "and the order to fix them."),
        "delivery": "5 working days from complete data. Written report, one round of questions.",
        "email_subject": "Nidhipati audit $500 — payment confirmed",
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
<p class="s">Questions before you pay: <a href="mailto:maxim.pkk@gmail.com?subject=Nidhipati%20audit%20%24500%20—%20question">ask a question first</a>.</p>
</main>
<script>
const PRODUCT = "{product}";
const PRICE = "{price}";
const out = document.getElementById("out");
let orderId = null;

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
