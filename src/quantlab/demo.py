"""Run a reproducible synthetic-data ML signal demonstration."""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from quantlab import backtest, performance_metrics


def make_synthetic_market(seed: int = 17, periods: int = 1500) -> pd.DataFrame:
    """Generate clearly synthetic returns and price-derived features."""
    rng = np.random.default_rng(seed)
    latent = rng.normal(0, 0.01, periods)
    returns = np.empty(periods)
    returns[0] = latent[0]
    for i in range(1, periods):
        returns[i] = 0.08 * returns[i - 1] + latent[i]
    frame = pd.DataFrame({"return": returns})
    frame["momentum_5d"] = frame["return"].rolling(5).sum()
    frame["volatility_20d"] = frame["return"].rolling(20).std()
    frame["volume_zscore"] = rng.normal(size=periods)
    frame["target"] = (frame["return"].shift(-1) > 0).astype(int)
    return frame.dropna().reset_index(drop=True)


def run_demo() -> dict[str, float]:
    data = make_synthetic_market()
    features = ["momentum_5d", "volatility_20d", "volume_zscore"]
    split = int(len(data) * 0.7)
    train, test = data.iloc[:split], data.iloc[split:]
    model = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=1000))
    model.fit(train[features], train["target"])
    probability = model.predict_proba(test[features])[:, 1]
    # A close-time forecast is used only on the next period's return by backtest().
    result = backtest(test["return"], pd.Series((probability > 0.55).astype(float), index=test.index), 5.0)
    return performance_metrics(result.returns)


if __name__ == "__main__":
    print("Illustrative synthetic-data results (not real market performance):")
    for name, value in run_demo().items():
        print(f"{name}: {value:.4f}")
