#!/usr/bin/env python3
"""Measure Q-policy training and evaluation-seed uncertainty in the synthetic gym."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from quantlab.rl_study import evaluate_policies, train_q_table
from quantlab.simulation import CatalystAssumptions


ROOT = Path(__file__).resolve().parents[1]
COMPARATORS = ("cash", "buy_and_hold", "trend_rule", "pre_catalyst_exit")
METRICS = ("annualized_return", "benchmark_relative_compounded_return", "max_drawdown")


def two_way_bootstrap(
    differences: np.ndarray,
    *,
    seed: int,
    replicates: int = 10_000,
) -> dict[str, float | int | str]:
    """Resample independent training and evaluation seeds as crossed clusters."""
    if differences.ndim != 2 or min(differences.shape) < 2:
        raise ValueError("paired differences must be a 2-D training-seed by evaluation-seed matrix")
    rng = np.random.default_rng(seed)
    estimates = np.empty(replicates, dtype=np.float64)
    n_training, n_evaluation = differences.shape
    for index in range(replicates):
        training_rows = rng.integers(0, n_training, size=n_training)
        evaluation_columns = rng.integers(0, n_evaluation, size=n_evaluation)
        estimates[index] = differences[np.ix_(training_rows, evaluation_columns)].mean()
    low, high = np.quantile(estimates, [0.025, 0.975])
    return {
        "training_seed_count": int(n_training),
        "evaluation_seed_count": int(n_evaluation),
        "paired_cells": int(differences.size),
        "mean_difference": float(differences.mean()),
        "median_cell_difference": float(np.median(differences)),
        "bootstrap_95pct_interval_low": float(low),
        "bootstrap_95pct_interval_high": float(high),
        "bootstrap_replicates": int(replicates),
        "bootstrap_seed": int(seed),
        "bootstrap_unit": "crossed_training_seed_and_shared_evaluation_episode_seed",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-replicates", type=int, default=10)
    parser.add_argument("--training-seed-start", type=int, default=17)
    parser.add_argument("--training-seed-stride", type=int, default=1000)
    parser.add_argument("--training-episodes", type=int, default=300)
    parser.add_argument("--evaluation-runs", type=int, default=60)
    parser.add_argument("--episode-length", type=int, default=252)
    parser.add_argument("--evaluation-seed", type=int, default=30_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20261015)
    parser.add_argument("--bootstrap-replicates", type=int, default=10_000)
    parser.add_argument("--assumptions", type=Path, default=ROOT / "config/biopharma_rl_synthetic.json")
    parser.add_argument("--output", type=Path, default=ROOT / "book/_static/rl-training-robustness.json")
    args = parser.parse_args()
    if args.training_replicates < 2 or args.training_episodes < 1 or args.evaluation_runs < 2:
        raise SystemExit("need at least 2 training replicates, positive training episodes, and 2 evaluation runs")
    if args.training_seed_stride <= 0 or args.bootstrap_replicates < 100:
        raise SystemExit("training seed stride must be positive and bootstrap replicates at least 100")
    if not args.assumptions.exists():
        raise SystemExit(f"Simulator assumptions file not found: {args.assumptions}")

    raw_assumptions = args.assumptions.read_bytes()
    try:
        assumptions = CatalystAssumptions.from_mapping(json.loads(raw_assumptions))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid simulator assumptions file: {exc}") from exc

    result_frames: list[pd.DataFrame] = []
    training_diagnostics: list[dict[str, int]] = []
    for replicate in range(args.training_replicates):
        training_seed = args.training_seed_start + replicate * args.training_seed_stride
        visit_counts = np.zeros((36, 2), dtype=np.int64)
        q_values = train_q_table(
            episodes=args.training_episodes,
            episode_length=args.episode_length,
            seed=training_seed,
            assumptions=assumptions,
            visit_counts=visit_counts,
        )
        frame = evaluate_policies(
            q_values,
            runs=args.evaluation_runs,
            episode_length=args.episode_length,
            seed=args.evaluation_seed,
            assumptions=assumptions,
        )
        frame["training_seed"] = training_seed
        result_frames.append(frame)
        greedy_long = q_values[:, 1] > q_values[:, 0]
        training_diagnostics.append({
            "training_seed": training_seed,
            "greedy_long_state_count": int(greedy_long.sum()),
            "training_states_visited": int(np.any(visit_counts > 0, axis=1).sum()),
            "training_state_action_pairs_visited": int((visit_counts > 0).sum()),
            "training_decisions": int(visit_counts.sum()),
        })
        print(
            f"Training replicate {replicate + 1}/{args.training_replicates}: seed={training_seed}, "
            f"greedy long states={int(greedy_long.sum())}/36",
            flush=True,
        )

    results = pd.concat(result_frames, ignore_index=True)
    comparisons: dict[str, dict[str, dict[str, float | int | str]]] = {}
    for comparator_index, comparator in enumerate(COMPARATORS):
        comparisons[comparator] = {}
        for metric_index, metric in enumerate(METRICS):
            wide = results.pivot(index=["training_seed", "seed"], columns="policy", values=metric)
            differences = (wide["q_learner"] - wide[comparator]).unstack("seed").to_numpy(dtype=float)
            comparisons[comparator][metric] = two_way_bootstrap(
                differences,
                seed=args.bootstrap_seed + comparator_index * 100 + metric_index,
                replicates=args.bootstrap_replicates,
            )

    q_results = results.loc[results.policy == "q_learner"]
    report = {
        "study": "synthetic_q_learning_training_seed_robustness",
        "evidence_status": "synthetic_simulator_diagnostic_only",
        "not_a_claim": "No historical prices, point-in-time trial outcomes, or market generalization are represented.",
        "protocol": {
            "training": "Independently train one Q table per training seed on the same base generator; no policy is selected from evaluation results.",
            "evaluation": "Every trained Q table and rule-based comparator uses the same held-out episode seed block, creating a crossed training-seed by evaluation-seed design.",
            "bootstrap": "Two-way percentile bootstrap resamples training-seed rows and shared evaluation-seed columns independently.",
            "limitations": "Intervals are conditional on one synthetic generator and one hyperparameter configuration. They do not represent historical-market uncertainty or correct for prior tuning of the study design.",
        },
        "configuration": {
            "training_replicates": args.training_replicates,
            "training_seed_start": args.training_seed_start,
            "training_seed_stride": args.training_seed_stride,
            "training_episodes_per_replicate": args.training_episodes,
            "evaluation_runs_per_training_replicate": args.evaluation_runs,
            "episode_length_sessions": args.episode_length,
            "evaluation_seed_start": args.evaluation_seed,
            "evaluation_seed_block_shared": True,
            "bootstrap_replicates": args.bootstrap_replicates,
            "bootstrap_seed": args.bootstrap_seed,
            "learning_rate": 0.12,
            "discount_factor": 0.98,
            "assumptions_path": str(args.assumptions),
            "assumptions_sha256": hashlib.sha256(raw_assumptions).hexdigest(),
            "policies": ["cash", "buy_and_hold", "trend_rule", "pre_catalyst_exit", "q_learner"],
        },
        "q_policy_training_diagnostics": training_diagnostics,
        "greedy_long_state_count_distribution": {
            "minimum": int(min(row["greedy_long_state_count"] for row in training_diagnostics)),
            "median": float(np.median([row["greedy_long_state_count"] for row in training_diagnostics])),
            "maximum": int(max(row["greedy_long_state_count"] for row in training_diagnostics)),
            "available_states": 36,
        },
        "q_policy_evaluation_distribution": {
            metric: {
                "median": float(q_results[metric].median()),
                "p10": float(q_results[metric].quantile(0.10)),
                "p90": float(q_results[metric].quantile(0.90)),
            }
            for metric in (*METRICS, "exposure_fraction", "catalyst_exposure_fraction", "annual_turnover")
        },
        "paired_q_policy_comparisons": comparisons,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote multi-training-seed RL robustness report to {args.output}")
    print("Intervals include both training-seed and evaluation-seed variation within the fixed synthetic generator.")


if __name__ == "__main__":
    main()
