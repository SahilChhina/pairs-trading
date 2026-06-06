import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";

function EqTip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const v = payload[0].value;
  const init = 100000;
  const pct = ((v - init) / init * 100).toFixed(2);
  const sign = pct >= 0 ? "+" : "";
  return (
    <div className="tooltip">
      <div className="t-label">{label}</div>
      <div className="t-val">${Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
      <div style={{ fontSize: 12, color: v >= init ? "var(--green)" : "var(--red)", marginTop: 3 }}>
        {sign}{pct}% vs start
      </div>
    </div>
  );
}

function DdTip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const v = payload[0].value;
  return (
    <div className="tooltip">
      <div className="t-label">{label}</div>
      <div className="t-val" style={{ color: "var(--red)" }}>{Number(v).toFixed(2)}%</div>
      <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 3 }}>below peak</div>
    </div>
  );
}

export default function EquitySection({ data }) {
  if (!data?.length) return null;

  const init = data[0]?.equity ?? 100000;
  const step = Math.max(1, Math.floor(data.length / 6));
  const ticks = data.filter((_, i) => i % step === 0).map((d) => d.date);
  const fmt = (d) => d ? d.slice(0, 7) : "";

  return (
    <section className="step">
      <div className="step-number">Step 5 — Portfolio Over Time</div>
      <h2 className="step-heading">How did the portfolio value change?</h2>
      <p className="step-body">
        The equity curve below shows the portfolio's dollar value on each trading day
        during the test period. The drawdown chart shows how far below the previous
        peak the portfolio was at any point — a measure of pain during the strategy's
        worst stretches.
      </p>

      <div className="panel">
        <div className="panel-title">Portfolio value ($)</div>
        <div className="panel-sub">Starting capital: $100,000 · Test period: 2022 → present</div>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={data} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
            <defs>
              <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4f9cf9" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#4f9cf9" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#232c3f" vertical={false} />
            <XAxis dataKey="date" ticks={ticks} tickFormatter={fmt} tickLine={false} axisLine={{ stroke: "#232c3f" }} />
            <YAxis tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} tickLine={false} axisLine={false} width={52} domain={["auto","auto"]} />
            <Tooltip content={<EqTip />} />
            <Area type="monotone" dataKey="equity" stroke="#4f9cf9" strokeWidth={2} fill="url(#eqGrad)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="panel">
        <div className="panel-title">Drawdown (%)</div>
        <div className="panel-sub">How far below the portfolio's previous high-water mark — lower is worse</div>
        <ResponsiveContainer width="100%" height={160}>
          <AreaChart data={data} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
            <defs>
              <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f7556a" stopOpacity={0.05} />
                <stop offset="100%" stopColor="#f7556a" stopOpacity={0.4} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#232c3f" vertical={false} />
            <XAxis dataKey="date" ticks={ticks} tickFormatter={fmt} tickLine={false} axisLine={{ stroke: "#232c3f" }} />
            <YAxis tickFormatter={(v) => `${v}%`} tickLine={false} axisLine={false} width={52} />
            <Tooltip content={<DdTip />} />
            <Area type="monotone" dataKey="drawdown" stroke="#f7556a" strokeWidth={1.5} fill="url(#ddGrad)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
