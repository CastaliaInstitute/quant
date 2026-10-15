"""Reproducible quantitative research primitives."""

from .backtest import BacktestResult, backtest, cost_sensitivity, performance_metrics

__all__ = ["BacktestResult", "backtest", "cost_sensitivity", "performance_metrics"]
