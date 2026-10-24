const assert = require("node:assert");
const { analyzeCSV, parseCSV } = require("../docs/spend-audit.js");

const CSV = `ts,agent_id,tool,model,quote,settled,actual,refund,asset,network,tx_hash,payee,status
2026-10-01T10:00:00Z,writer,llm,gpt,0.02,0.02,0.02,0,USDC,base,0x1,0xpayee,ok
2026-10-01T10:01:00Z,writer,llm,gpt,0.02,0.05,0.05,0,USDC,base,0x2,0xpayee,ok
2026-10-01T10:02:00Z,writer,llm,gpt,0.02,0.02,0.02,0,USDC,base,0x1,0xpayee,ok
2026-10-01T10:03:00Z,writer,llm,gpt,0.02,0.02,0.02,0,USDC,base,,0xpayee,failed
2026-10-01T10:04:00Z,writer,llm,gpt,0.10,0.10,0.04,0,USDC,base,0x3,0xpayee,ok
2026-10-01T10:05:00Z,writer,llm,gpt,0.02,0.02,0.02,0,MOON,moonnet,0x4,,ok
`;

const parsed = parseCSV(CSV);
assert.equal(parsed.headers[0], "ts");
assert.equal(parsed.rows.length, 6);

const result = analyzeCSV(CSV, { budgetPerAgent: 0.2 });
assert.equal(result.ok, true, result.errors.join("; "));
const codes = new Set(result.findings.map((f) => f.code));
for (const code of ["duplicate_charge", "price_escalation", "failed_but_billed", "missing_refund", "unknown_asset", "unknown_network", "missing_payee", "model_overpay", "budget_exceeded"]) {
  assert.ok(codes.has(code), "missing " + code + " in " + [...codes].join(","));
}
assert.ok(result.summary.no_reason > 0);
assert.ok(result.summary.above_usual > 0);
assert.ok(result.summary.over_budget > 0);

const clean = analyzeCSV(`ts,agent_id,tool,model,quote,settled,tx_hash,payee,status
2026-10-01T10:00:00Z,a,t,m,0.02,0.02,0x1,0xpayee,ok
2026-10-01T10:01:00Z,a,t,m,0.02,0.02,0x2,0xpayee,ok
2026-10-01T10:02:00Z,a,t,m,0.02,0.02,0x3,0xpayee,ok
`, { budgetPerAgent: 1 });
assert.equal(clean.findings.filter((f) => f.severity === "error").length, 0, JSON.stringify(clean.findings));

const noBudget = analyzeCSV(CSV);
assert.ok(noBudget.findings.some((f) => f.code === "budget_bypass"));

// 31 calls in 60s -> runaway
let rows = "ts,agent_id,tool,quote,settled,status\n";
for (let i = 0; i < 31; i++) {
  rows += `2026-10-01T10:00:${String(i).padStart(2, "0")}Z,loop,t,0.01,0.01,ok\n`;
}
const runaway = analyzeCSV(rows, { budgetPerAgent: 1 });
assert.ok(runaway.findings.some((f) => f.code === "runaway_loop"), JSON.stringify(runaway.findings));

console.log("spend-audit js tests: ok", result.findings.length, "findings");
