# Charter of Quantitative Inquiry

```{raw} html
<p class="castalia-kicker">THE LABORATORY'S COVENANT</p>
```

A backtest is a claim about evidence. It is not a promise about the future. Every QuantLab experiment follows these articles before it may be described as a result.

## Article I — The question precedes the model

Write one narrow hypothesis before inspecting the final holdout. Name the target, horizon, universe, and the observation that would count against the claim. A question that cannot lose is not yet researchable.

## Article II — Time is part of the data

Features must be available at the stated decision time. A signal observed at close *t* may first affect a position held during *t + 1*. Training, validation, and final evaluation follow chronology. The final holdout remains untouched during model selection.

## Article III — A baseline is a necessary interlocutor

Compare a proposed model with buy-and-hold, cash, and a simple rule suited to the question. Include turnover, fees, spread, slippage, and execution delay. A strategy that does not survive these comparisons has not established incremental value.

## Article IV — Preserve the failed path

Record rejected hypotheses, failed runs, data revisions, and changed assumptions. Do not erase a result because it complicates the story. A research ledger should make it possible for another investigator to reconstruct what happened.

## Article V — Challenge is a form of care

Invite review from more than one discipline. Ask the statistician about selection bias, the engineer about timing and failure modes, the economist about mechanisms, and the skeptic about what would falsify the account. Automated critique can suggest questions; it cannot certify the result.

## Article VI — Conclusions carry their limits

Use explicit evidence labels:

- **Exploratory:** a question or method is being investigated.
- **Not supported:** the stated test did not support the hypothesis.
- **Replicated:** the result was reproduced under the recorded procedure.
- **Robust under stated assumptions:** it survived the documented sensitivity checks; this does not guarantee future performance.

A finding earns only the strongest label its evidence warrants. No backtest grants permission to risk capital.
