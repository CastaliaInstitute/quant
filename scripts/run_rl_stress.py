#!/usr/bin/env python3
"""Evaluate one base-trained RL policy across frozen assumption stresses."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from quantlab.rl_study import evaluate_policies, train_q_table
from quantlab.simulation import CatalystAssumptions


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_METRICS = (
    "annualized_return",
    "benchmark_relative_compounded_return",
    "max_drawdown",
    "expected_shortfall_95",
    "annual_turnover",
    "total_cost",
    "exposure_fraction",
    "catalyst_exposure_fraction",
    "catalyst_underlying_return_worst",
    "catalyst_trial_success_fraction",
    "phase_ii_trial_success_fraction",
    "phase_iii_trial_success_fraction",
    "catalyst_market_return_given_success_mean",
    "catalyst_market_return_given_failure_mean",
    "catalyst_positive_market_reaction_fraction_given_success",
    "catalyst_positive_market_reaction_fraction_given_failure",
    "catalyst_policy_net_expected_shortfall_95",
)


def summarize(frame, metrics: tuple[str, ...] = SUMMARY_METRICS) -> dict[str, dict[str, float]]:
    return {
        metric: {
            "median": float(frame[metric].median()),
            "p10": float(frame[metric].quantile(0.10)),
            "p90": float(frame[metric].quantile(0.90)),
        }
        for metric in metrics
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-episodes", type=int, default=300)
    parser.add_argument("--evaluation-runs", type=int, default=60)
    parser.add_argument("--episode-length", type=int, default=252)
    parser.add_argument("--training-seed", type=int, default=17)
    parser.add_argument("--evaluation-seed", type=int, default=20_000)
    parser.add_argument("--learning-rate", type=float, default=0.12)
    parser.add_argument("--discount", type=float, default=0.98)
    parser.add_argument("--assumptions", type=Path, default=ROOT / "config/biopharma_rl_synthetic.json")
    parser.add_argument("--output", type=Path, default=ROOT / "book/_static/rl-stress.json")
    args = parser.parse_args()
    if not args.assumptions.exists():
        raise SystemExit(f"Simulator assumptions file not found: {args.assumptions}")
    raw_assumptions = args.assumptions.read_bytes()
    try:
        base = CatalystAssumptions.from_mapping(json.loads(raw_assumptions))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid simulator assumptions file: {exc}") from exc

    stressed_success_down = tuple(max(0.0, value - 0.10) for value in base.phase_success_probabilities)
    stressed_success_up = tuple(min(1.0, value + 0.10) for value in base.phase_success_probabilities)
    scenarios = {
        "base": base,
        "success_probability_minus_10pp": replace(base, phase_success_probabilities=stressed_success_down),
        "success_probability_plus_10pp": replace(base, phase_success_probabilities=stressed_success_up),
        "negative_market_gaps_1_5x_more_severe": replace(
            base, phase_negative_market_gaps=tuple(value * 1.5 for value in base.phase_negative_market_gaps)
        ),
        "success_market_response_minus_15pp": replace(
            base,
            phase_success_market_positive_probabilities=tuple(
                max(0.0, value - 0.15) for value in base.phase_success_market_positive_probabilities
            ),
        ),
        "event_residual_noise_2x": replace(
            base, event_residual_volatility=base.event_residual_volatility * 2.0
        ),
        "transaction_costs_2x": replace(
            base, transaction_cost_bps_per_unit_turnover=base.transaction_cost_bps_per_unit_turnover * 2.0
        ),
        "transaction_costs_4x": replace(
            base, transaction_cost_bps_per_unit_turnover=base.transaction_cost_bps_per_unit_turnover * 4.0
        ),
    }

    q_values = train_q_table(
        episodes=args.training_episodes,
        episode_length=args.episode_length,
        seed=args.training_seed,
        learning_rate=args.learning_rate,
        discount=args.discount,
        assumptions=base,
    )
    results: dict[str, dict[str, dict[str, dict[str, float]]]] = {}
    scenario_assumptions: dict[str, dict[str, object]] = {}
    for name, assumptions in scenarios.items():
        episode_results = evaluate_policies(
            q_values,
            runs=args.evaluation_runs,
            episode_length=args.episode_length,
            seed=args.evaluation_seed,
            assumptions=assumptions,
        )
        results[name] = {
            policy: summarize(frame)
            for policy, frame in episode_results.groupby("policy", sort=False)
        }
        values = assumptions.to_dict()
        scenario_assumptions[name] = {
            "values": values,
            "sha256": hashlib.sha256(
                json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }

    report = {
        "study": "frozen_policy_biotech_catalyst_assumption_stress",
        "evidence_status": "synthetic_counterfactual_robustness_diagnostic_only",
        "not_a_claim": "No historical prices, trial outcomes, or trading edge are represented.",
        "protocol": {
            "training": "Q table trained once using only the base assumptions; it is frozen across all stress scenarios.",
            "evaluation": "Each scenario uses the same independent evaluation seed block; policies are compared on matched paths within each scenario.",
            "evaluation_seed_block_used_for_policy_tuning": False,
            "scenario_tuning": "One assumption family changes at a time; no policy or hyperparameter is selected from stress results.",
        },
        "configuration": {
            "training_episodes": args.training_episodes,
            "evaluation_runs": args.evaluation_runs,
            "episode_length_sessions": args.episode_length,
            "training_seed": args.training_seed,
            "evaluation_seed_start": args.evaluation_seed,
            "learning_rate": args.learning_rate,
            "discount_factor": args.discount,
            "training_assumptions_sha256": hashlib.sha256(raw_assumptions).hexdigest(),
            "training_assumptions_path": str(args.assumptions),
            "policies": ["cash", "buy_and_hold", "trend_rule", "pre_catalyst_exit", "q_learner"],
        },
        "scenario_assumptions": scenario_assumptions,
        "summary_metrics": list(SUMMARY_METRICS),
        "scenario_results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote frozen-policy synthetic stress report to {args.output}")
    print("The Q table was trained once on base assumptions and not retuned on stress scenarios.")
    for scenario, policies in results.items():
        q = policies["q_learner"]
        print(
            f"{scenario:>38}  Q CAGR {q['annualized_return']['median']:+.2%}  "
            f"relative {q['benchmark_relative_compounded_return']['median']:+.2%}  "
            f"MaxDD {q['max_drawdown']['median']:+.2%}  "
            f"event exposure {q['catalyst_exposure_fraction']['median']:.0%}"
        )


if __name__ == "__main__":
    main()
