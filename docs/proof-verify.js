/* Nidhipati Proof of Spend — browser verifier.
   No upload, no keys, no network. Ed25519 via WebCrypto. */
(function (root) {
  "use strict";

  function sortValue(value) {
    if (Array.isArray(value)) return value.map(sortValue);
    if (value && typeof value === "object") {
      const out = {};
      Object.keys(value).sort().forEach(function (k) { out[k] = sortValue(value[k]); });
      return out;
    }
    return value;
  }

  function canonical(value) {
    return JSON.stringify(sortValue(value));
  }

  function b64urlToBytes(text) {
    const padded = text.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (text.length % 4)) % 4);
    const raw = atob(padded);
    const out = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
    return out;
  }

  function hexToBytes(text) {
    const clean = text.replace(/^0x/, "");
    const out = new Uint8Array(clean.length / 2);
    for (let i = 0; i < out.length; i++) out[i] = parseInt(clean.slice(i * 2, i * 2 + 2), 16);
    return out;
  }

  function keyBytes(text) {
    const trimmed = String(text || "").trim();
    if (/^(0x)?[0-9a-fA-F]{64}$/.test(trimmed)) return hexToBytes(trimmed);
    return b64urlToBytes(trimmed);
  }

  function parseTime(value) {
    const t = Date.parse(value);
    return Number.isFinite(t) ? t : null;
  }

  function num(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  async function verifyReceipt(input, publicKey) {
    const checks = {};
    const errors = [];
    const warnings = ["onchain_verified=false: this build does not query the chain"];
    let doc;
    try {
      doc = typeof input === "string" ? JSON.parse(input) : input;
    } catch (e) {
      return { ok: false, receipt_id: "", checks: {}, errors: ["JSON parse: " + e.message], warnings: warnings };
    }
    const required = ["version", "receipt_id", "issued_at", "agent", "mandate", "action", "payment", "usage", "verdict", "signature"];
    const missing = required.filter(function (k) { return doc[k] === undefined || doc[k] === null; });
    checks.schema = { ok: missing.length === 0, detail: missing.length ? "missing: " + missing.join(", ") : "required fields present" };
    if (missing.length) errors.push("schema: missing " + missing.join(", "));

    const sig = doc.signature || {};
    checks.signature_alg = { ok: sig.alg === "Ed25519", detail: sig.alg || "missing" };
    if (sig.alg !== "Ed25519") errors.push("signature_alg: expected Ed25519");

    try {
      const payload = JSON.parse(JSON.stringify(doc));
      payload.signature.value = "";
      const key = await crypto.subtle.importKey("raw", keyBytes(publicKey), { name: "Ed25519" }, false, ["verify"]);
      const ok = await crypto.subtle.verify(
        { name: "Ed25519" }, key, b64urlToBytes(sig.value || ""),
        new TextEncoder().encode(canonical(payload))
      );
      checks.signature = { ok: ok, detail: ok ? "Ed25519 valid" : "invalid" };
      if (!ok) errors.push("signature: invalid");
    } catch (e) {
      checks.signature = { ok: false, detail: "bad public key or signature: " + e.message };
      errors.push("signature: " + e.message);
    }

    const payment = doc.payment || {};
    const mandate = doc.mandate || {};
    const settled = parseTime(payment.settled_at);
    const expires = parseTime(mandate.expires_at);
    const expiryOk = settled !== null && expires !== null && settled <= expires;
    checks.mandate_expiry = { ok: expiryOk, detail: "settled <= expires" };
    if (!expiryOk) errors.push("mandate_expiry: payment after expiry or bad date");

    const amount = num(payment.amount);
    const amountOk = amount !== null && amount > 0;
    checks.amount_positive = { ok: amountOk, detail: String(payment.amount) };
    if (!amountOk) errors.push("amount: must be positive");

    const usage = doc.usage || {};
    const qty = num(usage.quantity);
    const unit = num(usage.unit_price);
    const usageOk = qty !== null && unit !== null && amount !== null && Math.abs(qty * unit - amount) <= 1e-9;
    checks.usage_amount = { ok: usageOk, detail: "quantity * unit_price == amount" };
    if (!usageOk) errors.push("usage: quantity * unit_price does not match amount");

    const refund = num((doc.refund || {}).amount || 0);
    const refundOk = refund !== null && amount !== null && refund >= 0 && refund <= amount;
    checks.refund = { ok: refundOk, detail: "0 <= refund <= amount" };
    if (!refundOk) errors.push("refund: must be between 0 and amount");

    const verdict = doc.verdict || {};
    const verdictOk = verdict.decision === "allow";
    checks.verdict_allow = { ok: verdictOk, detail: verdict.decision || "missing" };
    if (!verdictOk) errors.push("verdict: settled payment requires allow");

    const receiptOk = Boolean(String(doc.receipt_id || "").trim());
    checks.receipt_id = { ok: receiptOk, detail: receiptOk ? "present" : "empty" };
    if (!receiptOk) errors.push("receipt_id: empty");

    return {
      ok: errors.length === 0,
      receipt_id: doc.receipt_id || "",
      checks: checks,
      errors: errors,
      warnings: warnings
    };
  }

  const api = { verifyReceipt: verifyReceipt, canonical: canonical };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.ProofVerify = api;
})(typeof window !== "undefined" ? window : globalThis);
