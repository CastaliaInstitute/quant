#!/usr/bin/env python3
"""Rebuild the versioned synthetic biotech catalyst RL report used by the book."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from quantlab.rl_study import run_rl_study
from quantlab.simulation import CatalystAssumptions


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-episodes", type=int, default=300)
    parser.add_argument("--evaluation-runs", type=int, default=60)
    parser.add_argument("--episode-length", type=int, default=252)
    parser.add_argument("--training-seed", type=int, default=17)
    parser.add_argument("--evaluation-seed", type=int, default=10_000)
    parser.add_argument("--learning-rate", type=float, default=0.12)
    parser.add_argument("--discount", type=float, default=1.0)
    parser.add_argument("--assumptions", type=Path, default=ROOT / "config/biopharma_rl_synthetic.json")
    parser.add_argument("--output", type=Path, default=ROOT / "book" / "_static" / "rl-simulation.json")
    args = parser.parse_args()
    if not args.assumptions.exists():
        raise SystemExit(f"Simulator assumptions file not found: {args.assumptions}")
    raw_assumptions = args.assumptions.read_bytes()
    try:
        assumptions = CatalystAssumptions.from_mapping(json.loads(raw_assumptions))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid simulator assumptions file: {exc}") from exc

    study = run_rl_study(
        training_episodes=args.training_episodes,
        evaluation_runs=args.evaluation_runs,
        episode_length=args.episode_length,
        training_seed=args.training_seed,
        evaluation_seed=args.evaluation_seed,
        learning_rate=args.learning_rate,
        discount=args.discount,
        assumptions=assumptions,
        assumptions_sha256=hashlib.sha256(raw_assumptions).hexdigest(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(study.report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    print("Synthetic simulator diagnostic only; not historical performance.")
    for policy, result in study.report["evaluation_summary"].items():
        cagr = result["annualized_return"]
        sharpe = result["sharpe"]
        drawdown = result["max_drawdown"]
        turnover = result["annual_turnover"]
        print(
            f"{policy:>12}  CAGR median {cagr['median']:+.2%} "
            f"[p10 {cagr['p10']:+.2%}, p90 {cagr['p90']:+.2%}]  "
            f"Sharpe median {sharpe['median']:+.2f}  "
            f"MaxDD median {drawdown['median']:+.2%}  "
            f"turnover median {turnover['median']:.1f}x"
        )


if __name__ == "__main__":
    main()
