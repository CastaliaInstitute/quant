# Quant. Research Portfolio · Castalia Institute

```{raw} html
<p class="castalia-kicker">CASTALIA INSTITUTE · QUANTITATIVE INQUIRY</p>
```

## A system to make your own

Quant. is an open system for building quantitative research applications. Its first research domain is biotech and pharma, where clinical-trial design, biomedical publications, disclosure timing, and stock-price gaps meet. Start with its reproducibility conventions, then tune or fork the question, trial universe, event sources, market data, features, model, costs, and risk limits. Its Castalian character is a method of inquiry: make a claim, say what could disprove it, invite challenge, and preserve the record.

This site is also a work-in-progress portfolio for quantitative research and research-engineering roles. It connects my PhD background in computational biology to event ontologies, trial endpoints, published biomedical evidence, and finance-specific measurement. Start at the [portfolio](portfolio.md) to see the current artifacts, the historical-data pilot, and what evidence is still missing.

```{raw} html
<p class="castalia-motto">No signal speaks without its evidence. No result stands without challenge.</p>
```

This book is both a working research record and a map of the system's extension points. Its cells execute on a Cloudflare Python Worker using a deliberately limited teaching runtime. Cells are not connected to market feeds, accounts, or brokerages. The included observations are synthetic unless a page explicitly identifies and versions an external dataset. Fork the repository to build a full research application; do not mistake the public cell runner for a general Jupyter kernel.

```{admonition} Read the status before the result
:class: caution
The platform is a research prototype. A successful calculation demonstrates only that the calculation ran on its stated inputs; it does not establish a durable market edge or predict future returns. Live trading is disabled.
```

## The inquiry, in order

1. [Charter of inquiry](charter.md): standards every experiment must meet.
2. [Quant research portfolio](portfolio.md): implemented artifacts, current evidence, and the path toward historical research.
3. [MagAI (Quant) program](program.md): a planned learning pathway using and extending this research system.
4. [Biopharma data sources](data-sources.md): trial records, papers, issuer disclosures, and licensed market data with lineage.
5. [The first research question](research/question.md): a falsifiable biotech event-risk hypothesis and rival explanations.
6. [Measurement](research/measurement.md): features, time cutoffs, and biological-market source quality.
7. [Baselines](research/baselines.md): compare event-risk forecasts with simple reference estimates.
8. [Return metrics](research/metrics.md): the net performance and tail-risk scorecards.
9. [Evidence review](research/evidence-review.md): published clinical-transition and market-response evidence, and how each may shape the simulator.
10. [AI impact watch](research/ai-impact.md): distinguish AI claims from measured effects in drug pipelines, trial operations, and company value.
11. [Simulation and RL study](research/rl-study.md): a seeded biotech catalyst gym, Q-learning policy, and simulator-only result.
12. [Adversarial review](research/review.md): identify leakage, fragility, and reasons to reject the result.

## How to tune and fork Quant.

Begin with the [fork guide](forking.md). It identifies the system seams, gives a small configuration example, and outlines a reproducible path from a question to a published result. The project is a foundation, not a single prescribed strategy: forks should make their own assumptions explicit while retaining the evidence trail.

## How to work with a cell

Use **Run all live cells** to execute the page in order, or run a single cell. Each request resubmits that page’s visible code cells to a stateless Worker, so earlier variables are reconstructed for each run. The runtime supports basic Python arithmetic, lists, loops, and a small set of quantitative helpers. It does not support imports, network calls, filesystem access, arbitrary functions, or brokerage operations.
