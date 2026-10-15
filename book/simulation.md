# Simulation and Reinforcement-Learning Gyms

```{raw} html
<p class="castalia-kicker">A WORLD FOR THE POLICY · A TEST FOR THE CLAIM</p>
```

Quant. should lean heavily on simulation. Forks can use configurable market simulators and RL gyms to teach sequential decisions, probe risk, and compare policies across controlled conditions. Simulated worlds make assumptions visible and experiments repeatable. They also make it easy to learn the wrong lesson from an unrealistic world.

## A gym is a research instrument

An RL environment defines a transition process: the agent observes a state, selects an action, receives a reward, and moves to a new state. For quantitative research, the environment must also declare the market clock, execution convention, position accounting, costs, constraints, episode boundaries, and reset behavior.

For biotech/pharma research, start with transparent environments before adding complexity:

1. **Deterministic toy market:** verify action timing, inventory, reward arithmetic, and reset behavior.
2. **Synthetic catalyst market:** vary issuer/sector correlation, volatility, scheduled and unscheduled disclosures, clinical outcomes, market expectations/reactions, gap-size distributions, and liquidity under known data-generating processes.
3. **Historical replay:** source trial design and biomedical evidence as-of each timestamp, join verified issuer disclosures and market prices, and expose only information available before the decision. Model non-tradable gaps, delayed fills, costs, and capacity.
4. **Stress suite:** alter outcome frequencies, widen or reverse event gaps, shift release timestamps across sessions, remove records, add overlapping news, and test recovery behavior.

The current synthetic catalyst parameters live in [`config/biopharma_rl_synthetic.json`](../config/biopharma_rl_synthetic.json). It exposes catalyst spacing, market and issuer daily-return distributions, issuer market beta, Phase II/III mixture and program-advancement probabilities, outcome-conditional market-reaction probabilities, positive/negative price-gap sizes, event residual noise, and transaction costs. The Phase II/III advancement probabilities use published 2011–2020 all-disease phase-transition rates; see the [evidence review](research/evidence-review.md). Here, “success” means program advancement to the next stage, not an individual trial meeting a primary endpoint. `scripts/run_rl_study.py --assumptions PATH` loads a fork's JSON file, validates it, and writes the exact parameter values and SHA-256 into the report. Advancement and the stock's positive/negative reaction are sampled separately: a stock rally can follow suspension, and a selloff can follow advancement. Market gaps and ordinary return parameters remain illustrative only; changing the file changes the simulated world, not the evidence status. A future empirical market calibration should estimate parameters from training-window event panels only, include uncertainty ranges, and preserve the source panel and fitting code.

Each stage answers a different question. Performance on toy and synthetic markets checks implementation and behavior under stated assumptions. Historical replay examines a strategy against one recorded path. Neither alone establishes future profitability.

### Keep known schedules separate from realized events

In empirical replay, a disclosure's historical date is an outcome label, not automatically a date the agent could have anticipated. The gym accepts `scheduled_event_phases` for event dates/phases proven public before the decision cutoff, and `realized_event_phases` for event-session labels used only after the action and return. Historical callers should pass verified pre-event schedules separately from realized labels; if no schedule was known, pass an all-`-1` schedule. The legacy `event_phases` option populates both arrays for compatibility with the synthetic generator, where catalyst timing is deliberately scheduled by construction. If callers supply both the legacy labels and `realized_event_phases` but omit `scheduled_event_phases`, the gym defaults the observable schedule to no known events. Never feed a later press-release date into `scheduled_event_phases` during historical replay.

## Separate reward from evidence

Reward is an optimization device, not the research conclusion. A policy can maximize a reward that accidentally rewards turnover, exploits simulator artifacts, or omits tail risk. Publish the exact reward function and report its components separately from evaluation metrics.

Use a fixed evaluation protocol that is separate from policy training:

- Train on earlier windows and tune only on designated validation windows.
- Preserve a final chronological holdout; do not select checkpoints or hyperparameters using it.
- Evaluate multiple independent random seeds and report dispersion, not only the best run.
- Compare with cash, buy-and-hold, and transparent rules using identical execution assumptions.
- Stress fees, spread, slippage, latency, partial fills, market impact, and position caps.
- Report return, volatility, drawdown, turnover, exposure, and tail outcomes together.
- For catalyst work, show issuer, phase, indication, event timestamp precision, cluster period, and the source/version of every feature.
- Keep failed experiments, environment changes, and reward revisions in the record.

Repeatedly searching policies against a finite historical sample can overfit that sample even when the optimizer is called reinforcement learning. A simulator does not remove selection bias; it can hide it behind many episodes and tuning runs.

## Suggested fork interfaces

A fork can implement familiar Gymnasium-style `reset(seed=...)` and `step(action)` methods, but it should also keep these concerns independently inspectable:

| Interface | Questions the environment must answer |
| --- | --- |
| Observation | Are all fields known at decision time? Are units and scaling documented? |
| Action | Does the action represent target exposure, an order, or a portfolio weight? |
| Transition | When does an action take effect? How are missing sessions and episode ends handled? |
| Execution | What are the fill price, spread, fees, slippage, and capacity assumptions? |
| Reward | Which return and risk terms enter reward, and how can each be exploited? |
| Evaluation | Which periods, seeds, baselines, and stress scenarios remain outside training? |

This book's live Cloudflare Worker is only a bounded Python teaching-cell service. It is not an RL runtime. Put training workloads in a controlled local or private compute environment; publish source, environment specifications, data provenance, and reproducible evaluation artifacts through the fork.

## MagAI (Quant) pathway

The planned MagAI (Quant) program can use the same system as a progression: construct a toy catalyst gym, inspect a real trial/event join, vary biological and market assumptions one at a time, train a policy, then write an adversarial evaluation record. Learners should be able to fork the environment and see how outcomes depend on data provenance, biological context, event timing, and return tails. A completed exercise demonstrates research practice, not investment performance.
