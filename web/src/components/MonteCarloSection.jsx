function Band({ label, p5, p50, p95, actual, unit = "%", actualLabel = "You got" }) {
  // Position the markers on a 0–100% scale spanning [p5, p95].
  const lo = Math.min(p5, actual ?? p5);
  const hi = Math.max(p95, actual ?? p95);
  const span = hi - lo || 1;
  const pos = (v) => `${((v - lo) / span) * 100}%`;

  return (
    <div className="mc-band">
      <div className="mc-band-head">
        <span className="mc-band-label">{label}</span>
        {actual != null && (
          <span className="mc-band-actual">
            {actualLabel}: <strong>{actual.toFixed(2)}{unit}</strong>
          </span>
        )}
      </div>
      <div className="mc-track">
        <div className="mc-fill" style={{ left: pos(p5), right: `calc(100% - ${pos(p95)})` }} />
        <div className="mc-tick mc-median" style={{ left: pos(p50) }} title={`Median ${p50}${unit}`} />
        {actual != null && (
          <div className="mc-tick mc-you" style={{ left: pos(actual) }} title={`Actual ${actual}${unit}`} />
        )}
      </div>
      <div className="mc-scale">
        <span>5th: {p5.toFixed(1)}{unit}</span>
        <span>median: {p50.toFixed(1)}{unit}</span>
        <span>95th: {p95.toFixed(1)}{unit}</span>
      </div>
    </div>
  );
}

export default function MonteCarloSection({ mc }) {
  if (!mc || !mc.trade_bootstrap || !mc.monthly_bootstrap) return null;

  const tb = mc.trade_bootstrap;
  const mb = mc.monthly_bootstrap;

  return (
    <section className="step">
      <div className="step-number">Robustness — Monte Carlo</div>
      <h2 className="step-heading">Is the result real, or did we just get lucky?</h2>
      <p className="step-body">
        A single backtest is one path through history — it can't tell you whether the
        +66.9% came from a genuine edge or a lucky sequence of events. So we resampled
        the actual results <strong>{Number(mc.n_sims).toLocaleString()} times</strong> to
        build a distribution of alternate outcomes. The markers below show where the real
        result landed within that distribution.
      </p>

      {/* TEST 1 — edge significance */}
      <div className="callout blue">
        <span className="callout-icon">🎯</span>
        <div className="callout-text">
          <strong>Test 1 — Is the per-trade edge real?</strong> We reshuffle the{" "}
          {Number(tb.n_trades).toLocaleString()} individual trades thousands of times.
          If the edge keeps showing up across random samples, it's signal, not noise.
        </div>
      </div>

      <div className="outcome-card" style={{ marginBottom: 16 }}>
        <div className="outcome-label">Simulations with a positive edge</div>
        <div className={`outcome-value ${tb.pct_sims_mean_positive >= 90 ? "pos" : "neutral"}`}>
          {tb.pct_sims_mean_positive.toFixed(1)}%
        </div>
        <div className="outcome-fine">
          A coin-flip strategy would land near 50%. At{" "}
          <strong>{tb.pct_sims_mean_positive.toFixed(0)}%</strong>, the momentum edge is very
          likely <strong>real</strong> — but thin: {tb.pct_sims_pf_above_1.toFixed(0)}% of
          samples had a profit factor above 1.0, and the worst-case profit factor (
          {tb.profit_factor.p5}) sits right on the break-even line.
        </div>
      </div>

      <Band label="Mean return per trade"
        p5={tb.mean_return_pct.p5} p50={tb.mean_return_pct.p50} p95={tb.mean_return_pct.p95}
        actual={tb.actual_mean_return_pct} unit="%" />
      <Band label="Profit factor (no unit)"
        p5={tb.profit_factor.p5} p50={tb.profit_factor.p50} p95={tb.profit_factor.p95}
        actual={null} unit="" />

      {/* TEST 2 — outcome range */}
      <div className="callout blue" style={{ marginTop: 24 }}>
        <span className="callout-icon">🎲</span>
        <div className="callout-text">
          <strong>Test 2 — What range of outcomes was possible?</strong> We reshuffle the{" "}
          {mb.n_months} monthly portfolio returns into thousands of alternate equity curves.
          This reveals how much the headline number — and the drawdown — depended on the
          specific order events happened in.
        </div>
      </div>

      <div className="stat-row" style={{ gridTemplateColumns: "repeat(3,1fr)", marginBottom: 16 }}>
        <div className="stat-card">
          <div className="stat-label">Simulations ending positive</div>
          <div className={`stat-value ${mb.pct_sims_positive >= 50 ? "pos" : "neg"}`}>
            {mb.pct_sims_positive.toFixed(0)}%
          </div>
          <div className="stat-explain">How often the strategy made money at all</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Simulations beating benchmark</div>
          <div className="stat-value neg">{mb.pct_sims_beat_benchmark?.toFixed(0)}%</div>
          <div className="stat-explain">
            Underperformance vs buy-and-hold is structural, not bad luck
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Worst-case drawdown (5th %ile)</div>
          <div className="stat-value neg">{mb.max_drawdown_pct.p5.toFixed(0)}%</div>
          <div className="stat-explain">The −52% we saw was <em>not</em> the worst plausible case</div>
        </div>
      </div>

      <Band label="Total return"
        p5={mb.total_return_pct.p5} p50={mb.total_return_pct.p50} p95={mb.total_return_pct.p95}
        actual={mb.actual_total_return_pct} unit="%" />
      <Band label="Max drawdown"
        p5={mb.max_drawdown_pct.p5} p50={mb.max_drawdown_pct.p50} p95={mb.max_drawdown_pct.p95}
        actual={null} unit="%" />
      <Band label="Sharpe ratio"
        p5={mb.sharpe_ratio.p5} p50={mb.sharpe_ratio.p50} p95={mb.sharpe_ratio.p95}
        actual={null} unit="" />

      <div className="callout amber" style={{ marginTop: 20 }}>
        <span className="callout-icon">📝</span>
        <div className="callout-text">
          <strong>What Monte Carlo settled:</strong> The edge is <em>real</em> (
          {tb.pct_sims_mean_positive.toFixed(0)}% of samples positive) but small, and the
          realised +{mb.actual_total_return_pct.toFixed(0)}% was an almost perfectly{" "}
          <em>typical</em> outcome (median was {mb.total_return_pct.p50.toFixed(0)}%) — so we
          weren't lucky. But the variance is brutal: outcomes spanned{" "}
          {mb.total_return_pct.p5.toFixed(0)}% to +{mb.total_return_pct.p95.toFixed(0)}%, drawdowns
          reached {mb.max_drawdown_pct.p5.toFixed(0)}%, and only{" "}
          {mb.pct_sims_beat_benchmark?.toFixed(0)}% of histories beat buy-and-hold. Verdict:
          a legitimate signal, but not deployable as-is.
        </div>
      </div>

      <div className="mc-legend">
        <span><i className="mc-dot mc-median-dot" /> Median of simulations</span>
        <span><i className="mc-dot mc-you-dot" /> Actual realised result</span>
        <span><i className="mc-dot mc-range-dot" /> 5th–95th percentile range</span>
      </div>
    </section>
  );
}
