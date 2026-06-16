"""Cross-sectional momentum & factor investing engine.

A self-contained sub-package that reuses the project's data_loader, metrics,
and utils modules but implements a *cross-sectional* strategy (rank the whole
universe each month, long the winners, short the losers) rather than the
time-series pairs strategy in the parent package.
"""
