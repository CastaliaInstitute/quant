"""Reproducible quantitative research primitives."""

from .backtest import BacktestResult, backtest, cost_sensitivity, performance_metrics
from .portfolio import (
    AllocationResult,
    PortfolioBacktestResult,
    allocate_portfolio,
    portfolio_backtest,
    portfolio_cost_sensitivity,
)

__all__ = [
    "AllocationResult",
    "BacktestResult",
    "PortfolioBacktestResult",
    "allocate_portfolio",
    "backtest",
    "cost_sensitivity",
    "performance_metrics",
    "portfolio_backtest",
    "portfolio_cost_sensitivity",
]
