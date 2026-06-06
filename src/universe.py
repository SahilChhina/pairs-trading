from __future__ import annotations

DEFAULT_UNIVERSE: list[str] = [
    "KO", "PEP",
    "GS", "MS",
    "JPM", "BAC",
    "XOM", "CVX",
    "MA", "V",
    "HD", "LOW",
    "WMT", "TGT",
    "AAPL", "MSFT",
    "GOOGL", "META",
]

SECTOR_UNIVERSE: dict[str, list[str]] = {
    "beverages":    ["KO", "PEP"],
    "banks":        ["GS", "MS", "JPM", "BAC", "C", "WFC"],
    "energy":       ["XOM", "CVX", "COP", "SLB"],
    "payments":     ["MA", "V", "AXP", "PYPL"],
    "retail":       ["HD", "LOW", "WMT", "TGT", "COST"],
    "tech":         ["AAPL", "MSFT", "GOOGL", "META", "AMZN"],
}


def get_default_universe() -> list[str]:
    return list(DEFAULT_UNIVERSE)


def get_sector_universe(sector: str) -> list[str]:
    sector = sector.lower()
    if sector not in SECTOR_UNIVERSE:
        raise ValueError(f"Unknown sector '{sector}'. Available: {list(SECTOR_UNIVERSE)}")
    return list(SECTOR_UNIVERSE[sector])


def get_all_sectors() -> list[str]:
    return list(SECTOR_UNIVERSE.keys())
