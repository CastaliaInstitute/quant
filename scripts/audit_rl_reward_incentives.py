#!/usr/bin/env python3
"""Attribute the synthetic gym's cash-heavy Q policy to assumed reward economics."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from quantlab.simulation import CatalystAssumptions


ROOT = Path(__file__).resolve().parents[1]


def normal_expectation_log1p(mean: float, volatility: float, cost: float = 0.0, order: int = 80) -> float:
    """Gauss-Hermite quadrature for E[log(1 + Normal(mean, volatility²) - cost)]."""
    nodes, weights = np.polynomial.hermite.hermgauss(order)
    returns = mean + np.sqrt(2.0) * volatility * nodes - cost
    if np.any(returns <= -1.0):
        raise ValueError("quadrature reached a periodic return at or below -100%")
    return float(np.dot(weights, np.log1p(returns)) / np.sqrt(np.pi))


def break_even_arithmetic_mean(volatility: float, cost: float = 0.0) -> float:
    """Solve for the arithmetic mean that makes expected log reward equal cash."""
    low, high = -0.5, 0.5
    for _ in range(100):
        middle = (low + high) / 2.0
        if normal_expectation_log1p(middle, volatility, cost) < 0.0:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def event_branches(config: CatalystAssumptions, phase: int) -> list[dict[str, float | str]]:
    success_probability = config.phase_success_probabilities[phase]
    positive_gaps = config.phase_positive_market_gaps[phase]
    negative_gaps = config.phase_negative_market_gaps[phase]
    branches: list[dict[str, float | str]] = []
    for outcome, outcome_probability in (
        ("advancement", success_probability),
        ("suspension", 1.0 - success_probability),
    ):
        reaction_probability = (
            config.phase_success_market_positive_probabilities[phase]
            if outcome == "advancement"
            else config.phase_failure_market_positive_probabilities[phase]
        )
        for reaction, reaction_probability_value, gap in (
            ("positive", reaction_probability, positive_gaps),
            ("negative", 1.0 - reaction_probability, negative_gaps),
        ):
            probability = outcome_probability * reaction_probability_value
            mean = config.issuer_market_beta * config.broad_market_daily_mean + gap
            volatility = float(np.hypot(
                config.issuer_market_beta * config.broad_market_daily_volatility,
                config.event_residual_volatility,
            ))
            branches.append({
                "clinical_outcome": outcome,
                "market_reaction": reaction,
                "probability": float(probability),
                "mean_simple_return": float(mean),
                "expected_log_reward": normal_expectation_log1p(mean, volatility),
            })
    return branches


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assumptions", type=Path, default=ROOT / "config/biopharma_rl_synthetic.json")
    parser.add_argument("--training-report", type=Path, default=ROOT / "book/_static/rl-training-robustness.json")
    parser.add_argument("--output", type=Path, default=ROOT / "book/_static/rl-reward-incentive-audit.json")
    parser.add_argument("--episode-length", type=int, default=252)
    args = parser.parse_args()
    if not args.assumptions.exists():
        raise SystemExit(f"Simulator assumptions file not found: {args.assumptions}")
    if args.episode_length <= 0:
        raise SystemExit("episode-length must be positive")
    raw_assumptions = args.assumptions.read_bytes()
    try:
        config = CatalystAssumptions.from_mapping(json.loads(raw_assumptions))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid simulator assumptions file: {exc}") from exc

    ordinary_mean = config.issuer_market_beta * config.broad_market_daily_mean + config.issuer_daily_mean
    ordinary_volatility = float(np.hypot(
        config.issuer_market_beta * config.broad_market_daily_volatility,
        config.issuer_idiosyncratic_daily_volatility,
    ))
    ordinary_log_reward = normal_expectation_log1p(ordinary_mean, ordinary_volatility)
    ordinary_entry_log_reward = normal_expectation_log1p(
        ordinary_mean,
        ordinary_volatility,
        config.transaction_cost_bps_per_unit_turnover / 10_000.0,
    )
    phase_names = ("phase_ii", "phase_iii")
    phase_reports = {}
    for phase, name in enumerate(phase_names):
        branches = event_branches(config, phase)
        phase_reports[name] = {
            "program_advancement_probability": config.phase_success_probabilities[phase],
            "branches": branches,
            "expected_simple_return": float(sum(
                branch["probability"] * branch["mean_simple_return"]
                for branch in branches
            )),
            "expected_log_reward": float(sum(
                branch["probability"] * branch["expected_log_reward"]
                for branch in branches
            )),
        }

    event_indices = list(range(config.catalyst_interval_sessions, args.episode_length, config.catalyst_interval_sessions))
    ordinary_sessions = args.episode_length - len(event_indices)
    event_rate = len(event_indices) / args.episode_length
    phase_probabilities = config.phase_sampling_probabilities
    expected_event_log_reward = float(sum(
        probability * phase_reports[phase_names[index]]["expected_log_reward"]
        for index, probability in enumerate(phase_probabilities)
    ))
    expected_episode_log_reward_no_cost = (
        ordinary_sessions * ordinary_log_reward + len(event_indices) * expected_event_log_reward
    )
    expected_episode_log_reward_with_entry_cost = (
        ordinary_sessions * ordinary_log_reward
        - ordinary_log_reward
        + ordinary_entry_log_reward
        + len(event_indices) * expected_event_log_reward
    ) if ordinary_sessions else expected_episode_log_reward_no_cost
    break_even_mean = break_even_arithmetic_mean(ordinary_volatility)

    training_coverage = None
    if args.training_report.exists():
        training_report = json.loads(args.training_report.read_text(encoding="utf-8"))
        report_assumptions_hash = training_report.get("configuration", {}).get("assumptions_sha256")
        assumptions_hash = hashlib.sha256(raw_assumptions).hexdigest()
        if report_assumptions_hash and report_assumptions_hash != assumptions_hash:
            raise SystemExit(
                "training report assumptions hash does not match --assumptions; "
                "supply the matching report or omit it"
            )
        diagnostics = training_report.get("q_policy_training_diagnostics", [])
        if diagnostics:
            training_coverage = {
                "training_replicates": len(diagnostics),
                "state_count": 36,
                "state_action_count": 72,
                "training_states_visited_min": min(row["training_states_visited"] for row in diagnostics),
                "training_states_visited_max": max(row["training_states_visited"] for row in diagnostics),
                "state_action_pairs_visited_min": min(row["training_state_action_pairs_visited"] for row in diagnostics),
                "state_action_pairs_visited_max": max(row["training_state_action_pairs_visited"] for row in diagnostics),
                "greedy_long_state_count_min": min(row["greedy_long_state_count"] for row in diagnostics),
                "greedy_long_state_count_max": max(row["greedy_long_state_count"] for row in diagnostics),
                "interpretation": "State visits are high; cash-heavy behavior is not explained by gross state undercoverage in this training run.",
            }

    report = {
        "study": "synthetic_rl_reward_incentive_audit",
        "evidence_status": "assumption_arithmetic_diagnostic_only",
        "not_a_claim": "This audit explains behavior under configured synthetic assumptions; it does not estimate historical biotech returns or a deployable optimum.",
        "assumptions_sha256": hashlib.sha256(raw_assumptions).hexdigest(),
        "configuration": {
            "assumptions_path": str(args.assumptions),
            "episode_length_sessions": args.episode_length,
            "catalyst_interval_sessions": config.catalyst_interval_sessions,
            "catalyst_indices_zero_based": event_indices,
            "transaction_cost_bps_per_unit_turnover": config.transaction_cost_bps_per_unit_turnover,
            "phase_sampling_probabilities": list(config.phase_sampling_probabilities),
        },
        "ordinary_session": {
            "arithmetic_mean_return": float(ordinary_mean),
            "return_volatility": ordinary_volatility,
            "expected_log_reward_long": ordinary_log_reward,
            "expected_log_reward_after_initial_entry_cost": ordinary_entry_log_reward,
            "break_even_arithmetic_mean_return_for_zero_log_reward": break_even_mean,
            "mean_return_shortfall_to_log_break_even": float(break_even_mean - ordinary_mean),
        },
        "catalyst_sessions": {
            "event_count_per_episode": len(event_indices),
            "event_fraction": event_rate,
            "by_phase": phase_reports,
            "phase_mixture_expected_log_reward": expected_event_log_reward,
        },
        "episode_long_only": {
            "expected_log_wealth_change_no_cost": float(expected_episode_log_reward_no_cost),
            "expected_geometric_wealth_return_no_cost": float(np.expm1(expected_episode_log_reward_no_cost)),
            "expected_log_wealth_change_with_initial_entry_cost": float(expected_episode_log_reward_with_entry_cost),
            "expected_geometric_wealth_return_with_initial_entry_cost": float(np.expm1(expected_episode_log_reward_with_entry_cost)),
            "cash_expected_log_wealth_change": 0.0,
            "interpretation": "Expected log rewards add over sessions; the geometric return is exp(expected log wealth change) minus one, not expected arithmetic compounded return.",
        },
        "observed_training_coverage": training_coverage,
        "diagnosis": (
            "The configured ordinary-session arithmetic drift is below the volatility-implied break-even drift for log growth, "
            "and configured catalyst gaps have negative expected log reward in both phases. Cash-heavy Q behavior is therefore aligned "
            "with this generator's reward incentives; this is not evidence that the learner found an investable edge."
        ),
        "research_implication": (
            "Calibrate ordinary-return drift, volatility, and event-gap distributions from point-in-time historical data before using policy exposure as a research conclusion. "
            "Keep cash as a valid action; evaluate any risk budget or drawdown constraint as an explicit objective rather than forcing exposure."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote reward-incentive audit to {args.output}")
    print(f"Ordinary expected log reward: {ordinary_log_reward:+.8f}; cash: +0.00000000")
    print(f"Expected long-only geometric episode return after entry cost: {np.expm1(expected_episode_log_reward_with_entry_cost):+.2%}")


if __name__ == "__main__":
    main()
