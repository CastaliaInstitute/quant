"""A reproducible, simulator-only tabular RL study around biotech catalysts."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

import numpy as np
import pandas as pd

from quantlab.backtest import performance_metrics
from quantlab.simulation import CatalystAssumptions, BiotechCatalystGym, discretize_observation

RL_STATE_COUNT = 288


@dataclass(frozen=True)
class RLStudy:
    q_values: np.ndarray
    episode_results: pd.DataFrame
    report: dict


def _distribution(values: pd.Series) -> dict[str, float | None]:
    finite = pd.to_numeric(values, errors="coerce").dropna()
    if finite.empty:
        return {"median": None, "p10": None, "p90": None}
    return {
        "median": float(finite.median()),
        "p10": float(finite.quantile(0.10)),
        "p90": float(finite.quantile(0.90)),
    }


def _paired_bootstrap_difference(
    results: pd.DataFrame,
    policy: str,
    comparator: str,
    metric: str,
    seed: int,
    replicates: int = 10_000,
) -> dict[str, float | int]:
    """Bootstrap paired episode-seed differences for one synthetic generator."""
    paired = results.pivot(index="seed", columns="policy", values=metric)
    if policy not in paired or comparator not in paired:
        raise ValueError(f"missing policy comparison: {policy} vs {comparator}")
    differences = (paired[policy] - paired[comparator]).dropna().to_numpy(dtype=float)
    if differences.size == 0:
        raise ValueError(f"no paired observations for {policy} vs {comparator}")
    rng = np.random.default_rng(seed)
    samples = rng.choice(differences, size=(replicates, differences.size), replace=True).mean(axis=1)
    lower, upper = np.quantile(samples, [0.025, 0.975])
    return {
        "paired_episode_seeds": int(differences.size),
        "mean_difference": float(differences.mean()),
        "median_difference": float(np.median(differences)),
        "bootstrap_95pct_interval_low": float(lower),
        "bootstrap_95pct_interval_high": float(upper),
        "bootstrap_replicates": int(replicates),
        "bootstrap_seed": int(seed),
    }


def train_q_table(
    episodes: int = 300,
    episode_length: int = 252,
    seed: int = 17,
    learning_rate: float = 0.12,
    discount: float = 1.0,
    assumptions: CatalystAssumptions | None = None,
    visit_counts: np.ndarray | None = None,
) -> np.ndarray:
    """Train a Markov-state learner on independent, generated catalyst episodes."""
    if episodes <= 0:
        raise ValueError("episodes must be positive")
    if not 0.0 < learning_rate <= 1.0:
        raise ValueError("learning_rate must be in (0, 1]")
    if not 0.0 <= discount <= 1.0:
        raise ValueError("discount must be in [0, 1]")
    if visit_counts is not None and visit_counts.shape != (RL_STATE_COUNT, 2):
        raise ValueError(f"visit_counts must have shape ({RL_STATE_COUNT}, 2)")
    rng = np.random.default_rng(seed)
    env = BiotechCatalystGym(episode_length=episode_length, assumptions=assumptions)
    catalyst_interval = env.catalyst_interval
    q_values = np.zeros((RL_STATE_COUNT, 2), dtype=np.float64)
    for episode in range(episodes):
        observation, _ = env.reset(seed=seed + episode)
        epsilon = max(0.04, 0.35 * (1.0 - episode / episodes))
        terminated = False
        while not terminated:
            state = discretize_observation(observation, catalyst_interval)
            action = int(rng.integers(0, 2)) if rng.random() < epsilon else int(np.argmax(q_values[state]))
            if visit_counts is not None:
                visit_counts[state, action] += 1
            next_observation, reward, terminated, _, _ = env.step(action)
            next_state = discretize_observation(next_observation, catalyst_interval)
            bootstrap = 0.0 if terminated else discount * float(np.max(q_values[next_state]))
            q_values[state, action] += learning_rate * (reward + bootstrap - q_values[state, action])
            observation = next_observation
    return q_values


def _policy_action(
    policy: str,
    observation: np.ndarray,
    q_values: np.ndarray,
    catalyst_interval: int = 63,
) -> int:
    if policy == "cash":
        return 0
    if policy == "buy_and_hold":
        return 1
    if policy == "trend_rule":
        return int(observation[0] > 0.0)
    if policy == "pre_catalyst_exit":
        # Observation[2] is normalized time-to-event. Exit inside the final 5
        # sessions regardless of event phase; event class is not a risk score.
        return int(observation[2] > 5 / catalyst_interval)
    if policy == "q_learner":
        return int(np.argmax(q_values[discretize_observation(observation, catalyst_interval)]))
    raise ValueError(f"unknown policy: {policy}")


def evaluate_policies(
    q_values: np.ndarray,
    runs: int = 60,
    episode_length: int = 252,
    seed: int = 10_000,
    assumptions: CatalystAssumptions | None = None,
) -> pd.DataFrame:
    """Compare fixed policies on matched seeded paths from one generator family."""
    if runs <= 0:
        raise ValueError("runs must be positive")
    rows: list[dict] = []
    policies = ("cash", "buy_and_hold", "trend_rule", "pre_catalyst_exit", "q_learner")
    for run in range(runs):
        episode_seed = seed + run
        for policy in policies:
            env = BiotechCatalystGym(episode_length=episode_length, assumptions=assumptions)
            catalyst_interval = env.catalyst_interval
            observation, _ = env.reset(seed=episode_seed)
            returns: list[float] = []
            benchmarks: list[float] = []
            turnovers: list[float] = []
            costs: list[float] = []
            event_returns: list[float] = []
            event_net_returns: list[float] = []
            event_costs: list[float] = []
            event_exposures: list[float] = []
            event_phases: list[int] = []
            event_trial_outcomes: list[int] = []
            exposures: list[float] = []
            terminated = False
            while not terminated:
                action = _policy_action(policy, observation, q_values, catalyst_interval)
                observation, _, terminated, _, info = env.step(action)
                returns.append(info["net_return"])
                benchmarks.append(info["benchmark_return"])
                turnovers.append(info["turnover"])
                costs.append(info["transaction_cost"])
                exposures.append(info["exposure"])
                event_phase = int(info["event_phase_observed_after_transition"])
                if event_phase >= 0:
                    event_returns.append(info["market_return"])
                    event_net_returns.append(info["net_return"])
                    event_costs.append(info["transaction_cost"])
                    event_exposures.append(float(info["exposure"]))
                    event_phases.append(event_phase)
                    observed_success = info["program_advancement_observed_after_transition"]
                    event_trial_outcomes.append(-1 if observed_success is None else int(observed_success))
            metrics = performance_metrics(pd.Series(returns), benchmark_returns=pd.Series(benchmarks))
            event_losses = np.asarray(event_returns, dtype=float)
            policy_event_losses = np.asarray(event_net_returns, dtype=float)
            phases_array = np.asarray(event_phases, dtype=int)
            outcomes_array = np.asarray(event_trial_outcomes, dtype=int)
            known_outcome = outcomes_array >= 0
            success_array = outcomes_array[known_outcome]
            known_returns = event_losses[known_outcome]
            phase_ii = known_outcome & (phases_array == 0)
            phase_iii = known_outcome & (phases_array == 1)
            success_returns = event_losses[known_outcome & (outcomes_array == 1)]
            failure_returns = event_losses[known_outcome & (outcomes_array == 0)]
            success_positive_count = int(np.sum(success_returns > 0.0))
            failure_positive_count = int(np.sum(failure_returns > 0.0))
            tail_n = max(1, int(np.ceil(0.05 * len(event_losses)))) if len(event_losses) else 0
            event_es95 = float(np.mean(np.sort(event_losses)[:tail_n])) if tail_n else 0.0
            policy_tail_n = max(1, int(np.ceil(0.05 * len(policy_event_losses)))) if len(policy_event_losses) else 0
            policy_event_es95 = float(np.mean(np.sort(policy_event_losses)[:policy_tail_n])) if policy_tail_n else 0.0
            rows.append({
                "policy": policy,
                "seed": episode_seed,
                **metrics,
                "annual_turnover": float(np.sum(turnovers) * 252 / episode_length),
                "total_cost": float(np.sum(costs)),
                "exposure_fraction": float(np.mean(exposures)),
                "catalyst_exposure_fraction": float(np.mean(event_exposures)) if event_exposures else 0.0,
                "catalyst_event_count": len(event_returns),
                "catalyst_sessions_per_episode": len(event_returns),
                "catalyst_trial_outcome_count": int(known_outcome.sum()),
                "catalyst_trial_success_count": int(np.sum(success_array)),
                "catalyst_trial_failure_count": int(np.sum(success_array == 0)),
                "catalyst_trial_success_fraction": float(np.mean(success_array)) if len(success_array) else np.nan,
                "phase_ii_trial_success_fraction": float(np.mean(outcomes_array[phase_ii])) if phase_ii.any() else np.nan,
                "phase_iii_trial_success_fraction": float(np.mean(outcomes_array[phase_iii])) if phase_iii.any() else np.nan,
                "phase_ii_trial_count": int(phase_ii.sum()),
                "phase_ii_trial_success_count": int(outcomes_array[phase_ii].sum()) if phase_ii.any() else 0,
                "phase_iii_trial_count": int(phase_iii.sum()),
                "phase_iii_trial_success_count": int(outcomes_array[phase_iii].sum()) if phase_iii.any() else 0,
                "catalyst_market_return_given_success_mean": float(np.mean(success_returns)) if len(success_returns) else np.nan,
                "catalyst_market_return_given_failure_mean": float(np.mean(failure_returns)) if len(failure_returns) else np.nan,
                "catalyst_market_return_sum_given_success": float(np.sum(success_returns)) if len(success_returns) else 0.0,
                "catalyst_market_return_sum_given_failure": float(np.sum(failure_returns)) if len(failure_returns) else 0.0,
                "catalyst_positive_market_reaction_fraction_given_success": success_positive_count / len(success_returns) if len(success_returns) else np.nan,
                "catalyst_positive_market_reaction_fraction_given_failure": failure_positive_count / len(failure_returns) if len(failure_returns) else np.nan,
                "catalyst_positive_market_reaction_count_given_success": success_positive_count,
                "catalyst_positive_market_reaction_count_given_failure": failure_positive_count,
                "catalyst_underlying_return_mean": float(np.mean(event_returns)) if event_returns else 0.0,
                "catalyst_underlying_return_worst": float(np.min(event_returns)) if event_returns else 0.0,
                "catalyst_unconditional_expected_shortfall_95": event_es95,
                "catalyst_policy_net_expected_shortfall_95": policy_event_es95,
                "catalyst_policy_net_mean": float(np.mean(event_net_returns)) if event_net_returns else 0.0,
                "catalyst_policy_net_worst": float(np.min(event_net_returns)) if event_net_returns else 0.0,
                "catalyst_event_transaction_cost": float(np.sum(event_costs)),
                "catalyst_event_expected_shortfall_95": event_es95,
            })
    return pd.DataFrame(rows)


def run_rl_study(
    training_episodes: int = 300,
    evaluation_runs: int = 60,
    episode_length: int = 252,
    training_seed: int = 17,
    evaluation_seed: int = 10_000,
    learning_rate: float = 0.12,
    discount: float = 1.0,
    assumptions: CatalystAssumptions | None = None,
    assumptions_sha256: str | None = None,
) -> RLStudy:
    config = assumptions or CatalystAssumptions()
    training_visit_counts = np.zeros((RL_STATE_COUNT, 2), dtype=np.int64)
    q_values = train_q_table(
        training_episodes,
        episode_length,
        training_seed,
        learning_rate=learning_rate,
        discount=discount,
        assumptions=config,
        visit_counts=training_visit_counts,
    )
    episode_results = evaluate_policies(q_values, evaluation_runs, episode_length, evaluation_seed, config)
    metrics = (
        "observation_count", "annualized_return", "annualized_volatility", "sharpe", "sortino", "max_drawdown",
        "calmar", "value_at_risk_95", "expected_shortfall_95",
        "benchmark_total_return", "benchmark_relative_compounded_return", "information_ratio",
        "annual_turnover", "total_cost", "exposure_fraction",
        "catalyst_exposure_fraction", "catalyst_sessions_per_episode",
        "catalyst_trial_outcome_count", "catalyst_trial_success_fraction",
        "phase_ii_trial_success_fraction", "phase_iii_trial_success_fraction",
        "catalyst_market_return_given_success_mean", "catalyst_market_return_given_failure_mean",
        "catalyst_positive_market_reaction_fraction_given_success",
        "catalyst_positive_market_reaction_fraction_given_failure",
        "catalyst_underlying_return_mean", "catalyst_underlying_return_worst",
        "catalyst_unconditional_expected_shortfall_95",
        "catalyst_policy_net_expected_shortfall_95", "catalyst_policy_net_mean",
        "catalyst_policy_net_worst", "catalyst_event_transaction_cost",
    )
    summary: dict[str, dict[str, dict[str, float | None]]] = {}
    for policy, frame in episode_results.groupby("policy", sort=False):
        summary[policy] = {
            metric: _distribution(frame[metric])
            for metric in metrics
        }
    momentum_names = ("negative", "neutral", "positive")
    volatility_names = ("lower", "upper")
    proximity_names = ("more_than_5_sessions", "within_5_sessions", "event_session")
    state_policy = []
    horizon_names = ("early", "mid_early", "mid_late", "late")
    for state, values in enumerate(q_values):
        position_bin = state % 2
        horizon_bin = (state // 2) % 4
        market_state = state // 8
        phase_bin = market_state % 2
        event_bin = (market_state // 2) % 3
        volatility_bin = (market_state // 6) % 2
        momentum_bin = market_state // 12
        cash_value, long_value = (float(values[0]), float(values[1]))
        state_policy.append({
            "state": state,
            "momentum_regime": momentum_names[momentum_bin],
            "volatility_regime": volatility_names[volatility_bin],
            "catalyst_proximity": proximity_names[event_bin],
            "upcoming_phase": "phase_III" if phase_bin else "phase_II",
            "episode_horizon": horizon_names[horizon_bin],
            "current_position": "long" if position_bin else "cash",
            "training_cash_visits": int(training_visit_counts[state, 0]),
            "training_long_visits": int(training_visit_counts[state, 1]),
            "q_cash": cash_value,
            "q_long": long_value,
            "greedy_action": "long" if long_value > cash_value else "cash",
            "q_long_minus_cash": long_value - cash_value,
        })
    report = {
        "study": "synthetic_biotech_catalyst_gym",
        "evidence_status": "synthetic_simulator_diagnostic_only",
        "not_a_claim": "No point-in-time trial-event panel or historical security data is fitted; no evidence of a trading edge is represented.",
        "biological_and_market_outcomes": {
            "clinical_success": "Legacy metric label for program advancement: Phase II to Phase III or Phase III to NDA/BLA; it does not mean an individual trial met its primary endpoint.",
            "stock_reaction": "Sampled separately from phase- and clinical-outcome-conditional probabilities of a positive reaction, with independent positive/negative gap sizes and market noise.",
            "interpretation": "Program advancement is not equivalent to positive stock return; positive reactions can follow suspension and negative reactions can follow advancement.",
            "parameter_status": "Phase advancement priors are anchored to published 2011-2020 all-indication transition rates; event-level outcomes are not fitted. Market-reaction probabilities, gaps, and daily price parameters remain illustrative and uncalibrated.",
        },
        "configuration": {
            "training_episodes": training_episodes,
            "evaluation_runs": evaluation_runs,
            "episode_length_sessions": episode_length,
            "training_seed": training_seed,
            "learning_rate": learning_rate,
            "discount_factor": discount,
            "exploration_schedule": "epsilon=max(0.04, 0.35 * (1 - episode / training_episodes)); linear decay with 0.04 floor",
            "evaluation_seed_start": evaluation_seed,
            "simulator_assumptions": config.to_dict(),
            "policies": ["cash", "buy_and_hold", "trend_rule", "pre_catalyst_exit", "q_learner"],
        },
        "assumption_provenance": {
            "status": "published_aggregate_advancement_prior_plus_synthetic_market_parameters",
            "clinical_transition_source": {
                "citation": "BIO, Informa Pharma Intelligence, and QLS Advisors, Clinical Development Success Rates and Contributing Factors 2011-2020 (2021)",
                "url": "https://go.bio.org/rs/490-EHZ-999/images/ClinicalDevelopmentSuccessRates2011_2020.pdf",
                "phase_ii_to_iii": {"probability": 0.289, "transitions": 4933},
                "phase_iii_to_nda_bla": {"probability": 0.578, "transitions": 1928},
                "scope_note": "Published aggregates from proprietary Biomedtracker and Pharmapremia program-transition data; advancement vs suspension, not per-trial endpoint success.",
            },
            "market_parameter_status": "synthetic_uncalibrated_no_historical_security_price_panel",
            "sha256": assumptions_sha256 or hashlib.sha256(
                json.dumps(config.to_dict(), sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "interpretation": "Hash identifies the exact JSON config file when run through scripts/run_rl_study.py; direct API runs hash canonicalized parameter values.",
        },
        "evaluation_protocol": {
            "episodes": "matched independent random seeds sampled from the same synthetic generator family used in training",
            "market_holdout": False,
            "evaluation_seed_block_used_for_post_hoc_search": False,
            "interpretation": "Checks simulator behavior and seed variation only; it does not test historical or new-regime generalization.",
        },
        "metric_definitions": {
            "learning_reward": (
                "Q-learning maximizes sum(gamma**k * log(1 + net_return_k)). "
                "At gamma=1 in this finite-horizon environment, this equals log terminal wealth; "
                "gamma below one is a time-preference sensitivity and no longer equals terminal log wealth."
            ),
            "discount_factor": float(discount),
            "reward_discount_half_life_sessions": (
                float(np.log(0.5) / np.log(discount)) if 0.0 < discount < 1.0 else None
            ),
            "catalyst_unconditional_expected_shortfall_95": "Mean underlying issuer return in the worst ceil(5% of event observations); independent of policy exposure.",
            "catalyst_policy_net_expected_shortfall_95": "Mean strategy net return on event sessions in its worst ceil(5%); includes zero-return cash exposure and transaction costs.",
            "annual_turnover": "Sum of absolute daily exposure changes multiplied by 252 / episode length.",
            "episode_sample_size": "Each evaluation seed contributes one episode per policy; catalyst-tail denominators are also reported per episode.",
        },
        "learned_q_values": q_values.tolist(),
        "learned_policy_by_state": state_policy,
        "state_encoding": {
            "state_formula": "(((((momentum_bin * 2 + volatility_bin) * 3 + catalyst_proximity_bin) * 2 + upcoming_phase_bin) * 4 + episode_horizon_bin) * 2) + current_position_bin",
            "momentum_bins": list(momentum_names),
            "volatility_bins": list(volatility_names),
            "catalyst_proximity_bins": list(proximity_names),
            "upcoming_phase_bins": ["phase_II", "phase_III"],
            "episode_horizon_bins": list(horizon_names),
            "current_position_bins": ["cash", "long"],
            "available_states": RL_STATE_COUNT,
            "visit_counts_include": "all epsilon-greedy training actions; evaluation paths are not included",
        },
        "evaluation_summary": summary,
        "paired_q_policy_comparisons": {
            comparator: {
                "annualized_return_difference": _paired_bootstrap_difference(
                    episode_results, "q_learner", comparator, "annualized_return",
                    evaluation_seed + index,
                ),
                "benchmark_relative_compounded_return_difference": _paired_bootstrap_difference(
                    episode_results, "q_learner", comparator, "benchmark_relative_compounded_return",
                    evaluation_seed + 100 + index,
                ),
            }
            for index, comparator in enumerate(("cash", "buy_and_hold", "trend_rule", "pre_catalyst_exit"))
        },
        "paired_comparison_interpretation": (
            "Intervals resample matched synthetic evaluation episode seeds and describe uncertainty under this one fixed generator and trained policy. "
            "They are not historical-market confidence intervals, do not include policy-training uncertainty, and do not establish statistical significance or a trading edge."
        ),
    }
    paths = episode_results.drop_duplicates("seed")
    event_count = int(paths.catalyst_trial_outcome_count.sum())
    success_count = int(paths.catalyst_trial_success_count.sum())
    failure_count = int(paths.catalyst_trial_failure_count.sum())
    phase_ii_count = int(paths.phase_ii_trial_count.sum())
    phase_ii_success_count = int(paths.phase_ii_trial_success_count.sum())
    phase_iii_count = int(paths.phase_iii_trial_count.sum())
    phase_iii_success_count = int(paths.phase_iii_trial_success_count.sum())
    success_positive_count = int(paths.catalyst_positive_market_reaction_count_given_success.sum())
    failure_positive_count = int(paths.catalyst_positive_market_reaction_count_given_failure.sum())
    success_return_sum = float(paths.catalyst_market_return_sum_given_success.sum())
    failure_return_sum = float(paths.catalyst_market_return_sum_given_failure.sum())
    report["evaluation_event_process_summary"] = {
        "independent_episode_seeds": int(paths.seed.nunique()),
        "catalyst_count": event_count,
        "clinical_success_count": success_count,
        "clinical_failure_count": failure_count,
        "clinical_success_fraction": success_count / event_count if event_count else None,
        "phase_ii_count": phase_ii_count,
        "phase_ii_clinical_success_fraction": phase_ii_success_count / phase_ii_count if phase_ii_count else None,
        "phase_iii_count": phase_iii_count,
        "phase_iii_clinical_success_fraction": phase_iii_success_count / phase_iii_count if phase_iii_count else None,
        "positive_market_reaction_fraction_given_clinical_success": success_positive_count / success_count if success_count else None,
        "positive_market_reaction_fraction_given_clinical_failure": failure_positive_count / failure_count if failure_count else None,
        "mean_issuer_event_return_given_clinical_success": success_return_sum / success_count if success_count else None,
        "mean_issuer_event_return_given_clinical_failure": failure_return_sum / failure_count if failure_count else None,
        "interpretation": "Synthetic generator diagnostics across unique matched evaluation paths; advancement and stock reaction are separate draws. Advancement priors use published aggregate transitions; these counts are not empirical event-panel estimates.",
    }
    return RLStudy(q_values, episode_results, report)
