"""Reproducible quantitative research primitives."""

from .backtest import BacktestResult, backtest, cost_sensitivity, performance_metrics
from .portfolio import AllocationResult, allocate_portfolio

__all__ = [
    "AllocationResult",
    "BacktestResult",
    "allocate_portfolio",
    "backtest",
    "cost_sensitivity",
    "performance_metrics",
]
