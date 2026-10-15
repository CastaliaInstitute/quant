# Tune and Fork the Quant. System

```{raw} html
<p class="castalia-kicker">OPEN SYSTEM · REPRODUCIBLE FORKS</p>
```

Quant. is a foundation to build around. A fork may become a focused research app, a teaching environment, or a simulation lab. Keep the core research record portable: question, data provenance, environment version, assumptions, code revision, random seeds, evaluation protocol, and results.

## Extension points

| Layer | Examples of choices to tune |
| --- | --- |
| Research specification | Question, target, horizon, falsification criteria |
| Market and synthetic data | Provider, symbols, sampling, corporate actions, regimes |
| Environment | Observation space, action space, episode boundaries, reset rules |
| Agent or strategy | Rules, supervised models, policies, reward shaping |
| Execution simulator | Fill timing, spread, fees, slippage, capacity, partial fills |
| Risk and evaluation | Constraints, baselines, walk-forward windows, stress scenarios |
| Presentation | Research notebooks, dashboards, lesson sequence, reports |

Replace a layer when the research question requires it. Record its interface and version so that another fork can determine what changed.

## A small fork-specific specification

The following is an illustrative configuration, not a live-data connection or a claim that the chosen assets are suitable:

```yaml
experiment:
  id: phase-3-catalyst-risk-v1
  hypothesis: "Point-in-time trial and market context helps calibrate catalyst-window downside risk."
  universe: "versioned biotech/pharma issuer-event cohort"
  data:
    trial_registry: "archived ClinicalTrials.gov study versions"
    research_metadata: "versioned PubMed/Europe PMC records"
    price_source: "licensed vendor export; include inactive issuers"
    event_clock: "issuer disclosure timestamp with source URL and timezone"
    adjustment: split_dividend_and_spinoff_adjusted
  environment:
    frequency: "daily event replay; intraday for verified release times"
    observation: [pre_event_volatility, trial_phase_asof, endpoint_design_asof, issuer_and_sector_context]
    action: "risk forecast first; paper portfolio only after separate validation"
    event_window_sessions: [-1, 2]
    seed: 1701
  execution:
    decision_time: "strictly before issuer disclosure"
    earliest_fill: "first verifiably tradable bar after disclosure"
    costs: "provider and instrument specific"
  validation:
    method: "chronological walk-forward grouped by issuer and calendar period"
    final_holdout: untouched
    baselines: [training_fold_tail_rate, issuer_realized_volatility, biotech_index_context]
```

This declarative sketch is a template for a fork to implement and validate. The current public Worker only runs small educational Python cells; it does not parse this configuration or host a reinforcement-learning environment.

## Preserve what makes a fork scientific

- Freeze the environment's observation and action semantics before evaluating a policy.
- Record simulator version, source data identifier, preprocessing, random seeds, and all reward terms.
- Keep training, tuning, and final evaluation periods separate in time.
- Report results across independent seeds and market regimes, including failed runs.
- For event-risk work, compare calibration to simple training-fold baselines before converting any forecast into a trading policy.
- Test sensitivity to spread, slippage, delays, capacity, missing data, and regime changes.
- Label simulation-only findings as exploratory; they are not empirical market results.

The [simulation and RL gym guide](simulation.md) explains the distinction between training a policy in a gym and evaluating a trading claim.
