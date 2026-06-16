import { useEffect, useState } from "react";
import EquitySection from "./components/EquitySection.jsx";
import PairSection from "./components/PairSection.jsx";
import ResultsSection from "./components/ResultsSection.jsx";
import TradeSection from "./components/TradeSection.jsx";
import DiagnosticsSection from "./components/DiagnosticsSection.jsx";
import MomentumSection from "./components/MomentumSection.jsx";

const BASE = import.meta.env.BASE_URL;

export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${BASE}data/results.json`)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  const ready = data && (data.equity_curve?.length || Object.keys(data.metrics || {}).length);

  return (
    <div className="page">

      {/* ── HERO ──────────────────────────────────────── */}
      <header className="hero">
        <div className="hero-eyebrow">⚡ Quantitative Finance · Research Project</div>
        <h1>Pairs Trading Engine</h1>
        <p className="hero-sub">
          A market-neutral strategy that finds two stocks that historically move together,
          then profits when they temporarily drift apart — without betting on the market
          going up or down.
        </p>
        {data?.generated_at && (
          <div className="hero-meta">Last run <code>{data.generated_at}</code></div>
        )}
      </header>

      {error && (
        <div className="empty-state">
          <h3>No results loaded</h3>
          <p>Run the engine first, then refresh:</p>
          <code>python3 main.py --all</code>
          <code>python3 export_web_data.py</code>
          <p style={{fontSize:12, marginTop:16}}>({error})</p>
        </div>
      )}

      {!error && !data && (
        <div className="empty-state"><h3>Loading…</h3></div>
      )}

      {ready && (
        <>
          {/* ── STEP 1: How it works ───────────────────── */}
          <section className="step">
            <div className="step-number">Step 1 — The Strategy</div>
            <h2 className="step-heading">How does pairs trading work?</h2>
            <p className="step-body">
              Think of Visa and Mastercard. They operate in the same business,
              compete for the same customers, and respond to the same news. So their
              stock prices tend to move in lockstep over time.
              <br /><br />
              When they <strong>temporarily diverge</strong> — say Mastercard drops
              while Visa stays flat — that gap is unusual. The bet is that the gap
              will close. We short the one that's relatively expensive and go long
              the one that's relatively cheap, then close both positions when prices
              converge. The direction of the overall market doesn't matter — only
              the <em>relationship</em> between the two stocks does.
            </p>

            <div className="callout blue">
              <span className="callout-icon">📐</span>
              <div className="callout-text">
                <strong>Market neutral</strong> — because we're simultaneously long one
                stock and short another for roughly the same dollar amount, the portfolio
                has near-zero net exposure to market moves. A crash affects both legs
                similarly and mostly cancels out.
              </div>
            </div>

            <div className="timeline">
              <div className="tl-seg train">
                <div className="tl-label">Training period</div>
                <div className="tl-dates">2018 → 2021</div>
                <div className="tl-note">Find which pairs move together. No trading here.</div>
              </div>
              <div className="tl-seg test">
                <div className="tl-label">Test period</div>
                <div className="tl-dates">2022 → present</div>
                <div className="tl-note">Actually trade the selected pairs. Results reported here.</div>
              </div>
            </div>
          </section>

          {/* ── STEP 2: Pair selection ─────────────────── */}
          <PairSection pairs={data.pairs} base={BASE} figures={data.figures} />

          {/* ── STEP 3: The signal ────────────────────── */}
          <section className="step">
            <div className="step-number">Step 3 — The Signal</div>
            <h2 className="step-heading">When exactly do we trade?</h2>
            <p className="step-body">
              We track the <strong>spread</strong> between the two stocks (adjusted
              for their typical relative size). Then we convert it to a
              <strong> z-score</strong> — a measure of how unusual the current gap is
              compared to the last 60 trading days.
            </p>

            <div className="callout blue">
              <span className="callout-icon">📊</span>
              <div className="callout-text">
                <strong>Z-score in plain English:</strong> 0 = the spread is normal.
                ±1 = a bit unusual. ±2 = quite unusual — time to trade.
                ±3.5 = something might actually be wrong — exit immediately (stop loss).
              </div>
            </div>

            <div className="stat-row" style={{gridTemplateColumns:'repeat(3,1fr)'}}>
              <div className="stat-card">
                <div className="stat-label">Enter trade when</div>
                <div className="stat-value neutral">z &gt; ±2</div>
                <div className="stat-explain">Spread is unusually large — bet it narrows</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Exit trade when</div>
                <div className="stat-value neutral">z &lt; ±0.25</div>
                <div className="stat-explain">Spread returned to normal — take profit</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Stop loss when</div>
                <div className="stat-value neutral">z &gt; ±3.5</div>
                <div className="stat-explain">Spread keeps widening — cut the loss</div>
              </div>
            </div>

            <DiagnosticsSection figures={data.figures} base={BASE} filter="zscore" label="MA/V spread z-score — entry (▲) and exit (▼) signals marked" />
          </section>

          {/* ── STEP 4: Results ───────────────────────── */}
          <ResultsSection metrics={data.metrics} />

          {/* ── STEP 5: Equity curve ──────────────────── */}
          <EquitySection data={data.equity_curve} />

          {/* ── STEP 6: Every trade ───────────────────── */}
          <TradeSection trades={data.trades} />

          {/* ── MOMENTUM STRATEGY ─────────────────────── */}
          {data.momentum && <MomentumSection data={data.momentum} />}

          {/* ── Appendix: all charts ──────────────────── */}
          <DiagnosticsSection figures={data.figures} base={BASE} all label="All diagnostic charts" stepNum="Appendix" />
        </>
      )}

      <footer className="footer">
        Built with Python (pandas · statsmodels · NumPy) and React. Strategy: Engle-Granger
        cointegration test + custom Kalman filter for dynamic hedge ratios.
        <br />
        <em>Research and education only. Not financial advice. Past results do not predict future performance.</em>
      </footer>
    </div>
  );
}
