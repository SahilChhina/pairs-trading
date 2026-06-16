import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer,
  Tooltip, XAxis, YAxis, ReferenceLine,
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

function Stat({ label, value, color, explain }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color: color || "var(--text-muted)" }}>{value}</div>
      {explain && <div className="stat-explain">{explain}</div>}
    </div>
  );
}

export default function MomentumSection({ data }) {
  const m = data?.metrics;
  const curve = data?.equity_curve;
  if (!m || !Object.keys(m).length) return null;

  const totalReturn = Number(m.total_return_pct);
  const isPos = totalReturn >= 0;

  const step = curve?.length ? Math.max(1, Math.floor(curve.length / 6)) : 1;
  const ticks = curve?.filter((_, i) => i % step === 0).map((d) => d.date) ?? [];
  const fmt = (d) => d ? d.slice(0, 7) : "";

  const green = "var(--green)";
  const red = "var(--red)";
  const neutral = "var(--text-muted)";

  return (
    <section className="step">
      <div className="step-number">Momentum Strategy</div>
      <h2 className="step-heading">Cross-sectional momentum — rank the universe, ride the winners</h2>
      <p className="step-body">
        Every month we score <strong>53 large-cap stocks</strong> by how much they returned
        over the past year (skipping the most recent month to avoid short-term reversal).
        The top 20% become <strong>long positions</strong>; the bottom 20% become
        <strong> short positions</strong>. We rebalance every month and charge realistic
        transaction costs (5 bps) and slippage (5 bps) on every dollar turned over.
      </p>

      <div className="callout blue">
        <span className="callout-icon">📈</span>
        <div className="callout-text">
          <strong>The idea in one sentence:</strong> stocks that have been rising tend to keep
          rising for a while — and stocks that have been falling tend to keep falling.
          We systematically exploit that pattern across an entire universe every month.
        </div>
      </div>

      {/* Headline */}
      <div className="outcome-card" style={{ marginBottom: 20 }}>
        <div className="outcome-label">Total return on $100,000 · 2016 → present</div>
        <div className={`outcome-value ${isPos ? "pos" : "neg"}`}>
          {isPos ? "+" : ""}{totalReturn.toFixed(2)}%
        </div>
        <div className="outcome-fine">
          $100,000 grew to{" "}
          <strong>${Number(m.final_value).toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong>
          {" · "}{Number(m.n_trades).toLocaleString()} individual position trades
          {" · "}{m.n_rebalances} monthly rebalances
        </div>
      </div>

      {/* Risk / return grid */}
      <div className="stat-row">
        <Stat label="CAGR" value={`${Number(m.cagr_pct).toFixed(2)}%`}
          color={m.cagr_pct >= 0 ? green : red}
          explain="Annualised compound return" />
        <Stat label="Sharpe ratio" value={Number(m.sharpe_ratio).toFixed(2)}
          color={m.sharpe_ratio >= 1 ? green : m.sharpe_ratio >= 0 ? neutral : red}
          explain="Return per unit of risk. Above 1 is good; below 0 means the risk wasn't worth it." />
        <Stat label="Max drawdown" value={`${Number(m.max_drawdown_pct).toFixed(1)}%`}
          color={red}
          explain="Worst peak-to-trough loss during the backtest" />
        <Stat label="Sortino ratio" value={Number(m.sortino_ratio).toFixed(2)}
          color={m.sortino_ratio >= 1 ? green : neutral}
          explain="Like Sharpe but only penalises downside volatility" />
      </div>

      {/* Per-trade grid */}
      <div className="stat-row" style={{ marginTop: 12 }}>
        <Stat label="Win rate" value={`${Number(m.win_rate_pct).toFixed(1)}%`}
          color={m.win_rate_pct >= 50 ? green : red}
          explain="How often each individual position ended in profit" />
        <Stat label="Profit factor" value={Number(m.profit_factor).toFixed(3)}
          color={m.profit_factor >= 1 ? green : red}
          explain="Total profits ÷ total losses. Above 1 means more won than lost in dollar terms." />
        <Stat label="Avg trade return" value={`+${Number(m.avg_trade_return_pct).toFixed(2)}%`}
          color={green}
          explain="Mean return per individual position held for one month" />
        <Stat label="Avg holding" value={`${Number(m.avg_holding_days).toFixed(0)} days`}
          color={neutral}
          explain="Each position held for roughly one calendar month" />
      </div>

      {/* Monthly stats */}
      <div className="stat-row" style={{ marginTop: 12, gridTemplateColumns: "repeat(3,1fr)" }}>
        <Stat label="Monthly hit rate" value={`${Number(m.monthly_hit_rate_pct).toFixed(1)}%`}
          color={m.monthly_hit_rate_pct >= 50 ? green : red}
          explain="Percentage of rebalance periods where the portfolio made money" />
        <Stat label="Best month" value={`+${Number(m.best_month_pct).toFixed(2)}%`}
          color={green} explain="Strongest single rebalance period" />
        <Stat label="Worst month" value={`${Number(m.worst_month_pct).toFixed(2)}%`}
          color={red} explain="Weakest single rebalance period" />
      </div>

      {/* Equity chart */}
      {curve?.length > 0 && (
        <div className="panel" style={{ marginTop: 24 }}>
          <div className="panel-title">Portfolio value over time ($)</div>
          <div className="panel-sub">
            Starting capital $100,000 · 53-stock universe · monthly rebalance · costs included
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={curve} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
              <defs>
                <linearGradient id="momGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#a78bfa" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#a78bfa" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#232c3f" vertical={false} />
              <XAxis dataKey="date" ticks={ticks} tickFormatter={fmt}
                tickLine={false} axisLine={{ stroke: "#232c3f" }} />
              <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                tickLine={false} axisLine={false} width={56} domain={["auto", "auto"]} />
              <ReferenceLine y={100000} stroke="#444c62" strokeDasharray="4 4" />
              <Tooltip content={<EqTip />} />
              <Area type="monotone" dataKey="equity" stroke="#a78bfa"
                strokeWidth={2} fill="url(#momGrad)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Benchmark vs cost context */}
      <div className="stat-row" style={{ marginTop: 16, gridTemplateColumns: "1fr 1fr" }}>
        <div className="stat-card">
          <div className="stat-label">vs Buy-and-hold benchmark</div>
          <div className="stat-value neg">
            {Number(m.annualized_alpha_pct).toFixed(2)}%/yr alpha
          </div>
          <div className="stat-explain">
            The equal-weight benchmark returned{" "}
            <strong>+{Number(m.benchmark_total_return_pct).toFixed(1)}%</strong> over the
            same period — significantly more than the momentum strategy's +{totalReturn.toFixed(1)}%.
            The 2016–2026 bull market heavily rewarded buy-and-hold in mega-cap tech.
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Cost drag from turnover</div>
          <div className="stat-value neg">
            −{Number(m.total_cost_drag_pct).toFixed(1)}%
          </div>
          <div className="stat-explain">
            Avg monthly turnover of{" "}
            <strong>{Number(m.avg_turnover_pct).toFixed(0)}%</strong> means the portfolio
            is nearly fully replaced each month. At 10 bps round-trip that compounds to a
            significant performance drag. Reducing rebalance frequency to quarterly
            would cut costs by ~3×.
          </div>
        </div>
      </div>

      <div className="callout amber" style={{ marginTop: 16 }}>
        <span className="callout-icon">📝</span>
        <div className="callout-text">
          <strong>What the numbers actually say:</strong> The strategy has a real edge —
          win rate above 50%, profit factor above 1, and positive average trade return.
          The problem is <em>not</em> the signal; it's the cost. High monthly turnover
          (88.6%) drags ~9% off the total return. The momentum effect is real and
          positive, but it's being eaten by friction. The clearest improvement is
          reducing rebalance frequency (quarterly) or narrowing the universe to
          concentrate only in the strongest signals.
        </div>
      </div>
    </section>
  );
}
