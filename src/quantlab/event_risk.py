"""Chronological, leakage-resistant evaluation for biotech catalyst downside."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


DEFAULT_FEATURES = (
    "pre_event_return_5d",
    "pre_event_return_20d",
    "pre_event_volatility_20d",
    "pre_event_relative_volume",
    "market_pre_event_return_20d",
    "sector_pre_event_return_20d",
    "trial_phase_stage_asof_event",
    "trial_enrollment_asof_event",
    "trial_primary_outcome_count_asof_event",
    "trial_condition_count_asof_event",
    "trial_intervention_count_asof_event",
    "point_in_time_research_record_count",
    "research_role_pre_event_count_asof_event",
    "research_role_primary_count_asof_event",
    "research_role_secondary_count_asof_event",
    "research_class_preclinical_count_asof_event",
    "research_class_clinical_count_asof_event",
    "research_class_review_count_asof_event",
    "issuer_filing_count_90d",
    "issuer_days_since_last_filing",
)


@dataclass(frozen=True)
class WalkForwardResult:
    predictions: pd.DataFrame
    fold_metrics: pd.DataFrame
    calibration: pd.DataFrame
    summary: dict[str, object]


def _score(y: pd.Series, probability: np.ndarray) -> dict[str, float | None]:
    clipped = np.clip(probability, 1e-6, 1.0 - 1e-6)
    auc = float(roc_auc_score(y, clipped)) if y.nunique() == 2 else None
    return {
        "event_count": int(len(y)),
        "downside_rate": float(y.mean()) if len(y) else 0.0,
        "brier": float(brier_score_loss(y, clipped)) if len(y) else float("nan"),
        "log_loss": float(log_loss(y, clipped, labels=[0, 1])) if len(y) else float("nan"),
        "roc_auc": auc,
    }


def _calibration_table(predictions: pd.DataFrame, bins: int = 5) -> pd.DataFrame:
    """Summarize observed downside rates in fixed-width development OOS bins."""
    probability_columns = {
        "training_fold_base_rate": "baseline_probability",
        "volatility_conditioned": "volatility_conditioned_probability",
        "phase_conditioned": "phase_conditioned_probability",
        "regularized_logit": "logit_probability",
    }
    rows: list[dict[str, object]] = []
    observed = predictions.observed.to_numpy(dtype=int)
    for model_name, column in probability_columns.items():
        probabilities = np.clip(predictions[column].to_numpy(dtype=float), 0.0, 1.0)
        bin_ids = np.minimum((probabilities * bins).astype(int), bins - 1)
        for bin_id in range(bins):
            selected = bin_ids == bin_id
            if not selected.any():
                continue
            mean_probability = float(probabilities[selected].mean())
            observed_rate = float(observed[selected].mean())
            rows.append({
                "model": model_name,
                "probability_bin": bin_id,
                "probability_lower_inclusive": bin_id / bins,
                "probability_upper_exclusive": (bin_id + 1) / bins,
                "event_count": int(selected.sum()),
                "mean_predicted_probability": mean_probability,
                "observed_downside_rate": observed_rate,
                "observed_minus_predicted": observed_rate - mean_probability,
            })
    return pd.DataFrame(rows)


def _shrunk_group_probability(
    train_group: pd.Series,
    train_target: pd.Series,
    test_group: pd.Series,
    prior: float,
    prior_strength: float = 5.0,
) -> np.ndarray:
    """Estimate group event rates with a training-only empirical-Bayes prior."""
    grouped = pd.DataFrame({"group": train_group, "target": train_target}).dropna(subset=["group"])
    stats = grouped.groupby("group", dropna=True).target.agg(["sum", "count"])
    rates = (stats["sum"] + prior_strength * prior) / (stats["count"] + prior_strength)
    values = test_group.map(rates)
    return values.fillna(prior).to_numpy(dtype=float)


def _issuer_cluster_skill_intervals(
    predictions: pd.DataFrame,
    baseline_column: str,
    repetitions: int = 1000,
    seed: int = 2026,
) -> dict[str, object]:
    """Paired issuer-cluster bootstrap for baseline-minus-model score skill."""
    issuers = predictions.ticker.dropna().astype(str).unique()
    if len(issuers) < 5:
        return {
            "issuer_clusters": int(len(issuers)),
            "status": "withheld_fewer_than_5_issuer_clusters",
            "brier_improvement_95_interval": None,
            "log_loss_improvement_95_interval": None,
        }
    clusters = {
        issuer: predictions.index[predictions.ticker.astype(str) == issuer].to_numpy()
        for issuer in issuers
    }
    rng = np.random.default_rng(seed)
    brier_improvements: list[float] = []
    log_loss_improvements: list[float] = []
    issuer_list = list(issuers)
    for _ in range(repetitions):
        sampled = rng.choice(issuer_list, size=len(issuer_list), replace=True)
        row_ids = np.concatenate([clusters[issuer] for issuer in sampled])
        sample = predictions.loc[row_ids]
        observed = sample.observed.astype(int)
        baseline = np.clip(sample[baseline_column].to_numpy(dtype=float), 1e-6, 1.0 - 1e-6)
        model = np.clip(sample.logit_probability.to_numpy(dtype=float), 1e-6, 1.0 - 1e-6)
        brier_improvements.append(float(brier_score_loss(observed, baseline) - brier_score_loss(observed, model)))
        log_loss_improvements.append(float(
            log_loss(observed, baseline, labels=[0, 1]) - log_loss(observed, model, labels=[0, 1])
        ))
    return {
        "issuer_clusters": int(len(issuers)),
        "bootstrap_repetitions": repetitions,
        "seed": seed,
        "status": "issuer_cluster_bootstrap_descriptive",
        "brier_improvement_95_interval": [
            float(np.quantile(brier_improvements, 0.025)),
            float(np.quantile(brier_improvements, 0.975)),
        ],
        "log_loss_improvement_95_interval": [
            float(np.quantile(log_loss_improvements, 0.025)),
            float(np.quantile(log_loss_improvements, 0.975)),
        ],
    }


def walk_forward_event_risk(
    panel: pd.DataFrame,
    *,
    features: tuple[str, ...] | None = None,
    target: str = "down_10pct_event_window",
    date_column: str = "event_date",
    label_end_column: str = "matched_second_session",
    issuer_column: str = "ticker",
    minimum_training_events: int = 30,
    minimum_test_events: int = 8,
    folds: int = 3,
    final_holdout_fraction: float = 0.20,
) -> WalkForwardResult:
    """Evaluate a frozen regularized logit on expanding chronological windows.

    The final chronological block is excluded from fitting, feature selection,
    and reported development metrics. Features are imputed/scaled inside each
    fold. The function refuses small panels rather than presenting a noisy fit.
    """
    selected_features = tuple(features) if features is not None else tuple(dict.fromkeys(
        [feature for feature in DEFAULT_FEATURES if feature in panel.columns]
        + sorted(
            column for column in panel.columns
            if column.startswith("research_numeric_") and column.endswith("_median")
        )
    ))
    if len(selected_features) < 2:
        raise ValueError("event panel needs at least two available pre-event features")
    required = {target, date_column, label_end_column, issuer_column, *selected_features}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"event panel is missing columns: {', '.join(sorted(missing))}")
    if minimum_training_events < 2 or minimum_test_events < 1 or folds < 1:
        raise ValueError("training/test minima and fold count must be positive")
    if not 0.05 <= final_holdout_fraction < 0.5:
        raise ValueError("final_holdout_fraction must be between 0.05 and 0.5")

    data = panel.copy()
    data[date_column] = pd.to_datetime(data[date_column], errors="coerce")
    data[label_end_column] = pd.to_datetime(data[label_end_column], errors="coerce")
    data[target] = pd.to_numeric(data[target], errors="coerce")
    for feature in selected_features:
        data[feature] = pd.to_numeric(data[feature], errors="coerce")
    data = data.dropna(subset=[date_column, label_end_column, target]).sort_values([date_column, issuer_column]).reset_index(drop=True)
    if not data[target].isin([0, 1]).all():
        raise ValueError(f"target {target} must contain only binary 0/1 labels")
    if data.empty:
        raise ValueError("event panel has no dated target rows")

    dates = np.array(sorted(data[date_column].dt.normalize().unique()))
    if len(dates) < 5:
        raise ValueError("need at least five distinct event dates for chronological evaluation")
    holdout_start_index = max(1, int(np.floor(len(dates) * (1.0 - final_holdout_fraction))))
    development_dates = dates[:holdout_start_index]
    final_holdout_dates = dates[holdout_start_index:]
    min_train_dates = max(2, int(np.ceil(len(development_dates) * 0.4)))
    if len(development_dates) <= min_train_dates:
        raise ValueError("not enough development dates before the untouched final holdout")
    test_date_blocks = [block for block in np.array_split(development_dates[min_train_dates:], folds) if len(block)]

    predictions: list[pd.DataFrame] = []
    fold_rows: list[dict[str, object]] = []
    for fold_id, test_dates in enumerate(test_date_blocks, start=1):
        test_start = pd.Timestamp(test_dates[0])
        # Purge past events whose two-session outcome window touches the test.
        train = data.loc[(data[date_column] < test_start) & (data[label_end_column] < test_start)]
        test = data.loc[data[date_column].dt.normalize().isin(test_dates)]
        if len(train) < minimum_training_events or len(test) < minimum_test_events or train[target].nunique() < 2:
            continue

        # The preprocessing and model are fitted only on this fold's past rows.
        model = make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
            StandardScaler(),
            LogisticRegression(C=1.0, class_weight=None, max_iter=2000, random_state=0),
        )
        model.fit(train.loc[:, list(selected_features)], train[target].astype(int))
        probability = model.predict_proba(test.loc[:, list(selected_features)])[:, 1]
        baseline_probability = np.full(len(test), float(train[target].mean()))
        training_prior = float(train[target].mean())
        train_volatility = train.get("pre_event_volatility_20d", pd.Series(np.nan, index=train.index))
        test_volatility = test.get("pre_event_volatility_20d", pd.Series(np.nan, index=test.index))
        finite_volatility = train_volatility.dropna()
        if finite_volatility.nunique() >= 2:
            vol_edges = np.unique(finite_volatility.quantile([1 / 3, 2 / 3]).to_numpy(dtype=float))
            train_volatility_group = pd.Series(np.searchsorted(vol_edges, train_volatility, side="right"), index=train.index).where(train_volatility.notna())
            test_volatility_group = pd.Series(np.searchsorted(vol_edges, test_volatility, side="right"), index=test.index).where(test_volatility.notna())
            volatility_probability = _shrunk_group_probability(
                train_volatility_group, train[target], test_volatility_group, training_prior
            )
        else:
            volatility_probability = baseline_probability.copy()
        train_phase = train.get("trial_phase_stage_asof_event", pd.Series(np.nan, index=train.index))
        test_phase = test.get("trial_phase_stage_asof_event", pd.Series(np.nan, index=test.index))
        phase_probability = _shrunk_group_probability(
            train_phase, train[target], test_phase, training_prior
        ) if train_phase.notna().any() else baseline_probability.copy()
        fold_rows.append({
            "fold": fold_id,
            "train_start": train[date_column].min().date().isoformat(),
            "train_end": train[date_column].max().date().isoformat(),
            "test_start": test[date_column].min().date().isoformat(),
            "test_end": test[date_column].max().date().isoformat(),
            "train_events": int(len(train)),
            "test_events": int(len(test)),
            "train_issuers": int(train[issuer_column].nunique()),
            "test_issuers": int(test[issuer_column].nunique()),
            "baseline": _score(test[target].astype(int), baseline_probability),
            "volatility_conditioned_baseline": _score(test[target].astype(int), volatility_probability),
            "phase_conditioned_baseline": _score(test[target].astype(int), phase_probability),
            "regularized_logit": _score(test[target].astype(int), probability),
        })
        predictions.append(pd.DataFrame({
            "event_date": test[date_column].dt.date.astype(str).to_numpy(),
            "ticker": test[issuer_column].astype(str).to_numpy(),
            "observed": test[target].astype(int).to_numpy(),
            "baseline_probability": baseline_probability,
            "volatility_conditioned_probability": volatility_probability,
            "phase_conditioned_probability": phase_probability,
            "logit_probability": probability,
            "fold": fold_id,
        }))

    if not predictions:
        raise ValueError(
            "no walk-forward fold met the minimum sample/class requirements; "
            "expand the historical cohort instead of lowering the gate for the pilot"
        )
    prediction_frame = pd.concat(predictions, ignore_index=True)
    calibration = _calibration_table(prediction_frame)
    pooled_y = prediction_frame["observed"].astype(int)
    skill_intervals = {
        "training_fold_base_rate": _issuer_cluster_skill_intervals(prediction_frame, "baseline_probability"),
        "volatility_conditioned": _issuer_cluster_skill_intervals(prediction_frame, "volatility_conditioned_probability"),
        "phase_conditioned": _issuer_cluster_skill_intervals(prediction_frame, "phase_conditioned_probability"),
    }
    summary = {
        "evidence_status": "historical_walk_forward_development_only_final_holdout_untouched",
        "target": target,
        "features": list(selected_features),
        "model": "median_imputation_with_missingness_indicators_standardization_logistic_regression_C_1",
        "baseline": "training_fold_downside_base_rate",
        "additional_baselines": [
            "training-only volatility-tertile downside rates, shrunk toward the fold base rate with prior strength 5",
            "training-only archived-phase downside rates, shrunk toward the fold base rate with prior strength 5",
        ],
        "label_overlap_purge": f"training rows require {label_end_column} strictly before each test-fold start",
        "rows": int(len(data)),
        "unique_event_dates": int(data[date_column].dt.normalize().nunique()),
        "unique_issuers": int(data[issuer_column].nunique()),
        "development_rows": int(data[date_column].dt.normalize().isin(development_dates).sum()),
        "untouched_final_holdout_rows": int(data[date_column].dt.normalize().isin(final_holdout_dates).sum()),
        "evaluated_oos_rows": int(len(prediction_frame)),
        "development_rows_without_oos_predictions": int(data[date_column].dt.normalize().isin(development_dates).sum() - len(prediction_frame)),
        "pooled_baseline": _score(pooled_y, prediction_frame["baseline_probability"].to_numpy()),
        "pooled_volatility_conditioned_baseline": _score(pooled_y, prediction_frame["volatility_conditioned_probability"].to_numpy()),
        "pooled_phase_conditioned_baseline": _score(pooled_y, prediction_frame["phase_conditioned_probability"].to_numpy()),
        "pooled_regularized_logit": _score(pooled_y, prediction_frame["logit_probability"].to_numpy()),
        "calibration_protocol": "fixed_width_5_bins_on_development_walk_forward_predictions_only; final_holdout_not_included",
        "issuer_cluster_bootstrap_skill_intervals": skill_intervals,
        "limitations": [
            "Walk-forward metrics are development evidence; the final chronological holdout remains unused.",
            "ROC AUC is undefined in a test fold containing only one outcome class.",
            "Events from one issuer or market episode can be dependent; issuer/event counts and per-fold results must accompany pooled metrics.",
            "Issuer-cluster bootstrap intervals are withheld below five issuers and do not account for shared market-date dependence.",
            "The five-event COVID-19 seed cohort cannot satisfy these sample gates and must not be fit.",
        ],
    }
    return WalkForwardResult(prediction_frame, pd.DataFrame(fold_rows), calibration, summary)
