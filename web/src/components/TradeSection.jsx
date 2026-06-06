import { useMemo, useState } from "react";

const COLS = [
  { key: "entry_date",   label: "Entry",      type: "str" },
  { key: "exit_date",    label: "Exit",       type: "str" },
  { key: "direction",    label: "Direction",  type: "dir" },
  { key: "holding_days", label: "Days held",  type: "int" },
  { key: "entry_zscore", label: "Z at entry", type: "num" },
  { key: "exit_zscore",  label: "Z at exit",  type: "num" },
  { key: "net_pnl",      label: "Net P&L",    type: "money" },
  { key: "exit_reason",  label: "Exit reason",type: "reason" },
];

function fmt(v, type) {
  if (v === undefined || v === null) return "—";
  switch (type) {
    case "money": return `${Number(v) >= 0 ? "+" : ""}$${Math.abs(Number(v)).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
    case "num":   return Number(v).toFixed(2);
    case "int":   return Number(v);
    default:      return v;
  }
}

const REASON_LABELS = {
  mean_reversion: "✅ Converged",
  stop_loss:      "🛑 Stop loss",
  max_holding:    "⏱ Time limit",
  end_of_period:  "📅 Period end",
};

export default function TradeSection({ trades }) {
  const [sortKey, setSortKey] = useState("entry_date");
  const [asc, setAsc]         = useState(true);

  const sorted = useMemo(() => {
    return [...(trades || [])].sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey];
      return av === bv ? 0 : (av > bv ? 1 : -1) * (asc ? 1 : -1);
    });
  }, [trades, sortKey, asc]);

  if (!trades?.length) return null;

  const wins  = trades.filter((t) => t.net_pnl > 0).length;
  const total = trades.length;

  const onSort = (k) => { if (k === sortKey) setAsc(!asc); else { setSortKey(k); setAsc(true); } };

  return (
    <section className="step">
      <div className="step-number">Step 6 — Every Trade</div>
      <h2 className="step-heading">The full trade log</h2>
      <p className="step-body">
        Every trade the strategy made during the test period.{" "}
        <strong>{wins} wins out of {total} trades</strong> ({(wins/total*100).toFixed(0)}% win rate).
        Click any column header to sort. <em>Net P&L</em> includes transaction costs
        and slippage.
      </p>

      <div className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {COLS.map((c) => (
                  <th key={c.key} onClick={() => onSort(c.key)}>
                    {c.label}{sortKey === c.key ? (asc ? " ↑" : " ↓") : ""}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((t, i) => (
                <tr key={i}>
                  {COLS.map((c) => {
                    if (c.type === "dir") {
                      const isLong = String(t[c.key]).includes("long");
                      return <td key={c.key}><span className={`badge ${isLong ? "long" : "short"}`}>{isLong ? "↑ Long spread" : "↓ Short spread"}</span></td>;
                    }
                    if (c.type === "reason") {
                      return <td key={c.key}><span className="badge muted">{REASON_LABELS[t[c.key]] ?? t[c.key]}</span></td>;
                    }
                    if (c.key === "net_pnl") {
                      const n = Number(t[c.key]);
                      return <td key={c.key} style={{ color: n >= 0 ? "var(--green)" : "var(--red)", fontWeight: 600 }}>{fmt(t[c.key], c.type)}</td>;
                    }
                    return <td key={c.key}>{fmt(t[c.key], c.type)}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
