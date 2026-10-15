---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: '0.13'
kernelspec:
  name: python3
  display_name: Python 3
  language: python
---

# Research Question: Can Trial and Literature History Clarify Catalyst Risk?

```{raw} html
<p class="castalia-kicker">INQUIRY 001 · BIOTECH EVENT STUDY · EXPLORATORY</p>
```

> **Hypothesis to test.** Before a public clinical-trial readout, point-in-time trial history, the biomedical evidence available at the time, issuer price/volume history, and market/sector context help characterize the distribution of near-term stock-price downside after the disclosure.

The target is **event-window risk**, not whether a treatment works and not a recommendation to buy or sell. Trial evidence can be informative about biological plausibility or uncertainty only through features that were actually public before the event; the model target remains the issuer's subsequent price-risk distribution. Scientific outcome and market reaction are separate outcomes: a positive trial result can still produce a negative stock response if expectations were already priced in. Compare simple historical estimates with regularized models, include matched non-event dates, and evaluate only with chronological splits.

## First pilot: event provenance, not model training

The original seed cohort recorded prominent COVID-19 vaccine Phase III readouts from 2020–2021. It has been supplemented with public Phase III disclosures covering Alzheimer’s disease, asthma, oncology, eosinophilic esophagitis, heart failure, chronic rhinosinusitis with nasal polyps, and Duchenne muscular dystrophy, including positive results and primary-endpoint misses. The expanded eighteen-disclosure set includes date-only timestamps, after-hours releases, joint-company announcements, and repeated issuers. Its purpose is to make trial-to-issuer mapping, source evidence, price-calendar matching, and feature cutoffs inspectable. It remains far too small and clustered for ML training or an investment claim.

```{code-cell} ipython3
event_dates = ["2020-11-09", "2020-11-16", "2020-11-23", "2021-01-28", "2021-01-29"]
event_issuers = ["Pfizer", "Moderna", "AstraZeneca", "Novavax", "Johnson & Johnson"]
event_types = ["Phase III interim readout", "Phase III interim readout", "Phase III interim readout", "Phase III readout", "Phase III interim readout"]
for date, issuer, event in zip(event_dates, event_issuers, event_types):
    print(date, "·", issuer, "·", event)
```

These are source-documented dates rather than timestamps inferred from trial completion. The Moderna, Pfizer, AstraZeneca, Novavax, and J&J source links and precision notes are in the [data guide](../data-sources.md) and `data/biopharma/public_events.csv`.

## Feature/label boundary

Candidate features across all modalities are frozen at the prior regular-session close, because the target includes overnight/event-gap price movement. They include trailing 5/20-session returns, realized volatility, relative volume where available, archived trial phase/enrollment/design descriptors, and dated literature evidence with separate eligibility roles (pre-event/primary/secondary) and evidence classes (preclinical/clinical/review). Biomedical measurements require an explicit endpoint, population, comparator, units, assay/species, and source version before aggregation; measurements from incompatible experimental systems must not be pooled. The initial pipeline does not infer efficacy or sentiment from paper titles, abstracts, or papers linked to a trial after its readout. The outcomes are realized price moves after disclosure, not post-event trial or literature metadata fed back into the feature set.

The first event-panel target is a descriptive two-session close-to-close return and a downside indicator of −10% or worse. The panel now also reports a two-factor market-model CAR using SPY/XBI returns estimated over sessions −230 through −31 (with a 30-session gap), with at least 120 complete observations. This CAR is an event-study outcome, not a pre-event feature. For outcome sensitivity, the evaluator can instead score `down_10pct_market_model_car_0_1`; it is not a second model feature set or a substitute for the raw issuer-loss target. A production study should move to timestamped intraday data and next-executable prices, include a matched biotech index and broad-market return, model corporate actions, and report continuous tail-loss metrics. The current two-session convention is a practical diagnostic for date-only or after-hours events, not an exact abnormal-return estimate.

## What would count against it?

The hypothesis is not supported if the feature model adds no stable calibration or ranking over a base-rate/event-volatility baseline, if its value disappears with a biotech-index control, if it depends on one issuer, indication, or pandemic cluster, or if event timestamps move the result materially. A model that predicts trial success poorly or misstates event dates is rejected even if its price fit looks attractive.

## Rival explanations

- Issuer volatility and market/sector regimes explain price gaps better than trial biology.
- Readouts were anticipated and repriced before the recorded press release.
- The selected public events are unusually salient and unrepresentative.
- Trial phase, outcome, and publication fields were revised after outcomes became known.
- Daily bars cannot resolve whether an announcement preceded or followed the market close.
- Survivorship, event selection, overlapping events, and model search create a false apparent edge.

## Preregister before fitting

Freeze the company-to-security map, event inclusion rules, source hierarchy, feature availability dates, sector benchmark, price vendor and adjustment policy, sample years, split dates, target window, missing-data rules, and variants to be compared. Preserve an untouched final time block. The present eighteen-disclosure source cohort has no final evaluation set; it is a pipeline fixture only.

## Gated first model

The precise, versioned estimand, data eligibility, features, split geometry, baselines, and score gates are frozen in the [event-risk protocol](protocol.md) and its machine-readable [JSON source](../../config/biopharma_event_risk_protocol.json). Treat that protocol as binding; deviations require an explicit flag and are written into the run summary.

Once a broader panel exists, `scripts/evaluate_event_risk.py` compares the training-window downside base rate, volatility- and archived-phase-conditioned historical rates, and a fixed regularized logistic model. Conditional rates are shrunk toward each fold's base rate; imputers and scalers are fit inside each chronological training fold. Brier score and log loss measure probability quality; `calibration.csv` reports five fixed-width reliability bins for development walk-forward predictions only. Paired issuer × calendar-quarter pigeonhole bootstrap intervals summarize score improvement over each baseline and are withheld unless at least ten clusters exist on both dimensions. Sparse issuer-quarter crossings can also withhold intervals. These descriptive intervals condition on fixed OOS predictions and do not model serial dependence across quarters. ROC AUC is included only when a test fold contains both outcome classes. The latest 20% of distinct event dates is reserved and never scored by this development command. Defaults require at least 30 training and 8 test events per fold; the eighteen-disclosure seed cohort fails the gate. The fixed feature list uses prior issuer, SPY/XBI, volume, archived trial phase/enrollment/design counts, evidence-class-stratified counts of eligible point-in-time research records, and explicitly curated numeric research measurements where available. It omits current registry hindsight columns and unstructured literature text. The research count measures this project's dated evidence ledger, not the completeness or quality of all biomedical literature.
