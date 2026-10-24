const assert = require("node:assert");
const fs = require("node:fs");
const { verifyReceipt } = require("../docs/proof-verify.js");

(async () => {
  const doc = fs.readFileSync("docs/proof-sample.signed.json", "utf8");
  const pub = fs.readFileSync("docs/proof-sample.pub", "utf8").trim();
  const good = await verifyReceipt(doc, pub);
  assert.equal(good.ok, true, good.errors.join("; "));
  assert.equal(good.checks.signature.ok, true);

  const tampered = JSON.parse(doc);
  tampered.payment.amount = "9";
  const bad = await verifyReceipt(tampered, pub);
  assert.equal(bad.ok, false);
  assert.equal(bad.checks.signature.ok, false);

  const expired = JSON.parse(doc);
  expired.mandate.expires_at = "2026-10-24T11:00:00Z";
  const exp = await verifyReceipt(expired, pub);
  assert.equal(exp.ok, false);
  assert.equal(exp.checks.mandate_expiry.ok, false);

  console.log("proof-verify js tests: ok", Object.keys(good.checks).length, "checks");
})().catch((e) => { console.error(e); process.exit(1); });
