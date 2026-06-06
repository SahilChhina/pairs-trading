export default function ResultsSection({ metrics: m }) {
  if (!m || !Object.keys(m).length) return null;

  const totalReturn = Number(m.total_return_pct);
  const isWin = totalReturn >= 0;

  return (
    <section className="step">
      <div className="step-number">Step 4 — Results</div>
      <h2 className="step-heading">How did it perform?</h2>
      <p className="step-body">
        Results are on the <strong>out-of-sample test period (2022 → present)</strong>.
        The strategy was not allowed to see this data during pair selection — it's a fair
        evaluation. All results include realistic transaction costs (5 bps per trade) and
        slippage.
      </p>

      {/* Headline result */}
      <div className="outcome-card" style={{ marginBottom: 20 }}>
        <div className="outcome-label">Total return on $100,000</div>
        <div className={`outcome-value ${isWin ? "pos" : "neg"}`}>
          {isWin ? "+" : ""}{totalReturn.toFixed(2)}%
        </div>
        <div className="outcome-fine">
          Starting capital $100,000 → ending value{" "}
          <strong>${Number(m.final_value).toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong>
          {" · "}{m.n_trades} trades over the test period
        </div>
      </div>

      {/* Key metrics */}
      <div className="stat-row">
        <div className="stat-card">
          <div className="stat-label">Max drawdown</div>
          <div className={`stat-value ${Number(m.max_drawdown_pct) < -10 ? "neg" : "neutral"}`}>
            {Number(m.max_drawdown_pct).toFixed(2)}%
          </div>
          <div className="stat-explain">
            Worst peak-to-trough loss. Small drawdown = strategy didn't blow up.
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Win rate</div>
          <div className={`stat-value ${Number(m.win_rate_pct) >= 50 ? "pos" : "neg"}`}>
            {Number(m.win_rate_pct).toFixed(1)}%
          </div>
          <div className="stat-explain">
            Percentage of trades that were profitable.
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg holding period</div>
          <div className="stat-value neutral">
            {Number(m.avg_holding_days).toFixed(1)}d
          </div>
          <div className="stat-explain">
            How long a typical trade was held before closing.
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Sharpe ratio</div>
          <div className={`stat-value ${Number(m.sharpe_ratio) >= 1 ? "pos" : Number(m.sharpe_ratio) >= 0 ? "neutral" : "neg"}`}>
            {Number(m.sharpe_ratio).toFixed(2)}
          </div>
          <div className="stat-explain">
            Return per unit of risk. Above 1.0 is considered good; below 0 means the risk wasn't worth it.
          </div>
        </div>
      </div>

      {/* Honest context */}
      <div className="callout amber">
        <span className="callout-icon">📝</span>
        <div className="callout-text">
          <strong>Honest take:</strong> Only one pair (MA/V) cleared the cointegration
          filter from a universe of 12 stocks. A larger universe would likely yield more
          pairs and a more robust portfolio effect. These results reflect a single pair
          strategy, not a diversified portfolio. This is normal for a rigorous, no-cheat
          backtest — and far more credible than one that's been overfit to look good.
        </div>
      </div>
    </section>
  );
}
