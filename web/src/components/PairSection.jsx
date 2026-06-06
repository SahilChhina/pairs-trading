export default function PairSection({ pairs }) {
  const selected = (pairs || []).filter((p) => p.selected);
  const total = (pairs || []).length;

  return (
    <section className="step">
      <div className="step-number">Step 2 — Pair Selection</div>
      <h2 className="step-heading">Which stock pairs actually move together?</h2>
      <p className="step-body">
        Not all pairs are created equal. We ran a statistical test called{" "}
        <strong>cointegration</strong> on the training data (2018–2021) to find pairs
        whose prices are genuinely linked over time — not just correlated by coincidence.
        We tested <strong>{total} combinations</strong> from a universe of 12 stocks.
      </p>

      <div className="callout blue">
        <span className="callout-icon">🔬</span>
        <div className="callout-text">
          <strong>Cointegration vs correlation:</strong> Two stocks can be correlated
          just because they both went up in a bull market. Cointegration is stricter —
          it means the gap between their prices has a stable, predictable long-run
          relationship even when individual prices drift. That's what makes it tradeable.
        </div>
      </div>

      {selected.length === 0 ? (
        <div className="callout amber">
          <span className="callout-icon">⚠️</span>
          <div className="callout-text">No pairs passed the cointegration test. Try a larger universe.</div>
        </div>
      ) : (
        selected.map((p) => (
          <div className="pair-card" key={`${p.stock_a}/${p.stock_b}`}>
            <div className="pair-tickers">
              <span>{p.stock_a}</span>
              <span className="vs">vs</span>
              <span>{p.stock_b}</span>
            </div>
            <div className="pair-stats">
              <div className="pair-stat">
                <div className="ps-label">Price correlation</div>
                <div className="ps-val">{(Number(p.correlation) * 100).toFixed(1)}%</div>
              </div>
              <div className="pair-stat">
                <div className="ps-label">Cointegration p-value</div>
                <div className="ps-val">{Number(p.coint_pvalue).toFixed(4)}</div>
              </div>
              <div className="pair-stat">
                <div className="ps-label">Training days used</div>
                <div className="ps-val">{p.n_obs}</div>
              </div>
            </div>
            <div className="pair-explanation">
              <strong>p-value in plain English:</strong> the p-value of{" "}
              <strong>{Number(p.coint_pvalue).toFixed(4)}</strong> means there is less
              than a {(Number(p.coint_pvalue) * 100).toFixed(1)}% chance this
              relationship would appear by random chance. Below 5% is the standard
              threshold for statistical significance — this pair passes.
            </div>
          </div>
        ))
      )}

      {total > 0 && (
        <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 8 }}>
          {total - selected.length} of {total} combinations tested were rejected. Only
          cointegrated pairs proceed to trading.
        </p>
      )}
    </section>
  );
}
