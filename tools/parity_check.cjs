// Cross-check the browser audit against the Python one on the same files.
// Prints JSON: {counts, no_reason, above_usual, over_budget}. Exit 2 if unsupported.
const fs = require("node:fs");
const path = require("node:path");
require(path.join(__dirname, "..", "docs", "spend-audit.js"));
const api = globalThis.SpendAudit || globalThis.NidhipatiSpend;
if (!api) { console.error("spend-audit.js did not export"); process.exit(2); }
const [csvPath, policyPath] = process.argv.slice(2);
const text = fs.readFileSync(csvPath, "utf8");
const options = {};
if (policyPath && fs.existsSync(policyPath)) options.policy = JSON.parse(fs.readFileSync(policyPath, "utf8"));
const result = api.analyzeCSV(text, options);
if (!result.ok) { console.error(result.errors.join("; ")); process.exit(2); }
const counts = {};
for (const f of result.findings) counts[f.code] = (counts[f.code] || 0) + 1;
console.log(JSON.stringify({
  counts,
  no_reason: result.summary.no_reason,
  above_usual: result.summary.above_usual,
  over_budget: result.summary.over_budget,
}));
