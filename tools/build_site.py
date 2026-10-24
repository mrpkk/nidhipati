#!/usr/bin/env python3
"""Build the static Nidhipati SEO site into docs/."""

from __future__ import annotations

import html
import json
from pathlib import Path

BASE = "https://mrpkk.github.io/nidhipati"
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
FORM = "https://github.com/mrpkk/nidhipati/issues/new?template=scan-request.yml"

NAV = """
<header><div class="wrap nav">
  <a class="brand" href="index.html"><span class="mark">N</span> Nidhipati</a>
  <nav class="navlinks">
    <a href="agent-spend-audit.html">Spend audit</a>
    <a href="x402-receipt.html">x402 receipt</a>
    <a href="rwa-proof-of-reserve.html">RWA reserve</a>
    <a href="prediction-resolution.html">Prediction</a>
    <a href="stablecoin-reconciliation.html">Stablecoin</a>
    <a href="https://github.com/mrpkk/nidhipati">GitHub</a>
    <a class="btn primary" href="%s">Free scan</a>
  </nav>
</div></header>
""" % FORM

FOOT = """
<footer><div class="wrap">
  <div class="foot">
    <div>© 2026 Nidhipati · <a href="https://github.com/mrpkk/nidhipati">GitHub</a> · <a href="https://github.com/mrpkk/nidhipati/blob/main/SPEC.md">Spec</a></div>
    <div>No custody · no money transmission · no token</div>
  </div>
  <div class="fine" style="margin-top:12px">Nidhipati is a draft product. Reports are technical evidence, not statutory audits, legal, tax, or investment advice. Figures are from public 2026 reports and are context, not a guarantee. If no finding is verified, the report says so.</div>
</div></footer>
"""


