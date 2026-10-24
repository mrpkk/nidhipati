/* Nidhipati free spend audit — runs entirely in the browser.
   No network, no keys, no storage. Estimates only. */
(function (root) {
  "use strict";

  const REQUIRED = ["ts", "agent_id", "tool", "quote", "settled", "status"];
  const KNOWN_ASSETS = new Set(["USDC", "USDT", "DAI", "USDG", "PYUSD"]);
  const KNOWN_NETWORKS = new Set(["base", "solana", "ethereum", "arbitrum", "polygon", "optimism", "eip155:8453", "eip155:1"]);
  const FAILED = new Set(["failed", "error", "rejected", "timeout", "5xx"]);
  const MS = 1000;

  function parseCSV(text) {
    text = String(text || "").replace(/^\uFEFF/, "");
    const rows = [];
    let row = [];
    let field = "";
    let quoted = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (quoted) {
        if (ch === '"' && text[i + 1] === '"') { field += '"'; i++; }
        else if (ch === '"') quoted = false;
        else field += ch;
      } else if (ch === '"') {
        quoted = true;
      } else if (ch === ",") {
        row.push(field); field = "";
      } else if (ch === "\n") {
        row.push(field); rows.push(row); row = []; field = "";
      } else if (ch !== "\r") {
        field += ch;
      }
    }
    row.push(field);
    rows.push(row);
    const clean = rows.filter((r) => r.some((v) => String(v).trim() !== ""));
    if (!clean.length) return { headers: [], rows: [] };
    const headers = clean.shift().map((h) => String(h).trim().toLowerCase());
    return { headers, rows: clean.map((r) => {
      const obj = {};
      headers.forEach((h, i) => { obj[h] = (r[i] ?? "").trim(); });
      return obj;
    }) };
  }

  function num(value) {
    if (value === "" || value === null || value === undefined) return null;
    const n = Number(String(value).trim());
    return Number.isFinite(n) ? n : null;
  }

  function median(values) {
    if (!values.length) return 0;
    const sorted = values.slice().sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  }

  function money(n) {
    return "$" + (Math.round(n * 100) / 100).toFixed(2);
  }

  function analyzeCSV(text, options) {
    const parsed = parseCSV(text);
    const missing = REQUIRED.filter((h) => !parsed.headers.includes(h));
    if (missing.length) {
      return { ok: false, errors: ["missing columns: " + missing.join(", ")], findings: [], summary: null, rows: 0 };
    }
    const errors = [];
    const items = [];
    parsed.rows.forEach((raw, index) => {
      const row = index + 2; // header is line 1
      const ts = Date.parse(raw.ts);
      if (!Number.isFinite(ts)) { errors.push("row " + row + ": bad ts"); return; }
      const quote = num(raw.quote);
      const settled = num(raw.settled);
      if (quote === null || settled === null) { errors.push("row " + row + ": quote/settled must be numbers"); return; }
      items.push({
        row, ts, raw,
        agent: raw.agent_id || "(missing)",
        tool: raw.tool || "(missing)",
        model: raw.model || "",
        quote, settled,
        actual: num(raw.actual),
        refund: num(raw.refund) || 0,
        status: String(raw.status || "").toLowerCase(),
        tx: raw.tx_hash || "",
        asset: (raw.asset || "").trim(),
        network: (raw.network || "").trim(),
        payee: (raw.payee || "").trim()
      });
    });

    const findings = [];
    const add = (item, code, severity, amount, detail, evidence) => {
      findings.push({ row: item.row, code, severity, agent: item.agent, amount: amount || 0, detail, evidence: evidence || "" });
    };

    // duplicates: same tx, or equal payment within 120s with no receipt on both
    const byHash = new Map();
    const noReceipt = [];
    for (const item of items) {
      if (item.tx) {
        if (byHash.has(item.tx)) add(item, "duplicate_charge", "error", item.settled, "same tx_hash as row " + byHash.get(item.tx), item.tx);
        else byHash.set(item.tx, item.row);
      } else {
        for (const prev of noReceipt) {
          if (prev.agent === item.agent && prev.tool === item.tool &&
              Math.abs(prev.settled - item.settled) < 1e-9 &&
              Math.abs(prev.ts - item.ts) <= 120 * MS) {
            add(item, "duplicate_charge", "error", item.settled, "equal payment within 120s; no receipt on both rows", "");
            break;
          }
        }
        noReceipt.push(item);
      }
    }

    for (const item of items) {
      if (item.settled > item.quote * 1.01) {
        add(item, "price_escalation", "error", item.settled - item.quote,
          "settled " + money(item.settled) + " above quote " + money(item.quote), item.tx);
      }
      if ((FAILED.has(item.status) || /^5\d\d$/.test(item.status)) && item.settled > 0) {
        add(item, "failed_but_billed", "error", item.settled,
          "status '" + item.status + "' with " + money(item.settled) + " charged", item.tx);
      }
      if (item.actual !== null && item.settled > item.actual + 1e-9 && item.refund <= 0) {
        add(item, "missing_refund", "error", item.settled - item.actual,
          "charged " + money(item.settled) + " for actual " + money(item.actual) + ", refund not recorded", item.tx);
      }
      if (item.asset && !KNOWN_ASSETS.has(item.asset.toUpperCase())) {
        add(item, "unknown_asset", "warning", item.settled, "asset '" + item.asset + "' is not recognised", item.tx);
      }
      if (item.network && !KNOWN_NETWORKS.has(item.network.toLowerCase())) {
        add(item, "unknown_network", "warning", item.settled, "network '" + item.network + "' is not recognised", item.tx);
      }
      if (!item.payee) add(item, "missing_payee", "warning", item.settled, "no payee recorded", item.tx);
    }

    // runaway: >30 calls in any 60s window per agent
    const byAgent = new Map();
    for (const item of items) {
      if (!byAgent.has(item.agent)) byAgent.set(item.agent, []);
      byAgent.get(item.agent).push(item);
    }
    for (const [agent, list] of byAgent) {
      list.sort((a, b) => a.ts - b.ts);
      let left = 0;
      let reported = false;
      for (let right = 0; right < list.length; right++) {
        while (list[right].ts - list[left].ts > 60 * MS) left++;
        if (right - left + 1 > 30 && !reported) {
          add(list[right], "runaway_loop", "warning", 0, (right - left + 1) + " calls in 60s for " + agent + " (threshold 30)", "");
          reported = true;
        }
      }
    }

    // model overpay: >3x the same agent's median for the same tool+model, group >=3
    const groups = new Map();
    for (const item of items) {
      if (!item.model) continue;
      const key = item.agent + "|" + item.tool + "|" + item.model;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    }
    for (const list of groups.values()) {
      if (list.length < 3) continue;
      const med = median(list.map((x) => x.settled));
      if (med <= 0) continue;
      for (const item of list) {
        if (item.settled > med * 3) {
          add(item, "model_overpay", "warning", item.settled - med,
            "paid " + money(item.settled) + " against a median " + money(med) + " for this tool and model", item.tx);
        }
      }
    }

    // budget: optional per-agent monthly limit
    const budget = num(options && options.budgetPerAgent);
    if (budget !== null && budget > 0) {
      const totals = new Map();
      for (const item of items) totals.set(item.agent, (totals.get(item.agent) || 0) + item.settled);
      for (const [agent, total] of totals) {
        if (total > budget) add({ row: 1, agent, tx: "" }, "budget_exceeded", "error", total - budget,
          "spent " + money(total) + " against a limit of " + money(budget), "");
      }
    } else {
      findings.push({ row: 0, code: "budget_bypass", severity: "warning", agent: "-", amount: 0,
        detail: "no monthly budget supplied: a budget in the prompt is not a control", evidence: "" });
    }

    findings.sort((a, b) => a.row - b.row || a.code.localeCompare(b.code));
    const spent = items.reduce((s, x) => s + x.settled, 0);
    const noReasonCodes = new Set(["duplicate_charge", "failed_but_billed", "missing_refund"]);
    const noReason = findings.filter((f) => noReasonCodes.has(f.code)).reduce((s, f) => s + f.amount, 0);
    const aboveUsual = findings.filter((f) => f.code === "model_overpay").reduce((s, f) => s + f.amount, 0);
    const overBudget = findings.filter((f) => f.code === "budget_exceeded").reduce((s, f) => s + f.amount, 0);
    return {
      ok: true,
      errors,
      rows: items.length,
      findings,
      summary: {
        settled: spent,
        no_reason: noReason,
        above_usual: aboveUsual,
        over_budget: overBudget,
        errors: findings.filter((f) => f.severity === "error").length,
        warnings: findings.filter((f) => f.severity === "warning").length
      }
    };
  }

  function reportMarkdown(result) {
    if (!result.ok) return "# Agent spend audit\n\n" + result.errors.join("\n") + "\n";
    const s = result.summary;
    const lines = [
      "# Agent spend audit",
      "",
      "Rows read: **" + result.rows + "** · settled **" + money(s.settled) + "** · " +
        "spent without a reason **" + money(s.no_reason) + "** · above the usual price **" +
        money(s.above_usual) + "** · over the limit **" + money(s.over_budget) + "** · errors " +
        s.errors + ", warnings " + s.warnings,
      "",
      "| row | code | severity | agent | $ | detail | evidence |",
      "|---|---|---|---|---|---|---|"
    ];
    for (const f of result.findings) {
      lines.push("| " + [f.row, "`" + f.code + "`", f.severity, f.agent, f.amount.toFixed(2), f.detail.replace(/\|/g, "\\|"), f.evidence].join(" | ") + " |");
    }
    lines.push("");
    lines.push("> Estimates from the records provided. Nothing was recovered; nothing was verified on-chain.");
    lines.push("> Categories can overlap; do not add them into one \"saved\" number.");
    return lines.join("\n") + "\n";
  }

  const api = { parseCSV, analyzeCSV, reportMarkdown, money };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.SpendAudit = api;
})(typeof window !== "undefined" ? window : globalThis);
