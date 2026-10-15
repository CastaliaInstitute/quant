import pandas as pd
import pytest

from quantlab import backtest, performance_metrics


def test_signal_is_lagged_and_cost_applied_on_entry():
    returns = pd.Series([0.10, 0.10, -0.10])
    signals = pd.Series([1.0, 1.0, 0.0])
    result = backtest(returns, signals, transaction_cost_bps=100)
    assert result.positions.tolist() == [0.0, 1.0, 1.0]
    assert result.returns.iloc[0] == 0
    assert result.returns.iloc[1] == pytest.approx(0.09)
    assert result.returns.iloc[2] == pytest.approx(-0.10)


def test_signal_is_clipped_to_long_or_cash():
    result = backtest(pd.Series([0.0, 0.1]), pd.Series([2.0, -1.0]), 0)
    assert result.positions.tolist() == [0.0, 1.0]


def test_performance_metrics_empty_and_flat_series():
    assert performance_metrics(pd.Series(dtype=float))["sharpe"] == 0
    assert performance_metrics(pd.Series([0.0, 0.0]))["max_drawdown"] == 0


def test_negative_cost_rejected():
    with pytest.raises(ValueError):
        backtest(pd.Series([0.1]), pd.Series([1.0]), -1)