def page(slug: str, title: str, description: str, h1: str, body: str, faq: list[tuple[str, str]] | None = None) -> str:
    canonical = BASE + ("/" if slug == "" else f"/{slug}.html")
    faq_html = ""
    faq_json = None
    if faq:
        faq_html = '<section><div class="wrap"><h2>Questions</h2><div class="faq">'
        for q, a in faq:
            faq_html += f"<details><summary>{html.escape(q)}</summary><p>{a}</p></details>"
        faq_html += "</div></div></section>"
        faq_json = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in faq
            ],
        }
    app = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "Nidhipati",
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web, CLI",
        "description": "Proof of Spend and spend audit for AI agents. Verify mandate, amount, asset, network, payee and refund in a signed receipt.",
        "url": canonical,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD", "description": "Free scan"},
    }
    jsonld = [app] + ([faq_json] if faq_json else [])
    jsonld_html = "\n".join(
        f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in jsonld
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="website">
<link rel="stylesheet" href="styles.css">
{jsonld_html}
</head>
<body>
{NAV}
<main>
<section class="hero"><div class="wrap">
  <span class="kicker"><span class="dot"></span> Draft v0.1 · open spec · no custody</span>
  <h1>{h1}</h1>
  <div class="lede">{description}</div>
  <div class="actions">
    <a class="btn primary" href="{FORM}">Request a free scan</a>
    <a class="btn" href="https://github.com/mrpkk/nidhipati/blob/main/docs/PROOF-OF-SPEND.md">Read the spec</a>
  </div>
  <div class="micro">Written scope and written report — no calls. No wallet access for the first scan.</div>
</div></section>
{body}
</main>
{FOOT}
</body>
</html>"""


def index_body() -> str:
    return """
<section><div class="wrap">
  <div class="grid cards">
    <div class="card"><span class="tag">Market</span><b>112 agent-payment startups</b><p>Dealroom mapped 112 agent-payment startups; 81 of 94 with a known date were founded in 2025–2026. Rails are crowded.</p></div>
    <div class="card"><span class="tag">Pain</span><b>73% AI budgets overrun</b><p>98% of FinOps teams track AI spend, but 73% still blow the budget; only 26% see it fully in real time.</p></div>
    <div class="card"><span class="tag">Trust</span><b>4% would let an agent finish checkout</b><p>BCG: 81% of US consumers expect to use agents when shopping, but only 4% would let an agent complete the purchase.</p></div>
  </div>
</div></section>

<section><div class="wrap two">
  <div>
    <h2>A dashboard shows spend. It does not prove the charge was correct.</h2>
    <p class="sub">Nidhipati verifies the payment path: mandate, amount, asset, network, payee, usage, refund, verdict. It is independent of the rail, the model vendor and the custodian.</p>
    <ul class="checks">
      <li>Agent and key that signed</li>
      <li>Mandate and policy</li>
      <li>Amount, asset, network, payee</li>
      <li>Transaction hash</li>
      <li>Usage and unit price</li>
      <li>Refund and remaining amount</li>
      <li>Policy verdict and reasons</li>
      <li>Replay / receipt ID</li>
    </ul>
  </div>
  <div class="panel">
    <h3>Not another dashboard</h3>
    <p>AI FinOps and LLM observability show what you spent. They do not prove the charge was correct, and they do not recover the difference. Nidhipati is a signed receipt and an independent audit — paid only when the finding is verified.</p>
    <div style="height:14px"></div>
    <a class="btn" href="agent-spend-audit.html">How the audit works</a>
  </div>
</div></section>

<section><div class="wrap">
  <h2>Three modules, one money layer</h2>
  <div class="grid cards">
    <div class="card"><span class="tag">Proof</span><b>Proof of Spend</b><p>Signed JSON receipt. Verify mandate, amount, asset, network, payee, usage and refund offline.</p><a class="btn" href="x402-receipt.html">x402 receipt</a></div>
    <div class="card"><span class="tag">Spend</span><b>Agent Spend Audit</b><p>Duplicates, price escalation, failed-but-billed, runaway loops, missing refunds, model overpay.</p><a class="btn" href="agent-spend-audit.html">Spend audit</a></div>
    <div class="card"><span class="tag">Reserve</span><b>RWA proof of reserve</b><p>Reserve composition, NAV inputs, source hashes, signed report — for small issuers and funds.</p><a class="btn" href="rwa-proof-of-reserve.html">RWA reserve</a></div>
  </div>
</div></section>

<section><div class="wrap">
  <h2>How it works</h2>
  <div class="grid cards">
    <div class="card"><b>1. Send the data</b><p>Public tx hashes, a CSV/invoice export, or a description. No keys, no custody.</p></div>
    <div class="card"><b>2. Get the evidence</b><p>48-hour free scan; paid audit with findings, amounts and fixes.</p></div>
    <div class="card"><b>3. Fix and retest</b><p>One retest of the agreed findings; then a monthly control retainer if useful.</p></div>
  </div>
</div></section>

<section><div class="wrap">
  <h2>Pricing</h2>
  <table>
    <tr><th>Offer</th><th>Price</th><th>What</th></tr>
    <tr><td>Free scan</td><td>0</td><td>One flow / one week, 48h report</td></tr>
    <tr><td>Spend audit</td><td>$2,500 or 20% of verified savings</td><td>Duplicates, escalation, failed-but-billed, refunds, routing</td></tr>
    <tr><td>Control retainer</td><td>$1,500/mo</td><td>Budgets, alerts, receipt checks, monthly report</td></tr>
    <tr><td>RWA reserve report</td><td>$2,500–5,000</td><td>Proof of reserve / NAV, signed, sourced</td></tr>
    <tr><td>Prediction resolution</td><td>$500–2,000</td><td>Evidence, sources, conflicts, signed report</td></tr>
  </table>
  <p class="micro">USDC on Base/Solana; 50% upfront. Card on-ramp by request; no custody.</p>
</div></section>
"""


def audit_body() -> str:
    return """
<section><div class="wrap two">
  <div>
    <h2>Eight checks before the invoice</h2>
    <ul class="checks">
      <li>Duplicate retries without idempotency</li>
      <li>Quote vs settled price</li>
      <li>Failed call that still billed</li>
      <li>Runaway loop / retry storm</li>
      <li>Missing refund after over-authorization</li>
      <li>Wrong asset, network or payee</li>
      <li>Frontier model on a simple task</li>
      <li>Budget that lives in the prompt, not the signing path</li>
    </ul>
  </div>
  <div class="panel">
    <h3>What you get</h3>
    <p>A written report: finding, evidence, estimated overpay, fix. We mark estimates as estimates; “recovered” means verified against the provider invoice or transaction.</p>
    <div style="height:14px"></div>
    <a class="btn primary" href="__FORM__">Request a free scan</a>
  </div>
</div></section>

<section><div class="wrap">
  <h2>Illustrative report (synthetic, not a client)</h2>
  <table>
    <tr><th>Finding</th><th>Calls</th><th>Overpay</th></tr>
    <tr><td>Duplicate retries</td><td>4.2%</td><td>$1,260</td></tr>
    <tr><td>Price escalation</td><td>1.8%</td><td>$840</td></tr>
    <tr><td>Failed-but-billed</td><td>0.9%</td><td>$310</td></tr>
    <tr><td>Frontier model on simple tasks</td><td>11%</td><td>$2,100</td></tr>
    <tr><td><b>Total</b></td><td></td><td><b>$4,510</b></td></tr>
  </table>
  <p class="micro">Example format only. No real client numbers are shown.</p>
</div></section>
""".replace("__FORM__", FORM)


def x402_body() -> str:
    return """
<section><div class="wrap two">
  <div>
    <h2>200 OK is not a payment</h2>
    <p class="sub">x402 makes payment part of the HTTP request. A 402 challenge is followed by an authorization and a settlement. The response can be 200 while the receipt is wrong, missing, replayed, or for a different payee.</p>
    <ul class="checks">
      <li>Amount, asset, network, payee</li>
      <li>Transaction hash and settlement time</li>
      <li>Mandate and expiry</li>
      <li>Usage × unit price</li>
      <li>Refund and remaining amount</li>
      <li>Replay / receipt ID</li>
      <li>Verdict and policy version</li>
      <li>On-chain verification (v0.2)</li>
    </ul>
  </div>
  <div class="panel">
    <h3>Proof of Spend v0.1</h3>
    <p>A signed JSON receipt. Draft schema, example and validator. Not a token, not custody.</p>
    <div style="height:14px"></div>
    <a class="btn" href="https://github.com/mrpkk/nidhipati/blob/main/docs/PROOF-OF-SPEND.md">Spec</a>
    <a class="btn" href="https://github.com/mrpkk/nidhipati">Validator</a>
  </div>
</div></section>

<section><div class="wrap">
  <h2>What the validator checks</h2>
  <pre>schema → signature → mandate expiry → amount
→ usage × price → refund ≤ payment → verdict = allow
→ receipt id</pre>
  <p class="micro">v0.1 does not query the chain; it says <code>onchain_verified=false</code> explicitly. That is the honest boundary.</p>
</div></section>
"""


def rwa_body() -> str:
    return """
<section><div class="wrap two">
  <div>
    <h2>Proof of reserve is not a statutory audit</h2>
    <p class="sub">A small RWA issuer needs a verifiable report: what backs the token, how NAV is calculated, which sources were used, and when. Nidhipati signs the evidence; a licensed auditor/legal partner handles the regulated opinion.</p>
    <ul class="checks">
      <li>Reserve composition and custody</li>
      <li>Bank/custodian statement hash</li>
      <li>NAV inputs and formulas</li>
      <li>Price sources and timestamps</li>
      <li>Outstanding token supply</li>
      <li>Reconciliation and exceptions</li>
      <li>Signed report and evidence links</li>
      <li>Human/legal review</li>
    </ul>
  </div>
  <div class="panel">
    <h3>Who it is for</h3>
    <p>Small RWA issuers, funds, DAOs and treasuries that need an independent evidence report without building a full audit team.</p>
    <div style="height:14px"></div>
    <a class="btn primary" href="__FORM__">Request a free reserve review</a>
  </div>
</div></section>

<section><div class="wrap">
  <h2>Data we can use</h2>
  <p>RWA.xyz, Chainstack rwa-sdk, RedStone, custodian statements, on-chain supply, issuer NAV files. If a source is missing, the report says “missing” — it does not invent a number.</p>
</div></section>
""".replace("__FORM__", FORM)


def prediction_body() -> str:
    return """
<section><div class="wrap two">
  <div>
    <h2>Resolution is evidence, not opinion</h2>
    <p class="sub">A prediction market dispute needs a timeline: rules, sources, timestamps, hashes, conflicts. Nidhipati produces a signed evidence report; it does not operate a market, take bets, or decide the outcome by itself.</p>
    <ul class="checks">
      <li>Market rules and resolution source</li>
      <li>Source URL, timestamp, hash</li>
      <li>Conflicting sources</li>
      <li>Resolution window</li>
      <li>Human review</li>
      <li>Signed report</li>
    </ul>
  </div>
  <div class="panel">
    <h3>For</h3>
    <p>Market creators, traders, media and dispute teams that need a verifiable evidence trail.</p>
    <div style="height:14px"></div>
    <a class="btn primary" href="__FORM__">Request an evidence review</a>
  </div>
</div></section>
""".replace("__FORM__", FORM)


def stable_body() -> str:
    return """
<section><div class="wrap two">
  <div>
    <h2>Reconcile USDC, invoices and refunds</h2>
    <p class="sub">A payment ops desk for DAOs and SMBs: match invoices to on-chain transactions, find duplicates, unmatched payments, missing refunds and wrong-network transfers. Read-only; no custody.</p>
    <ul class="checks">
      <li>Invoice ↔ tx matching</li>
      <li>Duplicate payments</li>
      <li>Unmatched / partial</li>
      <li>Refund missing</li>
      <li>Wrong asset/network</li>
      <li>Monthly signed report</li>
    </ul>
  </div>
  <div class="panel">
    <h3>Retainer</h3>
    <p>$1,500/mo, 3 months minimum. CSV/on-chain tx input. No keys, no custody, no money transmission.</p>
    <div style="height:14px"></div>
    <a class="btn primary" href="__FORM__">Request a free reconciliation sample</a>
  </div>
</div></section>
""".replace("__FORM__", FORM)


PAGES = [
    ("", "Proof of Spend for AI agents — verify what the agent paid", "Nidhipati verifies the payment path for AI agents: mandate, amount, asset, network, payee, usage, refund and verdict in a signed receipt. Free scan.", "Proof of Spend for AI agents", index_body()),
    ("agent-spend-audit", "AI agent spend audit — find duplicate calls and refunds", "Audit AI-agent, API and x402 spend: duplicates, price escalation, failed-but-but-billed calls, runaway loops and missing refunds. Free scan, written report.", "AI agent spend audit", audit_body()),
    ("x402-receipt", "x402 receipt verification — why 200 OK is not a payment", "Verify an x402 payment receipt: amount, asset, network, payee, tx hash, mandate, usage and refund. Proof of Spend v0.1 spec and validator.", "x402 receipt verification", x402_body()),
    ("rwa-proof-of-reserve", "RWA proof of reserve and NAV reporting", "Independent proof-of-reserve and NAV evidence for small RWA issuers and funds: reserve composition, source hashes, signed report. Not a statutory audit.", "RWA proof of reserve and NAV reporting", rwa_body()),
    ("prediction-resolution", "Prediction market resolution evidence and signed report", "A verifiable evidence trail for prediction market resolution: rules, sources, timestamps, hashes, conflicts and a signed report. Not gambling or market operation.", "Prediction market resolution evidence", prediction_body()),
    ("stablecoin-reconciliation", "Stablecoin reconciliation for DAOs and SMBs", "Match USDC invoices to on-chain transactions, find duplicates, unmatched payments and missing refunds. Read-only, no custody.", "Stablecoin reconciliation", stable_body()),
]

FAQS = {
    "": [
        ("Do you need my private keys?", "No. The first scan needs public transaction hashes, a CSV/invoice export, or a description. We never ask for keys or seed phrases."),
        ("Is this a statutory audit?", "No. It is technical evidence and a signed receipt. RWA/NAV work is a supporting report; a licensed auditor or lawyer gives the regulated opinion."),
        ("How much does it cost?", "Free scan for one flow. Paid audit: $2,500 or 20% of verified savings. Control retainer: $1,500/mo. No custody."),
        ("Are you certified?", "No certifications are claimed. We are a new practice with an open-source validator and a written report."),
    ],
    "agent-spend-audit": [
        ("What data do you need?", "A CSV/JSON usage export, invoice lines, or public transaction hashes. No keys or customer data."),
        ("How do you prove savings?", "Before/after measurement and provider invoice/transaction verification. Estimates are labelled; recovered means verified."),
        ("What if you find nothing?", "The report says so. There is no success fee without a verified finding."),
    ],
    "x402-receipt": [
        ("Does v0.1 verify the chain?", "No. It checks schema, signature, mandate, amount, usage, refund and verdict. On-chain verification is v0.2 and the result says onchain_verified=false."),
        ("Is this a token?", "No. It is a signed JSON document, not an asset."),
        ("Can a merchant use it?", "Yes: it can verify the agent's mandate and the payment receipt before fulfilling."),
    ],
    "rwa-proof-of-reserve": [
        ("Is this a statutory audit?", "No. It is an evidence report; a licensed auditor/legal partner provides the regulated opinion."),
        ("What if data is missing?", "The report marks it missing instead of inventing a number."),
    ],
    "prediction-resolution": [
        ("Do you operate a market?", "No. We produce evidence; we do not take bets, set odds, or operate a market."),
        ("What sources do you use?", "The market rules and the specified resolution sources, with timestamps and hashes."),
    ],
    "stablecoin-reconciliation": [
        ("Do you hold funds?", "No. Read-only reconciliation; no custody, no money transmission."),
        ("Which chains?", "Base and Solana first; more on request."),
    ],
}


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    urls = []
    for slug, title, desc, h1, body in PAGES:
        content = page(slug, title, desc, h1, body, FAQS.get(slug))
        name = "index.html" if slug == "" else f"{slug}.html"
        (DOCS / name).write_text(content, encoding="utf-8")
        urls.append(BASE + ("/" if slug == "" else f"/{slug}.html"))
    (DOCS / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % BASE, encoding="utf-8"
    )
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sitemap.append(f"<url><loc>{u}</loc><lastmod>2026-10-25</lastmod></url>")
    sitemap.append("</urlset>")
    (DOCS / "sitemap.xml").write_text("\n".join(sitemap), encoding="utf-8")
    (DOCS / "llms.txt").write_text(
        """# Nidhipati

> Proof of Spend for AI agents: verify mandate, amount, asset, network, payee, usage and refund in a signed receipt.

Nidhipati is a draft product with an open spec and a reference validator. It is not a payment rail, not a token, and not custody.

## Pages

- https://mrpkk.github.io/nidhipati/
- https://mrpkk.github.io/nidhipati/agent-spend-audit.html
- https://mrpkk.github.io/nidhipati/x402-receipt.html
- https://mrpkk.github.io/nidhipati/rwa-proof-of-reserve.html
- https://mrpkk.github.io/nidhipati/prediction-resolution.html
- https://mrpkk.github.io/nidhipati/stablecoin-reconciliation.html

## Spec

https://github.com/mrpkk/nidhipati/blob/main/docs/PROOF-OF-SPEND.md

## Pricing

Free scan. Audit $2,500 or 20% of verified savings. Control retainer $1,500/mo. USDC on Base/Solana. No custody.
""",
        encoding="utf-8",
    )
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built {len(urls)} pages into {DOCS}")


if __name__ == "__main__":
    main()
