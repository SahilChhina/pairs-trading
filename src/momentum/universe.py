"""Trading universe for the cross-sectional momentum engine.

A single pair needs only two names; a cross-sectional strategy needs a broad
universe so that the top/bottom quantiles each hold several stocks and the
long/short spread is diversified. We use ~50 large, liquid US names spread
across sectors so no single sector dominates the ranking.
"""

from __future__ import annotations

# ~50 liquid large/mid caps across sectors. Breadth matters more than picking
# "good" stocks — the strategy's edge comes from the cross-sectional ranking,
# not from the universe membership.
MOMENTUM_UNIVERSE: list[str] = [
    # Mega-cap tech / comms
    "AAPL", "MSFT", "GOOGL", "META", "AMZN", "NVDA", "NFLX", "ADBE", "CRM", "ORCL",
    # Semis
    "AMD", "INTC", "AVGO", "TXN", "QCOM",
    # Financials
    "JPM", "BAC", "WFC", "GS", "MS", "C", "AXP", "BLK",
    # Payments
    "V", "MA", "PYPL",
    # Healthcare
    "JNJ", "UNH", "PFE", "MRK", "ABBV", "TMO", "LLY",
    # Consumer staples
    "KO", "PEP", "PG", "WMT", "COST", "MCD",
    # Consumer discretionary / retail
    "HD", "LOW", "NKE", "SBUX", "TGT",
    # Energy
    "XOM", "CVX", "COP", "SLB",
    # Industrials
    "CAT", "BA", "GE", "HON", "UPS",
]


def get_momentum_universe() -> list[str]:
    return list(MOMENTUM_UNIVERSE)
